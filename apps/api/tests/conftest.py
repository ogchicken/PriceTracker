from __future__ import annotations

import os
from collections.abc import Callable, Iterator

import httpx
import pytest
from fastapi.testclient import TestClient

os.environ["PRICETRACKER_ENVIRONMENT"] = "test"
os.environ["PRICETRACKER_DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["PRICETRACKER_REDIS_URL"] = "redis://localhost:6379/15"

from app.config import Settings  # noqa: E402
from app.main import app  # noqa: E402
from app.providers.brightdata import BrightDataClient  # noqa: E402


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def brightdata_client_factory() -> Callable[..., tuple[BrightDataClient, httpx.AsyncClient]]:
    def make(
        settings: Settings,
        handler: Callable[[httpx.Request], httpx.Response],
    ) -> tuple[BrightDataClient, httpx.AsyncClient]:
        http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        return BrightDataClient(settings, http_client=http_client), http_client

    return make
