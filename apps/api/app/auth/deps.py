from __future__ import annotations

from typing import Annotated, Any

from fastapi import Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.core.exceptions import AuthenticationError, AuthorizationError
from apps.api.app.db.session import get_session
from apps.api.app.models.session import Session
from apps.api.app.models.user import User
from apps.api.app.auth.service.authorization import check_permission, check_role, get_user_permissions, get_user_roles
from apps.api.app.auth.middleware import AuthContext
from apps.api.app.auth.service.session import apply_sliding_window
from apps.api.app.auth.service.token import decode_access_token


async def get_current_user(
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
    db: AsyncSession = Depends(get_session),
) -> User:
    auth_context: AuthContext | None = request.state.auth_context if hasattr(request.state, "auth_context") else None
    if auth_context and auth_context.user:
        return auth_context.user

    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]

    if token is None:
        raise AuthenticationError("Missing authentication token")

    payload = decode_access_token(token)
    user_id = payload.get("sub")

    from sqlalchemy import select
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None or user.deleted_at is not None:
        raise AuthenticationError("User not found")

    if not user.is_active:
        raise AuthenticationError("Account is deactivated")

    return user


async def get_valid_session(
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> Session:
    auth_context: AuthContext | None = request.state.auth_context if hasattr(request.state, "auth_context") else None
    if auth_context and auth_context.session:
        session = auth_context.session
        await apply_sliding_window(session)
        return session

    token = None
    authorization = request.headers.get("authorization", "")
    if authorization.startswith("Bearer "):
        token = authorization[7:]

    if token is None:
        raise AuthenticationError("Missing authentication token")

    payload = decode_access_token(token)
    session_id = payload.get("sid")

    from sqlalchemy import select
    result = await db.execute(select(Session).where(Session.id == session_id, Session.user_id == user.id))
    session = result.scalar_one_or_none()

    if session is None or not session.is_active:
        raise AuthenticationError("Session has been revoked")

    await apply_sliding_window(session)
    return session


class PermissionDependency:
    def __init__(self, resource: str, action: str) -> None:
        self.resource = resource
        self.action = action

    async def __call__(
        self,
        user: User = Depends(get_current_user),
        session: Session = Depends(get_valid_session),
        db: AsyncSession = Depends(get_session),
    ) -> None:
        has_perm = await check_permission(user, self.resource, self.action, db)
        if not has_perm:
            from apps.api.app.auth.audit import AuditLogger
            await AuditLogger.log(
                db=db,
                user_id=user.id,
                session_id=session.id,
                event_type="auth.denied",
                resource=self.resource,
                action=self.action,
                actor_ip="",
                actor_ua="",
                metadata={"required_resource": self.resource, "required_action": self.action},
            )
            raise AuthorizationError(f"Missing permission: {self.resource}:{self.action}")


def require_permission(resource: str, action: str) -> PermissionDependency:
    return PermissionDependency(resource, action)


class RoleDependency:
    def __init__(self, role_name: str) -> None:
        self.role_name = role_name

    async def __call__(
        self,
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_session),
    ) -> None:
        has_role = await check_role(user, self.role_name, db)
        if not has_role:
            raise AuthorizationError(f"Missing role: {self.role_name}")


def require_role(role_name: str) -> RoleDependency:
    return RoleDependency(role_name)


async def get_jwks() -> dict:
    from apps.api.app.core.security import crypto
    return crypto.get_jwks().model_dump()