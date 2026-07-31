from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.core.config import settings
from apps.api.app.core.exceptions import (
    AccountDeactivatedError,
    AccountLockedError,
    AuthenticationError,
    ConflictError,
    NotFoundError,
    ValidationError,
)
from apps.api.app.models.refresh_token import RefreshToken
from apps.api.app.models.session import Session
from apps.api.app.models.user import User
from apps.api.app.auth.service.password import validate_and_hash, verify_password
from apps.api.app.auth.service.session import create_session
from apps.api.app.auth.service.token import (
    create_access_token,
    generate_refresh_token,
    rotate_refresh_token,
    revoke_token_jti,
    validate_refresh_token,
)

from apps.api.app.auth.audit import AuditLogger


async def register(
    email: str,
    password: str,
    display_name: str,
    ip_address: str,
    user_agent: str,
    db: AsyncSession,
) -> tuple[User, str, str, int]:
    existing = await db.execute(select(User).where(User.email == email))
    if existing.scalar_one_or_none():
        raise ConflictError("Email already registered")

    password_hash = await validate_and_hash(password)

    user = User(
        email=email,
        password_hash=password_hash,
        display_name=display_name,
        is_verified=False,
        is_active=True,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)

    session = await create_session(user.id, ip_address, user_agent, db=db)

    refresh_token_string, _, _ = generate_refresh_token()
    rt_hash = __import__("hashlib").sha256(refresh_token_string.encode()).hexdigest()
    rt = RefreshToken(
        user_id=user.id,
        session_id=session.id,
        token_hash=rt_hash,
        family=str(user.id),
        expires_at=datetime.now(timezone.utc)
        + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(rt)
    await db.flush()

    access_token, expires_in = create_access_token(user, session.id, [], [])

    await AuditLogger.log(
        db=db,
        user_id=user.id,
        session_id=session.id,
        event_type="auth.register",
        resource="user",
        resource_id=str(user.id),
        action="create",
        actor_ip=ip_address,
        actor_ua=user_agent,
    )

    return user, access_token, refresh_token_string, expires_in


async def login(
    email: str,
    password: str,
    ip_address: str,
    user_agent: str,
    device_info: dict | None,
    db: AsyncSession,
) -> tuple[User, Session, str, str, int]:
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if user is None:
        await _fake_verify()
        raise AuthenticationError("Invalid email or password")

    if user.deleted_at is not None:
        raise AccountDeactivatedError("Account has been deleted")

    if user.locked_until and user.locked_until.replace(tzinfo=timezone.utc) > datetime.now(timezone.utc):
        raise AccountLockedError("Account is temporarily locked")

    if user.password_hash is None:
        raise AuthenticationError("Account uses OAuth. Please sign in with Google/GitHub.")

    if not verify_password(password, user.password_hash):
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= 5:
            user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=15)
        await db.flush()
        raise AuthenticationError("Invalid email or password")

    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login_at = datetime.now(timezone.utc)

    session = await create_session(user.id, ip_address, user_agent, device_info, db)
    await db.flush()

    refresh_token_string, _, _ = generate_refresh_token()
    rt_hash = __import__("hashlib").sha256(refresh_token_string.encode()).hexdigest()
    rt = RefreshToken(
        user_id=user.id,
        session_id=session.id,
        token_hash=rt_hash,
        family=str(session.id),
        expires_at=datetime.now(timezone.utc)
        + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(rt)
    await db.flush()

    access_token, expires_in = create_access_token(user, session.id, [], [])

    await AuditLogger.log(
        db=db,
        user_id=user.id,
        session_id=session.id,
        event_type="auth.login",
        resource="session",
        resource_id=str(session.id),
        action="create",
        actor_ip=ip_address,
        actor_ua=user_agent,
    )

    return user, session, access_token, refresh_token_string, expires_in


async def refresh(
    refresh_token_string: str,
    db: AsyncSession,
) -> tuple[str, str, int]:
    rt, session, user = await validate_refresh_token(refresh_token_string, db)
    new_token_string, access_token, expires_in = await rotate_refresh_token(rt, session, user, db)

    await AuditLogger.log(
        db=db,
        user_id=user.id,
        session_id=session.id,
        event_type="auth.refresh",
        resource="session",
        resource_id=str(session.id),
        action="read",
        actor_ip="",
        actor_ua="",
    )

    return new_token_string, access_token, expires_in


async def logout(
    user_id: UUID,
    session_id: UUID,
    refresh_token_string: str | None,
    all_sessions: bool,
    db: AsyncSession,
) -> None:
    if all_sessions:
        result = await db.execute(
            select(Session).where(
                Session.user_id == user_id,
                Session.is_active == True,
                Session.id != session_id,
            )
        )
        other_sessions = list(result.scalars().all())
        for s in other_sessions:
            s.is_active = False

        rt_result = await db.execute(
            select(RefreshToken).where(
                RefreshToken.user_id == user_id,
                RefreshToken.session_id != session_id,
                RefreshToken.revoked_at.is_(None),
            )
        )
        for rt in rt_result.scalars().all():
            rt.revoked_at = datetime.now(timezone.utc)
    else:
        if refresh_token_string:
            token_hash = __import__("hashlib").sha256(refresh_token_string.encode()).hexdigest()
            rt_result = await db.execute(
                select(RefreshToken).where(RefreshToken.token_hash == token_hash)
            )
            rt = rt_result.scalar_one_or_none()
            if rt:
                rt.revoked_at = datetime.now(timezone.utc)

        session_result = await db.execute(
            select(Session).where(
                Session.id == session_id,
                Session.user_id == user_id,
            )
        )
        session = session_result.scalar_one_or_none()
        if session:
            session.is_active = False

    await db.flush()


async def _fake_verify() -> None:
    import hashlib
    import secrets
    dummy = secrets.token_bytes(32)
    hashlib.sha256(dummy).hexdigest()