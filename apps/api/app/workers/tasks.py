from __future__ import annotations

import asyncio
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.logging import get_logger
from app.models import StoreProduct, WebhookEvent
from app.providers.brightdata import BrightDataClient, BrightDataError
from app.providers.email import build_email_provider
from app.services.notifications import deliver_pending_notifications
from app.services.tracking import (
    claim_due_products,
    group_products_by_store,
    mark_stale_jobs,
    process_brightdata_event,
    stop_products_without_active_watches,
    trigger_snapshot,
    utcnow,
)
from app.workers.celery_app import celery_app

settings = get_settings()
logger = get_logger(__name__)


@asynccontextmanager
async def _worker_transaction() -> AsyncIterator[AsyncSession]:
    worker_engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    worker_sessions = async_sessionmaker(
        worker_engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )
    try:
        async with worker_sessions() as session, session.begin():
            yield session
    finally:
        await worker_engine.dispose()


def enqueue_immediate_lookup(product_id: str) -> None:
    try:
        immediate_lookup.delay(product_id)
    except Exception:
        logger.exception("immediate_lookup_enqueue_failed", product_id=product_id)


def enqueue_provider_event(event_id: str) -> None:
    try:
        process_provider_event.delay(event_id)
    except Exception:
        logger.exception("provider_event_enqueue_failed", event_id=event_id)


async def _run_tracking_cycle() -> int:
    client = BrightDataClient(settings)
    try:
        async with _worker_transaction() as session:
            await stop_products_without_active_watches(session)
            products = await claim_due_products(session, settings)
            for (store, _region), group in group_products_by_store(products).items():
                await trigger_snapshot(session, settings, client, store, group)
            return len(products)
    finally:
        await client.aclose()


@celery_app.task(name="tracking.claim_due_products")
def tracking_cycle() -> int:
    return asyncio.run(_run_tracking_cycle())


async def _run_immediate_lookup(product_id: str) -> bool:
    client = BrightDataClient(settings)
    try:
        async with _worker_transaction() as session:
            product = await session.scalar(
                select(StoreProduct)
                .where(StoreProduct.id == uuid.UUID(product_id), StoreProduct.active.is_(True))
                .with_for_update()
            )
            if product is None:
                return False
            product.lease_until = utcnow()
            await trigger_snapshot(session, settings, client, product.store, [product])
            return True
    finally:
        await client.aclose()


@celery_app.task(
    bind=True,
    name="tracking.immediate_lookup",
    max_retries=max(settings.provider_max_attempts - 1, 0),
    default_retry_delay=15,
)
def immediate_lookup(self, product_id: str) -> bool:
    try:
        return asyncio.run(_run_immediate_lookup(product_id))
    except Exception as exc:
        raise self.retry(exc=exc, countdown=min(15 * (2**self.request.retries), 300)) from exc


async def _process_provider_event(event_id: str) -> int:
    client = BrightDataClient(settings)
    try:
        async with _worker_transaction() as session:
            return await process_brightdata_event(
                session,
                settings,
                client,
                uuid.UUID(event_id),
            )
    finally:
        await client.aclose()


@celery_app.task(
    bind=True,
    name="tracking.process_brightdata_event",
    max_retries=settings.provider_max_attempts,
    default_retry_delay=10,
)
def process_provider_event(self, event_id: str) -> int:
    try:
        return asyncio.run(_process_provider_event(event_id))
    except Exception as exc:
        raise self.retry(exc=exc, countdown=min(10 * (2**self.request.retries), 300)) from exc


async def _process_webhook_inbox() -> int:
    client = BrightDataClient(settings)
    processed = 0
    try:
        async with _worker_transaction() as session:
            event_ids = (
                await session.scalars(
                    select(WebhookEvent.id)
                    .where(
                        WebhookEvent.provider == "bright_data",
                        WebhookEvent.processed_at.is_(None),
                    )
                    .order_by(WebhookEvent.received_at)
                    .limit(50)
                )
            ).all()
            for event_id in event_ids:
                try:
                    async with session.begin_nested():
                        await process_brightdata_event(
                            session,
                            settings,
                            client,
                            event_id,
                        )
                except (LookupError, BrightDataError):
                    continue
                processed += 1
        return processed
    finally:
        await client.aclose()


@celery_app.task(name="tracking.process_webhook_inbox")
def process_webhook_inbox() -> int:
    return asyncio.run(_process_webhook_inbox())


async def _mark_stale() -> int:
    async with _worker_transaction() as session:
        return await mark_stale_jobs(session, settings)


@celery_app.task(name="tracking.mark_stale_jobs")
def stale_provider_jobs() -> int:
    return asyncio.run(_mark_stale())


async def _deliver_notifications() -> int:
    provider = build_email_provider(settings)
    async with _worker_transaction() as session:
        return await deliver_pending_notifications(
            session,
            provider,
            max_attempts=settings.provider_max_attempts,
        )


@celery_app.task(name="notifications.deliver")
def deliver_notifications() -> int:
    return asyncio.run(_deliver_notifications())
