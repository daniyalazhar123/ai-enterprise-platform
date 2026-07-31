from __future__ import annotations

import pytest
from httpx import AsyncClient

from apps.api.app.auth.rate_limit import TokenBucket


@pytest.mark.asyncio
async def test_rate_limit_default_bucket() -> None:
    bucket = TokenBucket(capacity=10, refill_rate=10)
    for _ in range(10):
        assert bucket.consume() is True
    assert bucket.consume() is False


@pytest.mark.asyncio
async def test_rate_limit_refill() -> None:
    import time

    bucket = TokenBucket(capacity=5, refill_rate=10)
    for _ in range(5):
        bucket.consume()
    assert bucket.consume() is False

    time.sleep(0.2)
    assert bucket.consume() is True


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"