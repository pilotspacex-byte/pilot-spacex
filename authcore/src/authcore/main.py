"""AuthCore FastAPI application entry point."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from authcore.api.v1.middleware.error_handler import authcore_exception_handler
from authcore.api.v1.middleware.request_id import RequestIDMiddleware
from authcore.api.v1.routers import admin, auth
from authcore.container.container import Container
from authcore.domain.exceptions import AuthCoreException
from authcore.infrastructure.cache.redis_client import RedisClient

logger = structlog.get_logger(__name__)

_container: Container | None = None


def _get_container() -> Container:
    global _container
    if _container is None:
        _container = Container()
    return _container


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        Configured FastAPI application instance.
    """
    container = _get_container()
    container.wire(
        modules=[
            "authcore.api.v1.routers.auth",
            "authcore.api.v1.routers.admin",
            "authcore.api.dependencies.auth",
        ]
    )

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
        logger.info("authcore_starting")
        yield
        # Graceful shutdown: close Redis + DB engine
        redis: RedisClient = await container.infra.redis_client()  # type: ignore[misc]
        await redis.close()  # type: ignore[misc]
        engine = await container.infra.db_engine()  # type: ignore[misc]
        await engine.dispose()  # type: ignore[misc]
        logger.info("authcore_stopped")

    app = FastAPI(
        title="AuthCore",
        version="0.1.0",
        description="Standalone JWT authentication microservice",
        lifespan=lifespan,
    )

    # Attach DI container to app state for testing
    app.container = container  # type: ignore[attr-defined]

    # Middleware (order matters: outermost first)
    settings = container.config()  # type: ignore[misc]
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.debug else [],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Exception handlers
    app.add_exception_handler(AuthCoreException, authcore_exception_handler)  # type: ignore[arg-type]

    # Routers
    app.include_router(auth.router, prefix="/api/v1")
    app.include_router(admin.router, prefix="/api/v1")

    # Health endpoints
    app.add_api_route("/health", _liveness, methods=["GET"], tags=["health"])
    app.add_api_route("/health/live", _liveness, methods=["GET"], tags=["health"])
    app.add_api_route("/health/ready", _readiness, methods=["GET"], tags=["health"])

    return app


async def _liveness() -> dict[str, str]:
    return {"status": "ok"}


async def _readiness() -> dict[str, str]:
    container = _get_container()
    redis: RedisClient = container.infra.redis_client()  # type: ignore[misc]
    redis_ok: bool = await redis.ping()  # type: ignore[misc]
    if not redis_ok:
        raise HTTPException(status_code=503, detail="Redis unavailable")
    return {"status": "ready"}


app = create_app()
