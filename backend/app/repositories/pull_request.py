import uuid
from typing import Optional, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.pull_request import PullRequest
from app.schemas.pull_request import PullRequestCreate, PullRequestUpdate
from app.repositories.base import BaseRepository


class PullRequestRepository(BaseRepository[PullRequest, PullRequestCreate, PullRequestUpdate]):
    async def get_by_github_number(
        self, db: AsyncSession, *, repository_id: uuid.UUID, github_pr_number: int
    ) -> Optional[PullRequest]:
        stmt = select(self.model).where(
            self.model.repository_id == repository_id,
            self.model.github_pr_number == github_pr_number
        )
        result = await db.execute(stmt)
        return result.scalars().first()

    async def get_by_repository(
        self, db: AsyncSession, *, repository_id: uuid.UUID, skip: int = 0, limit: int = 100
    ) -> List[PullRequest]:
        stmt = select(self.model).where(
            self.model.repository_id == repository_id
        ).offset(skip).limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all())


pull_request = PullRequestRepository(PullRequest)
