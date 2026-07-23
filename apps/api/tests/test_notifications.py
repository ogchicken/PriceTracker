from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.clerk import AuthUser
from app.models import (
    Alert,
    AlertKind,
    AvailabilityStatus,
    NotificationChannel,
    NotificationOutbox,
    NotificationStatus,
    PriceObservation,
    ProviderName,
    Store,
    User,
    Watch,
)
from app.providers.adapters import NormalizedProduct
from app.stores.repositories import upsert_store_product, upsert_user
from tests.conftest import OTHER_IDENTITY, PRIMARY_IDENTITY

PRODUCT = NormalizedProduct(
    store=Store.AMAZON,
    external_id="B08N5WRWNW",
    canonical_url="https://www.amazon.com/dp/B08N5WRWNW",
    region="com",
)


async def seed_notification(
    session: AsyncSession,
    identity: AuthUser,
    *,
    channel: NotificationChannel = NotificationChannel.IN_APP,
    read: bool = False,
    external_id: str | None = None,
) -> NotificationOutbox:
    """Build the user -> watch -> observation -> alert -> outbox chain a real alert produces."""
    suffix = external_id or uuid.uuid4().hex[:10].upper()
    user: User = await upsert_user(
        session, clerk_user_id=identity.clerk_user_id, email=identity.email
    )
    product = await upsert_store_product(
        session,
        NormalizedProduct(
            store=PRODUCT.store,
            external_id=suffix,
            canonical_url=f"https://www.amazon.com/dp/{suffix}",
            region=PRODUCT.region,
        ),
    )
    watch = Watch(user_id=user.id, product_id=product.id, target_price_minor=10_000, currency="USD")
    observation = PriceObservation(
        product_id=product.id,
        price_minor=9_000,
        item_price_minor=9_000,
        shipping_price_minor=0,
        currency="USD",
        availability=AvailabilityStatus.IN_STOCK,
        observed_at=datetime.now(UTC),
        source=ProviderName.BRIGHT_DATA,
    )
    session.add_all([watch, observation])
    await session.flush()
    alert = Alert(
        watch_id=watch.id,
        user_id=user.id,
        observation_id=observation.id,
        kind=AlertKind.PRICE_DROP,
        price_minor=9_000,
        target_price_minor=10_000,
        currency="USD",
        dedupe_key=f"{watch.id}:{observation.id}:price_drop",
    )
    session.add(alert)
    await session.flush()
    notification = NotificationOutbox(
        alert_id=alert.id,
        user_id=user.id,
        channel=channel,
        status=NotificationStatus.SENT,
        recipient=identity.email or "",
        dedupe_key=f"{channel.value}:{alert.dedupe_key}",
        payload={"kind": "price_drop", "product_title": "Test product", "price_minor": 9_000},
        read_at=datetime.now(UTC) if read else None,
    )
    session.add(notification)
    await session.commit()
    return notification


async def test_notifications_require_authentication(client: TestClient) -> None:
    assert client.get("/api/v1/notifications").status_code == 401


async def test_list_notifications_returns_in_app_rows(
    authed_client: TestClient, db_session: AsyncSession
) -> None:
    notification = await seed_notification(db_session, PRIMARY_IDENTITY)

    body = authed_client.get("/api/v1/notifications").json()

    assert [item["id"] for item in body] == [str(notification.id)]
    assert body[0]["channel"] == "in_app"
    assert body[0]["payload"]["product_title"] == "Test product"


async def test_list_notifications_hides_the_email_channel(
    authed_client: TestClient, db_session: AsyncSession
) -> None:
    # Email rows are outbox plumbing for the worker, not user-facing feed items.
    await seed_notification(db_session, PRIMARY_IDENTITY, channel=NotificationChannel.EMAIL)

    assert authed_client.get("/api/v1/notifications").json() == []


async def test_list_notifications_can_filter_to_unread(
    authed_client: TestClient, db_session: AsyncSession
) -> None:
    unread = await seed_notification(db_session, PRIMARY_IDENTITY, read=False)
    await seed_notification(db_session, PRIMARY_IDENTITY, read=True)

    everything = authed_client.get("/api/v1/notifications").json()
    only_unread = authed_client.get("/api/v1/notifications", params={"unread_only": True}).json()

    assert len(everything) == 2
    assert [item["id"] for item in only_unread] == [str(unread.id)]


async def test_list_notifications_excludes_other_users(
    authed_client: TestClient, db_session: AsyncSession
) -> None:
    await seed_notification(db_session, OTHER_IDENTITY)

    assert authed_client.get("/api/v1/notifications").json() == []


async def test_mark_notification_read_and_unread(
    authed_client: TestClient, db_session: AsyncSession
) -> None:
    notification = await seed_notification(db_session, PRIMARY_IDENTITY)

    marked = authed_client.patch(f"/api/v1/notifications/{notification.id}", json={"read": True})
    assert marked.status_code == 200
    assert marked.json()["read_at"] is not None

    cleared = authed_client.patch(f"/api/v1/notifications/{notification.id}", json={"read": False})
    assert cleared.json()["read_at"] is None


async def test_mark_notification_is_scoped_to_its_owner(
    authenticate: Callable[[AuthUser], TestClient],
    authed_client: TestClient,
    db_session: AsyncSession,
) -> None:
    notification = await seed_notification(db_session, PRIMARY_IDENTITY)

    other = authenticate(OTHER_IDENTITY)

    response = other.patch(f"/api/v1/notifications/{notification.id}", json={"read": True})
    assert response.status_code == 404


async def test_mark_unknown_notification_returns_404(authed_client: TestClient) -> None:
    response = authed_client.patch(f"/api/v1/notifications/{uuid.uuid4()}", json={"read": True})

    assert response.status_code == 404
