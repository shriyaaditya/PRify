import uuid
from typing import List, Dict, Any
from langchain_text_splitters import RecursiveCharacterTextSplitter, MarkdownTextSplitter

from app.rag.models import DocumentChunk, DocumentMetadata
from app.rag.loaders.repository_loader import DiscoveredDocument

class TextChunker:
    """
    Splits documents into semantically meaningful chunks while preserving headers.
    """
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        self.markdown_splitter = MarkdownTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap
        )
        
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap
        )

    def chunk_documents(self, repository: str, docs: List[DiscoveredDocument]) -> List[DocumentChunk]:
        """
        Takes a list of DiscoveredDocuments and returns a list of DocumentChunks.
        """
        chunks = []
        for doc in docs:
            # Decide splitter based on extension
            if doc.path.lower().endswith(".md") or doc.document_type in ("README", "CONTRIBUTING", "ARCHITECTURE"):
                splits = self.markdown_splitter.split_text(doc.content)
            else:
                splits = self.text_splitter.split_text(doc.content)

            for i, split_content in enumerate(splits):
                chunk_id = str(uuid.uuid4())
                
                # Attempt to extract a simple section name from markdown headers if present
                section = None
                lines = split_content.splitlines()
                for line in lines:
                    if line.startswith("#"):
                        section = line.lstrip("# ").strip()
                        break
                
                metadata = DocumentMetadata(
                    repository=repository,
                    document=doc.path.split("/")[-1],
                    path=doc.path,
                    document_type=doc.document_type,
                    chunk_id=chunk_id,
                    checksum=doc.checksum,
                    section=section
                )
                
                chunks.append(DocumentChunk(
                    id=chunk_id,
                    content=split_content,
                    metadata=metadata
                ))

        return chunks
