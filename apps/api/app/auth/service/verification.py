from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.core.config import settings
from apps.api.app.core.exceptions import NotFoundError, ValidationError
from apps.api.app.models.password_history import PasswordHistory
from apps.api.app.models.refresh_token import RefreshToken
from apps.api.app.models.session import Session
from apps.api.app.models.user import User
from apps.api.app.models.verification_token import VerificationToken
from apps.api.app.auth.service.password import validate_and_hash, verify_password

from apps.api.app.auth.audit import AuditLogger


def generate_verification_token() -> tuple[str, str]:
    token_bytes = secrets.token_bytes(32)
    import base64
    token_string = base64.urlsafe_b64encode(token_bytes).rstrip(b"=").decode()
    token_hash = hashlib.sha256(token_string.encode()).hexdigest()
    return token_string, token_hash


async def create_email_verification_token(
    user_id: UUID,
    db: AsyncSession,
) -> str:
    token_string, token_hash = generate_verification_token()
    vt = VerificationToken(
        user_id=user_id,
        token_hash=token_hash,
        purpose="email_verification",
        expires_at=datetime.now(timezone.utc)
        + timedelta(hours=settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS),
    )
    db.add(vt)
    await db.flush()
    return token_string


async def verify_email(token_string: str, db: AsyncSession) -> User:
    token_hash = hashlib.sha256(token_string.encode()).hexdigest()
    result = await db.execute(
        select(VerificationToken).where(
            VerificationToken.token_hash == token_hash,
            VerificationToken.purpose == "email_verification",
        )
    )
    vt = result.scalar_one_or_none()

    if vt is None:
        raise ValidationError("Invalid verification token")
    if vt.used_at is not None:
        raise ValidationError("Verification token already used")
    if vt.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise ValidationError("Verification token expired")

    user_result = await db.execute(select(User).where(User.id == vt.user_id))
    user = user_result.scalar_one_or_none()
    if user is None:
        raise NotFoundError("User not found")

    vt.used_at = datetime.now(timezone.utc)
    user.is_verified = True
    await db.flush()
    return user


async def create_password_reset_token(
    user_id: UUID,
    db: AsyncSession,
) -> str:
    await db.execute(
        update(VerificationToken)
        .where(
            VerificationToken.user_id == user_id,
            VerificationToken.purpose == "password_reset",
            VerificationToken.used_at.is_(None),
        )
        .values(used_at=datetime.now(timezone.utc))
    )

    token_string, token_hash = generate_verification_token()
    vt = VerificationToken(
        user_id=user_id,
        token_hash=token_hash,
        purpose="password_reset",
        expires_at=datetime.now(timezone.utc)
        + timedelta(hours=settings.PASSWORD_RESET_TOKEN_EXPIRE_HOURS),
    )
    db.add(vt)
    await db.flush()
    return token_string


async def reset_password(
    token_string: str,
    new_password: str,
    ip_address: str,
    user_agent: str,
    db: AsyncSession,
) -> User:
    token_hash = hashlib.sha256(token_string.encode()).hexdigest()
    result = await db.execute(
        select(VerificationToken).where(
            VerificationToken.token_hash == token_hash,
            VerificationToken.purpose == "password_reset",
        )
    )
    vt = result.scalar_one_or_none()

    if vt is None:
        raise ValidationError("Invalid reset token")
    if vt.used_at is not None:
        raise ValidationError("Reset token already used")
    if vt.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise ValidationError("Reset token expired")

    user_result = await db.execute(select(User).where(User.id == vt.user_id))
    user = user_result.scalar_one_or_none()
    if user is None:
        raise NotFoundError("User not found")

    new_hash = await validate_and_hash(new_password, str(user.id))

    history_result = await db.execute(
        select(PasswordHistory.password_hash)
        .where(PasswordHistory.user_id == user.id)
        .order_by(PasswordHistory.created_at.desc())
        .limit(settings.PASSWORD_HISTORY_CHECK)
    )
    for historical_hash in history_result.scalars().all():
        if verify_password(new_password, historical_hash):
            raise ValidationError("Password has been used recently")

    vt.used_at = datetime.now(timezone.utc)
    user.password_hash = new_hash

    db.add(PasswordHistory(user_id=user.id, password_hash=new_hash))

    await db.execute(
        update(Session)
        .where(Session.user_id == user.id, Session.is_active == True)
        .values(is_active=False)
    )
    await db.execute(
        update(RefreshToken)
        .where(
            RefreshToken.user_id == user.id,
            RefreshToken.revoked_at.is_(None),
        )
        .values(revoked_at=datetime.now(timezone.utc))
    )

    await AuditLogger.log(
        db=db,
        user_id=user.id,
        event_type="user.password.reset",
        resource="user",
        resource_id=str(user.id),
        action="update",
        actor_ip=ip_address,
        actor_ua=user_agent,
    )

    await db.flush()
    return user