from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Store(str, enum.Enum):
    AMAZON = "amazon"
    EBAY = "ebay"


class WatchStatus(str, enum.Enum):
    ACTIVE = "active"
    PAUSED = "paused"


class AlertState(str, enum.Enum):
    ARMED = "armed"
    TRIGGERED = "triggered"


class ProviderName(str, enum.Enum):
    BRIGHT_DATA = "bright_data"


class ProviderJobState(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    STALE = "stale"


class AvailabilityStatus(str, enum.Enum):
    UNKNOWN = "unknown"
    IN_STOCK = "in_stock"
    OUT_OF_STOCK = "out_of_stock"
    UNAVAILABLE = "unavailable"


class AlertKind(str, enum.Enum):
    INITIAL_BELOW_TARGET = "initial_below_target"
    PRICE_DROP = "price_drop"


class NotificationChannel(str, enum.Enum):
    EMAIL = "email"
    IN_APP = "in_app"


class NotificationStatus(str, enum.Enum):
    PENDING = "pending"
    SENDING = "sending"
    SENT = "sent"
    FAILED = "failed"


def _enum(enum_type: type[enum.Enum], name: str) -> SAEnum:
    return SAEnum(
        enum_type,
        name=name,
        native_enum=False,
        values_callable=lambda members: [member.value for member in members],
    )


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    clerk_user_id: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    email: Mapped[str | None] = mapped_column(String(320))
    preferences_data: Mapped[dict[str, Any]] = mapped_column(
        "preferences", JSON, default=dict, nullable=False
    )

    watches: Mapped[list[Watch]] = relationship(back_populates="user", cascade="all, delete-orphan")
    alerts: Mapped[list[Alert]] = relationship(back_populates="user", passive_deletes=True)
    notifications: Mapped[list[NotificationOutbox]] = relationship(
        back_populates="user", passive_deletes=True
    )

    __table_args__ = (Index("ix_users_email", "email"),)


class StoreProduct(TimestampMixin, Base):
    __tablename__ = "store_products"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    store: Mapped[Store] = mapped_column(_enum(Store, "store_name"), nullable=False)
    region: Mapped[str] = mapped_column(String(32), nullable=False)
    external_id: Mapped[str] = mapped_column(String(128), nullable=False)
    canonical_url: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str | None] = mapped_column(Text)
    image_url: Mapped[str | None] = mapped_column(Text)
    currency: Mapped[str | None] = mapped_column(String(3))
    item_price_minor: Mapped[int | None] = mapped_column(BigInteger)
    shipping_price_minor: Mapped[int | None] = mapped_column(BigInteger)
    current_price_minor: Mapped[int | None] = mapped_column(BigInteger)
    availability: Mapped[AvailabilityStatus] = mapped_column(
        _enum(AvailabilityStatus, "availability_status"),
        default=AvailabilityStatus.UNKNOWN,
        nullable=False,
    )
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    next_check_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSON, default=dict, nullable=False
    )

    watches: Mapped[list[Watch]] = relationship(back_populates="product", passive_deletes=True)
    observations: Mapped[list[PriceObservation]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint(
            "store",
            "region",
            "external_id",
            name="uq_store_products_store_region_external_id",
        ),
        CheckConstraint(
            "current_price_minor IS NULL OR current_price_minor >= 0",
            name="store_product_nonnegative_price",
        ),
        CheckConstraint(
            "item_price_minor IS NULL OR item_price_minor >= 0",
            name="store_product_nonnegative_item_price",
        ),
        CheckConstraint(
            "shipping_price_minor IS NULL OR shipping_price_minor >= 0",
            name="store_product_nonnegative_shipping_price",
        ),
        CheckConstraint("consecutive_failures >= 0", name="store_product_nonnegative_failures"),
        Index("ix_store_products_due", "active", "next_check_at", "lease_until"),
    )


class Watch(TimestampMixin, Base):
    __tablename__ = "watches"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("store_products.id", ondelete="CASCADE"), nullable=False
    )
    target_price_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    status: Mapped[WatchStatus] = mapped_column(
        _enum(WatchStatus, "watch_status"), default=WatchStatus.ACTIVE, nullable=False
    )
    alert_state: Mapped[AlertState] = mapped_column(
        _enum(AlertState, "alert_state"), default=AlertState.ARMED, nullable=False
    )
    notify_initial_below_target: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_evaluated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship(back_populates="watches")
    product: Mapped[StoreProduct] = relationship(back_populates="watches")
    alerts: Mapped[list[Alert]] = relationship(back_populates="watch", passive_deletes=True)

    __table_args__ = (
        UniqueConstraint("user_id", "product_id", name="uq_watches_user_product"),
        CheckConstraint("target_price_minor >= 0", name="watch_nonnegative_target"),
        Index("ix_watches_user_status", "user_id", "status"),
        Index("ix_watches_product_status", "product_id", "status"),
    )


class ProviderJob(TimestampMixin, Base):
    __tablename__ = "provider_jobs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider: Mapped[ProviderName] = mapped_column(
        _enum(ProviderName, "provider_name"),
        default=ProviderName.BRIGHT_DATA,
        nullable=False,
    )
    external_job_id: Mapped[str | None] = mapped_column(String(255))
    dataset_id: Mapped[str] = mapped_column(String(255), nullable=False)
    state: Mapped[ProviderJobState] = mapped_column(
        _enum(ProviderJobState, "provider_job_state"),
        default=ProviderJobState.PENDING,
        nullable=False,
    )
    product_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    stale_after: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error: Mapped[str | None] = mapped_column(Text)
    response_data: Mapped[dict[str, Any]] = mapped_column(
        "response", JSON, default=dict, nullable=False
    )

    observations: Mapped[list[PriceObservation]] = relationship(
        back_populates="provider_job", passive_deletes=True
    )

    __table_args__ = (
        UniqueConstraint(
            "provider", "external_job_id", name="uq_provider_jobs_provider_external_job_id"
        ),
        CheckConstraint("attempts >= 0", name="provider_job_nonnegative_attempts"),
        Index("ix_provider_jobs_state_stale_after", "state", "stale_after"),
    )


class PriceObservation(Base):
    __tablename__ = "price_observations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("store_products.id", ondelete="CASCADE"), nullable=False
    )
    provider_job_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("provider_jobs.id", ondelete="SET NULL")
    )
    price_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    item_price_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    shipping_price_minor: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    availability: Mapped[AvailabilityStatus] = mapped_column(
        _enum(AvailabilityStatus, "observation_availability"),
        default=AvailabilityStatus.UNKNOWN,
        nullable=False,
    )
    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    source: Mapped[ProviderName] = mapped_column(_enum(ProviderName, "observation_source"))
    raw_data: Mapped[dict[str, Any]] = mapped_column("raw_metadata", JSON, default=dict)

    product: Mapped[StoreProduct] = relationship(back_populates="observations")
    provider_job: Mapped[ProviderJob | None] = relationship(back_populates="observations")
    alerts: Mapped[list[Alert]] = relationship(back_populates="observation", passive_deletes=True)

    __table_args__ = (
        UniqueConstraint("provider_job_id", "product_id", name="uq_price_observations_job_product"),
        CheckConstraint("price_minor >= 0", name="observation_nonnegative_price"),
        CheckConstraint("item_price_minor >= 0", name="observation_nonnegative_item_price"),
        CheckConstraint(
            "shipping_price_minor >= 0",
            name="observation_nonnegative_shipping_price",
        ),
        Index("ix_price_observations_product_observed", "product_id", "observed_at"),
    )


class WebhookEvent(Base):
    __tablename__ = "webhook_events"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    external_event_id: Mapped[str] = mapped_column(String(255), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        UniqueConstraint(
            "provider", "external_event_id", name="uq_webhook_events_provider_external_event_id"
        ),
        Index("ix_webhook_events_unprocessed", "provider", "processed_at"),
    )


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    watch_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("watches.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    observation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("price_observations.id", ondelete="CASCADE"),
        nullable=False,
    )
    kind: Mapped[AlertKind] = mapped_column(_enum(AlertKind, "alert_kind"), nullable=False)
    price_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    target_price_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    dedupe_key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    watch: Mapped[Watch] = relationship(back_populates="alerts")
    user: Mapped[User] = relationship(back_populates="alerts")
    observation: Mapped[PriceObservation] = relationship(back_populates="alerts")
    notifications: Mapped[list[NotificationOutbox]] = relationship(
        back_populates="alert", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("ix_alerts_user_created", "user_id", "created_at"),)


class NotificationOutbox(TimestampMixin, Base):
    __tablename__ = "notification_outbox"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    alert_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("alerts.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    channel: Mapped[NotificationChannel] = mapped_column(
        _enum(NotificationChannel, "notification_channel"),
        default=NotificationChannel.EMAIL,
        nullable=False,
    )
    status: Mapped[NotificationStatus] = mapped_column(
        _enum(NotificationStatus, "notification_status"),
        default=NotificationStatus.PENDING,
        nullable=False,
    )
    recipient: Mapped[str] = mapped_column(String(320), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    dedupe_key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)

    alert: Mapped[Alert] = relationship(back_populates="notifications")
    user: Mapped[User] = relationship(back_populates="notifications")

    __table_args__ = (
        CheckConstraint("attempts >= 0", name="notification_nonnegative_attempts"),
        Index("ix_notification_outbox_delivery", "status", "available_at"),
        Index("ix_notification_outbox_user_created", "user_id", "created_at"),
    )


__all__ = [
    "Alert",
    "AlertKind",
    "AlertState",
    "AvailabilityStatus",
    "NotificationChannel",
    "NotificationOutbox",
    "NotificationStatus",
    "PriceObservation",
    "ProviderJob",
    "ProviderJobState",
    "ProviderName",
    "Store",
    "StoreProduct",
    "User",
    "Watch",
    "WatchStatus",
    "WebhookEvent",
]
