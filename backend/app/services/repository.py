import uuid
from typing import Optional, List

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.repository import Repository
from app.schemas.repository import RepositoryCreate, RepositoryUpdate
from app.repositories import repository as repo_module


class RepositoryService:
    async def get_repository(self, db: AsyncSession, repo_id: uuid.UUID) -> Optional[Repository]:
        return await repo_module.repository.get(db, id=repo_id)

    async def get_by_github_repo_id(self, db: AsyncSession, github_repo_id: str) -> Optional[Repository]:
        return await repo_module.repository.get_by_github_repo_id(db, github_repo_id=github_repo_id)

    async def get_by_owner(self, db: AsyncSession, owner_id: uuid.UUID) -> List[Repository]:
        return await repo_module.repository.get_by_owner(db, owner_id=owner_id)

    async def create_repository(self, db: AsyncSession, repo_in: RepositoryCreate) -> Repository:
        return await repo_module.repository.create(db, obj_in=repo_in)

    async def update_repository(
        self, db: AsyncSession, db_repo: Repository, repo_in: RepositoryUpdate
    ) -> Repository:
        return await repo_module.repository.update(db, db_obj=db_repo, obj_in=repo_in)


repository_service = RepositoryService()
