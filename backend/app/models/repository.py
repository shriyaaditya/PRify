import uuid
from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy import String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class Repository(Base):
    __tablename__ = "repositories"

    github_repo_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String)
    full_name: Mapped[str] = mapped_column(String, unique=True, index=True)
    default_branch: Mapped[str] = mapped_column(String, default="main")
    installation_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    owner_user: Mapped["User"] = relationship("User", back_populates="repositories")
    pull_requests: Mapped[List["PullRequest"]] = relationship(
        "PullRequest", back_populates="repository", cascade="all, delete-orphan"
    )
    indexed_documents: Mapped[List["IndexedDocument"]] = relationship(
        "IndexedDocument", back_populates="repository", cascade="all, delete-orphan"
    )
