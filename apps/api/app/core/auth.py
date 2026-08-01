from __future__ import annotations

from typing import Annotated, Any

from fastapi import Depends, Header, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.auth.middleware import AuthContext
from apps.api.app.auth.service.token import decode_access_token
from apps.api.app.db.session import get_session
from apps.api.app.models.user import User


async def get_current_user_optional(
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
    db: AsyncSession = Depends(get_session),
) -> User | None:
    """Resolve the current user when a valid token is present.

    Mirrors ``auth.deps.get_current_user`` but is fail-soft: returns ``None``
    instead of raising when the token is absent, invalid, or the user is
    unavailable. Used by streaming endpoints that allow anonymous access.
    """
    auth_context: AuthContext | None = request.state.auth_context if hasattr(request.state, "auth_context") else None
    if auth_context and auth_context.user:
        return auth_context.user

    token: str | None = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]

    if token is None:
        return None

    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")

        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if user is None or user.deleted_at is not None or not user.is_active:
            return None

        return user
    except Exception:
        return None
