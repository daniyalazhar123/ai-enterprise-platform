from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_user_model_create(client: AsyncClient, db_session) -> None:
    from apps.api.app.models.user import User

    user = User(
        email="model@example.com",
        password_hash="$argon2id$v=19$m=65536,t=3,p=4$hash",
        display_name="Model User",
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)

    assert user.id is not None
    assert user.email == "model@example.com"
    assert user.is_active is True
    assert user.is_verified is False
    assert user.created_at is not None


@pytest.mark.asyncio
async def test_user_model_soft_delete(client: AsyncClient, db_session) -> None:
    from datetime import datetime, timezone
    from apps.api.app.models.user import User

    user = User(
        email="delete@example.com",
        password_hash="$argon2id$hash",
        display_name="Delete User",
    )
    db_session.add(user)
    await db_session.flush()

    user.deleted_at = datetime.now(timezone.utc)
    user.is_active = False
    await db_session.flush()

    from sqlalchemy import select
    result = await db_session.execute(
        select(User).where(User.email == "delete@example.com", User.deleted_at.is_(None))
    )
    assert result.scalar_one_or_none() is None

    result = await db_session.execute(
        select(User).where(User.email == "delete@example.com")
    )
    assert result.scalar_one_or_none() is not None


@pytest.mark.asyncio
async def test_session_model_create(client: AsyncClient, db_session) -> None:
    from apps.api.app.models.user import User
    from apps.api.app.models.session import Session
    from datetime import datetime, timedelta, timezone

    user = User(
        email="sessionmodel@example.com",
        password_hash="hash",
        display_name="Session Model",
    )
    db_session.add(user)
    await db_session.flush()

    session = Session(
        user_id=user.id,
        token_hash="test_token_hash",
        ip_address="127.0.0.1",
        user_agent="pytest",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        last_used_at=datetime.now(timezone.utc),
    )
    db_session.add(session)
    await db_session.flush()

    assert session.id is not None
    assert session.user_id == user.id
    assert session.is_active is True


@pytest.mark.asyncio
async def test_refresh_token_model(client: AsyncClient, db_session) -> None:
    from apps.api.app.models.user import User
    from apps.api.app.models.session import Session
    from apps.api.app.models.refresh_token import RefreshToken
    from datetime import datetime, timedelta, timezone

    user = User(email="rtmodel@example.com", password_hash="hash", display_name="RT Model")
    db_session.add(user)
    await db_session.flush()

    session = Session(
        user_id=user.id,
        token_hash="rt_test_hash",
        ip_address="127.0.0.1",
        user_agent="pytest",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        last_used_at=datetime.now(timezone.utc),
    )
    db_session.add(session)
    await db_session.flush()

    rt = RefreshToken(
        user_id=user.id,
        session_id=session.id,
        token_hash="refresh_token_hash",
        family="test_family",
        expires_at=datetime.now(timezone.utc) + timedelta(days=30),
    )
    db_session.add(rt)
    await db_session.flush()

    assert rt.id is not None
    assert rt.revoked_at is None