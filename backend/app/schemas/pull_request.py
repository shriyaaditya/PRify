import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class PullRequestBase(BaseModel):
    github_pr_number: int
    title: str
    description: Optional[str] = None
    branch: str
    base_branch: str
    state: str = "open"


class PullRequestCreate(PullRequestBase):
    repository_id: uuid.UUID


class PullRequestUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    branch: Optional[str] = None
    base_branch: Optional[str] = None
    state: Optional[str] = None


class PullRequestResponse(PullRequestBase):
    id: uuid.UUID
    repository_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
