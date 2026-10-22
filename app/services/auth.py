import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import (
    EmailAlreadyRegisteredError,
    InactiveUserError,
    InvalidCredentialsError,
    InvalidRefreshTokenError,
)
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.models import User
from app.repositories.refresh_token import RefreshTokenRepository
from app.repositories.user import UserRepository
from app.schemas.auth import TokenResponse
from app.schemas.user import UserCreate

_DUMMY_HASH = hash_password("dummy-password-for-timing")


class AuthService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.users = UserRepository(session)
        self.refresh_tokens = RefreshTokenRepository(session)

    async def _issue__tokens(self, user_id: uuid.UUID) -> TokenResponse:
        raw_refresh = generate_refresh_token()
        expires_at = datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days)
        await self.refresh_tokens.create(user_id, hash_refresh_token(raw_refresh), expires_at)
        return TokenResponse(
            access_token=create_access_token(str(user_id)),
            refresh_token=raw_refresh,
        )

    async def register(self, data: UserCreate) -> User:
        if await self.users.get_by_email(data.email):
            raise EmailAlreadyRegisteredError()

        try:
            user = await self.users.create(data.email, hash_password(data.password))
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            raise EmailAlreadyRegisteredError() from None

        return user

    async def login(self, email: str, password: str) -> TokenResponse:
        user = await self.users.get_by_email(email)
        if user is None:
            verify_password(password, _DUMMY_HASH)
            raise InvalidCredentialsError()

        if not verify_password(password, user.hashed_password):
            raise InvalidCredentialsError()

        if not user.is_active:
            raise InactiveUserError()

        tokens = await self._issue__tokens(user.id)
        await self.session.commit()
        return tokens

    async def refresh(self, raw_token: str) -> TokenResponse:
        stored = await self.refresh_tokens.get_by_hash(hash_refresh_token(raw_token))
        if stored is None:
            raise InvalidRefreshTokenError()

        if stored.revoked_at is not None:
            await self.refresh_tokens.revoke_all_for_user(stored.user_id)
            await self.session.commit()
            raise InvalidRefreshTokenError()

        if stored.expires_at <= datetime.now(UTC):
            raise InvalidRefreshTokenError()

        user = await self.users.get_by_id(stored.user_id)
        if user is None or not user.is_active:
            raise InvalidRefreshTokenError()

        await self.refresh_tokens.revoke(stored)
        tokens = await self._issue__tokens(user.id)
        await self.session.commit()
        return tokens

    async def logout(self, raw_token: str) -> None:
        stored = await self.refresh_tokens.get_by_hash(hash_refresh_token(raw_token))
        if stored is not None and stored.revoked_at is None:
            await self.refresh_tokens.revoke(stored)
            await self.session.commit()
