import uuid
from typing import Optional, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.repository import Repository
from app.schemas.repository import RepositoryCreate, RepositoryUpdate
from app.repositories.base import BaseRepository


class RepositoryRepository(BaseRepository[Repository, RepositoryCreate, RepositoryUpdate]):
    async def get_by_github_repo_id(self, db: AsyncSession, *, github_repo_id: str) -> Optional[Repository]:
        stmt = select(self.model).where(self.model.github_repo_id == github_repo_id)
        result = await db.execute(stmt)
        return result.scalars().first()

    async def get_by_full_name(self, db: AsyncSession, *, full_name: str) -> Optional[Repository]:
        stmt = select(self.model).where(self.model.full_name == full_name)
        result = await db.execute(stmt)
        return result.scalars().first()
        
    async def get_by_owner(self, db: AsyncSession, *, owner_id: uuid.UUID) -> List[Repository]:
        stmt = select(self.model).where(self.model.owner_id == owner_id)
        result = await db.execute(stmt)
        return list(result.scalars().all())


repository = RepositoryRepository(Repository)
