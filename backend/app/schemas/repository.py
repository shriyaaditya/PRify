import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class RepositoryBase(BaseModel):
    github_repo_id: str
    name: str
    full_name: str
    default_branch: str = "main"
    installation_id: Optional[str] = None


class RepositoryCreate(RepositoryBase):
    owner_id: uuid.UUID


class RepositoryUpdate(BaseModel):
    name: Optional[str] = None
    full_name: Optional[str] = None
    default_branch: Optional[str] = None
    installation_id: Optional[str] = None


class RepositoryResponse(RepositoryBase):
    id: uuid.UUID
    owner_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
