from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import StoreProduct, User, Watch, WebhookEvent
from app.providers.adapters import NormalizedProduct

# Without this, an upsert whose row is already in the session's identity map
# returns the stale in-memory instance instead of what RETURNING just produced,
# so callers can read pre-upsert values (for example a product's `active` flag or
# `currency`) that no longer match the database.
POPULATE_EXISTING = {"populate_existing": True}


async def record_webhook_event(
    session: AsyncSession,
    *,
    provider: str,
    external_event_id: str,
    payload: dict[str, Any],
) -> WebhookEvent | None:
    """Insert a webhook event, ignoring duplicates by (provider, external_event_id).

    Returns the inserted row, or ``None`` when the event was already recorded.
    """
    statement = (
        insert(WebhookEvent)
        .values(
            provider=provider,
            external_event_id=external_event_id,
            payload=payload,
        )
        .on_conflict_do_nothing(
            index_elements=[WebhookEvent.provider, WebhookEvent.external_event_id]
        )
        .returning(WebhookEvent)
    )
    return (await session.execute(statement)).scalar_one_or_none()


async def upsert_user(
    session: AsyncSession,
    *,
    clerk_user_id: str,
    email: str | None,
) -> User:
    statement = (
        insert(User)
        .values(
            {
                User.clerk_user_id: clerk_user_id,
                User.email: email,
                User.preferences_data: {},
            }
        )
        .on_conflict_do_update(
            index_elements=[User.clerk_user_id],
            set_={
                "email": func.coalesce(insert(User).excluded.email, User.email),
                "updated_at": func.now(),
            },
        )
        .returning(User)
    )
    result = await session.execute(statement, execution_options=POPULATE_EXISTING)
    return result.scalar_one()


async def upsert_store_product(
    session: AsyncSession,
    product: NormalizedProduct,
) -> StoreProduct:
    statement = (
        insert(StoreProduct)
        .values(
            {
                StoreProduct.store: product.store,
                StoreProduct.region: product.region,
                StoreProduct.external_id: product.external_id,
                StoreProduct.canonical_url: product.canonical_url,
                StoreProduct.metadata_json: {"region": product.region},
            }
        )
        .on_conflict_do_update(
            index_elements=[
                StoreProduct.store,
                StoreProduct.region,
                StoreProduct.external_id,
            ],
            set_={
                "canonical_url": product.canonical_url,
                "active": True,
                "updated_at": func.now(),
            },
        )
        .returning(StoreProduct)
    )
    result = await session.execute(statement, execution_options=POPULATE_EXISTING)
    return result.scalar_one()


async def get_owned_watch(
    session: AsyncSession,
    watch_id: uuid.UUID,
    user_id: uuid.UUID,
    *,
    include_product: bool = False,
) -> Watch | None:
    query = select(Watch).where(Watch.id == watch_id, Watch.user_id == user_id)
    if include_product:
        query = query.options(selectinload(Watch.product))
    return await session.scalar(query)
