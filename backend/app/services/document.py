import uuid
from typing import Optional, List

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import IndexedDocument
from app.schemas.document import IndexedDocumentCreate, IndexedDocumentUpdate
from app.repositories import document as doc_repo


class DocumentService:
    async def get_document(self, db: AsyncSession, doc_id: uuid.UUID) -> Optional[IndexedDocument]:
        return await doc_repo.document.get(db, id=doc_id)

    async def get_by_qdrant_point_id(
        self, db: AsyncSession, qdrant_point_id: str
    ) -> Optional[IndexedDocument]:
        return await doc_repo.document.get_by_qdrant_point_id(
            db, qdrant_point_id=qdrant_point_id
        )

    async def get_by_repository(
        self, db: AsyncSession, repository_id: uuid.UUID, skip: int = 0, limit: int = 100
    ) -> List[IndexedDocument]:
        return await doc_repo.document.get_by_repository(
            db, repository_id=repository_id, skip=skip, limit=limit
        )

    async def create_document(
        self, db: AsyncSession, doc_in: IndexedDocumentCreate
    ) -> IndexedDocument:
        return await doc_repo.document.create(db, obj_in=doc_in)

    async def update_document(
        self, db: AsyncSession, db_doc: IndexedDocument, doc_in: IndexedDocumentUpdate
    ) -> IndexedDocument:
        return await doc_repo.document.update(db, db_obj=db_doc, obj_in=doc_in)


document_service = DocumentService()
