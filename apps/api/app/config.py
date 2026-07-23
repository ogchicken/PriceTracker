from __future__ import annotations

import ipaddress
from functools import lru_cache
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_LOCAL_HOSTNAMES = {"localhost", "localhost.localdomain"}


def points_at_this_machine(url: str) -> bool:
    """Whether a connection URL targets the local machine.

    Matched by resolved meaning rather than by spelling: the development
    defaults use 127.0.0.1 (Compose publishes on IPv4 only, and resolving
    localhost costs a failed ::1 attempt first), so a check for the literal
    string "localhost" would wave those same defaults through in production.
    """
    try:
        host = urlsplit(url).hostname
    except ValueError:
        return False
    if not host:
        return False
    host = host.lower().rstrip(".")
    if host in _LOCAL_HOSTNAMES:
        return True
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return False
    return address.is_loopback or address.is_unspecified


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="PRICETRACKER_",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "PriceTracker API"
    environment: Literal["development", "test", "staging", "production"] = "development"
    service_role: Literal["all", "api", "worker", "scheduler"] = "all"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"
    allowed_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/pricetracker"
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str | None = None
    celery_result_backend: str | None = None

    clerk_issuer: str = "https://example.clerk.accounts.dev"
    clerk_audience: str | None = None
    clerk_authorized_parties: list[str] = Field(default_factory=list)
    clerk_jwks_url: str | None = None
    clerk_jwks_json: str | None = None
    clerk_pem_public_key: str | None = None
    clerk_webhook_secret: str | None = None

    bright_data_api_base_url: str = "https://api.brightdata.com"
    bright_data_api_token: str | None = None
    bright_data_amazon_dataset_id: str | None = None
    bright_data_ebay_dataset_id: str | None = None
    bright_data_webhook_url: str | None = None
    bright_data_webhook_secret: str | None = None

    # Price provider selection. "fake" is a development/test-only stand-in that
    # returns deterministic synthetic prices without calling Bright Data; it is
    # rejected in staging and production (see guard_unsafe_modes).
    price_provider: Literal["bright_data", "fake"] = "bright_data"
    fake_provider_delay_seconds: float = 2.0
    fake_fixtures_path: str | None = None

    resend_api_key: str | None = None
    email_from: str = "PriceTracker <alerts@example.test>"
    frontend_base_url: str = "http://localhost:3000"

    tracking_interval_hours: int = 6
    tracking_jitter_minutes: int = 30
    product_lease_minutes: int = 15
    provider_job_stale_minutes: int = 45
    provider_max_attempts: int = 5
    alert_rearm_percent: int = 3
    max_active_watches_per_user: int = 50
    watch_create_rate_limit_per_hour: int = 20
    webhook_max_bytes: int = 5_000_000

    log_level: str = "INFO"

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_postgres_driver(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        if value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql+asyncpg://", 1)
        if value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+asyncpg://", 1)
        return value

    @property
    def effective_celery_broker_url(self) -> str:
        return self.celery_broker_url or self.redis_url

    @property
    def effective_celery_result_backend(self) -> str:
        return self.celery_result_backend or self.redis_url

    @property
    def effective_clerk_jwks_url(self) -> str:
        return self.clerk_jwks_url or f"{self.clerk_issuer.rstrip('/')}/.well-known/jwks.json"

    @model_validator(mode="after")
    def guard_unsafe_modes(self) -> Settings:
        if self.environment in {"staging", "production"}:
            if self.price_provider != "bright_data":
                raise ValueError("the fake price provider is not allowed in staging or production")
            validates_api = self.service_role in {"all", "api"}
            validates_worker = self.service_role in {"all", "worker"}
            required: dict[str, object] = {
                "database_url": self.database_url,
                "redis_url": self.redis_url,
            }
            if validates_api:
                required.update(
                    {
                        "frontend_base_url": self.frontend_base_url,
                        "allowed_origins": self.allowed_origins,
                        "clerk_issuer": self.clerk_issuer,
                        "clerk_audience": self.clerk_audience,
                        "clerk_authorized_parties": self.clerk_authorized_parties,
                        "clerk_webhook_secret": self.clerk_webhook_secret,
                        "bright_data_webhook_secret": self.bright_data_webhook_secret,
                    }
                )
            if validates_worker:
                required.update(
                    {
                        "bright_data_api_token": self.bright_data_api_token,
                        "bright_data_amazon_dataset_id": self.bright_data_amazon_dataset_id,
                        "bright_data_ebay_dataset_id": self.bright_data_ebay_dataset_id,
                        "bright_data_webhook_url": self.bright_data_webhook_url,
                        "bright_data_webhook_secret": self.bright_data_webhook_secret,
                        "resend_api_key": self.resend_api_key,
                        "email_from": self.email_from,
                    }
                )
            missing = [name for name, value in required.items() if not value]
            if missing:
                raise ValueError(f"missing required deployment settings: {', '.join(missing)}")
            if points_at_this_machine(self.database_url) or points_at_this_machine(self.redis_url):
                raise ValueError(
                    "production data services may not point at this machine "
                    "(localhost, a loopback address, or 0.0.0.0)"
                )
            if validates_api:
                if "example.clerk.accounts.dev" in self.clerk_issuer:
                    raise ValueError("a real Clerk issuer is required outside development and test")
                public_urls = [self.frontend_base_url, *self.allowed_origins]
                if any(not url.startswith("https://") for url in public_urls):
                    raise ValueError("production frontend URLs and origins must use HTTPS")
                if any("*" in url for url in self.allowed_origins):
                    raise ValueError("production origins must not contain wildcards")
                if any(not party.startswith("https://") for party in self.clerk_authorized_parties):
                    raise ValueError("production Clerk authorized parties must use HTTPS")
            if validates_worker:
                webhook_url = self.bright_data_webhook_url or ""
                if not webhook_url.startswith("https://"):
                    raise ValueError("the production Bright Data webhook URL must use HTTPS")
                if "example.test" in self.email_from:
                    raise ValueError("a verified production sender is required")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
