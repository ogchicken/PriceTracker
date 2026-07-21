#!/usr/bin/env python3
"""Validate .env for real (non-demo) PriceTracker operation."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


REQUIRED = [
    "NEXT_PUBLIC_DEMO_MODE",
    "NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY",
    "CLERK_SECRET_KEY",
    "CLERK_JWT_TEMPLATE_NAME",
    "API_BASE_URL",
    "PRICETRACKER_FAKE_AUTH_ENABLED",
    "PRICETRACKER_FAKE_PROVIDER_ENABLED",
    "PRICETRACKER_CLERK_ISSUER",
    "PRICETRACKER_CLERK_AUDIENCE",
    "PRICETRACKER_CLERK_AUTHORIZED_PARTIES",
    "PRICETRACKER_CLERK_JWKS_URL",
    "PRICETRACKER_CLERK_WEBHOOK_SECRET",
    "PRICETRACKER_BRIGHT_DATA_API_TOKEN",
    "PRICETRACKER_BRIGHT_DATA_AMAZON_DATASET_ID",
    "PRICETRACKER_BRIGHT_DATA_EBAY_DATASET_ID",
    "PRICETRACKER_BRIGHT_DATA_WEBHOOK_URL",
    "PRICETRACKER_BRIGHT_DATA_WEBHOOK_SECRET",
    "PRICETRACKER_RESEND_API_KEY",
    "PRICETRACKER_EMAIL_FROM",
]


def parse_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--env-file",
        type=Path,
        default=Path(".env"),
        help="Path to the environment file (default: .env)",
    )
    args = parser.parse_args()
    if not args.env_file.exists():
        print(f"Missing {args.env_file}. Copy .env.example to .env first.")
        return 1

    env = parse_env(args.env_file)
    errors: list[str] = []
    warnings: list[str] = []

    for key in REQUIRED:
        if not env.get(key):
            errors.append(f"{key} is missing or empty")

    if env.get("NEXT_PUBLIC_DEMO_MODE", "true").lower() != "false":
        errors.append("NEXT_PUBLIC_DEMO_MODE must be false")
    if env.get("PRICETRACKER_FAKE_AUTH_ENABLED", "true").lower() != "false":
        errors.append("PRICETRACKER_FAKE_AUTH_ENABLED must be false")
    if env.get("PRICETRACKER_FAKE_PROVIDER_ENABLED", "true").lower() != "false":
        errors.append("PRICETRACKER_FAKE_PROVIDER_ENABLED must be false")

    issuer = env.get("PRICETRACKER_CLERK_ISSUER", "")
    if "replace-me" in issuer or "example.clerk" in issuer:
        errors.append("PRICETRACKER_CLERK_ISSUER still looks like a placeholder")

    webhook = env.get("PRICETRACKER_BRIGHT_DATA_WEBHOOK_URL", "")
    if webhook.startswith("http://localhost") or webhook.startswith("http://127."):
        errors.append(
            "PRICETRACKER_BRIGHT_DATA_WEBHOOK_URL must be a public HTTPS tunnel or "
            "production URL (Bright Data cannot call localhost)"
        )
    elif webhook and not webhook.startswith("https://"):
        errors.append("PRICETRACKER_BRIGHT_DATA_WEBHOOK_URL must use HTTPS")

    email_from = env.get("PRICETRACKER_EMAIL_FROM", "")
    if "example.test" in email_from:
        errors.append("PRICETRACKER_EMAIL_FROM still uses the example.test placeholder")

    if env.get("PRICETRACKER_CLERK_AUDIENCE") != "pricetracker-api":
        warnings.append(
            "PRICETRACKER_CLERK_AUDIENCE should match the aud claim in your Clerk "
            "JWT template (docs use pricetracker-api)."
        )
    if env.get("CLERK_JWT_TEMPLATE_NAME") != "pricetracker-api":
        warnings.append(
            "CLERK_JWT_TEMPLATE_NAME should match the Clerk JWT template name "
            "(docs use pricetracker-api)."
        )

    secret = env.get("PRICETRACKER_BRIGHT_DATA_WEBHOOK_SECRET", "")
    if secret and len(secret) < 24:
        warnings.append("PRICETRACKER_BRIGHT_DATA_WEBHOOK_SECRET should be a long random value")

    if not re.match(r"^pk_(test|live)_", env.get("NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY", "")):
        warnings.append("NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY does not look like a Clerk publishable key")
    if not re.match(r"^sk_(test|live)_", env.get("CLERK_SECRET_KEY", "")):
        warnings.append("CLERK_SECRET_KEY does not look like a Clerk secret key")

    for warning in warnings:
        print(f"WARNING: {warning}")
    if errors:
        print("Live-mode validation failed:")
        for error in errors:
            print(f"  - {error}")
        print("\nSee docs/go-live.md for the complete setup sequence.")
        return 1

    print("Live-mode environment looks ready.")
    print("Next: rebuild Compose so NEXT_PUBLIC_* values are baked into the web image.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
