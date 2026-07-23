from __future__ import annotations

import uuid
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.clerk import AuthUser
from app.config import get_settings
from app.main import app
from app.models import (
    AlertState,
    AvailabilityStatus,
    PriceObservation,
    ProviderName,
    Store,
    StoreProduct,
    Watch,
)
from tests.conftest import OTHER_IDENTITY, PRIMARY_IDENTITY, FailingRedis

AMAZON_URL = "https://www.amazon.com/dp/B08N5WRWNW"
AMAZON_ASIN = "B08N5WRWNW"
EBAY_URL = "https://www.ebay.com/itm/123456789012"


def post_watch(
    client: TestClient,
    *,
    url: str = AMAZON_URL,
    target_price_minor: int = 12_000,
    currency: str = "USD",
    **extra: object,
) -> httpx.Response:
    body: dict[str, object] = {
        "url": url,
        "target_price_minor": target_price_minor,
        "currency": currency,
        **extra,
    }
    return client.post("/api/v1/watches", json=body)


@contextmanager
def override_settings(**changes: Any) -> Iterator[None]:
    """Lower a limit for one test, so limit tests need not create 50 watches.

    Copies the real settings rather than rebuilding them, so only the named
    fields differ from what the application actually runs with.
    """
    overridden = get_settings().model_copy(update=changes)
    app.dependency_overrides[get_settings] = lambda: overridden
    try:
        yield
    finally:
        app.dependency_overrides.pop(get_settings, None)


# --- Create -------------------------------------------------------------------


async def test_create_watch_persists_product_and_enqueues_lookup(
    authed_client: TestClient,
    db_session: AsyncSession,
    enqueued_tasks: list[tuple[str, str]],
) -> None:
    response = post_watch(authed_client)

    assert response.status_code == 202
    body = response.json()
    assert body["target_price_minor"] == 12_000
    assert body["currency"] == "USD"
    assert body["status"] == "active"
    assert body["alert_state"] == "armed"
    assert body["product"]["external_id"] == AMAZON_ASIN
    assert body["product"]["store"] == "amazon"
    # The adapter canonicalises the submitted URL rather than storing it as-is.
    assert body["product"]["canonical_url"] == AMAZON_URL

    product = (await db_session.scalars(select(StoreProduct))).one()
    assert product.region == "com"
    assert product.active is True
    watch = (await db_session.scalars(select(Watch))).one()
    assert watch.product_id == product.id

    assert enqueued_tasks == [("immediate_lookup", str(product.id))]


async def test_create_watch_defaults_both_notification_flags_on(
    authed_client: TestClient,
) -> None:
    body = post_watch(authed_client).json()

    assert body["notify_initial_below_target"] is True
    assert body["notify_back_in_stock"] is True


async def test_create_watch_honours_explicit_notification_flags(
    authed_client: TestClient,
) -> None:
    body = post_watch(
        authed_client,
        notify_initial_below_target=False,
        notify_back_in_stock=False,
    ).json()

    assert body["notify_initial_below_target"] is False
    assert body["notify_back_in_stock"] is False


async def test_create_watch_rejects_unsupported_url(authed_client: TestClient) -> None:
    response = post_watch(authed_client, url="https://example.com/product/1")

    assert response.status_code == 422
    assert "unsupported store host" in response.json()["detail"]


async def test_create_watch_rejects_ebay_auction_url(authed_client: TestClient) -> None:
    response = post_watch(authed_client, url="https://www.ebay.com/itm/123456789012?LH_Auction=1")

    assert response.status_code == 422
    assert "auction" in response.json()["detail"]


async def test_create_watch_rejects_duplicate_product(authed_client: TestClient) -> None:
    assert post_watch(authed_client).status_code == 202

    response = post_watch(authed_client)

    assert response.status_code == 409
    assert response.json()["detail"] == "this product is already watched"


async def test_create_watch_rejects_currency_mismatch(
    authed_client: TestClient, db_session: AsyncSession
) -> None:
    # A product the pipeline has already priced in EUR cannot be watched in USD.
    db_session.add(
        StoreProduct(
            store=Store.AMAZON,
            region="com",
            external_id=AMAZON_ASIN,
            canonical_url=AMAZON_URL,
            currency="EUR",
        )
    )
    await db_session.commit()

    response = post_watch(authed_client, currency="USD")

    assert response.status_code == 422
    assert response.json()["detail"] == "product is priced in EUR"


async def test_create_watch_enforces_active_watch_limit(authed_client: TestClient) -> None:
    with override_settings(max_active_watches_per_user=1):
        assert post_watch(authed_client, url=AMAZON_URL).status_code == 202

        response = post_watch(authed_client, url=EBAY_URL)

    assert response.status_code == 409
    assert response.json()["detail"] == "active watch limit reached"


async def test_create_watch_enforces_hourly_rate_limit(authed_client: TestClient) -> None:
    with override_settings(watch_create_rate_limit_per_hour=1):
        assert post_watch(authed_client, url=AMAZON_URL).status_code == 202

        response = post_watch(authed_client, url=EBAY_URL)

    assert response.status_code == 429
    assert response.json()["detail"] == "watch creation rate limit exceeded"


async def test_create_watch_fails_closed_when_redis_unavailable(
    authed_client: TestClient,
) -> None:
    # The limiter guards paid provider lookups, so an outage must refuse rather
    # than degrade into an unlimited-create bypass.
    app.state.redis = FailingRedis()

    response = post_watch(authed_client)

    assert response.status_code == 503
    assert response.json()["detail"] == "watch creation is temporarily unavailable"


async def test_create_watch_requires_authentication(client: TestClient) -> None:
    response = post_watch(client)

    assert response.status_code == 401


# --- Read ---------------------------------------------------------------------


async def test_list_watches_excludes_other_users(
    authenticate: Callable[[AuthUser], TestClient],
    authed_client: TestClient,
) -> None:
    mine = post_watch(authed_client, url=AMAZON_URL).json()

    other = authenticate(OTHER_IDENTITY)
    assert other.get("/api/v1/watches").json() == []
    theirs = post_watch(other, url=EBAY_URL).json()
    assert [item["id"] for item in other.get("/api/v1/watches").json()] == [theirs["id"]]

    back_to_primary = authenticate(PRIMARY_IDENTITY)

    assert [item["id"] for item in back_to_primary.get("/api/v1/watches").json()] == [mine["id"]]


async def test_list_watches_filters_by_status(authed_client: TestClient) -> None:
    first = post_watch(authed_client, url=AMAZON_URL).json()
    post_watch(authed_client, url=EBAY_URL)
    authed_client.patch(f"/api/v1/watches/{first['id']}", json={"status": "paused"})

    active = authed_client.get("/api/v1/watches", params={"status": "active"}).json()
    paused = authed_client.get("/api/v1/watches", params={"status": "paused"}).json()

    assert [item["id"] for item in paused] == [first["id"]]
    assert first["id"] not in [item["id"] for item in active]
    assert len(active) == 1


async def test_get_watch_is_scoped_to_its_owner(
    authenticate: Callable[[AuthUser], TestClient],
    authed_client: TestClient,
) -> None:
    watch_id = post_watch(authed_client).json()["id"]
    assert authed_client.get(f"/api/v1/watches/{watch_id}").status_code == 200

    other = authenticate(OTHER_IDENTITY)

    assert other.get(f"/api/v1/watches/{watch_id}").status_code == 404


async def test_get_watch_returns_404_for_unknown_id(authed_client: TestClient) -> None:
    response = authed_client.get(f"/api/v1/watches/{uuid.uuid4()}")

    assert response.status_code == 404


# --- Update -------------------------------------------------------------------


async def test_update_watch_rearms_alert_state_with_new_target(
    authed_client: TestClient, db_session: AsyncSession
) -> None:
    watch_id = post_watch(authed_client).json()["id"]
    watch = await db_session.get(Watch, uuid.UUID(watch_id))
    assert watch is not None
    watch.alert_state = AlertState.TRIGGERED
    await db_session.commit()

    response = authed_client.patch(
        f"/api/v1/watches/{watch_id}", json={"target_price_minor": 9_500}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["target_price_minor"] == 9_500
    # A new target must re-open the watch for alerting.
    assert body["alert_state"] == "armed"


async def test_pausing_the_last_active_watch_deactivates_the_product(
    authed_client: TestClient, db_session: AsyncSession
) -> None:
    created = post_watch(authed_client).json()
    product_id = uuid.UUID(created["product"]["id"])

    response = authed_client.patch(f"/api/v1/watches/{created['id']}", json={"status": "paused"})

    assert response.status_code == 200
    assert response.json()["status"] == "paused"
    product = await db_session.get(StoreProduct, product_id)
    assert product is not None
    # No active watcher left, so the product must stop costing provider calls.
    assert product.active is False
    assert product.lease_until is None


async def test_resuming_a_watch_reactivates_the_product(
    authed_client: TestClient, db_session: AsyncSession
) -> None:
    created = post_watch(authed_client).json()
    product_id = uuid.UUID(created["product"]["id"])
    authed_client.patch(f"/api/v1/watches/{created['id']}", json={"status": "paused"})

    authed_client.patch(f"/api/v1/watches/{created['id']}", json={"status": "active"})

    product = await db_session.get(StoreProduct, product_id)
    assert product is not None
    assert product.active is True


async def test_update_watch_returns_a_refreshed_updated_at(authed_client: TestClient) -> None:
    # Regression: `updated_at` comes from a server-side onupdate, so the flush
    # expires it. Serialising the response without refreshing raised
    # MissingGreenlet and turned every PATCH into a 500.
    created = post_watch(authed_client).json()

    response = authed_client.patch(
        f"/api/v1/watches/{created['id']}", json={"notify_back_in_stock": False}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["updated_at"] is not None
    assert body["updated_at"] >= created["updated_at"]


async def test_update_watch_rejects_explicit_nulls(authed_client: TestClient) -> None:
    watch_id = post_watch(authed_client).json()["id"]

    response = authed_client.patch(f"/api/v1/watches/{watch_id}", json={"target_price_minor": None})

    assert response.status_code == 422
    assert response.json()["detail"] == "watch fields may not be null"


async def test_update_watch_is_scoped_to_its_owner(
    authenticate: Callable[[AuthUser], TestClient],
    authed_client: TestClient,
) -> None:
    watch_id = post_watch(authed_client).json()["id"]

    other = authenticate(OTHER_IDENTITY)

    response = other.patch(f"/api/v1/watches/{watch_id}", json={"target_price_minor": 1})
    assert response.status_code == 404


# --- Delete -------------------------------------------------------------------


async def test_delete_watch_deactivates_the_product(
    authed_client: TestClient, db_session: AsyncSession
) -> None:
    created = post_watch(authed_client).json()
    product_id = uuid.UUID(created["product"]["id"])

    response = authed_client.delete(f"/api/v1/watches/{created['id']}")

    assert response.status_code == 204
    assert (await db_session.scalars(select(Watch))).all() == []
    product = await db_session.get(StoreProduct, product_id)
    assert product is not None
    assert product.active is False
    assert product.lease_until is None


async def test_delete_watch_is_scoped_to_its_owner(
    authenticate: Callable[[AuthUser], TestClient],
    authed_client: TestClient,
) -> None:
    watch_id = post_watch(authed_client).json()["id"]

    other = authenticate(OTHER_IDENTITY)

    assert other.delete(f"/api/v1/watches/{watch_id}").status_code == 404


# --- History ------------------------------------------------------------------


async def _add_observation(
    session: AsyncSession, product_id: uuid.UUID, *, days_ago: int, price_minor: int
) -> None:
    session.add(
        PriceObservation(
            product_id=product_id,
            price_minor=price_minor,
            item_price_minor=price_minor,
            shipping_price_minor=0,
            currency="USD",
            availability=AvailabilityStatus.IN_STOCK,
            observed_at=datetime.now(UTC) - timedelta(days=days_ago),
            source=ProviderName.BRIGHT_DATA,
        )
    )


async def test_watch_history_filters_by_range_and_is_newest_first(
    authed_client: TestClient, db_session: AsyncSession
) -> None:
    created = post_watch(authed_client).json()
    product_id = uuid.UUID(created["product"]["id"])
    await _add_observation(db_session, product_id, days_ago=1, price_minor=1_100)
    await _add_observation(db_session, product_id, days_ago=20, price_minor=2_200)
    await _add_observation(db_session, product_id, days_ago=200, price_minor=3_300)
    await db_session.commit()

    recent = authed_client.get(
        f"/api/v1/watches/{created['id']}/history", params={"range": "7d"}
    ).json()
    monthly = authed_client.get(
        f"/api/v1/watches/{created['id']}/history", params={"range": "30d"}
    ).json()
    everything = authed_client.get(
        f"/api/v1/watches/{created['id']}/history", params={"range": "all"}
    ).json()

    assert [point["price_minor"] for point in recent] == [1_100]
    assert [point["price_minor"] for point in monthly] == [1_100, 2_200]
    assert [point["price_minor"] for point in everything] == [1_100, 2_200, 3_300]


async def test_watch_history_honours_limit(
    authed_client: TestClient, db_session: AsyncSession
) -> None:
    created = post_watch(authed_client).json()
    product_id = uuid.UUID(created["product"]["id"])
    for day in range(4):
        await _add_observation(db_session, product_id, days_ago=day, price_minor=1_000 + day)
    await db_session.commit()

    body = authed_client.get(f"/api/v1/watches/{created['id']}/history", params={"limit": 2}).json()

    assert len(body) == 2


async def test_watch_history_is_scoped_to_its_owner(
    authenticate: Callable[[AuthUser], TestClient],
    authed_client: TestClient,
) -> None:
    watch_id = post_watch(authed_client).json()["id"]

    other = authenticate(OTHER_IDENTITY)

    assert other.get(f"/api/v1/watches/{watch_id}/history").status_code == 404


async def test_watch_status_query_rejects_unknown_value(authed_client: TestClient) -> None:
    response = authed_client.get("/api/v1/watches", params={"status": "archived"})

    assert response.status_code == 422
