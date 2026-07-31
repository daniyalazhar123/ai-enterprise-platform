from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

from joserfc import jwt
from joserfc.jwk import RSAKey
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.core.cache import get_redis
from apps.api.app.core.config import settings
from apps.api.app.core.exceptions import (
    AuthenticationError,
    TheftDetectedError,
    TokenExpiredError,
    TokenRevokedError,
)
from apps.api.app.core.security import crypto, uuid7
from apps.api.app.models.refresh_token import RefreshToken
from apps.api.app.models.session import Session
from apps.api.app.models.user import User


def create_access_token(
    user: User,
    session_id: UUID,
    roles: list[str],
    permissions: list[str],
) -> tuple[str, int]:
    now = datetime.now(timezone.utc)
    expires_in = settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
    expire_dt = now + timedelta(seconds=expires_in)

    claims = {
        "sub": str(user.id),
        "sid": str(session_id),
        "email": user.email,
        "name": user.display_name,
        "roles": roles,
        "permissions": permissions,
        "iat": int(now.timestamp()),
        "exp": int(expire_dt.timestamp()),
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_AUDIENCE,
        "jti": str(uuid7()),
        "type": "access",
    }

    rsa_key = RSAKey.import_key(crypto.private_key)
    token = jwt.encode({"alg": "RS256", "kid": crypto.kid, "typ": "JWT"}, claims, rsa_key)
    return token, expires_in


def decode_access_token(token: str) -> dict:
    rsa_key = RSAKey.import_key(crypto.public_key)
    try:
        decoded = jwt.decode(token, rsa_key, {"algorithms": ["RS256"]})
        payload = decoded.claims
    except Exception:
        raise AuthenticationError("Invalid token")

    if payload.get("type") != "access":
        raise AuthenticationError("Invalid token type")
    if payload.get("iss") != settings.JWT_ISSUER:
        raise AuthenticationError("Invalid issuer")
    if payload.get("aud") != settings.JWT_AUDIENCE:
        raise AuthenticationError("Invalid audience")

    return payload


def generate_refresh_token() -> tuple[str, str, str]:
    token_bytes = secrets.token_bytes(settings.REFRESH_TOKEN_BYTES)
    token_string = _base64url_encode(token_bytes)
    token_hash = hashlib.sha256(token_string.encode()).hexdigest()
    family = str(uuid7())
    return token_string, token_hash, family


def hash_refresh_token(token_string: str) -> str:
    return hashlib.sha256(token_string.encode()).hexdigest()


async def validate_refresh_token(
    token_string: str,
    db: AsyncSession,
) -> tuple[RefreshToken, Session, User]:
    token_hash = hash_refresh_token(token_string)

    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    rt = result.scalar_one_or_none()

    if rt is None:
        raise TokenExpiredError("Refresh token not found")

    if rt.revoked_at is not None:
        await _handle_theft_detection(rt.family, db)
        raise TheftDetectedError("Refresh token reuse detected")

    if rt.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise TokenExpiredError("Refresh token expired")

    session_result = await db.execute(select(Session).where(Session.id == rt.session_id))
    session = session_result.scalar_one_or_none()

    if session is None or not session.is_active:
        raise TokenRevokedError("Session has been revoked")

    user_result = await db.execute(select(User).where(User.id == rt.user_id))
    user = user_result.scalar_one_or_none()

    if user is None or user.deleted_at is not None:
        raise AuthenticationError("Account not found or deactivated")

    return rt, session, user


async def rotate_refresh_token(
    old_token: RefreshToken,
    session: Session,
    user: User,
    db: AsyncSession,
) -> tuple[str, str, int]:
    new_token_string, new_token_hash, family = generate_refresh_token()
    new_rt = RefreshToken(
        user_id=user.id,
        session_id=session.id,
        token_hash=new_token_hash,
        family=old_token.family if old_token.family else family,
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(new_rt)
    old_token.revoked_at = datetime.now(timezone.utc)
    session.last_used_at = datetime.now(timezone.utc)

    access_token, expires_in = create_access_token(
        user=user,
        session_id=session.id,
        roles=[],
        permissions=[],
    )

    return new_token_string, access_token, expires_in


async def _handle_theft_detection(family: str, db: AsyncSession) -> None:
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.family == family,
            RefreshToken.revoked_at.is_(None),
        )
    )
    family_tokens = result.scalars().all()

    session_ids = set()
    for rt in family_tokens:
        rt.revoked_at = datetime.now(timezone.utc)
        session_ids.add(rt.session_id)

    for sid in session_ids:
        s_result = await db.execute(select(Session).where(Session.id == sid))
        s = s_result.scalar_one_or_none()
        if s:
            s.is_active = False

    await db.flush()


async def revoke_token_jti(jti: str, ttl: int) -> None:
    r = await get_redis()
    await r.setex(f"revoked:jti:{jti}", ttl, "1")


async def is_token_revoked(jti: str) -> bool:
    r = await get_redis()
    result = await r.get(f"revoked:jti:{jti}")
    return result is not None


def _base64url_encode(data: bytes) -> str:
    import base64
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()