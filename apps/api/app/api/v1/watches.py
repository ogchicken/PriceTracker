from __future__ import annotations

import uuid
from datetime import timedelta
from typing import Annotated, Literal

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Query,
    Request,
    Response,
    status,
)
from redis.exceptions import RedisError
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DbSession
from app.config import Settings, get_settings
from app.logging import get_logger
from app.models import AlertState, PriceObservation, Watch, WatchStatus
from app.providers.adapters import AdapterError, adapter_registry
from app.schemas import (
    PriceObservationResponse,
    WatchCreate,
    WatchResponse,
    WatchUpdate,
)
from app.stores.repositories import get_owned_watch, upsert_store_product
from app.services.tracking import utcnow
from app.workers.tasks import enqueue_immediate_lookup

router = APIRouter()
logger = get_logger(__name__)


async def _enforce_create_limits(
    request: Request,
    session: DbSession,
    user: CurrentUser,
    settings: Settings,
) -> None:
    active_count = await session.scalar(
        select(func.count())
        .select_from(Watch)
        .where(Watch.user_id == user.id, Watch.status == WatchStatus.ACTIVE)
    )
    if (active_count or 0) >= settings.max_active_watches_per_user:
        raise HTTPException(status_code=409, detail="active watch limit reached")
    bucket = int(utcnow().timestamp() // 3600)
    key = f"rate:watch-create:{user.id}:{bucket}"
    try:
        count = await request.app.state.redis.incr(key)
        if count == 1:
            await request.app.state.redis.expire(key, 3700)
    except RedisError as exc:
        # Fail closed: this limiter is a cost control on paid provider lookups
        # (each create triggers an immediate snapshot). A Redis outage must not
        # degrade into an unlimited-create bypass, so refuse rather than allow.
        logger.warning("watch_create_rate_limit_unavailable", user_id=str(user.id))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="watch creation is temporarily unavailable",
        ) from exc
    if count > settings.watch_create_rate_limit_per_hour:
        raise HTTPException(status_code=429, detail="watch creation rate limit exceeded")


@router.post("", response_model=WatchResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_watch(
    body: WatchCreate,
    background_tasks: BackgroundTasks,
    request: Request,
    session: DbSession,
    user: CurrentUser,
    settings: Annotated[Settings, Depends(get_settings)],
) -> Watch:
    await _enforce_create_limits(request, session, user, settings)
    try:
        normalized = adapter_registry.parse(body.url)
    except AdapterError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    product = await upsert_store_product(session, normalized)
    if product.currency and product.currency.upper() != body.currency:
        raise HTTPException(
            status_code=422,
            detail=f"product is priced in {product.currency.upper()}",
        )
    existing = await session.scalar(
        select(Watch).where(Watch.user_id == user.id, Watch.product_id == product.id)
    )
    if existing:
        raise HTTPException(status_code=409, detail="this product is already watched")
    watch = Watch(
        user_id=user.id,
        product_id=product.id,
        target_price_minor=body.target_price_minor,
        currency=body.currency,
        notify_initial_below_target=body.notify_initial_below_target,
        notify_back_in_stock=body.notify_back_in_stock,
        product=product,
    )
    session.add(watch)
    await session.commit()
    background_tasks.add_task(enqueue_immediate_lookup, str(product.id))
    return watch


@router.get("", response_model=list[WatchResponse])
async def list_watches(
    session: DbSession,
    user: CurrentUser,
    watch_status: WatchStatus | None = Query(default=None, alias="status"),
) -> list[Watch]:
    query = (
        select(Watch)
        .where(Watch.user_id == user.id)
        .options(selectinload(Watch.product))
        .order_by(Watch.created_at.desc())
    )
    if watch_status:
        query = query.where(Watch.status == watch_status)
    return list((await session.scalars(query)).all())


@router.get("/{watch_id}", response_model=WatchResponse)
async def get_watch(
    watch_id: uuid.UUID,
    session: DbSession,
    user: CurrentUser,
) -> Watch:
    watch = await get_owned_watch(session, watch_id, user.id, include_product=True)
    if watch is None:
        raise HTTPException(status_code=404, detail="watch not found")
    return watch


@router.patch("/{watch_id}", response_model=WatchResponse)
async def update_watch(
    watch_id: uuid.UUID,
    body: WatchUpdate,
    session: DbSession,
    user: CurrentUser,
) -> Watch:
    watch = await get_owned_watch(
        session,
        watch_id,
        user.id,
        include_product=True,
    )
    if watch is None:
        raise HTTPException(status_code=404, detail="watch not found")
    changes = body.model_dump(exclude_unset=True)
    if any(value is None for value in changes.values()):
        raise HTTPException(status_code=422, detail="watch fields may not be null")
    if "target_price_minor" in changes:
        watch.target_price_minor = changes["target_price_minor"]
        watch.alert_state = AlertState.ARMED
    if "status" in changes:
        watch.status = changes["status"]
        await session.flush()
        if changes["status"] is WatchStatus.ACTIVE:
            watch.product.active = True
        else:
            active_count = await session.scalar(
                select(func.count())
                .select_from(Watch)
                .where(
                    Watch.product_id == watch.product_id,
                    Watch.status == WatchStatus.ACTIVE,
                )
            )
            watch.product.active = bool(active_count)
            if not active_count:
                watch.product.lease_until = None
    if "notify_initial_below_target" in changes:
        watch.notify_initial_below_target = changes["notify_initial_below_target"]
    if "notify_back_in_stock" in changes:
        watch.notify_back_in_stock = changes["notify_back_in_stock"]
    await session.flush()
    return watch


@router.delete("/{watch_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_watch(
    watch_id: uuid.UUID,
    session: DbSession,
    user: CurrentUser,
) -> Response:
    watch = await get_owned_watch(session, watch_id, user.id, include_product=True)
    if watch is None:
        raise HTTPException(status_code=404, detail="watch not found")
    product = watch.product
    await session.delete(watch)
    await session.flush()
    active_count = await session.scalar(
        select(func.count())
        .select_from(Watch)
        .where(Watch.product_id == product.id, Watch.status == WatchStatus.ACTIVE)
    )
    if not active_count:
        product.active = False
        product.lease_until = None
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{watch_id}/history", response_model=list[PriceObservationResponse])
async def watch_history(
    watch_id: uuid.UUID,
    session: DbSession,
    user: CurrentUser,
    limit: int = Query(default=100, ge=1, le=500),
    history_range: Literal["7d", "30d", "90d", "all"] = Query(default="30d", alias="range"),
) -> list[PriceObservation]:
    watch = await get_owned_watch(session, watch_id, user.id)
    if watch is None:
        raise HTTPException(status_code=404, detail="watch not found")
    query = select(PriceObservation).where(PriceObservation.product_id == watch.product_id)
    if history_range != "all":
        days = {"7d": 7, "30d": 30, "90d": 90}[history_range]
        query = query.where(PriceObservation.observed_at >= utcnow() - timedelta(days=days))
    observations = (
        await session.scalars(query.order_by(PriceObservation.observed_at.desc()).limit(limit))
    ).all()
    return list(observations)
