from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import StoreProduct, User, Watch
from app.providers.adapters import NormalizedProduct


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
    result = await session.execute(statement)
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
    result = await session.execute(statement)
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
