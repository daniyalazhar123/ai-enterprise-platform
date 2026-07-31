from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.core.config import settings
from apps.api.app.core.exceptions import SessionLimitError
from apps.api.app.models.session import Session
from apps.api.app.models.user import User


async def create_session(
    user_id: UUID,
    ip_address: str,
    user_agent: str,
    device_info: dict | None = None,
    db: AsyncSession | None = None,
) -> Session:
    active_count = await count_active_sessions(user_id, db)

    if active_count >= settings.MAX_ACTIVE_SESSIONS:
        result = await db.execute(
            select(Session.id)
            .where(Session.user_id == user_id, Session.is_active == True)
            .order_by(Session.last_used_at.asc())
            .limit(1)
        )
        oldest_id = result.scalar_one_or_none()
        if oldest_id:
            await db.execute(
                update(Session)
                .where(Session.id == oldest_id)
                .values(is_active=False)
            )

    session_token = secrets.token_bytes(32)
    token_hash = hashlib.sha256(session_token).hexdigest()
    now = datetime.now(timezone.utc)

    session = Session(
        user_id=user_id,
        token_hash=token_hash,
        ip_address=ip_address,
        user_agent=user_agent,
        device_info=device_info or {},
        is_active=True,
        expires_at=now + timedelta(days=settings.SESSION_MAX_EXTENDED_DAYS),
        last_used_at=now,
    )
    db.add(session)
    await db.flush()
    await db.refresh(session)
    return session


async def count_active_sessions(user_id: UUID, db: AsyncSession) -> int:
    result = await db.execute(
        select(func.count(Session.id)).where(
            Session.user_id == user_id,
            Session.is_active == True,
        )
    )
    return result.scalar() or 0


async def get_session_by_id(session_id: UUID, user_id: UUID, db: AsyncSession) -> Session | None:
    result = await db.execute(
        select(Session).where(
            Session.id == session_id,
            Session.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def revoke_session(session_id: UUID, db: AsyncSession) -> None:
    await db.execute(
        update(Session)
        .where(Session.id == session_id)
        .values(is_active=False)
    )


async def revoke_all_other_sessions(
    user_id: UUID,
    current_session_id: UUID,
    db: AsyncSession,
) -> int:
    result = await db.execute(
        update(Session)
        .where(
            Session.user_id == user_id,
            Session.id != current_session_id,
            Session.is_active == True,
        )
        .values(is_active=False)
    )
    return result.rowcount


async def apply_sliding_window(session: Session) -> None:
    now = datetime.now(timezone.utc)
    if session.last_used_at.replace(tzinfo=timezone.utc) < now - timedelta(hours=1):
        new_expires_at = min(
            now + timedelta(hours=settings.SESSION_SLIDING_WINDOW_HOURS),
            session.created_at.replace(tzinfo=timezone.utc)
            + timedelta(days=settings.SESSION_MAX_EXTENDED_DAYS),
        )
        session.last_used_at = now
        session.expires_at = new_expires_at


async def list_user_sessions(user_id: UUID, db: AsyncSession) -> list[Session]:
    result = await db.execute(
        select(Session)
        .where(Session.user_id == user_id)
        .order_by(Session.last_used_at.desc())
    )
    return list(result.scalars().all())


async def cleanup_expired_sessions(db: AsyncSession) -> int:
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(Session.id).where(Session.expires_at < now)
    )
    expired_ids = result.scalars().all()
    if expired_ids:
        await db.execute(
            update(Session)
            .where(Session.id.in_(expired_ids))
            .values(is_active=False)
        )
    return len(expired_ids)