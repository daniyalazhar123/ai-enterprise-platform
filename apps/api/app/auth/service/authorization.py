from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.models.permission import Permission, RolePermissionLink
from apps.api.app.models.role import Role, UserRoleLink
from apps.api.app.models.user import User

_ACTION_HIERARCHY: dict[str, list[str]] = {
    "manage": ["manage", "create", "read", "update", "delete"],
    "write": ["write", "create", "read", "update"],
    "create": ["create", "read"],
    "read": ["read"],
    "update": ["update", "read"],
    "delete": ["delete"],
    "*": ["*", "create", "read", "update", "delete", "manage"],
}


def _expand_action(action: str) -> list[str]:
    return _ACTION_HIERARCHY.get(action, [action])


def _match_resource(resource: str, pattern: str) -> bool:
    if pattern == "*":
        return True
    if pattern.endswith(":*"):
        prefix = pattern[:-2]
        return resource.startswith(prefix)
    return resource == pattern


async def get_user_permissions(user_id: UUID, db: AsyncSession) -> list[str]:
    result = await db.execute(
        select(Permission.resource, Permission.action)
        .select_from(UserRoleLink)
        .join(Role, Role.id == UserRoleLink.role_id)
        .join(RolePermissionLink, RolePermissionLink.role_id == Role.id)
        .join(Permission, Permission.id == RolePermissionLink.permission_id)
        .where(UserRoleLink.user_id == user_id)
    )
    return [f"{row.resource}:{row.action}" for row in result.all()]


async def get_user_roles(user_id: UUID, db: AsyncSession) -> list[str]:
    result = await db.execute(
        select(Role.name)
        .select_from(UserRoleLink)
        .join(Role, Role.id == UserRoleLink.role_id)
        .where(UserRoleLink.user_id == user_id)
    )
    return [row[0] for row in result.all()]


async def check_permission(
    user: User,
    required_resource: str,
    required_action: str,
    db: AsyncSession,
) -> bool:
    if user.is_superuser:
        return True

    result = await db.execute(
        select(Permission.resource, Permission.action)
        .select_from(UserRoleLink)
        .join(Role, Role.id == UserRoleLink.role_id)
        .join(RolePermissionLink, RolePermissionLink.role_id == Role.id)
        .join(Permission, Permission.id == RolePermissionLink.permission_id)
        .where(UserRoleLink.user_id == user.id)
    )

    for resource, action in result.all():
        if _match_resource(required_resource, resource):
            expanded = _expand_action(action)
            if required_action in expanded:
                return True

    return False


async def assign_roles(user_id: UUID, role_ids: list[UUID], db: AsyncSession) -> None:
    from sqlalchemy import delete
    await db.execute(delete(UserRoleLink).where(UserRoleLink.user_id == user_id))
    for role_id in role_ids:
        db.add(UserRoleLink(user_id=user_id, role_id=role_id))
    await db.flush()


async def check_role(user: User, role_name: str, db: AsyncSession) -> bool:
    if user.is_superuser:
        return True
    result = await db.execute(
        select(UserRoleLink)
        .join(Role, Role.id == UserRoleLink.role_id)
        .where(UserRoleLink.user_id == user.id, Role.name == role_name)
    )
    return result.scalar_one_or_none() is not None