import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.models.enums import DocumentType


class IndexedDocumentBase(BaseModel):
    document_name: str
    document_type: DocumentType
    qdrant_point_id: str
    checksum: str


class IndexedDocumentCreate(IndexedDocumentBase):
    repository_id: uuid.UUID


class IndexedDocumentUpdate(BaseModel):
    document_name: Optional[str] = None
    document_type: Optional[DocumentType] = None
    qdrant_point_id: Optional[str] = None
    checksum: Optional[str] = None


class IndexedDocumentResponse(IndexedDocumentBase):
    id: uuid.UUID
    repository_id: uuid.UUID
    indexed_at: datetime

    model_config = ConfigDict(from_attributes=True)
