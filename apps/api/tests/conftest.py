from __future__ import annotations

import os
from collections.abc import AsyncIterator, Callable, Iterator

import httpx
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

os.environ["PRICETRACKER_ENVIRONMENT"] = "test"
os.environ["PRICETRACKER_DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["PRICETRACKER_REDIS_URL"] = "redis://localhost:6379/15"

from app import models  # noqa: E402,F401  (register ORM tables on Base.metadata)
from app.config import Settings  # noqa: E402
from app.db import Base  # noqa: E402
from app.main import app  # noqa: E402
from app.providers.brightdata import BrightDataClient  # noqa: E402


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


@pytest_asyncio.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    """A committed-schema, in-memory SQLite session for service-level tests.

    Uses a dedicated engine with a StaticPool so the in-memory database persists
    for the lifetime of the fixture (a fresh connection would be an empty DB).
    """
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    try:
        async with session_factory() as session:
            yield session
    finally:
        await engine.dispose()


@pytest.fixture
def brightdata_client_factory() -> Callable[..., tuple[BrightDataClient, httpx.AsyncClient]]:
    def make(
        settings: Settings,
        handler: Callable[[httpx.Request], httpx.Response],
    ) -> tuple[BrightDataClient, httpx.AsyncClient]:
        http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        return BrightDataClient(settings, http_client=http_client), http_client

    return make
