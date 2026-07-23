from __future__ import annotations

from collections.abc import Callable

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.clerk import AuthUser
from app.models import User
from tests.conftest import OTHER_IDENTITY, PRIMARY_IDENTITY


async def test_preferences_requires_authentication(client: TestClient) -> None:
    assert client.get("/api/v1/me/preferences").status_code == 401


async def test_get_preferences_returns_defaults_for_a_new_user(
    authed_client: TestClient,
) -> None:
    body = authed_client.get("/api/v1/me/preferences").json()

    assert body == {
        "email": PRIMARY_IDENTITY.email,
        "email_enabled": True,
        "alert_rearm_percent": 3,
    }


async def test_first_request_provisions_the_user(
    authed_client: TestClient, db_session: AsyncSession
) -> None:
    # Users are created lazily from the verified token, not by a signup call.
    assert (await db_session.scalars(select(User))).all() == []

    authed_client.get("/api/v1/me/preferences")

    user = (await db_session.scalars(select(User))).one()
    assert user.clerk_user_id == PRIMARY_IDENTITY.clerk_user_id
    assert user.email == PRIMARY_IDENTITY.email


async def test_update_preferences_round_trips(authed_client: TestClient) -> None:
    updated = authed_client.patch(
        "/api/v1/me/preferences",
        json={"email_enabled": False, "alert_rearm_percent": 12},
    )

    assert updated.status_code == 200
    assert updated.json()["email_enabled"] is False
    assert updated.json()["alert_rearm_percent"] == 12
    assert authed_client.get("/api/v1/me/preferences").json() == updated.json()


async def test_update_preferences_merges_rather_than_replaces(
    authed_client: TestClient,
) -> None:
    authed_client.patch("/api/v1/me/preferences", json={"alert_rearm_percent": 20})

    body = authed_client.patch("/api/v1/me/preferences", json={"email_enabled": False}).json()

    assert body["alert_rearm_percent"] == 20
    assert body["email_enabled"] is False


async def test_update_preferences_rejects_an_out_of_range_percent(
    authed_client: TestClient,
) -> None:
    response = authed_client.patch("/api/v1/me/preferences", json={"alert_rearm_percent": 101})

    assert response.status_code == 422


async def test_preferences_are_per_user(
    authenticate: Callable[[AuthUser], TestClient],
    authed_client: TestClient,
) -> None:
    authed_client.patch("/api/v1/me/preferences", json={"alert_rearm_percent": 25})

    other = authenticate(OTHER_IDENTITY)

    assert other.get("/api/v1/me/preferences").json()["alert_rearm_percent"] == 3
