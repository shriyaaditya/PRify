import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, HttpUrl, Field


class UserBase(BaseModel):
    github_id: str
    username: str
    email: Optional[EmailStr] = None
    avatar_url: Optional[HttpUrl] = None


class UserCreate(UserBase):
    pass


class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    avatar_url: Optional[HttpUrl] = None


class UserResponse(UserBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
