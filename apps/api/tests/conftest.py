from __future__ import annotations

import asyncio
import os
import re
from collections.abc import AsyncIterator, Callable, Iterator

import httpx
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from redis.exceptions import RedisError
from sqlalchemy import text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

# The suite runs against a real PostgreSQL server: the repositories use
# PostgreSQL-only `INSERT ... ON CONFLICT` and the tracking pipeline relies on
# `FOR UPDATE SKIP LOCKED`, neither of which SQLite can express. `make infra-up`
# provides a suitable server; CI overrides the URL to point at its own service.
#
# 127.0.0.1 rather than localhost: Compose publishes PostgreSQL on IPv4 only, and
# resolving localhost tries ::1 first, so every connection pays a ~2s failed-
# connect penalty on Windows before falling back.
DEFAULT_TEST_DATABASE_URL = (
    "postgresql+asyncpg://pricetracker:change-me-locally@127.0.0.1:5432/pricetracker_pytest"
)
TEST_DATABASE_URL = os.environ.get("PRICETRACKER_TEST_DATABASE_URL", DEFAULT_TEST_DATABASE_URL)

# Set before importing the application: `app.db` builds its engine from these at
# import time, so the app under test must already point at the test database.
os.environ["PRICETRACKER_ENVIRONMENT"] = "test"
os.environ["PRICETRACKER_DATABASE_URL"] = TEST_DATABASE_URL
os.environ["PRICETRACKER_REDIS_URL"] = "redis://localhost:6379/15"

from app import models  # noqa: E402,F401  (register ORM tables on Base.metadata)
from app.api.v1 import watches as watches_module  # noqa: E402
from app.api.v1 import webhooks as webhooks_module  # noqa: E402
from app.auth.clerk import AuthUser, get_current_identity  # noqa: E402
from app.config import Settings  # noqa: E402
from app.db import Base  # noqa: E402
from app.main import app  # noqa: E402
from app.providers.brightdata import BrightDataClient  # noqa: E402

# example.com rather than example.test: `UserPreferencesResponse.email` is an
# EmailStr, and email-validator rejects the reserved .test TLD outright.
PRIMARY_IDENTITY = AuthUser(clerk_user_id="user_test_primary", email="primary@example.com")
OTHER_IDENTITY = AuthUser(clerk_user_id="user_test_other", email="other@example.com")

PREPARE_FAILED_HINT = (
    # Rendered with the password hidden: this message is printed on failure and
    # would otherwise put the database credentials into CI logs.
    "Could not prepare the test database "
    f"{make_url(TEST_DATABASE_URL).render_as_string(hide_password=True)}.\n"
    "If the server is not running, start it with `make infra-up` (or `docker "
    "compose --env-file .env -f infra/compose.yaml up -d postgres`), or point "
    "PRICETRACKER_TEST_DATABASE_URL at another server. Otherwise the underlying "
    "error below is the real cause."
)


async def _create_database_if_missing(url: URL) -> None:
    """Create the test database when it does not exist yet.

    Connects to the server's ``postgres`` maintenance database, because
    ``CREATE DATABASE`` cannot run inside a transaction or from within the
    database being created.
    """
    database = url.database or ""
    # CREATE DATABASE cannot take a bound parameter for its identifier, so the
    # name is interpolated. Constrain it first: this value comes from an
    # environment variable, and an embedded quote would append arbitrary DDL to a
    # statement running with AUTOCOMMIT on the maintenance database.
    if not re.fullmatch(r"[A-Za-z0-9_]{1,63}", database):
        raise ValueError(
            f"refusing to create test database {database!r}: the name must be 1-63 "
            "characters of ASCII letters, digits, or underscores"
        )
    admin_engine = create_async_engine(
        url.set(database="postgres"), isolation_level="AUTOCOMMIT", poolclass=NullPool
    )
    try:
        async with admin_engine.connect() as conn:
            exists = await conn.scalar(
                text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": database}
            )
            if not exists:
                await conn.execute(text(f'CREATE DATABASE "{database}"'))
    finally:
        await admin_engine.dispose()


async def _reset_schema(url: URL) -> None:
    engine = create_async_engine(url, poolclass=NullPool)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
    finally:
        await engine.dispose()


async def _prepare_database() -> None:
    url = make_url(TEST_DATABASE_URL)
    await _create_database_if_missing(url)
    await _reset_schema(url)


@pytest.fixture(scope="session")
def prepared_database() -> None:
    """Create the test database if needed and reset its schema, once per run.

    Not autouse either: pulled in by ``engine``, so a run that selects only
    database-free tests never contacts PostgreSQL at all.

    Runs in its own short-lived event loop so no connection outlives it; the
    per-test engines below open fresh connections in the loop that uses them.
    """
    try:
        asyncio.run(_prepare_database())
    except Exception as exc:
        # Deliberately broad. Driver-level failures do not share a base class the
        # way SQLAlchemy's do — a wrong password raises asyncpg's
        # InvalidPasswordError, which is not a SQLAlchemyError — and letting any
        # of them escape produces an identical raw traceback on every single
        # test instead of one actionable message. The hint names connectivity as
        # a likely cause rather than the cause, since a schema or permissions
        # failure lands here too.
        pytest.exit(f"{PREPARE_FAILED_HINT}\n\n{type(exc).__name__}: {exc}", returncode=1)


async def _truncate_all(engine: AsyncEngine) -> None:
    tables = ", ".join(f'"{table.name}"' for table in Base.metadata.sorted_tables)
    async with engine.begin() as conn:
        await conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))


@pytest_asyncio.fixture
async def engine(prepared_database: None) -> AsyncIterator[AsyncEngine]:
    """A per-test engine over an empty schema.

    Not autouse: the URL-parsing, normalisation, and config tests touch no
    database, and making them open a connection and truncate eight tables would
    put a PostgreSQL server between a contributor and a pure-function test suite.
    ``db_session`` and ``client`` depend on it, so anything that can write state
    still gets a clean schema.

    Truncating on setup rather than teardown means an interrupted run cannot leak
    rows into the next one. ``NullPool`` keeps connections from being reused
    across event loops, which asyncpg does not allow.
    """
    test_engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
    await _truncate_all(test_engine)
    try:
        yield test_engine
    finally:
        await test_engine.dispose()


@pytest_asyncio.fixture
async def db_session(engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        yield session


class FakeRedis:
    """Minimal in-memory Redis supporting the commands the app actually issues."""

    def __init__(self) -> None:
        self.store: dict[str, int] = {}

    async def incr(self, key: str) -> int:
        self.store[key] = self.store.get(key, 0) + 1
        return self.store[key]

    async def expire(self, key: str, ttl: int) -> bool:
        return True

    async def ping(self) -> bool:
        return True

    async def aclose(self) -> None:
        return None


class FailingRedis:
    """Stand-in Redis whose commands always raise, simulating an outage."""

    async def incr(self, *args: object, **kwargs: object) -> int:
        raise RedisError("redis unavailable")

    async def expire(self, *args: object, **kwargs: object) -> bool:  # pragma: no cover
        raise RedisError("redis unavailable")

    async def ping(self) -> bool:  # pragma: no cover
        raise RedisError("redis unavailable")

    async def aclose(self) -> None:
        return None


@pytest.fixture(autouse=True)
def enqueued_tasks(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, str]]:
    """Record Celery hand-offs instead of dispatching them to a broker.

    Both routers import their enqueue helper by value, so the patch has to land
    on the router module rather than on ``app.workers.tasks``.
    """
    recorded: list[tuple[str, str]] = []
    monkeypatch.setattr(
        watches_module,
        "enqueue_immediate_lookup",
        lambda product_id: recorded.append(("immediate_lookup", product_id)),
    )
    monkeypatch.setattr(
        webhooks_module,
        "enqueue_provider_event",
        lambda event_id: recorded.append(("provider_event", event_id)),
    )
    return recorded


@pytest.fixture
def client(engine: AsyncEngine) -> Iterator[TestClient]:
    """An unauthenticated client backed by the test database.

    The application's own engine already points at that database via the
    environment above; only Redis is swapped, so the rate limiter has
    deterministic state and the suite needs no Redis server.
    """
    with TestClient(app) as test_client:
        # Restored on teardown: `app` is a module-level singleton, and a test that
        # installs FailingRedis would otherwise leave it there for whatever runs
        # next.
        previous = getattr(app.state, "redis", None)
        app.state.redis = FakeRedis()
        try:
            yield test_client
        finally:
            app.state.redis = previous


@pytest.fixture
def authenticate(client: TestClient) -> Iterator[Callable[[AuthUser], TestClient]]:
    """Bypass JWT verification only, and default to the primary identity.

    ``get_current_user`` and its ``upsert_user`` call stay real, so every request
    still exercises the PostgreSQL upsert path. Call the returned function with
    ``OTHER_IDENTITY`` to act as a second user against the same database.
    """

    def use(identity: AuthUser) -> TestClient:
        app.dependency_overrides[get_current_identity] = lambda: identity
        return client

    use(PRIMARY_IDENTITY)
    try:
        yield use
    finally:
        app.dependency_overrides.pop(get_current_identity, None)


@pytest.fixture
def authed_client(authenticate: Callable[[AuthUser], TestClient]) -> TestClient:
    return authenticate(PRIMARY_IDENTITY)


@pytest.fixture
def brightdata_client_factory() -> Callable[..., tuple[BrightDataClient, httpx.AsyncClient]]:
    def make(
        settings: Settings,
        handler: Callable[[httpx.Request], httpx.Response],
    ) -> tuple[BrightDataClient, httpx.AsyncClient]:
        http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        return BrightDataClient(settings, http_client=http_client), http_client

    return make
