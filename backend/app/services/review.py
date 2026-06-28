import uuid
from typing import Optional, List

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.review import Review, ReviewFinding, AgentRun
from app.schemas.review import (
    ReviewCreate, ReviewUpdate,
    ReviewFindingCreate, ReviewFindingUpdate,
    AgentRunCreate, AgentRunUpdate
)
from app.repositories import review as review_repo


class ReviewService:
    async def get_review(self, db: AsyncSession, review_id: uuid.UUID) -> Optional[Review]:
        return await review_repo.review.get_with_relations(db, id=review_id)

    async def get_by_pull_request(
        self, db: AsyncSession, pull_request_id: uuid.UUID, skip: int = 0, limit: int = 100
    ) -> List[Review]:
        return await review_repo.review.get_by_pull_request(
            db, pull_request_id=pull_request_id, skip=skip, limit=limit
        )

    async def create_review(self, db: AsyncSession, review_in: ReviewCreate) -> Review:
        return await review_repo.review.create(db, obj_in=review_in)

    async def update_review(
        self, db: AsyncSession, db_review: Review, review_in: ReviewUpdate
    ) -> Review:
        return await review_repo.review.update(db, db_obj=db_review, obj_in=review_in)

    # --- Review Findings ---
    async def get_findings(self, db: AsyncSession, review_id: uuid.UUID) -> List[ReviewFinding]:
        return await review_repo.review_finding.get_by_review(db, review_id=review_id)

    async def create_finding(
        self, db: AsyncSession, finding_in: ReviewFindingCreate
    ) -> ReviewFinding:
        return await review_repo.review_finding.create(db, obj_in=finding_in)

    # --- Agent Runs ---
    async def get_agent_runs(self, db: AsyncSession, review_id: uuid.UUID) -> List[AgentRun]:
        return await review_repo.agent_run.get_by_review(db, review_id=review_id)

    async def create_agent_run(
        self, db: AsyncSession, agent_run_in: AgentRunCreate
    ) -> AgentRun:
        return await review_repo.agent_run.create(db, obj_in=agent_run_in)

    async def update_agent_run(
        self, db: AsyncSession, db_agent_run: AgentRun, agent_run_in: AgentRunUpdate
    ) -> AgentRun:
        return await review_repo.agent_run.update(db, db_obj=db_agent_run, obj_in=agent_run_in)


review_service = ReviewService()
