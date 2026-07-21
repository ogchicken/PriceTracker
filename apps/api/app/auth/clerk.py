from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass
from typing import Any

import httpx
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt.types import Options

from app.config import Settings, get_settings

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True, slots=True)
class AuthUser:
    clerk_user_id: str
    email: str | None = None


class ClerkTokenVerifier:
    def __init__(self) -> None:
        self._jwks: dict[str, Any] | None = None
        self._jwks_expires_at = 0.0
        self._lock = asyncio.Lock()

    async def _load_jwks(self, settings: Settings) -> dict[str, Any]:
        if settings.clerk_jwks_json:
            try:
                configured = json.loads(settings.clerk_jwks_json)
            except json.JSONDecodeError as exc:
                raise HTTPException(
                    status_code=500, detail="Clerk JWKS configuration is invalid"
                ) from exc
            if not isinstance(configured, dict) or not isinstance(configured.get("keys"), list):
                raise HTTPException(status_code=500, detail="Clerk JWKS configuration is invalid")
            return configured
        now = time.monotonic()
        if self._jwks and now < self._jwks_expires_at:
            return self._jwks
        async with self._lock:
            if self._jwks and time.monotonic() < self._jwks_expires_at:
                return self._jwks
            try:
                async with httpx.AsyncClient(timeout=5) as client:
                    response = await client.get(settings.effective_clerk_jwks_url)
                    response.raise_for_status()
                    data = response.json()
                    if not isinstance(data, dict) or not isinstance(data.get("keys"), list):
                        raise ValueError("JWKS response has no key set")
            except (httpx.HTTPError, ValueError) as exc:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="authentication key service unavailable",
                ) from exc
            self._jwks = data
            self._jwks_expires_at = time.monotonic() + 600
            return data

    async def verify(self, token: str, settings: Settings) -> AuthUser:
        try:
            header = jwt.get_unverified_header(token)
            algorithm = header.get("alg")
            if algorithm != "RS256":
                raise jwt.InvalidAlgorithmError("only RS256 is accepted")
            if settings.clerk_pem_public_key:
                key: Any = settings.clerk_pem_public_key.replace("\\n", "\n")
            else:
                jwks = await self._load_jwks(settings)
                key_id = header.get("kid")
                matching = next(
                    (item for item in jwks.get("keys", []) if item.get("kid") == key_id), None
                )
                if matching is None:
                    self._jwks_expires_at = 0
                    jwks = await self._load_jwks(settings)
                    matching = next(
                        (item for item in jwks.get("keys", []) if item.get("kid") == key_id),
                        None,
                    )
                if matching is None:
                    raise jwt.InvalidKeyError("signing key was not found")
                key = jwt.PyJWK.from_dict(matching, algorithm="RS256").key
            decode_options: Options = {
                "require": ["exp", "iat", "sub"],
                "verify_aud": bool(settings.clerk_audience),
            }
            claims = jwt.decode(
                token,
                key,
                algorithms=["RS256"],
                issuer=settings.clerk_issuer.rstrip("/"),
                audience=settings.clerk_audience,
                options=decode_options,
            )
            authorized_parties = settings.clerk_authorized_parties
            if authorized_parties and claims.get("azp") not in authorized_parties:
                raise jwt.InvalidTokenError("unauthorized token party")
            subject = claims.get("sub")
            if not isinstance(subject, str) or not subject:
                raise jwt.InvalidTokenError("token subject is missing")
            email = claims.get("email") or claims.get("primary_email_address")
            return AuthUser(clerk_user_id=subject, email=email if isinstance(email, str) else None)
        except HTTPException:
            raise
        except (jwt.PyJWTError, TypeError, ValueError) as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="invalid bearer token",
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc


token_verifier = ClerkTokenVerifier()


async def get_current_identity(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    settings: Settings = Depends(get_settings),
) -> AuthUser:
    if credentials is None:
        if settings.fake_auth_enabled and settings.environment in {"development", "test"}:
            return AuthUser(settings.fake_auth_user_id, settings.fake_auth_email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="bearer token required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="bearer token required")
    return await token_verifier.verify(credentials.credentials, settings)
