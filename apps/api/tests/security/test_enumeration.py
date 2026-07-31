from __future__ import annotations

import hashlib
import secrets

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_password_timing_constant_time(client: AsyncClient) -> None:
    from apps.api.app.auth.service.password import verify_password

    hashed = "$argon2id$v=19$m=65536,t=3,p=4$c29tZXNhbHQ$dGhlc3VwZXJzZWNyZXRoYXNo"

    import time

    times = []
    for _ in range(5):
        start = time.perf_counter()
        verify_password("wrong_password_1", hashed)
        times.append(time.perf_counter() - start)

    for _ in range(5):
        start = time.perf_counter()
        verify_password("wrong_password_2", hashed)
        times.append(time.perf_counter() - start)

    max_time = max(times)
    min_time = min(times)
    assert max_time - min_time < 0.5


@pytest.mark.asyncio
async def test_enumeration_protection(client: AsyncClient) -> None:
    existing_email = "existing@enumtest.com"
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": existing_email,
            "password": "StrongPass123!",
            "display_name": "Enum Test",
        },
    )

    resp_existing = await client.post(
        "/api/v1/auth/login",
        json={"email": existing_email, "password": "WrongPass123!"},
    )

    resp_nonexistent = await client.post(
        "/api/v1/auth/login",
        json={"email": "nonexistent@enumtest.com", "password": "WrongPass123!"},
    )

    assert resp_existing.status_code == resp_nonexistent.status_code


@pytest.mark.asyncio
async def test_forgot_password_enumeration(client: AsyncClient) -> None:
    resp_existing = await client.post(
        "/api/v1/auth/forgot-password",
        json={"email": "existing@enum2.com"},
    )
    resp_nonexistent = await client.post(
        "/api/v1/auth/forgot-password",
        json={"email": "nonexistent@enum2.com"},
    )
    assert resp_existing.status_code == 200
    assert resp_nonexistent.status_code == 200
    assert resp_existing.json() == resp_nonexistent.json()