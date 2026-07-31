from __future__ import annotations

import pytest
from httpx import AsyncClient

from apps.api.app.auth.service.authorization import check_permission, check_role
from apps.api.app.models.role import Role, UserRoleLink


@pytest.mark.asyncio
async def test_superuser_has_all_permissions(client: AsyncClient, db_session, test_user) -> None:
    test_user.is_superuser = True
    await db_session.flush()

    has_perm = await check_permission(test_user, "any_resource", "any_action", db_session)
    assert has_perm is True


@pytest.mark.asyncio
async def test_user_without_role_has_no_permissions(client: AsyncClient, db_session, test_user) -> None:
    has_perm = await check_permission(test_user, "users", "read", db_session)
    assert has_perm is False


@pytest.mark.asyncio
async def test_role_check(client: AsyncClient, db_session, test_user) -> None:
    role = Role(name="admin", is_system=True)
    db_session.add(role)
    await db_session.flush()

    link = UserRoleLink(user_id=test_user.id, role_id=role.id)
    db_session.add(link)
    await db_session.flush()

    has_role = await check_role(test_user, "admin", db_session)
    assert has_role is True

    has_role = await check_role(test_user, "viewer", db_session)
    assert has_role is False


@pytest.mark.asyncio
async def test_admin_users_read_permission(client: AsyncClient, db_session, test_user) -> None:
    admin_role = Role(name="admin", is_system=True)
    db_session.add(admin_role)
    await db_session.flush()

    from apps.api.app.models.permission import Permission, RolePermissionLink

    perm = Permission(resource="users", action="*", is_system=True)
    db_session.add(perm)
    await db_session.flush()

    db_session.add(RolePermissionLink(role_id=admin_role.id, permission_id=perm.id))
    db_session.add(UserRoleLink(user_id=test_user.id, role_id=admin_role.id))
    await db_session.flush()

    has_perm = await check_permission(test_user, "users", "read", db_session)
    assert has_perm is True

    has_perm = await check_permission(test_user, "audit", "read", db_session)
    assert has_perm is False