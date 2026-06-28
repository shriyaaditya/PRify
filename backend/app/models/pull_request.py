import uuid
from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy import String, DateTime, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class PullRequest(Base):
    __tablename__ = "pull_requests"

    github_pr_number: Mapped[int] = mapped_column(Integer, index=True)
    title: Mapped[str] = mapped_column(String)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    branch: Mapped[str] = mapped_column(String)
    base_branch: Mapped[str] = mapped_column(String)
    state: Mapped[str] = mapped_column(String, default="open")
    
    repository_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    repository: Mapped["Repository"] = relationship("Repository", back_populates="pull_requests")
    reviews: Mapped[List["Review"]] = relationship(
        "Review", back_populates="pull_request", cascade="all, delete-orphan"
    )
