import uuid
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.repositories import user as user_repo


class UserService:
    async def get_user(self, db: AsyncSession, user_id: uuid.UUID) -> Optional[User]:
        return await user_repo.user.get(db, id=user_id)

    async def get_user_by_github_id(self, db: AsyncSession, github_id: str) -> Optional[User]:
        return await user_repo.user.get_by_github_id(db, github_id=github_id)

    async def create_user(self, db: AsyncSession, user_in: UserCreate) -> User:
        return await user_repo.user.create(db, obj_in=user_in)

    async def update_user(self, db: AsyncSession, db_user: User, user_in: UserUpdate) -> User:
        return await user_repo.user.update(db, db_obj=db_user, obj_in=user_in)


user_service = UserService()
