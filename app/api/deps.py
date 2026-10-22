import uuid
from typing import Annotated

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenError, NotAuthenticatedError
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models import User
from app.repositories.user import UserRepository
from app.services.admin import AdminService
from app.services.auth import AuthService

# built-in security tool help to extract token from request
bearer_scheme = HTTPBearer(auto_error=False)

# create alias, so no need to write AsyncSession/Depends(get_db)whenever we need db
DbSession = Annotated[AsyncSession, Depends(get_db)]


def get_aut_service(db: DbSession) -> AuthService:
    return AuthService(db)


def get_admin_service(db: DbSession) -> AdminService:
    return AdminService(db)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: DbSession,
) -> User:
    # if user not sent authorization header/token along with request
    if credentials is None:
        raise NotAuthenticatedError()

    try:
        # credentials.credentials only extract token string
        # decode_access_token checks if token is invalid or expired
        payload = decode_access_token(credentials.credentials)
        user_id = uuid.UUID(payload["sub"])
    # if token invalid, this block will run.
    except (jwt.InvalidTokenError, ValueError):
        raise NotAuthenticatedError("Invalid or expired token") from None

    # find current loggedin user from db and check status
    user = await UserRepository(db).get_by_id(user_id)
    if user is None or not user.is_active:
        raise NotAuthenticatedError()

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_role(*roles: str):
    async def checker(current_user: CurrentUser) -> User:
        if current_user.role not in roles:
            raise ForbiddenError()

        return current_user

    return checker


AdminUser = Annotated[User, Depends(require_role("admin"))]
