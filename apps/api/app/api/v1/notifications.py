from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.models import NotificationChannel, NotificationOutbox
from app.schemas import NotificationResponse, NotificationUpdate
from app.services.tracking import utcnow

router = APIRouter()


@router.get("", response_model=list[NotificationResponse])
async def list_notifications(
    session: DbSession,
    user: CurrentUser,
    unread_only: bool = False,
    limit: int = Query(default=50, ge=1, le=200),
) -> list[NotificationOutbox]:
    query = (
        select(NotificationOutbox)
        .where(
            NotificationOutbox.user_id == user.id,
            NotificationOutbox.channel == NotificationChannel.IN_APP,
        )
        .order_by(NotificationOutbox.created_at.desc())
        .limit(limit)
    )
    if unread_only:
        query = query.where(NotificationOutbox.read_at.is_(None))
    return list((await session.scalars(query)).all())


@router.patch("/{notification_id}", response_model=NotificationResponse)
async def update_notification(
    notification_id: uuid.UUID,
    body: NotificationUpdate,
    session: DbSession,
    user: CurrentUser,
) -> NotificationOutbox:
    notification = await session.scalar(
        select(NotificationOutbox).where(
            NotificationOutbox.id == notification_id,
            NotificationOutbox.user_id == user.id,
            NotificationOutbox.channel == NotificationChannel.IN_APP,
        )
    )
    if notification is None:
        raise HTTPException(status_code=404, detail="notification not found")
    notification.read_at = utcnow() if body.read else None
    await session.flush()
    return notification
