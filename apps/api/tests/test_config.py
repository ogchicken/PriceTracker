from typing import Any

import pytest
from pydantic import ValidationError

from app.config import Settings


def production_api_settings() -> dict[str, Any]:
    return {
        "environment": "production",
        "service_role": "api",
        "database_url": "postgresql://user:password@database.internal/pricetracker",
        "redis_url": "rediss://redis.internal:6379/0",
        "frontend_base_url": "https://app.example.com",
        "allowed_origins": ["https://app.example.com"],
        "clerk_issuer": "https://pricetracker.clerk.accounts.dev",
        "clerk_audience": "pricetracker-api",
        "clerk_authorized_parties": ["https://app.example.com"],
        "clerk_webhook_secret": "whsec_clerk",
        "bright_data_webhook_secret": "bright-data-webhook-secret",
    }


def test_render_postgres_url_uses_asyncpg_driver() -> None:
    settings = Settings(database_url="postgres://user:password@database.internal/pricetracker")

    assert settings.database_url.startswith("postgresql+asyncpg://")


def test_production_api_configuration_is_role_aware() -> None:
    settings = Settings(**production_api_settings())

    assert settings.service_role == "api"
    assert settings.database_url.startswith("postgresql+asyncpg://")


def test_production_worker_requires_live_provider_and_email() -> None:
    settings = Settings(
        environment="production",
        service_role="worker",
        database_url="postgresql://user:password@database.internal/pricetracker",
        redis_url="rediss://redis.internal:6379/0",
        bright_data_api_token="bright-data-token",
        bright_data_amazon_dataset_id="amazon-dataset",
        bright_data_ebay_dataset_id="ebay-dataset",
        bright_data_webhook_url="https://api.example.com/api/v1/webhooks/bright-data",
        bright_data_webhook_secret="bright-data-webhook-secret",
        resend_api_key="re_live",
        email_from="PriceTracker <alerts@example.com>",
    )

    assert settings.service_role == "worker"


def test_production_scheduler_needs_only_data_services() -> None:
    settings = Settings(
        environment="production",
        service_role="scheduler",
        database_url="postgresql://user:password@database.internal/pricetracker",
        redis_url="rediss://redis.internal:6379/0",
    )

    assert settings.service_role == "scheduler"


def test_production_api_rejects_insecure_public_origin() -> None:
    values = production_api_settings()
    values["allowed_origins"] = ["http://app.example.com"]

    with pytest.raises(ValidationError, match="must use HTTPS"):
        Settings(**values)


@pytest.mark.parametrize(
    "database_url",
    [
        "postgresql://user:password@localhost:5432/pricetracker",
        # The development defaults ship 127.0.0.1, so a guard keyed on the
        # literal string "localhost" would let a copied .env reach production.
        "postgresql://user:password@127.0.0.1:5432/pricetracker",
        "postgresql://user:password@127.1.2.3:5432/pricetracker",
        "postgresql://user:password@[::1]:5432/pricetracker",
        "postgresql://user:password@0.0.0.0:5432/pricetracker",
    ],
)
def test_production_rejects_a_database_on_this_machine(database_url: str) -> None:
    values = production_api_settings()
    values["database_url"] = database_url

    with pytest.raises(ValidationError, match="may not point at this machine"):
        Settings(**values)


@pytest.mark.parametrize(
    "redis_url",
    ["redis://localhost:6379/0", "redis://127.0.0.1:6379/0", "redis://[::1]:6379/0"],
)
def test_production_rejects_a_redis_on_this_machine(redis_url: str) -> None:
    values = production_api_settings()
    values["redis_url"] = redis_url

    with pytest.raises(ValidationError, match="may not point at this machine"):
        Settings(**values)


def test_production_allows_a_remote_host_that_merely_contains_a_local_name() -> None:
    # "localhost" as a substring of a real hostname is not a loopback target;
    # the previous substring check rejected this.
    values = production_api_settings()
    values["database_url"] = "postgresql://user:password@localhost.db.example.com/pricetracker"

    assert Settings(**values).database_url.startswith("postgresql+asyncpg://")


def test_production_rejects_fake_price_provider() -> None:
    values = production_api_settings()
    values["price_provider"] = "fake"

    with pytest.raises(ValidationError, match="fake price provider"):
        Settings(**values)
