from typing import Optional, Literal
from pydantic import BaseModel, Field

class GitHubUser(BaseModel):
    id: int
    login: str
    avatar_url: Optional[str] = None
    email: Optional[str] = None

class GitHubRepository(BaseModel):
    id: int
    name: str
    full_name: str
    owner: GitHubUser
    default_branch: str

class GitHubPullRequest(BaseModel):
    id: int
    number: int
    title: str
    state: str
    body: Optional[str] = None
    user: GitHubUser
    head: dict
    base: dict

class Installation(BaseModel):
    id: int

class WebhookPayload(BaseModel):
    action: str
    pull_request: Optional[GitHubPullRequest] = None
    repository: GitHubRepository
    installation: Optional[Installation] = None
