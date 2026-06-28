import uuid
from typing import Optional, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import IndexedDocument
from app.schemas.document import IndexedDocumentCreate, IndexedDocumentUpdate
from app.repositories.base import BaseRepository


class IndexedDocumentRepository(BaseRepository[IndexedDocument, IndexedDocumentCreate, IndexedDocumentUpdate]):
    async def get_by_qdrant_point_id(
        self, db: AsyncSession, *, qdrant_point_id: str
    ) -> Optional[IndexedDocument]:
        stmt = select(self.model).where(self.model.qdrant_point_id == qdrant_point_id)
        result = await db.execute(stmt)
        return result.scalars().first()

    async def get_by_repository(
        self, db: AsyncSession, *, repository_id: uuid.UUID, skip: int = 0, limit: int = 100
    ) -> List[IndexedDocument]:
        stmt = select(self.model).where(
            self.model.repository_id == repository_id
        ).offset(skip).limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all())


document = IndexedDocumentRepository(IndexedDocument)
