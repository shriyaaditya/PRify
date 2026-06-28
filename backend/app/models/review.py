import uuid
from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy import String, DateTime, ForeignKey, Integer, Float, Text, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base
from app.models.enums import ReviewStatus, Severity, AgentStatus


class Review(Base):
    __tablename__ = "reviews"

    pull_request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pull_requests.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[ReviewStatus] = mapped_column(
        Enum(ReviewStatus, name="review_status"), default=ReviewStatus.PENDING
    )
    overall_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    overall_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    execution_time_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    pull_request: Mapped["PullRequest"] = relationship("PullRequest", back_populates="reviews")
    findings: Mapped[List["ReviewFinding"]] = relationship(
        "ReviewFinding", back_populates="review", cascade="all, delete-orphan"
    )
    agent_runs: Mapped[List["AgentRun"]] = relationship(
        "AgentRun", back_populates="review", cascade="all, delete-orphan"
    )


class ReviewFinding(Base):
    __tablename__ = "review_findings"

    review_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("reviews.id", ondelete="CASCADE"), nullable=False
    )
    agent_name: Mapped[str] = mapped_column(String)
    title: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(Text)
    severity: Mapped[Severity] = mapped_column(Enum(Severity, name="severity_level"))
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    file_path: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    line_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    recommendation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    review: Mapped["Review"] = relationship("Review", back_populates="findings")


class AgentRun(Base):
    __tablename__ = "agent_runs"

    review_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("reviews.id", ondelete="CASCADE"), nullable=False
    )
    agent_name: Mapped[str] = mapped_column(String)
    status: Mapped[AgentStatus] = mapped_column(
        Enum(AgentStatus, name="agent_status"), default=AgentStatus.PENDING
    )
    execution_time_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    tokens_used: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    model_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    review: Mapped["Review"] = relationship("Review", back_populates="agent_runs")
