from __future__ import annotations

import uuid
from types import SimpleNamespace
from typing import cast

import pytest
from fastapi import HTTPException, Request
from redis.exceptions import RedisError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.watches import _enforce_create_limits
from app.config import get_settings
from app.models import User


class _FailingRedis:
    """Stand-in Redis whose commands always raise, simulating an outage."""

    async def incr(self, *args: object, **kwargs: object) -> int:
        raise RedisError("redis unavailable")

    async def expire(self, *args: object, **kwargs: object) -> bool:  # pragma: no cover
        raise RedisError("redis unavailable")


class _FakeRedis:
    """Minimal in-memory Redis supporting the incr/expire the limiter uses."""

    def __init__(self) -> None:
        self.store: dict[str, int] = {}

    async def incr(self, key: str) -> int:
        self.store[key] = self.store.get(key, 0) + 1
        return self.store[key]

    async def expire(self, key: str, ttl: int) -> bool:
        return True


def _request(redis: object) -> Request:
    namespace = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(redis=redis)))
    return cast(Request, namespace)


def _user() -> User:
    return cast(User, SimpleNamespace(id=uuid.uuid4()))


async def test_enforce_create_limits_fails_closed_when_redis_unavailable(
    db_session: AsyncSession,
) -> None:
    settings = get_settings()

    with pytest.raises(HTTPException) as excinfo:
        await _enforce_create_limits(_request(_FailingRedis()), db_session, _user(), settings)

    assert excinfo.value.status_code == 503


async def test_enforce_create_limits_allows_under_limit(db_session: AsyncSession) -> None:
    settings = get_settings()

    # A single create for a fresh user is well under the hourly limit.
    await _enforce_create_limits(_request(_FakeRedis()), db_session, _user(), settings)


async def test_enforce_create_limits_blocks_over_limit(db_session: AsyncSession) -> None:
    request = _request(_FakeRedis())
    user = _user()
    settings = get_settings()
    limit = settings.watch_create_rate_limit_per_hour

    # Fill the hourly bucket up to the limit; each of these must be allowed.
    for _ in range(limit):
        await _enforce_create_limits(request, db_session, user, settings)

    # The next attempt in the same hour exceeds the limit and is rejected.
    with pytest.raises(HTTPException) as excinfo:
        await _enforce_create_limits(request, db_session, user, settings)

    assert excinfo.value.status_code == 429
