from __future__ import annotations

import time
from collections.abc import AsyncGenerator
from typing import Any

import redis.asyncio as aioredis
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

from apps.api.app.core.cache import get_redis
from apps.api.app.core.config import settings
from apps.api.app.core.exceptions import RateLimitError


class TokenBucket:
    def __init__(self, capacity: int, refill_rate: float) -> None:
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = float(capacity)
        self.last_refill = time.monotonic()

    def consume(self, tokens: float = 1.0) -> bool:
        now = time.monotonic()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now

        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False


_local_buckets: dict[str, TokenBucket] = {}


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        client_ip = request.client.host if request.client else "unknown"
        path = request.url.path

        if "/auth/login" in path:
            limit = settings.RATE_LIMIT_AUTH_LOGIN
        elif "/auth/register" in path:
            limit = settings.RATE_LIMIT_AUTH_REGISTER
        else:
            limit = settings.RATE_LIMIT_DEFAULT

        bucket_key = f"{client_ip}:{path}"
        if bucket_key not in _local_buckets:
            _local_buckets[bucket_key] = TokenBucket(
                capacity=limit,
                refill_rate=limit / settings.RATE_LIMIT_WINDOW_SECONDS,
            )

        bucket = _local_buckets[bucket_key]
        if not bucket.consume():
            raise RateLimitError("Too many requests. Please try again later.")

        return await call_next(request)


async def check_rate_limit_redis(
    key: str,
    max_requests: int,
    window_seconds: int,
) -> bool:
    r = await get_redis()
    now = int(time.time())
    window_key = f"ratelimit:{key}:{now // window_seconds}"
    count = await r.incr(window_key)
    if count == 1:
        await r.expire(window_key, window_seconds)
    return count <= max_requests


class SlidingWindowRateLimiter:
    def __init__(self, max_requests: int, window_seconds: int) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds

    async def check(self, key: str) -> bool:
        return await check_rate_limit_redis(key, self.max_requests, self.window_seconds)