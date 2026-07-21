from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Iterable

from sqlalchemy import exists, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.models import (
    AvailabilityStatus,
    PriceObservation,
    ProviderJob,
    ProviderJobState,
    ProviderName,
    Store,
    StoreProduct,
    Watch,
    WatchStatus,
    WebhookEvent,
)
from app.providers.brightdata import BrightDataClient, BrightDataError, normalize_result
from app.services.alerts import evaluate_watches_for_observation


def utcnow() -> datetime:
    return datetime.now(UTC)


def next_check_time(
    product_id: uuid.UUID, settings: Settings, *, now: datetime | None = None
) -> datetime:
    base = now or utcnow()
    jitter_window = max(settings.tracking_jitter_minutes, 0) * 60
    jitter_seconds = product_id.int % (jitter_window + 1) if jitter_window else 0
    return base + timedelta(hours=settings.tracking_interval_hours, seconds=jitter_seconds)


async def stop_products_without_active_watches(session: AsyncSession) -> int:
    active_watch = exists(
        select(Watch.id).where(
            Watch.product_id == StoreProduct.id,
            Watch.status == WatchStatus.ACTIVE,
        )
    )
    result = await session.execute(
        update(StoreProduct)
        .where(StoreProduct.active.is_(True), ~active_watch)
        .values(active=False, lease_until=None)
    )
    return int(getattr(result, "rowcount", 0) or 0)


async def claim_due_products(
    session: AsyncSession,
    settings: Settings,
    *,
    limit: int = 100,
) -> list[StoreProduct]:
    now = utcnow()
    active_watch = exists(
        select(Watch.id).where(
            Watch.product_id == StoreProduct.id,
            Watch.status == WatchStatus.ACTIVE,
        )
    )
    products = (
        await session.scalars(
            select(StoreProduct)
            .where(
                StoreProduct.active.is_(True),
                StoreProduct.next_check_at <= now,
                (StoreProduct.lease_until.is_(None) | (StoreProduct.lease_until < now)),
                active_watch,
            )
            .order_by(StoreProduct.next_check_at)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
    ).all()
    lease_until = now + timedelta(minutes=settings.product_lease_minutes)
    for product in products:
        product.lease_until = lease_until
    await session.flush()
    return list(products)


def group_products_by_store(
    products: Iterable[StoreProduct],
) -> dict[tuple[Store, str], list[StoreProduct]]:
    grouped: dict[tuple[Store, str], list[StoreProduct]] = defaultdict(list)
    for product in products:
        grouped[(product.store, product.region)].append(product)
    return dict(grouped)


async def trigger_snapshot(
    session: AsyncSession,
    settings: Settings,
    client: BrightDataClient,
    store: Store,
    products: list[StoreProduct],
) -> ProviderJob:
    now = utcnow()
    for product in products:
        product.lease_until = now + timedelta(minutes=settings.product_lease_minutes)
    job = ProviderJob(
        provider=ProviderName.BRIGHT_DATA,
        dataset_id=client.dataset_id_for(store),
        state=ProviderJobState.PENDING,
        product_ids=[str(product.id) for product in products],
        stale_after=now + timedelta(minutes=settings.provider_job_stale_minutes),
    )
    session.add(job)
    await session.flush()
    try:
        snapshot = await client.trigger(store, [product.canonical_url for product in products])
    except BrightDataError as exc:
        job.state = ProviderJobState.FAILED
        job.error = str(exc)
        job.attempts = 1
        for product in products:
            schedule_product_failure(product, settings, now=now)
        return job
    job.external_job_id = snapshot.snapshot_id
    job.state = ProviderJobState.RUNNING
    job.attempts = 1
    job.response_data = {"fake": snapshot.fake}
    if snapshot.fake:
        for product in products:
            watch_currency = await session.scalar(
                select(Watch.currency)
                .where(
                    Watch.product_id == product.id,
                    Watch.status == WatchStatus.ACTIVE,
                )
                .limit(1)
            )
            currency = watch_currency or product.currency or "USD"
            item_price_minor = 2_500 + (product.id.int % 25_000)
            observation = PriceObservation(
                product_id=product.id,
                provider_job_id=job.id,
                price_minor=item_price_minor,
                item_price_minor=item_price_minor,
                shipping_price_minor=0,
                currency=currency,
                availability=AvailabilityStatus.IN_STOCK,
                observed_at=now,
                source=ProviderName.BRIGHT_DATA,
                raw_data={"fake": True, "external_id": product.external_id},
            )
            session.add(observation)
            await session.flush()
            product.title = product.title or f"Demo {product.store.value.title()} product"
            product.item_price_minor = item_price_minor
            product.shipping_price_minor = 0
            product.current_price_minor = item_price_minor
            product.currency = currency
            product.availability = AvailabilityStatus.IN_STOCK
            product.last_checked_at = now
            product.consecutive_failures = 0
            product.lease_until = None
            product.next_check_at = next_check_time(product.id, settings, now=now)
            await evaluate_watches_for_observation(
                session,
                observation,
                default_rearm_percent=settings.alert_rearm_percent,
            )
        job.state = ProviderJobState.SUCCEEDED
        job.completed_at = now
    return job


def schedule_product_failure(
    product: StoreProduct,
    settings: Settings,
    *,
    now: datetime | None = None,
) -> None:
    current = now or utcnow()
    product.consecutive_failures += 1
    backoff_minutes = min(15 * (2 ** (product.consecutive_failures - 1)), 24 * 60)
    product.next_check_at = current + timedelta(minutes=backoff_minutes)
    product.lease_until = None


async def mark_stale_jobs(session: AsyncSession, settings: Settings) -> int:
    now = utcnow()
    jobs = (
        await session.scalars(
            select(ProviderJob)
            .where(
                ProviderJob.state.in_([ProviderJobState.PENDING, ProviderJobState.RUNNING]),
                ProviderJob.stale_after < now,
            )
            .with_for_update(skip_locked=True)
        )
    ).all()
    for job in jobs:
        job.state = ProviderJobState.STALE
        job.completed_at = now
        job.error = "provider job exceeded its stale deadline"
        product_uuids = [uuid.UUID(item) for item in job.product_ids]
        products = (
            await session.scalars(select(StoreProduct).where(StoreProduct.id.in_(product_uuids)))
        ).all()
        for product in products:
            schedule_product_failure(product, settings, now=now)
    return len(jobs)


async def process_brightdata_event(
    session: AsyncSession,
    settings: Settings,
    client: BrightDataClient,
    event_id: uuid.UUID,
) -> int:
    event = await session.scalar(
        select(WebhookEvent).where(WebhookEvent.id == event_id).with_for_update()
    )
    if event is None or event.processed_at is not None:
        return 0
    payload = event.payload
    snapshot_id = str(
        payload.get("snapshot_id") or payload.get("snapshotId") or payload.get("id") or ""
    )
    if not snapshot_id:
        event.error = "webhook did not include a snapshot ID"
        event.processed_at = utcnow()
        return 0
    job = await session.scalar(
        select(ProviderJob)
        .where(
            ProviderJob.provider == ProviderName.BRIGHT_DATA,
            ProviderJob.external_job_id == snapshot_id,
        )
        .with_for_update()
    )
    if job is None:
        raise LookupError("provider job is not yet available")
    product_uuids = [uuid.UUID(item) for item in job.product_ids]
    products = (
        await session.scalars(
            select(StoreProduct).where(StoreProduct.id.in_(product_uuids)).with_for_update()
        )
    ).all()
    products_by_external_id = {product.external_id: product for product in products}
    status = str(payload.get("status", "")).lower()
    if status in {"failed", "error", "cancelled", "canceled"}:
        job.state = ProviderJobState.FAILED
        job.completed_at = utcnow()
        job.error = str(payload.get("error") or "provider reported failure")
        for product in products:
            schedule_product_failure(product, settings)
        event.processed_at = utcnow()
        return 0
    embedded_results = payload.get("results") or payload.get("data")
    if embedded_results is None:
        results = await client.fetch_snapshot(snapshot_id)
    elif isinstance(embedded_results, list):
        results = [item for item in embedded_results if isinstance(item, dict)]
    else:
        job.state = ProviderJobState.FAILED
        job.completed_at = utcnow()
        job.error = "provider webhook results must be a list"
        for product in products:
            schedule_product_failure(product, settings)
        event.error = job.error
        event.processed_at = utcnow()
        return 0
    if not products:
        event.error = "provider job has no products"
        event.processed_at = utcnow()
        return 0
    store = products[0].store
    observed_product_ids: set[uuid.UUID] = set()
    normalization_errors: list[str] = []
    created = 0
    for raw_result in results:
        try:
            normalized = normalize_result(store, raw_result)
        except ValueError as exc:
            normalization_errors.append(str(exc))
            continue
        matched_product = products_by_external_id.get(normalized.external_id)
        if matched_product is None:
            normalization_errors.append(f"unknown product {normalized.external_id}")
            continue
        duplicate = await session.scalar(
            select(PriceObservation.id).where(
                PriceObservation.provider_job_id == job.id,
                PriceObservation.product_id == matched_product.id,
            )
        )
        if duplicate:
            observed_product_ids.add(matched_product.id)
            continue
        observation = PriceObservation(
            product_id=matched_product.id,
            provider_job_id=job.id,
            price_minor=normalized.price_minor,
            item_price_minor=normalized.item_price_minor,
            shipping_price_minor=normalized.shipping_price_minor,
            currency=normalized.currency,
            availability=normalized.availability,
            observed_at=normalized.observed_at,
            source=ProviderName.BRIGHT_DATA,
            raw_data=normalized.raw,
        )
        session.add(observation)
        await session.flush()
        matched_product.title = normalized.title or matched_product.title
        matched_product.image_url = normalized.image_url or matched_product.image_url
        matched_product.item_price_minor = normalized.item_price_minor
        matched_product.shipping_price_minor = normalized.shipping_price_minor
        matched_product.current_price_minor = normalized.price_minor
        matched_product.currency = normalized.currency
        matched_product.availability = normalized.availability
        matched_product.last_checked_at = normalized.observed_at
        matched_product.consecutive_failures = 0
        matched_product.lease_until = None
        matched_product.next_check_at = next_check_time(matched_product.id, settings)
        await evaluate_watches_for_observation(
            session,
            observation,
            default_rearm_percent=settings.alert_rearm_percent,
        )
        observed_product_ids.add(matched_product.id)
        created += 1
    for product in products:
        if product.id not in observed_product_ids:
            schedule_product_failure(product, settings)
    now = utcnow()
    job.state = ProviderJobState.SUCCEEDED if observed_product_ids else ProviderJobState.FAILED
    job.completed_at = now
    job.error = "; ".join(normalization_errors[:10]) or None
    job.response_data = {
        **(job.response_data or {}),
        "result_count": len(results),
        "observation_count": created,
        "normalization_errors": normalization_errors[:10],
    }
    event.processed_at = now
    event.error = job.error
    return created
