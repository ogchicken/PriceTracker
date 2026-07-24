from __future__ import annotations

import pytest
from sqlalchemy.engine import make_url

from tests.conftest import _validate_test_database_url


@pytest.mark.parametrize("database", ["pricetracker_pytest", "custom_123_pytest"])
def test_test_database_guard_accepts_pytest_suffix(database: str) -> None:
    url = make_url(f"postgresql+asyncpg://user:password@database.internal/{database}")

    assert _validate_test_database_url(url) == database


@pytest.mark.parametrize("database", ["pricetracker", "pricetracker_test", "postgres"])
def test_test_database_guard_rejects_non_pytest_databases(database: str) -> None:
    url = make_url(f"postgresql+asyncpg://user:password@database.internal/{database}")

    with pytest.raises(ValueError, match="must end in `_pytest`"):
        _validate_test_database_url(url)


@pytest.mark.parametrize("database", ["", "bad-name_pytest"])
def test_test_database_guard_rejects_invalid_identifiers(database: str) -> None:
    url = make_url(f"postgresql+asyncpg://user:password@database.internal/{database}")

    with pytest.raises(ValueError, match="ASCII letters"):
        _validate_test_database_url(url)
