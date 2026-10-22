from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import CurrentUser, get_aut_service
from app.schemas.auth import LoginRequest, RefreshRequest, TokenResponse
from app.schemas.user import UserCreate, UserRead
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])

AuthServiceDep = Annotated[AuthService, Depends(get_aut_service)]


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(data: UserCreate, service: AuthServiceDep):
    return await service.register(data)


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, service: AuthServiceDep):
    return await service.login(data.email, data.password)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(data: RefreshRequest, service: AuthServiceDep):
    return await service.refresh(data.refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(data: RefreshRequest, service: AuthServiceDep):
    await service.logout(data.refresh_token)


@router.get("/me", response_model=UserRead)
async def me(current_user: CurrentUser):
    return current_user
