from __future__ import annotations

import json
from datetime import timedelta
from functools import wraps
from typing import Any, Callable

import redis.asyncio as aioredis

from apps.api.app.core.config import settings

_redis: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis


async def close_redis() -> None:
    global _redis
    if _redis:
        await _redis.close()
        _redis = None


def cache_key(prefix: str, *args, **kwargs) -> str:
    parts = [prefix]
    for arg in args:
        parts.append(str(arg))
    for k, v in sorted(kwargs.items()):
        parts.append(f"{k}={v}")
    return ":".join(parts)


def cache_result(ttl: int | None = None):
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            r = await get_redis()
            key = cache_key(func.__name__, *args, **kwargs)
            cached = await r.get(key)
            if cached is not None:
                return json.loads(cached)
            result = await func(*args, **kwargs)
            await r.setex(key, ttl or settings.REDIS_CACHE_TTL, json.dumps(result, default=str))
            return result
        return wrapper
    return decorator


async def invalidate_cache(pattern: str) -> None:
    r = await get_redis()
    keys = await r.keys(pattern)
    if keys:
        await r.delete(*keys)