from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from html import escape

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import NotificationChannel, NotificationOutbox, NotificationStatus
from app.providers.email import EmailMessage, EmailProvider
from app.services.tracking import utcnow


def _format_money(minor: int, currency: str) -> str:
    exponent = {"BHD": 3, "JPY": 0, "KWD": 3}.get(currency, 2)
    amount = Decimal(minor) / (Decimal(10) ** exponent)
    return f"{amount:.{exponent}f} {currency}"


async def deliver_pending_notifications(
    session: AsyncSession,
    provider: EmailProvider,
    *,
    limit: int = 50,
    max_attempts: int = 5,
) -> int:
    now = utcnow()
    notifications = (
        await session.scalars(
            select(NotificationOutbox)
            .where(
                NotificationOutbox.status.in_(
                    [NotificationStatus.PENDING, NotificationStatus.FAILED]
                ),
                NotificationOutbox.channel == NotificationChannel.EMAIL,
                NotificationOutbox.available_at <= now,
                NotificationOutbox.attempts < max_attempts,
            )
            .order_by(NotificationOutbox.available_at)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
    ).all()
    sent = 0
    for notification in notifications:
        notification.status = NotificationStatus.SENDING
        notification.attempts += 1
        await session.flush()
        payload = notification.payload
        title = escape(str(payload.get("product_title", "Tracked product")))
        url = escape(str(payload.get("product_url", "#")), quote=True)
        currency = str(payload.get("currency", "USD"))
        price = _format_money(int(payload["price_minor"]), currency)
        item_price = _format_money(
            int(payload.get("item_price_minor", payload["price_minor"])), currency
        )
        shipping = _format_money(int(payload.get("shipping_price_minor", 0)), currency)
        target = _format_money(int(payload["target_price_minor"]), currency)
        if str(payload.get("kind")) == "back_in_stock":
            subject = f"Back in stock: {title}"
            body_html = (
                f"<p><strong>{title}</strong> is back in stock at {escape(price)}.</p>"
                f"<p>Item: {escape(item_price)} · Shipping: {escape(shipping)}</p>"
                f'<p><a href="{url}">View product</a></p>'
            )
        else:
            subject = f"Price alert: {title} is now {price}"
            body_html = (
                f"<p><strong>{title}</strong> is now {escape(price)}, "
                f"at or below your target of {escape(target)}.</p>"
                f"<p>Item: {escape(item_price)} · Shipping: {escape(shipping)}</p>"
                f'<p><a href="{url}">View product</a></p>'
            )
        message = EmailMessage(
            to=notification.recipient,
            subject=subject,
            html=body_html,
            idempotency_key=notification.dedupe_key,
        )
        try:
            await provider.send(message)
        except Exception as exc:
            notification.status = NotificationStatus.FAILED
            notification.last_error = str(exc)[:2000]
            notification.available_at = now + timedelta(minutes=min(2**notification.attempts, 60))
        else:
            notification.status = NotificationStatus.SENT
            notification.sent_at = utcnow()
            notification.last_error = None
            sent += 1
    return sent
