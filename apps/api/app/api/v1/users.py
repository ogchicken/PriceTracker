from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession
from app.schemas import UserPreferencesResponse, UserPreferencesUpdate

router = APIRouter()


def _preferences_response(user: CurrentUser) -> UserPreferencesResponse:
    preferences = user.preferences_data or {}
    return UserPreferencesResponse(
        email=user.email,
        email_enabled=bool(preferences.get("email_enabled", True)),
        alert_rearm_percent=int(preferences.get("alert_rearm_percent", 3)),
    )


@router.get("/preferences", response_model=UserPreferencesResponse)
async def get_preferences(user: CurrentUser) -> UserPreferencesResponse:
    return _preferences_response(user)


@router.patch("/preferences", response_model=UserPreferencesResponse)
async def update_preferences(
    body: UserPreferencesUpdate,
    session: DbSession,
    user: CurrentUser,
) -> UserPreferencesResponse:
    preferences = dict(user.preferences_data or {})
    preferences.update(body.model_dump(exclude_none=True))
    user.preferences_data = preferences
    await session.flush()
    return _preferences_response(user)
