from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any

import httpx

from app.config import Settings
from app.models import AvailabilityStatus, Store
from app.providers.adapters import AdapterError, adapter_registry
from app.providers.base import PriceProvider, TriggeredSnapshot


class BrightDataError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class NormalizedObservation:
    external_id: str
    price_minor: int
    item_price_minor: int
    shipping_price_minor: int
    currency: str
    availability: AvailabilityStatus
    observed_at: datetime
    title: str | None
    image_url: str | None
    raw: dict[str, Any]


_CURRENCY_EXPONENTS = {"BHD": 3, "JPY": 0, "KWD": 3}


def money_to_minor(value: Any, currency: str = "USD") -> int:
    if value is None or isinstance(value, bool):
        raise ValueError("price is missing")
    if isinstance(value, str):
        cleaned = re.sub(r"[^\d,.\-]", "", value.strip())
        if not cleaned:
            raise ValueError("price is invalid")
        if "," in cleaned and "." not in cleaned:
            tail = cleaned.rsplit(",", 1)[1]
            cleaned = cleaned.replace(",", ".") if len(tail) in {1, 2} else cleaned.replace(",", "")
        else:
            cleaned = cleaned.replace(",", "")
    else:
        cleaned = str(value)
    try:
        amount = Decimal(cleaned)
    except InvalidOperation as exc:
        raise ValueError("price is invalid") from exc
    if not amount.is_finite() or amount < 0:
        raise ValueError("price must be a finite non-negative amount")
    exponent = _CURRENCY_EXPONENTS.get(currency.upper(), 2)
    multiplier = Decimal(10) ** exponent
    minor = int((amount * multiplier).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    if minor > 9_000_000_000_000_000_000:
        raise ValueError("price exceeds the supported range")
    return minor


def _first(payload: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = payload.get(key)
        if value not in (None, ""):
            return value
    return None


def _shipping_to_minor(value: Any, currency: str) -> int:
    if value in (None, "", 0):
        return 0
    if isinstance(value, str) and value.strip().lower() in {
        "free",
        "free shipping",
        "included",
    }:
        return 0
    if isinstance(value, dict):
        value = _first(value, "value", "amount", "price")
    return money_to_minor(value, currency)


def _availability(payload: dict[str, Any]) -> AvailabilityStatus:
    raw = str(
        _first(payload, "availability", "stock_status", "availability_status", "in_stock") or ""
    ).lower()
    if raw in {"true", "1", "in stock", "available", "available now"}:
        return AvailabilityStatus.IN_STOCK
    if raw in {"false", "0", "out of stock", "sold out", "temporarily unavailable"}:
        return AvailabilityStatus.OUT_OF_STOCK
    if raw in {"unavailable", "ended", "removed", "not found"}:
        return AvailabilityStatus.UNAVAILABLE
    return AvailabilityStatus.UNKNOWN


def normalize_result(store: Store, payload: dict[str, Any]) -> NormalizedObservation:
    if store is Store.EBAY:
        listing_type = str(
            _first(payload, "listing_type", "buying_format", "format", "sale_type") or ""
        ).lower()
        if any(marker in listing_type for marker in ("auction", "bid")):
            raise ValueError("eBay auction results are not supported")
    currency_value = _first(payload, "currency", "currency_code", "price_currency")
    price_value = _first(
        payload,
        "final_price",
        "price",
        "current_price",
        "buy_it_now_price",
        "sale_price",
    )
    if isinstance(price_value, dict):
        currency_value = currency_value or _first(
            price_value,
            "currency",
            "currency_code",
        )
        price_value = _first(price_value, "value", "amount", "price")
    currency = str(currency_value or "USD").upper()
    item_price_minor = money_to_minor(price_value, currency)
    shipping_price_minor = _shipping_to_minor(
        _first(payload, "shipping_price", "shipping_cost", "delivery_price"),
        currency,
    )
    external_id = _first(payload, "asin", "item_id", "product_id", "sku")
    if external_id is None:
        source_url = _first(payload, "url", "input_url", "product_url")
        if source_url:
            try:
                normalized = adapter_registry.parse(str(source_url))
            except AdapterError as exc:
                raise ValueError("provider result has no supported product identifier") from exc
            if normalized.store is not store:
                raise ValueError("provider result store does not match job store")
            external_id = normalized.external_id
    if external_id is None:
        raise ValueError("provider result has no product identifier")
    external_id = str(external_id).upper() if store is Store.AMAZON else str(external_id)
    observed = _first(payload, "observed_at", "timestamp", "scraped_at")
    if isinstance(observed, str):
        try:
            observed_at = datetime.fromisoformat(observed.replace("Z", "+00:00"))
        except ValueError:
            observed_at = datetime.now(UTC)
    elif isinstance(observed, datetime):
        observed_at = observed
    else:
        observed_at = datetime.now(UTC)
    if observed_at.tzinfo is None:
        observed_at = observed_at.replace(tzinfo=UTC)
    return NormalizedObservation(
        external_id=external_id,
        price_minor=item_price_minor + shipping_price_minor,
        item_price_minor=item_price_minor,
        shipping_price_minor=shipping_price_minor,
        currency=currency,
        availability=_availability(payload),
        observed_at=observed_at,
        title=_first(payload, "title", "name", "product_name"),
        image_url=_first(payload, "image", "image_url", "main_image", "thumbnail"),
        raw=payload,
    )


class BrightDataClient(PriceProvider):
    def __init__(self, settings: Settings, http_client: httpx.AsyncClient | None = None) -> None:
        self.settings = settings
        self._client = http_client or httpx.AsyncClient(
            base_url=self.settings.bright_data_api_base_url,
            timeout=httpx.Timeout(30),
        )
        self._owns_client = http_client is None

    def dataset_id_for(self, store: Store) -> str:
        dataset_id = (
            self.settings.bright_data_amazon_dataset_id
            if store is Store.AMAZON
            else self.settings.bright_data_ebay_dataset_id
        )
        if not dataset_id:
            raise BrightDataError(f"Bright Data dataset ID is not configured for {store.value}")
        return dataset_id

    async def trigger(self, store: Store, urls: list[str]) -> TriggeredSnapshot:
        if not urls:
            raise BrightDataError("cannot trigger an empty snapshot")
        if not self.settings.bright_data_api_token:
            raise BrightDataError("Bright Data API token is not configured")
        if not self.settings.bright_data_webhook_url:
            raise BrightDataError("Bright Data webhook URL is not configured")
        if not self.settings.bright_data_webhook_secret:
            raise BrightDataError("Bright Data webhook secret is not configured")
        response = await self._client.post(
            f"{self.settings.bright_data_api_base_url.rstrip('/')}/datasets/v3/trigger",
            params={
                "dataset_id": self.dataset_id_for(store),
                "format": "json",
                "include_errors": "true",
                "endpoint": self.settings.bright_data_webhook_url,
                "uncompressed_webhook": "true",
                "webhook_header_Authorization": (
                    f"Bearer {self.settings.bright_data_webhook_secret}"
                ),
            },
            headers={"Authorization": f"Bearer {self.settings.bright_data_api_token}"},
            json=[{"url": url} for url in urls],
        )
        try:
            response.raise_for_status()
            data = response.json()
            snapshot_id = str(data["snapshot_id"])
        except (httpx.HTTPError, KeyError, ValueError) as exc:
            raise BrightDataError("Bright Data trigger failed") from exc
        return TriggeredSnapshot(snapshot_id=snapshot_id)

    async def fetch_snapshot(self, snapshot_id: str) -> list[dict[str, Any]]:
        if not self.settings.bright_data_api_token:
            raise BrightDataError("Bright Data API token is not configured")
        response = await self._client.get(
            (
                f"{self.settings.bright_data_api_base_url.rstrip('/')}"
                f"/datasets/v3/snapshot/{snapshot_id}"
            ),
            params={"format": "json"},
            headers={"Authorization": f"Bearer {self.settings.bright_data_api_token}"},
        )
        try:
            response.raise_for_status()
            data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise BrightDataError("Bright Data snapshot retrieval failed") from exc
        if not isinstance(data, list) or not all(isinstance(item, dict) for item in data):
            raise BrightDataError("Bright Data snapshot response was not a result list")
        return data

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()
