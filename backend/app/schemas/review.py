import uuid
from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, ConfigDict

from app.models.enums import ReviewStatus, Severity, AgentStatus


# --- ReviewFinding Schemas ---
class ReviewFindingBase(BaseModel):
    agent_name: str
    title: str
    description: str
    severity: Severity
    confidence: Optional[float] = None
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    recommendation: Optional[str] = None


class ReviewFindingCreate(ReviewFindingBase):
    review_id: uuid.UUID


class ReviewFindingUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    severity: Optional[Severity] = None
    confidence: Optional[float] = None
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    recommendation: Optional[str] = None


class ReviewFindingResponse(ReviewFindingBase):
    id: uuid.UUID
    review_id: uuid.UUID

    model_config = ConfigDict(from_attributes=True)


# --- AgentRun Schemas ---
class AgentRunBase(BaseModel):
    agent_name: str
    status: AgentStatus = AgentStatus.PENDING
    execution_time_ms: Optional[int] = None
    tokens_used: Optional[int] = None
    model_name: Optional[str] = None


class AgentRunCreate(AgentRunBase):
    review_id: uuid.UUID


class AgentRunUpdate(BaseModel):
    status: Optional[AgentStatus] = None
    execution_time_ms: Optional[int] = None
    tokens_used: Optional[int] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class AgentRunResponse(AgentRunBase):
    id: uuid.UUID
    review_id: uuid.UUID
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# --- Review Schemas ---
class ReviewBase(BaseModel):
    status: ReviewStatus = ReviewStatus.PENDING
    overall_score: Optional[float] = None
    overall_summary: Optional[str] = None
    execution_time_ms: Optional[int] = None


class ReviewCreate(ReviewBase):
    pull_request_id: uuid.UUID


class ReviewUpdate(BaseModel):
    status: Optional[ReviewStatus] = None
    overall_score: Optional[float] = None
    overall_summary: Optional[str] = None
    execution_time_ms: Optional[int] = None


class ReviewResponse(ReviewBase):
    id: uuid.UUID
    pull_request_id: uuid.UUID
    created_at: datetime
    
    findings: List[ReviewFindingResponse] = []
    agent_runs: List[AgentRunResponse] = []

    model_config = ConfigDict(from_attributes=True)
