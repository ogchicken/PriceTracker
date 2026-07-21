from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
VALIDATOR = ROOT / "scripts" / "check_live_env.py"


def valid_environment() -> dict[str, str]:
    return {
        "COMPOSE_PROFILES": "prod",
        "DOMAIN": "app.example.com",
        "ACME_EMAIL": "ops@example.com",
        "NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY": "pk_live_valid",
        "CLERK_SECRET_KEY": "sk_live_valid",
        "CLERK_JWT_TEMPLATE_NAME": "pricetracker-api",
        "PRICETRACKER_ENVIRONMENT": "production",
        "PRICETRACKER_DEBUG": "false",
        "PRICETRACKER_FRONTEND_BASE_URL": "https://app.example.com",
        "PRICETRACKER_ALLOWED_ORIGINS": '["https://app.example.com"]',
        "PRICETRACKER_CLERK_ISSUER": "https://clerk.app.example.com",
        "PRICETRACKER_CLERK_AUDIENCE": "pricetracker-api",
        "PRICETRACKER_CLERK_AUTHORIZED_PARTIES": '["https://app.example.com"]',
        "PRICETRACKER_CLERK_WEBHOOK_SECRET": "whsec_valid",
        "PRICETRACKER_BRIGHT_DATA_API_TOKEN": "bright-data-token",
        "PRICETRACKER_BRIGHT_DATA_AMAZON_DATASET_ID": "gd_amazon",
        "PRICETRACKER_BRIGHT_DATA_EBAY_DATASET_ID": "gd_ebay",
        "PRICETRACKER_BRIGHT_DATA_WEBHOOK_URL": (
            "https://app.example.com/api/v1/webhooks/bright-data"
        ),
        "PRICETRACKER_BRIGHT_DATA_WEBHOOK_SECRET": "a-secure-random-secret-value",
        "PRICETRACKER_RESEND_API_KEY": "re_valid",
        "PRICETRACKER_EMAIL_FROM": "PriceTracker <alerts@example.com>",
        "POSTGRES_PASSWORD": "a-secure-random-database-password",
    }


def run_validator(tmp_path: Path, values: dict[str, str]) -> subprocess.CompletedProcess[str]:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "".join(f"{key}={value}\n" for key, value in values.items()),
        encoding="utf-8",
    )
    return subprocess.run(
        [sys.executable, str(VALIDATOR), "--env-file", str(env_file)],
        check=False,
        capture_output=True,
        text=True,
    )


def test_valid_production_environment_passes(tmp_path: Path) -> None:
    result = run_validator(tmp_path, valid_environment())

    assert result.returncode == 0, result.stdout
    assert "Production environment looks ready." in result.stdout


def test_debug_mode_fails_production_validation(tmp_path: Path) -> None:
    values = valid_environment()
    values["PRICETRACKER_DEBUG"] = "true"

    result = run_validator(tmp_path, values)

    assert result.returncode == 1
    assert "PRICETRACKER_DEBUG must be false in production" in result.stdout


def test_short_bright_data_webhook_secret_fails_validation(tmp_path: Path) -> None:
    values = valid_environment()
    values["PRICETRACKER_BRIGHT_DATA_WEBHOOK_SECRET"] = "short"

    result = run_validator(tmp_path, values)

    assert result.returncode == 1
    assert (
        "PRICETRACKER_BRIGHT_DATA_WEBHOOK_SECRET must contain at least 24 characters"
        in result.stdout
    )
