from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

class DocumentMetadata(BaseModel):
    repository: str
    document: str
    path: str
    document_type: str
    chunk_id: str
    checksum: Optional[str] = None
    section: Optional[str] = None

class DocumentChunk(BaseModel):
    id: str
    content: str
    metadata: DocumentMetadata

class RetrievedContext(BaseModel):
    content: str
    score: float
    metadata: DocumentMetadata
    source_path: str
