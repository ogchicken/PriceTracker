from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.models import (
    Alert,
    AlertState,
    AvailabilityStatus,
    NotificationOutbox,
    PriceObservation,
    ProviderJob,
    ProviderJobState,
    ProviderName,
    Store,
    StoreProduct,
    User,
    Watch,
    WatchStatus,
    WebhookEvent,
)
from app.providers.brightdata import BrightDataClient, normalize_result
from app.providers.factory import build_price_provider
from app.providers.fake import (
    FakePriceProvider,
    FakeProviderError,
    _base_minor,
    build_fake_result,
    synthesize_price_minor,
)
from app.services.tracking import process_brightdata_event

EXTERNAL_ID = "B00TEST1234"
CANONICAL_URL = "https://www.amazon.com/dp/B00TEST1234"


# --- Deterministic pricing ---------------------------------------------------


def test_price_is_deterministic() -> None:
    assert synthesize_price_minor(EXTERNAL_ID, 3) == synthesize_price_minor(EXTERNAL_ID, 3)


def test_price_oscillates_across_ticks() -> None:
    base = _base_minor(EXTERNAL_ID)
    prices = [synthesize_price_minor(EXTERNAL_ID, tick) for tick in range(24)]
    # A sine wave around the base must move the price both below and above it,
    # which is what lets repeated checks trigger and later re-arm an alert.
    assert min(prices) < base < max(prices)


def test_price_never_below_floor() -> None:
    for external_id in ("A", "ZZZZ", EXTERNAL_ID, "123456789012"):
        for tick in range(50):
            assert synthesize_price_minor(external_id, tick) >= 100


# --- Result shape round-trips through the real normalizer --------------------


def test_amazon_result_roundtrips_through_normalize() -> None:
    settings = Settings()
    result = build_fake_result(Store.AMAZON, EXTERNAL_ID, CANONICAL_URL, 0, settings)
    observation = normalize_result(Store.AMAZON, result)

    assert observation.external_id == EXTERNAL_ID
    assert observation.currency == "USD"
    assert (
        observation.price_minor == observation.item_price_minor + observation.shipping_price_minor
    )
    assert observation.availability in set(AvailabilityStatus)


def test_ebay_result_roundtrips_and_is_not_treated_as_auction() -> None:
    settings = Settings()
    item_id = "123456789012"
    url = "https://www.ebay.com/itm/123456789012"
    result = build_fake_result(Store.EBAY, item_id, url, 2, settings)

    # eBay auction guard in normalize_result must not trip on fixed-price fakes.
    observation = normalize_result(Store.EBAY, result)
    assert observation.external_id == item_id


# --- Fixtures overrides ------------------------------------------------------


def _write_fixtures(tmp_path: Path, data: dict) -> Settings:
    path = tmp_path / f"{uuid.uuid4().hex}.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return Settings(fake_fixtures_path=str(path))


def test_fixture_fixed_price(tmp_path: Path) -> None:
    settings = _write_fixtures(tmp_path, {EXTERNAL_ID: {"price": 2500}})
    result = build_fake_result(Store.AMAZON, EXTERNAL_ID, CANONICAL_URL, 7, settings)
    assert result["final_price"] == "25.00"


def test_fixture_price_series_is_consumed_by_tick(tmp_path: Path) -> None:
    settings = _write_fixtures(tmp_path, {EXTERNAL_ID: {"prices": [1000, 2000, 3000]}})
    prices = [
        build_fake_result(Store.AMAZON, EXTERNAL_ID, CANONICAL_URL, tick, settings)["final_price"]
        for tick in range(5)
    ]
    # Consumed one entry per check, then settles on the last value.
    assert prices == ["10.00", "20.00", "30.00", "30.00", "30.00"]


def test_fixture_absent_key_falls_back_to_deterministic(tmp_path: Path) -> None:
    settings = _write_fixtures(tmp_path, {"OTHER_ID": {"price": 100}})
    result = build_fake_result(Store.AMAZON, EXTERNAL_ID, CANONICAL_URL, 0, settings)
    expected = synthesize_price_minor(EXTERNAL_ID, 0)
    assert result["final_price"] == f"{expected // 100}.{expected % 100:02d}"


def test_fixture_comment_key_is_ignored(tmp_path: Path) -> None:
    settings = _write_fixtures(tmp_path, {"_comment": "notes", EXTERNAL_ID: {"price": 100}})
    result = build_fake_result(Store.AMAZON, EXTERNAL_ID, CANONICAL_URL, 0, settings)
    assert result["final_price"] == "1.00"


def test_malformed_fixture_raises(tmp_path: Path) -> None:
    path = tmp_path / f"{uuid.uuid4().hex}.json"
    path.write_text('{"B00X": {"note": "no price here"}}', encoding="utf-8")
    settings = Settings(fake_fixtures_path=str(path))
    with pytest.raises(FakeProviderError):
        build_fake_result(Store.AMAZON, "B00X", CANONICAL_URL, 0, settings)


# --- Factory selection + guards ----------------------------------------------


def test_factory_returns_fake_in_development() -> None:
    settings = Settings(price_provider="fake", environment="development")
    assert isinstance(build_price_provider(settings), FakePriceProvider)


def test_factory_returns_bright_data_by_default() -> None:
    settings = Settings(price_provider="bright_data", environment="development")
    assert isinstance(build_price_provider(settings), BrightDataClient)


def test_factory_refuses_fake_outside_dev_and_test() -> None:
    settings = Settings(price_provider="fake", environment="development")
    # Bypass the config validator to exercise the factory's own guard.
    object.__setattr__(settings, "environment", "production")
    with pytest.raises(RuntimeError, match="fake price provider"):
        build_price_provider(settings)


# --- End-to-end: synthetic webhook drives the real pipeline ------------------


@pytest.mark.asyncio
async def test_fake_delivery_creates_observation_and_alert(db_session: AsyncSession) -> None:
    settings = Settings()
    snapshot_id = "fake-e2e-snapshot"

    user = User(clerk_user_id="user_123", email="shopper@example.test", preferences_data={})
    product = StoreProduct(
        store=Store.AMAZON,
        region="com",
        external_id=EXTERNAL_ID,
        canonical_url=CANONICAL_URL,
        active=True,
    )
    db_session.add_all([user, product])
    await db_session.flush()

    first_price = synthesize_price_minor(EXTERNAL_ID, 0)
    watch = Watch(
        user_id=user.id,
        product_id=product.id,
        target_price_minor=first_price + 5_000,  # ensure the first price is below target
        currency="USD",
        status=WatchStatus.ACTIVE,
    )
    job = ProviderJob(
        provider=ProviderName.BRIGHT_DATA,
        external_job_id=snapshot_id,
        dataset_id="fake-amazon",
        state=ProviderJobState.RUNNING,
        product_ids=[str(product.id)],
        stale_after=datetime.now(UTC) + timedelta(minutes=45),
    )
    result = build_fake_result(Store.AMAZON, EXTERNAL_ID, CANONICAL_URL, 0, settings)
    event = WebhookEvent(
        provider="bright_data",
        external_event_id=f"fake-{snapshot_id}",
        payload={"snapshot_id": snapshot_id, "status": "ready", "results": [result]},
    )
    db_session.add_all([watch, job, event])
    await db_session.flush()

    created = await process_brightdata_event(
        db_session, settings, FakePriceProvider(settings), event.id
    )

    assert created == 1
    observation = (
        await db_session.scalars(
            select(PriceObservation).where(PriceObservation.product_id == product.id)
        )
    ).one()
    assert observation.source is ProviderName.BRIGHT_DATA
    assert product.current_price_minor == observation.price_minor

    await db_session.refresh(watch)
    assert watch.alert_state is AlertState.TRIGGERED

    alerts = (await db_session.scalars(select(Alert).where(Alert.watch_id == watch.id))).all()
    assert len(alerts) == 1
    notifications = (
        await db_session.scalars(
            select(NotificationOutbox).where(NotificationOutbox.alert_id == alerts[0].id)
        )
    ).all()
    # One in-app notification plus one email (user has an address, email enabled).
    assert len(notifications) == 2
