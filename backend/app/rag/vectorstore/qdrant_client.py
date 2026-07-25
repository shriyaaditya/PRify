import logging
import uuid
from typing import List, Dict, Any, Optional
from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models as qmodels

from app.rag.models import DocumentChunk, RetrievedContext, DocumentMetadata

logger = logging.getLogger(__name__)

class QdrantVectorStore:
    """
    Service wrapper around Qdrant database.
    """
    def __init__(self, path: str = "./qdrant_storage"):
        # Local persistent storage for Qdrant
        self.client = AsyncQdrantClient(path=path)

    async def ensure_collection(self, collection_name: str, vector_size: int = 1536):
        """
        Creates the Qdrant collection if it does not already exist.
        Defaults to 1536 which is the size for text-embedding-3-small and text-embedding-ada-002.
        """
        collections_response = await self.client.get_collections()
        exists = any(c.name == collection_name for c in collections_response.collections)
        if not exists:
            logger.info(f"Creating Qdrant collection: {collection_name}")
            await self.client.create_collection(
                collection_name=collection_name,
                vectors_config=qmodels.VectorParams(
                    size=vector_size,
                    distance=qmodels.Distance.COSINE
                )
            )
            # Create payload indexes for faster filtering
            await self.client.create_payload_index(
                collection_name=collection_name,
                field_name="repository",
                field_schema=qmodels.PayloadSchemaType.KEYWORD,
            )
            await self.client.create_payload_index(
                collection_name=collection_name,
                field_name="document",
                field_schema=qmodels.PayloadSchemaType.KEYWORD,
            )

    async def upsert_chunks(self, collection_name: str, chunks: List[DocumentChunk], vectors: List[List[float]]):
        """
        Upserts document chunks and their vectors into the collection.
        """
        if not chunks or not vectors:
            return

        points = []
        for chunk, vector in zip(chunks, vectors):
            points.append(
                qmodels.PointStruct(
                    id=chunk.id,
                    vector=vector,
                    payload={
                        "content": chunk.content,
                        "metadata": chunk.metadata.model_dump()
                    }
                )
            )

        await self.client.upsert(
            collection_name=collection_name,
            points=points
        )

    async def delete_document_chunks(self, collection_name: str, repository: str, document_name: str):
        """
        Deletes all chunks associated with a specific document in a repository.
        """
        await self.client.delete(
            collection_name=collection_name,
            points_selector=qmodels.FilterSelector(
                filter=qmodels.Filter(
                    must=[
                        qmodels.FieldCondition(key="repository", match=qmodels.MatchValue(value=repository)),
                        qmodels.FieldCondition(key="document", match=qmodels.MatchValue(value=document_name)),
                    ]
                )
            )
        )

    async def search(
        self, collection_name: str, query_vector: List[float], repository: str, limit: int = 5
    ) -> List[RetrievedContext]:
        """
        Searches for semantically similar chunks within a specific repository.
        """
        search_result = await self.client.search(
            collection_name=collection_name,
            query_vector=query_vector,
            limit=limit,
            query_filter=qmodels.Filter(
                must=[
                    qmodels.FieldCondition(key="metadata.repository", match=qmodels.MatchValue(value=repository))
                ]
            )
        )

        results = []
        for scored_point in search_result:
            payload = scored_point.payload or {}
            meta_dict = payload.get("metadata", {})
            metadata = DocumentMetadata(**meta_dict)

            results.append(RetrievedContext(
                content=payload.get("content", ""),
                score=scored_point.score,
                metadata=metadata,
                source_path=metadata.path
            ))

        return results

qdrant_store = QdrantVectorStore()
