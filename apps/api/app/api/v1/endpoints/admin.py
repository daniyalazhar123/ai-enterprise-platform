from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.auth.deps import get_current_user, get_valid_session, require_permission
from apps.api.app.auth.service.authorization import assign_roles, get_user_permissions, get_user_roles
from apps.api.app.db.session import get_session as get_db
from apps.api.app.models.role import Role
from apps.api.app.models.session import Session as SessionModel
from apps.api.app.models.user import User
from apps.api.app.schemas.models import UserProfileResponse

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


@router.get("/users", response_model=list[UserProfileResponse])
async def list_users(
    user: User = Depends(get_current_user),
    session: SessionModel = Depends(get_valid_session),
    perm: None = Depends(require_permission("users", "read")),
    db: AsyncSession = Depends(get_db),
) -> list[UserProfileResponse]:
    result = await db.execute(select(User).where(User.deleted_at.is_(None)))
    users = result.scalars().all()
    result_list = []
    for u in users:
        roles = await get_user_roles(u.id, db)
        result_list.append(
            UserProfileResponse(
                id=u.id,
                email=u.email,
                display_name=u.display_name,
                avatar_url=u.avatar_url,
                is_verified=u.is_verified,
                locale=u.locale,
                roles=roles,
                created_at=u.created_at,
            )
        )
    return result_list


@router.get("/users/{user_id}", response_model=UserProfileResponse)
async def get_user(
    user_id: UUID,
    user: User = Depends(get_current_user),
    session: SessionModel = Depends(get_valid_session),
    perm: None = Depends(require_permission("users", "read")),
    db: AsyncSession = Depends(get_db),
) -> UserProfileResponse:
    from apps.api.app.core.exceptions import NotFoundError

    result = await db.execute(select(User).where(User.id == user_id, User.deleted_at.is_(None)))
    target = result.scalar_one_or_none()
    if target is None:
        raise NotFoundError("User not found")

    roles = await get_user_roles(target.id, db)
    return UserProfileResponse(
        id=target.id,
        email=target.email,
        display_name=target.display_name,
        avatar_url=target.avatar_url,
        is_verified=target.is_verified,
        locale=target.locale,
        roles=roles,
        created_at=target.created_at,
    )


@router.post("/users/{user_id}/roles")
async def assign_user_roles(
    user_id: UUID,
    role_ids: list[UUID],
    user: User = Depends(get_current_user),
    session: SessionModel = Depends(get_valid_session),
    perm: None = Depends(require_permission("users", "write")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    for rid in role_ids:
        result = await db.execute(select(Role).where(Role.id == rid))
        if not result.scalar_one_or_none():
            from apps.api.app.core.exceptions import NotFoundError
            raise NotFoundError(f"Role {rid} not found")

    await assign_roles(user_id, role_ids, db)

    from apps.api.app.core.cache import invalidate_cache
    await invalidate_cache(f"perms:{user_id}")
    await invalidate_cache(f"roles:{user_id}")

    return {"message": "Roles assigned successfully"}


@router.get("/roles")
async def list_roles(
    user: User = Depends(get_current_user),
    session: SessionModel = Depends(get_valid_session),
    perm: None = Depends(require_permission("roles", "read")),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    result = await db.execute(select(Role))
    roles = result.scalars().all()
    return [
        {
            "id": str(r.id),
            "name": r.name,
            "description": r.description,
            "is_system": r.is_system,
        }
        for r in roles
    ]