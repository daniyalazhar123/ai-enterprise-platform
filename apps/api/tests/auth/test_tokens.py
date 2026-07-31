from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_jwt_token_structure(client: AsyncClient) -> None:
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "jwt@example.com",
            "password": "StrongPass123!",
            "display_name": "JWT User",
        },
    )
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "jwt@example.com", "password": "StrongPass123!"},
    )
    token = login_resp.json()["access_token"]
    parts = token.split(".")
    assert len(parts) == 3


@pytest.mark.asyncio
async def test_access_token_expiry(client: AsyncClient) -> None:
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "expiry@example.com",
            "password": "StrongPass123!",
            "display_name": "Expiry User",
        },
    )
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "expiry@example.com", "password": "StrongPass123!"},
    )
    data = login_resp.json()
    assert data["expires_in"] == 900


@pytest.mark.asyncio
async def test_refresh_token_rotation(client: AsyncClient) -> None:
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "rotate@example.com",
            "password": "StrongPass123!",
            "display_name": "Rotate User",
        },
    )
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "rotate@example.com", "password": "StrongPass123!"},
    )
    old_refresh = login_resp.json()["refresh_token"]

    refresh_resp = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": old_refresh},
    )
    assert refresh_resp.status_code == 200
    new_refresh = refresh_resp.json()["refresh_token"]
    assert new_refresh != old_refresh

    reuse_resp = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": old_refresh},
    )
    assert reuse_resp.status_code == 401


@pytest.mark.asyncio
async def test_jwks_endpoint(client: AsyncClient) -> None:
    response = await client.get("/.well-known/jwks.json")
    assert response.status_code == 200
    data = response.json()
    assert "keys" in data
    assert len(data["keys"]) > 0
    key = data["keys"][0]
    assert key["kty"] == "RSA"
    assert key["alg"] == "RS256"