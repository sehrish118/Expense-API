import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    CannotactivateSelfError,
    CannotDeactivateSelfError,
    UserNotFoundError,
)
from app.models import User
from app.repositories.refresh_token import RefreshTokenRepository
from app.repositories.user import UserRepository


class AdminService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.user = UserRepository(session)
        self.refresh_tokens = RefreshTokenRepository(session)

    async def list_users(self, limit: int, offset: int) -> list[User]:
        return await self.user.get_all(limit, offset)

    async def deactivate_user(self, user_id: uuid.UUID, acting_admin: User) -> User:
        if user_id == acting_admin.id:
            raise CannotDeactivateSelfError()

        user = await self.user.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError()

        user.is_active = False

        await self.refresh_tokens.revoke_all_for_user(user.id)
        await self.session.commit()
        return user

    async def activate_user(self, user_id: uuid.UUID, acting_admin: User) -> User:
        if user_id == acting_admin.id:
            raise CannotactivateSelfError()

        user = await self.user.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError()

        user.is_active = True

        # await self.refresh_tokens.revoke_all_for_user(user.id)
        await self.session.commit()
        return user
