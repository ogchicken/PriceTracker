"""Create PriceTracker core schema.

Revision ID: 0001_initial
Revises:
Create Date: 2026-07-21
"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("clerk_user_id", sa.String(128), nullable=False),
        sa.Column("email", sa.String(320), nullable=True),
        sa.Column("preferences", sa.JSON(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("clerk_user_id", name="uq_users_clerk_user_id"),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "store_products",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "store",
            sa.Enum("amazon", "ebay", name="store_name", native_enum=False),
            nullable=False,
        ),
        sa.Column("region", sa.String(32), nullable=False),
        sa.Column("external_id", sa.String(128), nullable=False),
        sa.Column("canonical_url", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("image_url", sa.Text(), nullable=True),
        sa.Column("currency", sa.String(3), nullable=True),
        sa.Column("item_price_minor", sa.BigInteger(), nullable=True),
        sa.Column("shipping_price_minor", sa.BigInteger(), nullable=True),
        sa.Column("current_price_minor", sa.BigInteger(), nullable=True),
        sa.Column(
            "availability",
            sa.Enum(
                "unknown",
                "in_stock",
                "out_of_stock",
                "unavailable",
                name="availability_status",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column(
            "next_check_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("lease_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("consecutive_failures", sa.Integer(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "current_price_minor IS NULL OR current_price_minor >= 0",
            name="ck_store_products_store_product_nonnegative_price",
        ),
        sa.CheckConstraint(
            "item_price_minor IS NULL OR item_price_minor >= 0",
            name="ck_store_products_store_product_nonnegative_item_price",
        ),
        sa.CheckConstraint(
            "shipping_price_minor IS NULL OR shipping_price_minor >= 0",
            name="ck_store_products_store_product_nonnegative_shipping_price",
        ),
        sa.CheckConstraint(
            "consecutive_failures >= 0",
            name="ck_store_products_store_product_nonnegative_failures",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_store_products"),
        sa.UniqueConstraint(
            "store",
            "region",
            "external_id",
            name="uq_store_products_store_region_external_id",
        ),
    )
    op.create_index(
        "ix_store_products_due",
        "store_products",
        ["active", "next_check_at", "lease_until"],
    )

    op.create_table(
        "provider_jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "provider",
            sa.Enum("bright_data", name="provider_name", native_enum=False),
            nullable=False,
        ),
        sa.Column("external_job_id", sa.String(255), nullable=True),
        sa.Column("dataset_id", sa.String(255), nullable=False),
        sa.Column(
            "state",
            sa.Enum(
                "pending",
                "running",
                "succeeded",
                "failed",
                "stale",
                name="provider_job_state",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("product_ids", sa.JSON(), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("stale_after", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("response", sa.JSON(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "attempts >= 0",
            name="ck_provider_jobs_provider_job_nonnegative_attempts",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_provider_jobs"),
        sa.UniqueConstraint(
            "provider",
            "external_job_id",
            name="uq_provider_jobs_provider_external_job_id",
        ),
    )
    op.create_index(
        "ix_provider_jobs_state_stale_after",
        "provider_jobs",
        ["state", "stale_after"],
    )

    op.create_table(
        "watches",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("target_price_minor", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column(
            "status",
            sa.Enum("active", "paused", name="watch_status", native_enum=False),
            nullable=False,
        ),
        sa.Column(
            "alert_state",
            sa.Enum("armed", "triggered", name="alert_state", native_enum=False),
            nullable=False,
        ),
        sa.Column("notify_initial_below_target", sa.Boolean(), nullable=False),
        sa.Column("last_evaluated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "target_price_minor >= 0",
            name="ck_watches_watch_nonnegative_target",
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["store_products.id"],
            name="fk_watches_product_id_store_products",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_watches_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_watches"),
        sa.UniqueConstraint("user_id", "product_id", name="uq_watches_user_product"),
    )
    op.create_index("ix_watches_user_status", "watches", ["user_id", "status"])
    op.create_index("ix_watches_product_status", "watches", ["product_id", "status"])

    op.create_table(
        "price_observations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("provider_job_id", sa.Uuid(), nullable=True),
        sa.Column("price_minor", sa.BigInteger(), nullable=False),
        sa.Column("item_price_minor", sa.BigInteger(), nullable=False),
        sa.Column("shipping_price_minor", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column(
            "availability",
            sa.Enum(
                "unknown",
                "in_stock",
                "out_of_stock",
                "unavailable",
                name="observation_availability",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "observed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "source",
            sa.Enum("bright_data", name="observation_source", native_enum=False),
            nullable=False,
        ),
        sa.Column("raw_metadata", sa.JSON(), nullable=False),
        sa.CheckConstraint(
            "price_minor >= 0",
            name="ck_price_observations_observation_nonnegative_price",
        ),
        sa.CheckConstraint(
            "item_price_minor >= 0",
            name="ck_price_observations_observation_nonnegative_item_price",
        ),
        sa.CheckConstraint(
            "shipping_price_minor >= 0",
            name="ck_price_observations_observation_nonnegative_shipping_price",
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["store_products.id"],
            name="fk_price_observations_product_id_store_products",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["provider_job_id"],
            ["provider_jobs.id"],
            name="fk_price_observations_provider_job_id_provider_jobs",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_price_observations"),
        sa.UniqueConstraint(
            "provider_job_id",
            "product_id",
            name="uq_price_observations_job_product",
        ),
    )
    op.create_index(
        "ix_price_observations_product_observed",
        "price_observations",
        ["product_id", "observed_at"],
    )

    op.create_table(
        "webhook_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("external_event_id", sa.String(255), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column(
            "received_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_webhook_events"),
        sa.UniqueConstraint(
            "provider",
            "external_event_id",
            name="uq_webhook_events_provider_external_event_id",
        ),
    )
    op.create_index(
        "ix_webhook_events_unprocessed",
        "webhook_events",
        ["provider", "processed_at"],
    )

    op.create_table(
        "alerts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("watch_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("observation_id", sa.Uuid(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum(
                "initial_below_target",
                "price_drop",
                name="alert_kind",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("price_minor", sa.BigInteger(), nullable=False),
        sa.Column("target_price_minor", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("dedupe_key", sa.String(255), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["observation_id"],
            ["price_observations.id"],
            name="fk_alerts_observation_id_price_observations",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_alerts_user_id_users",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["watch_id"],
            ["watches.id"],
            name="fk_alerts_watch_id_watches",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_alerts"),
        sa.UniqueConstraint("dedupe_key", name="uq_alerts_dedupe_key"),
    )
    op.create_index("ix_alerts_user_created", "alerts", ["user_id", "created_at"])

    op.create_table(
        "notification_outbox",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("alert_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "channel",
            sa.Enum("email", "in_app", name="notification_channel", native_enum=False),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "sending",
                "sent",
                "failed",
                name="notification_status",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("recipient", sa.String(320), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("dedupe_key", sa.String(255), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column(
            "available_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "attempts >= 0",
            name="ck_notification_outbox_notification_nonnegative_attempts",
        ),
        sa.ForeignKeyConstraint(
            ["alert_id"],
            ["alerts.id"],
            name="fk_notification_outbox_alert_id_alerts",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_notification_outbox_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_notification_outbox"),
        sa.UniqueConstraint("dedupe_key", name="uq_notification_outbox_dedupe_key"),
    )
    op.create_index(
        "ix_notification_outbox_delivery",
        "notification_outbox",
        ["status", "available_at"],
    )
    op.create_index(
        "ix_notification_outbox_user_created",
        "notification_outbox",
        ["user_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_notification_outbox_user_created", table_name="notification_outbox")
    op.drop_index("ix_notification_outbox_delivery", table_name="notification_outbox")
    op.drop_table("notification_outbox")
    op.drop_index("ix_alerts_user_created", table_name="alerts")
    op.drop_table("alerts")
    op.drop_index("ix_webhook_events_unprocessed", table_name="webhook_events")
    op.drop_table("webhook_events")
    op.drop_index(
        "ix_price_observations_product_observed",
        table_name="price_observations",
    )
    op.drop_table("price_observations")
    op.drop_index("ix_watches_product_status", table_name="watches")
    op.drop_index("ix_watches_user_status", table_name="watches")
    op.drop_table("watches")
    op.drop_index("ix_provider_jobs_state_stale_after", table_name="provider_jobs")
    op.drop_table("provider_jobs")
    op.drop_index("ix_store_products_due", table_name="store_products")
    op.drop_table("store_products")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
