from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_sql_injection_login(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "' OR 1=1 --",
            "password": "' OR '1'='1",
        },
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_no_mass_assignment(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "mass@example.com",
            "password": "StrongPass123!",
            "display_name": "Mass User",
            "is_superuser": True,
            "is_verified": True,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data.get("is_superuser", False) is False


@pytest.mark.asyncio
async def test_xss_profile_update(client: AsyncClient) -> None:
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "xss@example.com",
            "password": "StrongPass123!",
            "display_name": "XSS User",
        },
    )
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "xss@example.com", "password": "StrongPass123!"},
    )
    token = login_resp.json()["access_token"]

    response = await client.patch(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
        json={"display_name": "<script>alert('xss')</script>"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["display_name"] == "<script>alert('xss')</script>"