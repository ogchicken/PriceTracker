from app.models import AlertKind, AlertState
from app.services.alerts import evaluate_alert


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
