"""Cover the repository layer's PostgreSQL-only ``INSERT ... ON CONFLICT`` paths."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Store, StoreProduct, User, Watch, WebhookEvent
from app.providers.adapters import NormalizedProduct
from app.stores.repositories import (
    get_owned_watch,
    record_webhook_event,
    upsert_store_product,
    upsert_user,
)

AMAZON_PRODUCT = NormalizedProduct(
    store=Store.AMAZON,
    external_id="B08N5WRWNW",
    canonical_url="https://www.amazon.com/dp/B08N5WRWNW",
    region="com",
)


# --- upsert_user --------------------------------------------------------------


async def test_upsert_user_inserts_then_returns_the_same_row(db_session: AsyncSession) -> None:
    created = await upsert_user(db_session, clerk_user_id="user_1", email="a@example.test")
    await db_session.flush()

    again = await upsert_user(db_session, clerk_user_id="user_1", email="a@example.test")

    assert again.id == created.id
    assert await db_session.scalar(select(func.count()).select_from(User)) == 1


async def test_upsert_user_updates_a_changed_email(db_session: AsyncSession) -> None:
    await upsert_user(db_session, clerk_user_id="user_1", email="old@example.test")
    await db_session.flush()

    updated = await upsert_user(db_session, clerk_user_id="user_1", email="new@example.test")

    assert updated.email == "new@example.test"


async def test_upsert_user_keeps_a_known_email_when_none_is_supplied(
    db_session: AsyncSession,
) -> None:
    # A Clerk JWT without an email claim must not blank out a stored address:
    # that is what the COALESCE in the ON CONFLICT clause is for.
    await upsert_user(db_session, clerk_user_id="user_1", email="known@example.test")
    await db_session.flush()

    updated = await upsert_user(db_session, clerk_user_id="user_1", email=None)

    assert updated.email == "known@example.test"


async def test_upsert_user_separates_distinct_clerk_ids(db_session: AsyncSession) -> None:
    first = await upsert_user(db_session, clerk_user_id="user_1", email="a@example.test")
    second = await upsert_user(db_session, clerk_user_id="user_2", email="b@example.test")

    assert first.id != second.id


# --- upsert_store_product -----------------------------------------------------


async def test_upsert_store_product_inserts_once_per_store_region_and_id(
    db_session: AsyncSession,
) -> None:
    created = await upsert_store_product(db_session, AMAZON_PRODUCT)
    await db_session.flush()

    again = await upsert_store_product(db_session, AMAZON_PRODUCT)

    assert again.id == created.id
    assert await db_session.scalar(select(func.count()).select_from(StoreProduct)) == 1


async def test_upsert_store_product_reactivates_a_dormant_product(
    db_session: AsyncSession,
) -> None:
    product = await upsert_store_product(db_session, AMAZON_PRODUCT)
    product.active = False
    product.current_price_minor = 4_200
    await db_session.flush()

    revived = await upsert_store_product(db_session, AMAZON_PRODUCT)

    assert revived.id == product.id
    assert revived.active is True
    # Re-watching must not discard the price history already collected.
    assert revived.current_price_minor == 4_200


async def test_upsert_store_product_refreshes_the_canonical_url(
    db_session: AsyncSession,
) -> None:
    product = await upsert_store_product(db_session, AMAZON_PRODUCT)
    await db_session.flush()
    relocated = NormalizedProduct(
        store=AMAZON_PRODUCT.store,
        external_id=AMAZON_PRODUCT.external_id,
        canonical_url="https://www.amazon.com/dp/B08N5WRWNW?refreshed",
        region=AMAZON_PRODUCT.region,
    )

    updated = await upsert_store_product(db_session, relocated)

    assert updated.id == product.id
    assert updated.canonical_url == relocated.canonical_url


async def test_upsert_store_product_treats_regions_as_distinct_products(
    db_session: AsyncSession,
) -> None:
    us = await upsert_store_product(db_session, AMAZON_PRODUCT)
    uk = await upsert_store_product(
        db_session,
        NormalizedProduct(
            store=Store.AMAZON,
            external_id=AMAZON_PRODUCT.external_id,
            canonical_url="https://www.amazon.co.uk/dp/B08N5WRWNW",
            region="co.uk",
        ),
    )

    assert us.id != uk.id


# --- record_webhook_event -----------------------------------------------------


async def test_record_webhook_event_returns_the_inserted_row(db_session: AsyncSession) -> None:
    event = await record_webhook_event(
        db_session,
        provider="bright_data",
        external_event_id="evt_1",
        payload={"snapshot_id": "snap_1"},
    )

    assert event is not None
    assert event.processed_at is None
    assert event.payload == {"snapshot_id": "snap_1"}


async def test_record_webhook_event_ignores_a_replayed_event(db_session: AsyncSession) -> None:
    # Providers retry deliveries; the second insert must be dropped rather than
    # reprocessed, which is what the None return tells the caller.
    await record_webhook_event(
        db_session, provider="bright_data", external_event_id="evt_1", payload={"a": 1}
    )
    await db_session.flush()

    duplicate = await record_webhook_event(
        db_session, provider="bright_data", external_event_id="evt_1", payload={"a": 2}
    )

    assert duplicate is None
    assert await db_session.scalar(select(func.count()).select_from(WebhookEvent)) == 1


async def test_record_webhook_event_scopes_ids_per_provider(db_session: AsyncSession) -> None:
    bright_data = await record_webhook_event(
        db_session, provider="bright_data", external_event_id="evt_1", payload={}
    )
    clerk = await record_webhook_event(
        db_session, provider="clerk", external_event_id="evt_1", payload={}
    )

    assert bright_data is not None
    assert clerk is not None
    assert bright_data.id != clerk.id


# --- get_owned_watch ----------------------------------------------------------


async def test_get_owned_watch_returns_none_for_another_owner(db_session: AsyncSession) -> None:
    owner = await upsert_user(db_session, clerk_user_id="owner", email="owner@example.test")
    stranger = await upsert_user(db_session, clerk_user_id="stranger", email="s@example.test")
    product = await upsert_store_product(db_session, AMAZON_PRODUCT)
    watch = Watch(user_id=owner.id, product_id=product.id, target_price_minor=1_000, currency="USD")
    db_session.add(watch)
    await db_session.flush()

    assert await get_owned_watch(db_session, watch.id, owner.id) is not None
    assert await get_owned_watch(db_session, watch.id, stranger.id) is None
