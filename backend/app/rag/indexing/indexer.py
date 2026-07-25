import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.github.client import GitHubClient
from app.models.document import IndexedDocument
from app.models.enums import DocumentType
from app.rag.chunking.text_chunker import TextChunker
from app.rag.embeddings.embedding_service import EmbeddingService
from app.rag.loaders.repository_loader import RepositoryLoader
from app.rag.vectorstore.qdrant_client import qdrant_store

logger = logging.getLogger(__name__)


class Indexer:
    """
    Orchestrates the entire repository indexing pipeline.
    """

    def __init__(self, gh_client: GitHubClient, session: AsyncSession):
        self.gh_client = gh_client
        self.session = session

        self.chunker = TextChunker()
        self.embedder = EmbeddingService()
        self.vectorstore = qdrant_store

    async def index_repository(
        self,
        repository_id: uuid.UUID,
        repo_fullname: str,
        branch: str = "main",
        collection_name: str = "repository_docs",
    ):
        """
        Indexes the repository documentation, skipping unchanged documents.
        """
        await self.vectorstore.ensure_collection(collection_name=collection_name)

        loader = RepositoryLoader(
            gh_client=self.gh_client, repo_fullname=repo_fullname, branch=branch
        )
        discovered_docs = await loader.discover_documents()

        if not discovered_docs:
            logger.info(f"No indexable documents found for {repo_fullname}.")
            return

        # Load existing index records for this repo
        result = await self.session.execute(
            select(IndexedDocument).where(
                IndexedDocument.repository_id == repository_id
            )
        )
        existing_records = result.scalars().all()
        existing_checksums = {
            doc.document_name: doc.checksum for doc in existing_records
        }
        existing_docs_dict = {doc.document_name: doc for doc in existing_records}

        docs_to_index = []
        for doc in discovered_docs:
            if doc.path in existing_checksums:
                if existing_checksums[doc.path] == doc.checksum:
                    # Unchanged, skip indexing
                    continue
                else:
                    # Document changed, remove old chunks from Qdrant
                    await self.vectorstore.delete_document_chunks(
                        collection_name=collection_name,
                        repository=repo_fullname,
                        document_name=doc.path.split("/")[-1],
                    )

            docs_to_index.append(doc)

        if not docs_to_index:
            logger.info(f"All documents are up-to-date for {repo_fullname}.")
            return

        logger.info(f"Indexing {len(docs_to_index)} documents for {repo_fullname}...")

        # Process and embed
        chunks = self.chunker.chunk_documents(
            repository=repo_fullname, docs=docs_to_index
        )

        if not chunks:
            logger.info("No chunks generated.")
            return

        texts = [chunk.content for chunk in chunks]

        try:
            vectors = await self.embedder.aembed_documents(texts)

            # Upsert to Qdrant
            await self.vectorstore.upsert_chunks(
                collection_name=collection_name, chunks=chunks, vectors=vectors
            )

            # Update PostgreSQL state
            for doc in docs_to_index:
                if doc.path in existing_docs_dict:
                    existing_doc = existing_docs_dict[doc.path]
                    existing_doc.checksum = doc.checksum
                else:
                    new_indexed_doc = IndexedDocument(
                        repository_id=repository_id,
                        document_name=doc.path,
                        document_type=DocumentType(doc.document_type),
                        qdrant_point_id=str(
                            uuid.uuid4()
                        ),  # We generate a UUID for the record, though chunks have their own IDs
                        checksum=doc.checksum,
                    )
                    self.session.add(new_indexed_doc)

            await self.session.commit()
            logger.info(
                f"Successfully indexed {len(docs_to_index)} documents for {repo_fullname}."
            )

        except Exception as e:
            logger.error(f"Failed to generate embeddings or index documents: {str(e)}")
            await self.session.rollback()
