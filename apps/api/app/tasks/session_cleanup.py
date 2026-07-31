from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.models.refresh_token import RefreshToken
from apps.api.app.models.session import Session


async def cleanup_expired_sessions(db: AsyncSession) -> int:
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(Session.id).where(Session.expires_at < now)
    )
    expired_ids = result.scalars().all()
    if expired_ids:
        from sqlalchemy import update
        await db.execute(
            update(Session)
            .where(Session.id.in_(expired_ids))
            .values(is_active=False)
        )
    return len(expired_ids)


async def cleanup_expired_refresh_tokens(db: AsyncSession) -> int:
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(RefreshToken.id).where(RefreshToken.expires_at < now)
    )
    expired_ids = result.scalars().all()
    if expired_ids:
        from sqlalchemy import update
        await db.execute(
            update(RefreshToken)
            .where(RefreshToken.id.in_(expired_ids))
            .values(revoked_at=now)
        )
    return len(expired_ids)