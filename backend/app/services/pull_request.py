import uuid
from typing import Optional, List

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.pull_request import PullRequest
from app.schemas.pull_request import PullRequestCreate, PullRequestUpdate
from app.repositories import pull_request as pr_repo


class PullRequestService:
    async def get_pull_request(self, db: AsyncSession, pr_id: uuid.UUID) -> Optional[PullRequest]:
        return await pr_repo.pull_request.get(db, id=pr_id)

    async def get_by_github_number(
        self, db: AsyncSession, repository_id: uuid.UUID, github_pr_number: int
    ) -> Optional[PullRequest]:
        return await pr_repo.pull_request.get_by_github_number(
            db, repository_id=repository_id, github_pr_number=github_pr_number
        )

    async def get_by_repository(
        self, db: AsyncSession, repository_id: uuid.UUID, skip: int = 0, limit: int = 100
    ) -> List[PullRequest]:
        return await pr_repo.pull_request.get_by_repository(
            db, repository_id=repository_id, skip=skip, limit=limit
        )

    async def create_pull_request(self, db: AsyncSession, pr_in: PullRequestCreate) -> PullRequest:
        return await pr_repo.pull_request.create(db, obj_in=pr_in)

    async def update_pull_request(
        self, db: AsyncSession, db_pr: PullRequest, pr_in: PullRequestUpdate
    ) -> PullRequest:
        return await pr_repo.pull_request.update(db, db_obj=db_pr, obj_in=pr_in)


pull_request_service = PullRequestService()
