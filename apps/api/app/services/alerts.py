from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    Alert,
    AlertKind,
    AlertState,
    AvailabilityStatus,
    NotificationChannel,
    NotificationOutbox,
    NotificationStatus,
    PriceObservation,
    Watch,
    WatchStatus,
)


@dataclass(frozen=True, slots=True)
class AlertDecision:
    state: AlertState
    trigger: bool = False
    kind: AlertKind | None = None


def evaluate_alert(
    *,
    state: AlertState,
    price_minor: int,
    target_price_minor: int,
    is_initial: bool,
    notify_initial_below_target: bool,
    rearm_percent: int,
) -> AlertDecision:
    if price_minor < 0 or target_price_minor < 0:
        raise ValueError("prices cannot be negative")
    if state is AlertState.TRIGGERED:
        if price_minor * 100 > target_price_minor * (100 + rearm_percent):
            return AlertDecision(AlertState.ARMED)
        return AlertDecision(AlertState.TRIGGERED)
    if price_minor > target_price_minor:
        return AlertDecision(AlertState.ARMED)
    if is_initial and not notify_initial_below_target:
        return AlertDecision(AlertState.TRIGGERED)
    kind = AlertKind.INITIAL_BELOW_TARGET if is_initial else AlertKind.PRICE_DROP
    return AlertDecision(AlertState.TRIGGERED, trigger=True, kind=kind)


async def _emit_alert(
    session: AsyncSession,
    *,
    watch: Watch,
    observation: PriceObservation,
    kind: AlertKind,
    preferences: dict[str, Any],
) -> None:
    """Persist an alert and its in-app (and optional email) outbox rows.

    Shared by the price-threshold and back-in-stock paths; the ``kind`` and its
    dedupe keys are the only things that vary between them.
    """
    dedupe_key = f"{watch.id}:{observation.id}:{kind.value}"
    alert = Alert(
        watch_id=watch.id,
        user_id=watch.user_id,
        observation_id=observation.id,
        kind=kind,
        price_minor=observation.price_minor,
        target_price_minor=watch.target_price_minor,
        currency=observation.currency,
        dedupe_key=dedupe_key,
    )
    session.add(alert)
    await session.flush()
    payload = {
        "kind": kind.value,
        "watch_id": str(watch.id),
        "product_title": watch.product.title or "Tracked product",
        "product_url": watch.product.canonical_url,
        "image_url": watch.product.image_url,
        "price_minor": observation.price_minor,
        "item_price_minor": observation.item_price_minor,
        "shipping_price_minor": observation.shipping_price_minor,
        "target_price_minor": watch.target_price_minor,
        "currency": observation.currency,
    }
    session.add(
        NotificationOutbox(
            alert_id=alert.id,
            user_id=watch.user_id,
            channel=NotificationChannel.IN_APP,
            status=NotificationStatus.SENT,
            recipient=watch.user.clerk_user_id,
            dedupe_key=f"in-app:{dedupe_key}",
            payload=payload,
            sent_at=observation.observed_at,
        )
    )
    if watch.user.email and preferences.get("email_enabled", True):
        session.add(
            NotificationOutbox(
                alert_id=alert.id,
                user_id=watch.user_id,
                channel=NotificationChannel.EMAIL,
                recipient=watch.user.email,
                dedupe_key=f"email:{dedupe_key}",
                payload=payload,
            )
        )


async def evaluate_watches_for_observation(
    session: AsyncSession,
    observation: PriceObservation,
    *,
    default_rearm_percent: int,
    previous_availability: AvailabilityStatus,
) -> int:
    watches = (
        await session.scalars(
            select(Watch)
            .where(
                Watch.product_id == observation.product_id,
                Watch.status == WatchStatus.ACTIVE,
            )
            .options(selectinload(Watch.user), selectinload(Watch.product))
            .with_for_update()
        )
    ).all()
    # A product-level edge: only a transition from out-of-stock/unavailable to
    # in-stock counts. A first-ever observation (previous == UNKNOWN) does not.
    came_back_in_stock = (
        previous_availability in {AvailabilityStatus.OUT_OF_STOCK, AvailabilityStatus.UNAVAILABLE}
        and observation.availability is AvailabilityStatus.IN_STOCK
    )
    triggered = 0
    for watch in watches:
        preferences = watch.user.preferences_data or {}
        # Back-in-stock is independent of price and currency.
        if came_back_in_stock and watch.notify_back_in_stock:
            await _emit_alert(
                session,
                watch=watch,
                observation=observation,
                kind=AlertKind.BACK_IN_STOCK,
                preferences=preferences,
            )
            triggered += 1
        if watch.currency.upper() != observation.currency.upper():
            continue
        rearm_percent = int(preferences.get("alert_rearm_percent", default_rearm_percent))
        watch_is_initial = watch.last_evaluated_at is None
        decision = evaluate_alert(
            state=watch.alert_state,
            price_minor=observation.price_minor,
            target_price_minor=watch.target_price_minor,
            is_initial=watch_is_initial,
            notify_initial_below_target=watch.notify_initial_below_target,
            rearm_percent=max(0, min(rearm_percent, 100)),
        )
        watch.alert_state = decision.state
        watch.last_evaluated_at = observation.observed_at
        if not decision.trigger or decision.kind is None:
            continue
        await _emit_alert(
            session,
            watch=watch,
            observation=observation,
            kind=decision.kind,
            preferences=preferences,
        )
        triggered += 1
    return triggered
