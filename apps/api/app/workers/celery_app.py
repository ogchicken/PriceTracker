from __future__ import annotations

from celery import Celery

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "pricetracker",
    broker=settings.effective_celery_broker_url,
    backend=settings.effective_celery_result_backend,
    include=["app.workers.tasks"],
)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
    beat_schedule={
        "claim-due-products": {
            "task": "tracking.claim_due_products",
            "schedule": 60.0,
        },
        "mark-stale-provider-jobs": {
            "task": "tracking.mark_stale_jobs",
            "schedule": 300.0,
        },
        "process-webhook-inbox": {
            "task": "tracking.process_webhook_inbox",
            "schedule": 60.0,
        },
        "deliver-notifications": {
            "task": "notifications.deliver",
            "schedule": 30.0,
        },
    },
)
