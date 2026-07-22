from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from sqlalchemy import select
from svix.webhooks import Webhook, WebhookVerificationError

from app.api.deps import DbSession
from app.config import Settings, get_settings
from app.models import User
from app.schemas import WebhookAccepted
from app.services.tracking import utcnow
from app.stores.repositories import record_webhook_event, upsert_user
from app.workers.tasks import enqueue_provider_event

router = APIRouter()


def _clerk_email(data: dict[str, Any]) -> str | None:
    primary_id = data.get("primary_email_address_id")
    addresses = data.get("email_addresses") or []
    primary = next((item for item in addresses if item.get("id") == primary_id), None)
    selected = primary or (addresses[0] if addresses else None)
    value = selected.get("email_address") if isinstance(selected, dict) else None
    return value if isinstance(value, str) else None


@router.post("/clerk", response_model=WebhookAccepted)
async def clerk_webhook(
    request: Request,
    session: DbSession,
    settings: Settings = Depends(get_settings),
) -> WebhookAccepted:
    if not settings.clerk_webhook_secret:
        raise HTTPException(status_code=503, detail="Clerk webhook secret is not configured")
    raw_body = await request.body()
    try:
        payload = Webhook(settings.clerk_webhook_secret).verify(
            raw_body,
            {
                "svix-id": request.headers.get("svix-id", ""),
                "svix-timestamp": request.headers.get("svix-timestamp", ""),
                "svix-signature": request.headers.get("svix-signature", ""),
            },
        )
    except WebhookVerificationError as exc:
        raise HTTPException(status_code=400, detail="invalid Clerk webhook signature") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="invalid Clerk webhook payload")
    external_event_id = str(payload.get("id") or request.headers.get("svix-id") or "")
    if not external_event_id:
        raise HTTPException(status_code=400, detail="Clerk event ID is missing")
    event = await record_webhook_event(
        session,
        provider="clerk",
        external_event_id=external_event_id,
        payload=payload,
    )
    if event is None:
        return WebhookAccepted(duplicate=True)
    event_type = str(payload.get("type", ""))
    data = payload.get("data")
    if not isinstance(data, dict) or not isinstance(data.get("id"), str):
        raise HTTPException(status_code=400, detail="Clerk user payload is invalid")
    clerk_user_id = data["id"]
    if event_type in {"user.created", "user.updated"}:
        await upsert_user(
            session,
            clerk_user_id=clerk_user_id,
            email=_clerk_email(data),
        )
    elif event_type == "user.deleted":
        user = await session.scalar(select(User).where(User.clerk_user_id == clerk_user_id))
        if user is not None:
            await session.delete(user)
    event.processed_at = utcnow()
    return WebhookAccepted()


@router.post("/bright-data", response_model=WebhookAccepted, status_code=status.HTTP_200_OK)
async def bright_data_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    session: DbSession,
    settings: Settings = Depends(get_settings),
) -> WebhookAccepted:
    if not settings.bright_data_webhook_secret:
        raise HTTPException(status_code=503, detail="Bright Data webhook secret is not configured")
    supplied = request.headers.get("x-brightdata-webhook-secret")
    authorization = request.headers.get("authorization", "")
    if authorization.lower().startswith("bearer "):
        supplied = authorization[7:]
    if supplied is None or not hmac.compare_digest(
        supplied,
        settings.bright_data_webhook_secret,
    ):
        raise HTTPException(status_code=401, detail="invalid Bright Data webhook credentials")
    content_type = request.headers.get("content-type", "").lower()
    if "application/json" not in content_type:
        raise HTTPException(status_code=415, detail="Bright Data webhook must use JSON")
    raw_body = await request.body()
    if len(raw_body) > settings.webhook_max_bytes:
        raise HTTPException(status_code=413, detail="Bright Data webhook payload is too large")
    try:
        decoded = json.loads(raw_body)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="invalid JSON payload") from exc
    snapshot_id = (
        request.headers.get("x-snapshot-id")
        or request.headers.get("x-brightdata-snapshot-id")
        or request.query_params.get("snapshot_id")
    )
    if isinstance(decoded, list):
        payload: dict[str, Any] = {"snapshot_id": snapshot_id, "results": decoded}
    elif isinstance(decoded, dict):
        payload = decoded
        if snapshot_id and not any(key in payload for key in ("snapshot_id", "snapshotId", "id")):
            payload["snapshot_id"] = snapshot_id
    else:
        raise HTTPException(status_code=400, detail="webhook payload must be an object or array")
    external_event_id = (
        request.headers.get("x-brightdata-event-id") or hashlib.sha256(raw_body).hexdigest()
    )
    event = await record_webhook_event(
        session,
        provider="bright_data",
        external_event_id=external_event_id,
        payload=payload,
    )
    if event is None:
        return WebhookAccepted(duplicate=True)
    await session.commit()
    background_tasks.add_task(enqueue_provider_event, str(event.id))
    return WebhookAccepted()
