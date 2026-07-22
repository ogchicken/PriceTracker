from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models import (
    AlertState,
    AvailabilityStatus,
    NotificationChannel,
    NotificationStatus,
    Store,
    WatchStatus,
)


class ApiModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ProductResponse(ApiModel):
    id: uuid.UUID
    store: Store
    region: str
    external_id: str
    canonical_url: str
    title: str | None
    image_url: str | None
    item_price_minor: int | None
    shipping_price_minor: int | None
    current_price_minor: int | None
    currency: str | None
    availability: AvailabilityStatus
    last_checked_at: datetime | None


class WatchCreate(BaseModel):
    url: str = Field(min_length=8, max_length=2048)
    target_price_minor: int = Field(ge=0, le=9_000_000_000_000_000_000)
    currency: str = Field(pattern=r"^[A-Za-z]{3}$")
    notify_initial_below_target: bool = True
    notify_back_in_stock: bool = True

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.upper()


class WatchUpdate(BaseModel):
    target_price_minor: int | None = Field(
        default=None,
        ge=0,
        le=9_000_000_000_000_000_000,
    )
    status: WatchStatus | None = None
    notify_initial_below_target: bool | None = None
    notify_back_in_stock: bool | None = None


class WatchResponse(ApiModel):
    id: uuid.UUID
    target_price_minor: int
    currency: str
    status: WatchStatus
    alert_state: AlertState
    notify_initial_below_target: bool
    notify_back_in_stock: bool
    created_at: datetime
    updated_at: datetime
    product: ProductResponse


class PriceObservationResponse(ApiModel):
    id: uuid.UUID
    price_minor: int
    item_price_minor: int
    shipping_price_minor: int
    currency: str
    availability: AvailabilityStatus
    observed_at: datetime


class NotificationResponse(ApiModel):
    id: uuid.UUID
    channel: NotificationChannel
    status: NotificationStatus
    payload: dict[str, Any]
    sent_at: datetime | None
    read_at: datetime | None
    created_at: datetime


class NotificationUpdate(BaseModel):
    read: bool


class UserPreferences(BaseModel):
    email_enabled: bool = True
    alert_rearm_percent: int = Field(default=3, ge=0, le=100)


class UserPreferencesUpdate(BaseModel):
    email_enabled: bool | None = None
    alert_rearm_percent: int | None = Field(default=None, ge=0, le=100)


class UserPreferencesResponse(UserPreferences):
    email: EmailStr | None = None


class WebhookAccepted(BaseModel):
    accepted: bool = True
    duplicate: bool = False
