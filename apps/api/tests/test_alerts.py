from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Alert,
    AlertKind,
    AlertState,
    AvailabilityStatus,
    NotificationChannel,
    NotificationOutbox,
    NotificationStatus,
    PriceObservation,
    ProviderName,
    Store,
    StoreProduct,
    User,
    Watch,
)
from app.schemas import WatchCreate
from app.services.alerts import evaluate_alert, evaluate_watches_for_observation
from app.services.tracking import utcnow


def test_initial_below_target_can_notify() -> None:
    decision = evaluate_alert(
        state=AlertState.ARMED,
        price_minor=900,
        target_price_minor=1000,
        is_initial=True,
        notify_initial_below_target=True,
        rearm_percent=3,
    )
    assert decision.trigger is True
    assert decision.kind is AlertKind.INITIAL_BELOW_TARGET
    assert decision.state is AlertState.TRIGGERED


def test_initial_below_target_can_be_silenced_without_later_duplicate() -> None:
    decision = evaluate_alert(
        state=AlertState.ARMED,
        price_minor=900,
        target_price_minor=1000,
        is_initial=True,
        notify_initial_below_target=False,
        rearm_percent=3,
    )
    assert decision.trigger is False
    assert decision.state is AlertState.TRIGGERED


def test_triggered_watch_rearms_only_above_threshold() -> None:
    still_triggered = evaluate_alert(
        state=AlertState.TRIGGERED,
        price_minor=1030,
        target_price_minor=1000,
        is_initial=False,
        notify_initial_below_target=True,
        rearm_percent=3,
    )
    rearmed = evaluate_alert(
        state=AlertState.TRIGGERED,
        price_minor=1031,
        target_price_minor=1000,
        is_initial=False,
        notify_initial_below_target=True,
        rearm_percent=3,
    )
    assert still_triggered.state is AlertState.TRIGGERED
    assert rearmed.state is AlertState.ARMED


def test_rearmed_watch_triggers_on_new_drop() -> None:
    decision = evaluate_alert(
        state=AlertState.ARMED,
        price_minor=1000,
        target_price_minor=1000,
        is_initial=False,
        notify_initial_below_target=True,
        rearm_percent=3,
    )
    assert decision.trigger is True
    assert decision.kind is AlertKind.PRICE_DROP


def test_watch_create_defaults_back_in_stock_on() -> None:
    body = WatchCreate(
        url="https://www.amazon.com/dp/B000000000", target_price_minor=1000, currency="USD"
    )
    assert body.notify_back_in_stock is True


async def _seed_watch(
    session: AsyncSession,
    *,
    notify_back_in_stock: bool = True,
    email: str | None = "buyer@example.test",
    currency: str = "USD",
    target_price_minor: int = 1_000,
    product_availability: AvailabilityStatus = AvailabilityStatus.OUT_OF_STOCK,
) -> tuple[User, StoreProduct, Watch]:
    user = User(clerk_user_id=f"user_{uuid.uuid4().hex}", email=email, preferences_data={})
    product = StoreProduct(
        store=Store.AMAZON,
        region="com",
        external_id=uuid.uuid4().hex[:10].upper(),
        canonical_url="https://www.amazon.com/dp/B000000000",
        availability=product_availability,
    )
    session.add_all([user, product])
    await session.flush()
    watch = Watch(
        user_id=user.id,
        product_id=product.id,
        target_price_minor=target_price_minor,
        currency=currency,
        notify_back_in_stock=notify_back_in_stock,
    )
    session.add(watch)
    await session.flush()
    return user, product, watch


async def _add_observation(
    session: AsyncSession,
    product: StoreProduct,
    *,
    availability: AvailabilityStatus,
    price_minor: int = 5_000,
    currency: str = "USD",
) -> PriceObservation:
    observation = PriceObservation(
        product_id=product.id,
        price_minor=price_minor,
        item_price_minor=price_minor,
        shipping_price_minor=0,
        currency=currency,
        availability=availability,
        observed_at=utcnow(),
        source=ProviderName.BRIGHT_DATA,
        raw_data={},
    )
    session.add(observation)
    await session.flush()
    return observation


async def _alerts_for(session: AsyncSession, watch: Watch) -> list[Alert]:
    return list((await session.scalars(select(Alert).where(Alert.watch_id == watch.id))).all())


async def test_back_in_stock_transition_creates_alert(db_session: AsyncSession) -> None:
    # price 5000 stays above target 1000, so no price alert competes.
    _user, product, watch = await _seed_watch(db_session)
    observation = await _add_observation(
        db_session, product, availability=AvailabilityStatus.IN_STOCK
    )

    triggered = await evaluate_watches_for_observation(
        db_session,
        observation,
        default_rearm_percent=3,
        previous_availability=AvailabilityStatus.OUT_OF_STOCK,
    )

    assert triggered == 1
    alerts = await _alerts_for(db_session, watch)
    assert [alert.kind for alert in alerts] == [AlertKind.BACK_IN_STOCK]

    outbox = list(
        (
            await db_session.scalars(
                select(NotificationOutbox).where(NotificationOutbox.alert_id == alerts[0].id)
            )
        ).all()
    )
    channels = {row.channel: row.status for row in outbox}
    assert channels[NotificationChannel.IN_APP] is NotificationStatus.SENT
    assert channels[NotificationChannel.EMAIL] is NotificationStatus.PENDING
    assert outbox[0].payload["kind"] == "back_in_stock"


async def test_no_stock_alert_when_already_in_stock(db_session: AsyncSession) -> None:
    _user, product, watch = await _seed_watch(db_session)
    observation = await _add_observation(
        db_session, product, availability=AvailabilityStatus.IN_STOCK
    )

    await evaluate_watches_for_observation(
        db_session,
        observation,
        default_rearm_percent=3,
        previous_availability=AvailabilityStatus.IN_STOCK,
    )

    assert await _alerts_for(db_session, watch) == []


async def test_no_stock_alert_from_unknown(db_session: AsyncSession) -> None:
    # A first-ever observation has no meaningful prior state.
    _user, product, watch = await _seed_watch(
        db_session, product_availability=AvailabilityStatus.UNKNOWN
    )
    observation = await _add_observation(
        db_session, product, availability=AvailabilityStatus.IN_STOCK
    )

    await evaluate_watches_for_observation(
        db_session,
        observation,
        default_rearm_percent=3,
        previous_availability=AvailabilityStatus.UNKNOWN,
    )

    assert await _alerts_for(db_session, watch) == []


async def test_stock_alert_respects_opt_out(db_session: AsyncSession) -> None:
    _user, product, watch = await _seed_watch(db_session, notify_back_in_stock=False)
    observation = await _add_observation(
        db_session, product, availability=AvailabilityStatus.IN_STOCK
    )

    await evaluate_watches_for_observation(
        db_session,
        observation,
        default_rearm_percent=3,
        previous_availability=AvailabilityStatus.OUT_OF_STOCK,
    )

    assert await _alerts_for(db_session, watch) == []


async def test_stock_alert_ignores_currency_mismatch(db_session: AsyncSession) -> None:
    # Watch priced in EUR, observation in USD: the price path is skipped but the
    # stock alert must still fire because it is currency-independent.
    _user, product, watch = await _seed_watch(db_session, currency="EUR", target_price_minor=10_000)
    observation = await _add_observation(
        db_session,
        product,
        availability=AvailabilityStatus.IN_STOCK,
        price_minor=5_000,
        currency="USD",
    )

    await evaluate_watches_for_observation(
        db_session,
        observation,
        default_rearm_percent=3,
        previous_availability=AvailabilityStatus.OUT_OF_STOCK,
    )

    alerts = await _alerts_for(db_session, watch)
    assert [alert.kind for alert in alerts] == [AlertKind.BACK_IN_STOCK]


async def test_stock_and_price_alerts_coexist_on_one_observation(db_session: AsyncSession) -> None:
    # Restocked AND below target on the first evaluation: two distinct alerts.
    _user, product, watch = await _seed_watch(db_session, target_price_minor=10_000)
    observation = await _add_observation(
        db_session, product, availability=AvailabilityStatus.IN_STOCK, price_minor=5_000
    )

    await evaluate_watches_for_observation(
        db_session,
        observation,
        default_rearm_percent=3,
        previous_availability=AvailabilityStatus.OUT_OF_STOCK,
    )

    alerts = await _alerts_for(db_session, watch)
    kinds = {alert.kind for alert in alerts}
    assert kinds == {AlertKind.BACK_IN_STOCK, AlertKind.INITIAL_BELOW_TARGET}
    assert len({alert.dedupe_key for alert in alerts}) == 2
