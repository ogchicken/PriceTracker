from fastapi import APIRouter

from app.api.v1 import notifications, users, watches, webhooks

router = APIRouter()
router.include_router(watches.router, prefix="/watches", tags=["watches"])
router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
router.include_router(users.router, prefix="/me", tags=["me"])
router.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])
