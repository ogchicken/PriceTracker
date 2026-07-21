from __future__ import annotations

import os
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

os.environ["PRICETRACKER_ENVIRONMENT"] = "test"
os.environ["PRICETRACKER_DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["PRICETRACKER_REDIS_URL"] = "redis://localhost:6379/15"
os.environ["PRICETRACKER_FAKE_PROVIDER_ENABLED"] = "true"
os.environ["PRICETRACKER_FAKE_AUTH_ENABLED"] = "false"

from app.main import app  # noqa: E402


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client
