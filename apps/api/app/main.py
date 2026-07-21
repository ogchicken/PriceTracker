from __future__ import annotations

import time
import uuid
from contextlib import asynccontextmanager
from typing import AsyncIterator

import redis.asyncio as redis
import structlog
from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from sqlalchemy import text

from app.api.v1 import router as api_v1_router
from app.config import get_settings
from app.db import SessionFactory, dispose_engine
from app.logging import configure_logging, get_logger

settings = get_settings()
configure_logging(settings.log_level, json_logs=settings.environment != "development")
logger = get_logger(__name__)

REQUESTS = Counter(
    "pricetracker_http_requests_total",
    "HTTP requests handled",
    ("method", "route", "status"),
)
LATENCY = Histogram(
    "pricetracker_http_request_duration_seconds",
    "HTTP request duration",
    ("method", "route"),
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.redis = redis.from_url(settings.redis_url, decode_responses=True)
    logger.info("application_started", environment=settings.environment)
    try:
        yield
    finally:
        await app.state.redis.aclose()
        await dispose_engine()
        logger.info("application_stopped")


def create_app() -> FastAPI:
    application = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        debug=settings.debug,
        lifespan=lifespan,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "Svix-Id",
            "Svix-Signature",
            "Svix-Timestamp",
        ],
    )

    @application.middleware("http")
    async def observability_middleware(request: Request, call_next) -> Response:
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)
        started = time.perf_counter()
        response_status = 500
        try:
            response = await call_next(request)
            response_status = response.status_code
        except Exception:
            logger.exception("unhandled_request_error", path=request.url.path)
            raise
        finally:
            route = request.scope.get("route")
            route_path = getattr(route, "path", "unmatched")
            REQUESTS.labels(request.method, route_path, str(response_status)).inc()
            LATENCY.labels(request.method, route_path).observe(time.perf_counter() - started)
            structlog.contextvars.clear_contextvars()
        response.headers["x-request-id"] = request_id
        return response

    @application.get("/healthz", include_in_schema=False)
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @application.get("/readyz", include_in_schema=False)
    async def readyz(request: Request) -> Response:
        checks: dict[str, str] = {}
        try:
            async with SessionFactory() as session:
                await session.execute(text("SELECT 1"))
            checks["database"] = "ok"
        except Exception:
            checks["database"] = "unavailable"
        try:
            await request.app.state.redis.ping()
            checks["redis"] = "ok"
        except Exception:
            checks["redis"] = "unavailable"
        ready = all(value == "ok" for value in checks.values())
        return JSONResponse(
            {"status": "ok" if ready else "not_ready", "checks": checks},
            status_code=status.HTTP_200_OK if ready else status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    @application.get("/metrics", include_in_schema=False)
    async def metrics() -> Response:
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    application.include_router(api_v1_router, prefix=settings.api_v1_prefix)
    return application


app = create_app()
