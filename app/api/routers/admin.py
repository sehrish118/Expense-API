import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import AdminUser, get_admin_service
from app.schemas.user import UserRead
from app.services.admin import AdminService

router = APIRouter(prefix="/admin", tags=["admin"])

AdminServiceDep = Annotated[AdminService, Depends(get_admin_service)]


@router.get("/users", response_model=list[UserRead])
async def list_users(
    admin: AdminUser,
    service: AdminServiceDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    return await service.list_users(limit, offset)


@router.patch("/users/{user_id}/deactivate", response_model=UserRead)
async def deactivate_user(user_id: uuid.UUID, admin: AdminUser, service: AdminServiceDep):
    return await service.deactivate_user(user_id, admin)


@router.patch("/users/{user_id}/activate", response_model=UserRead)
async def activate_user(user_id: uuid.UUID, admin: AdminUser, service: AdminServiceDep):
    return await service.activate_user(user_id, admin)
