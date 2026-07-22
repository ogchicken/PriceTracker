from __future__ import annotations

import hashlib
import json
import math
import uuid
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.config import Settings
from app.models import Store
from app.providers.base import PriceProvider, TriggeredSnapshot
from app.providers.brightdata import BrightDataError

# Mirror of the exponents used by app.providers.brightdata so that the major-unit
# strings emitted here round-trip cleanly back through ``normalize_result``.
_CURRENCY_EXPONENTS = {"BHD": 3, "JPY": 0, "KWD": 3}

_PLACEHOLDER_IMAGE = "https://example.test/fake-product.png"


class FakeProviderError(BrightDataError):
    """Fake-provider failure.

    Subclasses ``BrightDataError`` so the tracking pipeline degrades identically
    for fake and real providers (the fake masquerades as bright_data throughout).
    """


def _seed(external_id: str) -> int:
    return int(hashlib.sha256(external_id.encode("utf-8")).hexdigest(), 16)


def _base_minor(external_id: str) -> int:
    """Stable base price (minor units) in the $5.00 .. $499.99 range."""
    return 500 + (_seed(external_id) % 49_500)


def synthesize_price_minor(external_id: str, tick: int) -> int:
    """Deterministic, oscillating price (minor units) for a product and tick.

    The price is a stable per-product base plus a sine wave keyed to ``tick``
    (the number of prior observations for the product). Repeated checks move the
    price above and below any reasonable target, exercising both the price-drop
    trigger and the re-arm paths in ``app.services.alerts.evaluate_alert``.
    """
    base = _base_minor(external_id)
    amplitude = max(base // 5, 100)  # +/- ~20% of the base, at least $1.00
    phase_deg = (_seed(external_id) % 360) + tick * 37  # full cycle ~ every 10 checks
    delta = round(amplitude * math.sin(math.radians(phase_deg)))
    return max(base + delta, 100)  # floor at $1.00


def _minor_to_major(minor: int, currency: str) -> str:
    exponent = _CURRENCY_EXPONENTS.get(currency.upper(), 2)
    if exponent == 0:
        return str(minor)
    quantum = 10**exponent
    return f"{minor // quantum}.{minor % quantum:0{exponent}d}"


@lru_cache(maxsize=8)
def _load_fixtures(path: str) -> dict[str, dict[str, Any]]:
    try:
        raw = Path(path).read_text(encoding="utf-8")
        data = json.loads(raw)
    except (OSError, json.JSONDecodeError) as exc:
        raise FakeProviderError(f"could not read fake fixtures at {path}") from exc
    if not isinstance(data, dict):
        raise FakeProviderError("fake fixtures file must be a JSON object keyed by external_id")
    fixtures: dict[str, dict[str, Any]] = {}
    for key, entry in data.items():
        if str(key).startswith("_"):
            continue  # allow "_comment"-style annotation keys
        if not isinstance(entry, dict):
            raise FakeProviderError(f"fake fixture for {key!r} must be an object")
        if "price" not in entry and "prices" not in entry:
            raise FakeProviderError(f"fake fixture for {key!r} needs 'price' or 'prices'")
        fixtures[str(key).upper()] = entry
    return fixtures


def _fixture_for(external_id: str, settings: Settings) -> dict[str, Any] | None:
    if not settings.fake_fixtures_path:
        return None
    return _load_fixtures(settings.fake_fixtures_path).get(external_id.upper())


def _resolve_price_minor(external_id: str, tick: int, overrides: dict[str, Any] | None) -> int:
    if overrides is not None and "prices" in overrides:
        series = overrides["prices"]
        if not isinstance(series, list) or not series:
            raise FakeProviderError(f"'prices' for {external_id!r} must be a non-empty list")
        index = min(max(tick, 0), len(series) - 1)  # settle on the last value
        return int(series[index])
    if overrides is not None and "price" in overrides:
        return int(overrides["price"])
    return synthesize_price_minor(external_id, tick)


def build_fake_result(
    store: Store,
    external_id: str,
    canonical_url: str,
    tick: int,
    settings: Settings,
    *,
    observed_at: datetime | None = None,
) -> dict[str, Any]:
    """Build one Bright-Data-shaped result dict for the fake pipeline.

    The shape matches what ``app.providers.brightdata.normalize_result`` expects,
    so synthetic results flow through the real normalization, alert, and
    notification code exactly like a genuine provider webhook.
    """
    overrides = _fixture_for(external_id, settings)
    price_minor = _resolve_price_minor(external_id, tick, overrides)
    seed = _seed(external_id)
    currency = str((overrides or {}).get("currency", "USD")).upper()
    shipping_minor = int((overrides or {}).get("shipping_price_minor", 499 if seed % 2 else 0))
    availability = (overrides or {}).get(
        "availability",
        "out of stock" if (seed + tick) % 20 == 0 else "in stock",
    )
    title = (overrides or {}).get("title", f"Fake Product {external_id[:8]}")
    image = (overrides or {}).get("image", _PLACEHOLDER_IMAGE)
    observed = observed_at or datetime.now(UTC)

    result: dict[str, Any] = {
        "url": canonical_url,
        "final_price": _minor_to_major(price_minor, currency),
        "currency": currency,
        "shipping_price": _minor_to_major(shipping_minor, currency),
        "availability": availability,
        "title": title,
        "image": image,
        "timestamp": observed.isoformat(),
    }
    if store is Store.AMAZON:
        result["asin"] = external_id
    else:
        result["item_id"] = external_id
    return result


class FakePriceProvider(PriceProvider):
    """Development/test price provider that never calls an external service.

    ``trigger`` schedules the ``tracking.deliver_fake_snapshot`` Celery task,
    which synthesizes deterministic results and feeds them through the real
    webhook-processing path, faithfully reproducing Bright Data's asynchronous
    delivery. Results are always embedded in the delivered webhook, so the
    pull-based ``fetch_snapshot`` is never used.
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def dataset_id_for(self, store: Store) -> str:
        return f"fake-{store.value}"

    async def trigger(self, store: Store, urls: list[str]) -> TriggeredSnapshot:
        if not urls:
            raise FakeProviderError("cannot trigger an empty snapshot")
        # Imported lazily to keep the providers layer free of a worker dependency.
        from app.workers.celery_app import celery_app

        snapshot_id = f"fake-{uuid.uuid4()}"
        celery_app.send_task(
            "tracking.deliver_fake_snapshot",
            args=[snapshot_id],
            countdown=max(self.settings.fake_provider_delay_seconds, 0.0),
        )
        return TriggeredSnapshot(snapshot_id=snapshot_id)

    async def fetch_snapshot(self, snapshot_id: str) -> list[dict[str, Any]]:
        raise FakeProviderError(
            "FakePriceProvider delivers results via the webhook path; "
            "fetch_snapshot should not be called"
        )

    async def aclose(self) -> None:
        return None
