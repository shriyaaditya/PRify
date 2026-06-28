import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, ForeignKey, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base
from app.models.enums import DocumentType


class IndexedDocument(Base):
    __tablename__ = "indexed_documents"

    repository_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False
    )
    document_name: Mapped[str] = mapped_column(String)
    document_type: Mapped[DocumentType] = mapped_column(Enum(DocumentType, name="document_type"))
    qdrant_point_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    checksum: Mapped[str] = mapped_column(String)
    
    indexed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    repository: Mapped["Repository"] = relationship("Repository", back_populates="indexed_documents")
