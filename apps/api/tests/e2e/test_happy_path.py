from __future__ import annotations

import hashlib
import secrets

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_full_auth_flow(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "flow@example.com",
            "password": "StrongPass123!",
            "display_name": "Flow User",
        },
    )
    assert resp.status_code == 201

    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "flow@example.com", "password": "StrongPass123!"},
    )
    assert login_resp.status_code == 200
    login_data = login_resp.json()
    access_token = login_data["access_token"]
    refresh_token = login_data["refresh_token"]

    me_resp = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == "flow@example.com"

    refresh_resp = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_resp.status_code == 200
    new_access = refresh_resp.json()["access_token"]

    me_resp2 = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {new_access}"},
    )
    assert me_resp2.status_code == 200

    sessions_resp = await client.get(
        "/api/v1/auth/sessions",
        headers={"Authorization": f"Bearer {new_access}"},
    )
    assert sessions_resp.status_code == 200
    sessions_data = sessions_resp.json()
    assert sessions_data["total"] >= 1
    assert sessions_data["active_count"] >= 1


@pytest.mark.asyncio
async def test_password_reset_flow(client: AsyncClient) -> None:
    register_resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "resetflow@example.com",
            "password": "OriginalPass123!",
            "display_name": "Reset Flow",
        },
    )
    assert register_resp.status_code == 201

    forgot_resp = await client.post(
        "/api/v1/auth/forgot-password",
        json={"email": "resetflow@example.com"},
    )
    assert forgot_resp.status_code == 200


@pytest.mark.asyncio
async def test_session_management(client: AsyncClient) -> None:
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "sessionmgmt@example.com",
            "password": "StrongPass123!",
            "display_name": "Session Mgmt",
        },
    )
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "sessionmgmt@example.com", "password": "StrongPass123!"},
    )
    token = login_resp.json()["access_token"]
    session_id = login_resp.json()["session_id"]

    sessions_resp = await client.get(
        "/api/v1/auth/sessions",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert sessions_resp.status_code == 200

    delete_resp = await client.delete(
        f"/api/v1/auth/sessions/{session_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert delete_resp.status_code == 204