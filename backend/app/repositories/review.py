import uuid
from typing import Optional, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.review import Review, ReviewFinding, AgentRun
from app.schemas.review import (
    ReviewCreate, ReviewUpdate,
    ReviewFindingCreate, ReviewFindingUpdate,
    AgentRunCreate, AgentRunUpdate
)
from app.repositories.base import BaseRepository


class ReviewRepository(BaseRepository[Review, ReviewCreate, ReviewUpdate]):
    async def get_with_relations(self, db: AsyncSession, id: uuid.UUID) -> Optional[Review]:
        stmt = select(self.model).where(self.model.id == id).options(
            selectinload(self.model.findings),
            selectinload(self.model.agent_runs)
        )
        result = await db.execute(stmt)
        return result.scalars().first()

    async def get_by_pull_request(
        self, db: AsyncSession, *, pull_request_id: uuid.UUID, skip: int = 0, limit: int = 100
    ) -> List[Review]:
        stmt = select(self.model).where(
            self.model.pull_request_id == pull_request_id
        ).offset(skip).limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all())


class ReviewFindingRepository(BaseRepository[ReviewFinding, ReviewFindingCreate, ReviewFindingUpdate]):
    async def get_by_review(
        self, db: AsyncSession, *, review_id: uuid.UUID
    ) -> List[ReviewFinding]:
        stmt = select(self.model).where(self.model.review_id == review_id)
        result = await db.execute(stmt)
        return list(result.scalars().all())


class AgentRunRepository(BaseRepository[AgentRun, AgentRunCreate, AgentRunUpdate]):
    async def get_by_review(
        self, db: AsyncSession, *, review_id: uuid.UUID
    ) -> List[AgentRun]:
        stmt = select(self.model).where(self.model.review_id == review_id)
        result = await db.execute(stmt)
        return list(result.scalars().all())


review = ReviewRepository(Review)
review_finding = ReviewFindingRepository(ReviewFinding)
agent_run = AgentRunRepository(AgentRun)
