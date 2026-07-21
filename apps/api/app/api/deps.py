from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.clerk import AuthUser, get_current_identity
from app.db import get_db
from app.models import User
from app.stores.repositories import upsert_user

DbSession = Annotated[AsyncSession, Depends(get_db)]
Identity = Annotated[AuthUser, Depends(get_current_identity)]


async def get_current_user(
    session: DbSession,
    identity: Identity,
) -> User:
    user = await upsert_user(
        session,
        clerk_user_id=identity.clerk_user_id,
        email=identity.email,
    )
    await session.flush()
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
