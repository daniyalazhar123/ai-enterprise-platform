from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timezone
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.core.config import settings
from apps.api.app.core.exceptions import AuthenticationError, ConflictError
from apps.api.app.models.refresh_token import RefreshToken
from apps.api.app.models.session import Session
from apps.api.app.models.user import User
from apps.api.app.auth.service.session import create_session
from apps.api.app.auth.service.token import create_access_token, generate_refresh_token
from apps.api.app.auth.audit import AuditLogger


async def initiate_google_oauth(redirect: str | None = None) -> str:
    state = secrets.token_urlsafe(32)
    code_verifier = secrets.token_urlsafe(64)
    code_challenge = hashlib.sha256(code_verifier.encode()).hexdigest()

    from apps.api.app.core.cache import get_redis
    r = await get_redis()
    await r.setex(f"oauth:state:{state}", 600, code_verifier)
    if redirect:
        await r.setex(f"oauth:redirect:{state}", 600, redirect)

    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": f"{settings.API_PREFIX}/auth/oauth/google/callback",
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "access_type": "offline",
    }
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return f"https://accounts.google.com/o/oauth2/v2/auth?{query}"


async def handle_google_callback(
    code: str,
    state: str,
    ip_address: str,
    user_agent: str,
    db: AsyncSession,
) -> tuple[User, str, str, int]:
    from apps.api.app.core.cache import get_redis
    r = await get_redis()
    code_verifier = await r.get(f"oauth:state:{state}")
    if code_verifier is None:
        raise AuthenticationError("Invalid OAuth state")

    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": f"{settings.API_PREFIX}/auth/oauth/google/callback",
                "code_verifier": code_verifier,
                "grant_type": "authorization_code",
            },
        )
        token_data = token_resp.json()

        if "error" in token_data:
            raise AuthenticationError(f"OAuth error: {token_data['error']}")

        userinfo_resp = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {token_data['access_token']}"},
        )
        userinfo = userinfo_resp.json()

    google_id = str(userinfo["id"])
    email = userinfo.get("email", "")
    name = userinfo.get("name", email.split("@")[0])
    picture = userinfo.get("picture", "")
    verified = userinfo.get("verified_email", False)

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            email=email,
            password_hash=None,
            display_name=name,
            avatar_url=picture,
            is_verified=verified,
            is_active=True,
        )
        db.add(user)
        await db.flush()
        await db.refresh(user)
    else:
        user.display_name = name
        user.avatar_url = picture
        user.last_login_at = datetime.now(timezone.utc)
        if verified and not user.is_verified:
            user.is_verified = True

    session = await create_session(user.id, ip_address, user_agent, db=db)
    await db.flush()

    refresh_token_string, _, _ = generate_refresh_token()
    rt_hash = hashlib.sha256(refresh_token_string.encode()).hexdigest()
    rt = RefreshToken(
        user_id=user.id,
        session_id=session.id,
        token_hash=rt_hash,
        family=str(session.id),
        expires_at=None,
    )
    db.add(rt)
    await db.flush()

    access_token, expires_in = create_access_token(user, session.id, [], [])

    await AuditLogger.log(
        db=db,
        user_id=user.id,
        session_id=session.id,
        event_type="oauth.linked",
        resource="oauth",
        resource_id="google",
        action="create",
        actor_ip=ip_address,
        actor_ua=user_agent,
    )

    return user, access_token, refresh_token_string, expires_in


async def initiate_github_oauth(redirect: str | None = None) -> str:
    state = secrets.token_urlsafe(32)

    from apps.api.app.core.cache import get_redis
    r = await get_redis()
    await r.setex(f"oauth:github:state:{state}", 600, "1")
    if redirect:
        await r.setex(f"oauth:github:redirect:{state}", 600, redirect)

    params = {
        "client_id": settings.GITHUB_CLIENT_ID,
        "redirect_uri": f"{settings.API_PREFIX}/auth/oauth/github/callback",
        "scope": "read:user user:email",
        "state": state,
    }
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return f"https://github.com/login/oauth/authorize?{query}"


async def handle_github_callback(
    code: str,
    state: str,
    ip_address: str,
    user_agent: str,
    db: AsyncSession,
) -> tuple[User, str, str, int]:
    from apps.api.app.core.cache import get_redis
    r = await get_redis()
    stored = await r.get(f"oauth:github:state:{state}")
    if stored is None:
        raise AuthenticationError("Invalid OAuth state")

    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            "https://github.com/login/oauth/access_token",
            headers={"Accept": "application/json"},
            data={
                "client_id": settings.GITHUB_CLIENT_ID,
                "client_secret": settings.GITHUB_CLIENT_SECRET,
                "code": code,
                "redirect_uri": f"{settings.API_PREFIX}/auth/oauth/github/callback",
            },
        )
        token_data = token_resp.json()

        if "error" in token_data:
            raise AuthenticationError(f"OAuth error: {token_data['error']}")

        access_token = token_data.get("access_token", "")
        user_resp = await client.get(
            "https://api.github.com/user",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
                "User-Agent": "AI-Enterprises",
            },
        )
        github_user = user_resp.json()

        email = github_user.get("email")
        if not email:
            emails_resp = await client.get(
                "https://api.github.com/user/emails",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/json",
                    "User-Agent": "AI-Enterprises",
                },
            )
            emails = emails_resp.json()
            for e in emails:
                if e.get("verified") and e.get("primary"):
                    email = e["email"]
                    break
            if not email:
                for e in emails:
                    if e.get("verified"):
                        email = e["email"]
                        break

    github_id = str(github_user["id"])
    name = github_user.get("name", email.split("@")[0] if email else "User")
    picture = github_user.get("avatar_url", "")

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            email=email,
            password_hash=None,
            display_name=name,
            avatar_url=picture,
            is_verified=True,
            is_active=True,
        )
        db.add(user)
        await db.flush()
        await db.refresh(user)
    else:
        user.display_name = name
        user.avatar_url = picture
        user.last_login_at = datetime.now(timezone.utc)

    session = await create_session(user.id, ip_address, user_agent, db=db)
    await db.flush()

    refresh_token_string, _, _ = generate_refresh_token()
    rt_hash = hashlib.sha256(refresh_token_string.encode()).hexdigest()
    rt = RefreshToken(
        user_id=user.id,
        session_id=session.id,
        token_hash=rt_hash,
        family=str(session.id),
        expires_at=None,
    )
    db.add(rt)
    await db.flush()

    access_token_jwt, expires_in = create_access_token(user, session.id, [], [])

    await AuditLogger.log(
        db=db,
        user_id=user.id,
        session_id=session.id,
        event_type="oauth.linked",
        resource="oauth",
        resource_id="github",
        action="create",
        actor_ip=ip_address,
        actor_ua=user_agent,
    )

    return user, access_token_jwt, refresh_token_string, expires_in