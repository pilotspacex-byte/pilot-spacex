"""Rate limiting middleware.

Implements per-workspace rate limiting using Redis (NFR-019):
- Standard endpoints: 1000 requests/minute
- AI endpoints: 100 requests/minute

Per-workspace overrides are stored in Redis cache (ws_limits:{workspace_id})
with a 60s TTL. On cache miss the DB is queried. On any Redis/DB error the
system default is used (fail-open).

Violation counter (rl_violations:{workspace_id}:{YYYYMMDD}) is incremented
on every 429 response for audit / anomaly detection.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from fastapi import HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse

from pilot_space.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from redis.asyncio import Redis
    from starlette.responses import Response

logger = get_logger(__name__)

# System-level defaults (used when workspace columns are NULL or on error)
_DEFAULT_STANDARD_RPM = 1000
_DEFAULT_AI_RPM = 100


@dataclass
class RateLimitConfig:
    """Rate limit configuration."""

    requests_per_minute: int
    key_prefix: str


# Endpoint type configurations
RATE_LIMIT_CONFIGS = {
    "ai": RateLimitConfig(requests_per_minute=_DEFAULT_AI_RPM, key_prefix="ai"),
    "standard": RateLimitConfig(requests_per_minute=_DEFAULT_STANDARD_RPM, key_prefix="standard"),
}

# AI endpoint path prefixes
AI_ENDPOINT_PREFIXES = (
    "/api/v1/ai/",
    "/api/v1/notes/",  # Ghost text generation
    "/api/v1/issues/ai/",
    "/api/v1/pr-review/",
)

# Redis cache TTL for workspace limits (seconds)
_WS_LIMITS_TTL = 60

# Violation counter retention (7 days in seconds)
_VIOLATION_TTL = 86400 * 7


def _get_endpoint_type(path: str) -> str:
    """Determine endpoint type from request path.

    Args:
        path: Request URL path.

    Returns:
        Endpoint type: 'ai' or 'standard'.
    """
    if path.startswith(AI_ENDPOINT_PREFIXES):
        return "ai"
    return "standard"


def _get_workspace_id(request: Request) -> str | None:
    """Extract workspace ID from request.

    Checks headers and path parameters.

    Args:
        request: FastAPI request object.

    Returns:
        Workspace ID or None if not found.
    """
    # Check header first
    workspace_id = request.headers.get("X-Workspace-ID")
    if workspace_id:
        return workspace_id

    # Check path parameters
    if hasattr(request, "path_params"):
        workspace_id = request.path_params.get("workspace_id")
        if workspace_id:
            return str(workspace_id)

    return None


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware using Redis sliding window.

    Tracks request counts per workspace and endpoint type using Redis.
    Returns 429 Too Many Requests with Retry-After header when limit exceeded.

    Per-workspace limits are read from Redis cache (ws_limits:{workspace_id}).
    Cache miss triggers a DB lookup. Both Redis and DB errors fall back to
    system defaults (fail-open).
    """

    def __init__(
        self,
        app: object,
        redis_client: Redis | None = None,
        *,
        enabled: bool = True,
        db_url: str | None = None,
    ) -> None:
        """Initialize rate limiter.

        Args:
            app: ASGI application.
            redis_client: Redis async client. When provided (unit test path),
                          rate limiting is enabled immediately without lazy
                          resolution. When None (runtime path), the middleware
                          resolves the Redis client lazily from
                          ``request.app.state.container`` on the first request.
            enabled: Whether rate limiting is enabled. Set to False to disable
                     entirely (e.g. tests that explicitly opt out).
            db_url: Optional database URL for per-workspace limit lookups.
                    When None and no container is available, the DB fallback
                    path is disabled and system defaults are used on cache miss.
                    Ignored when ``redis_client`` is None — db_url is then read
                    lazily from the DI container settings.
        """
        super().__init__(app)  # type: ignore[arg-type]
        self.redis = redis_client
        self.enabled = enabled
        self._db_url = db_url
        self._session_factory: async_sessionmaker[AsyncSession] | None = None
        if db_url:
            engine = create_async_engine(db_url, pool_pre_ping=True)
            self._session_factory = async_sessionmaker(
                engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )
        # Lazy-resolution state (used when redis_client is not provided at init time)
        self._redis_resolved: bool = redis_client is not None

    # -------------------------------------------------------------------------
    # Lazy Redis resolver
    # -------------------------------------------------------------------------

    def _resolve_redis(self, request: Request) -> None:
        """Lazily resolve Redis client from app container on first request.

        Follows the same pattern as ``SessionRecordingMiddleware._resolve_dependencies``.
        No-op after the first successful resolution. Fails open (rate limiting
        disabled) when the container is not yet available or Redis is not
        configured.

        Args:
            request: Incoming request with access to ``request.app.state.container``.
        """
        if self._redis_resolved:
            return
        try:
            container = request.app.state.container
            redis_client_wrapper = container.redis_client()
            if redis_client_wrapper is not None:
                self.redis = redis_client_wrapper.client  # raw redis.asyncio.Redis instance
            settings = container.settings()
            db_url: str | None = settings.database_url.get_secret_value()
            if db_url and self._session_factory is None:
                engine = create_async_engine(db_url, pool_pre_ping=True)
                self._session_factory = async_sessionmaker(
                    engine,
                    class_=AsyncSession,
                    expire_on_commit=False,
                )
            self._redis_resolved = True
        except Exception:
            logger.debug("RateLimitMiddleware: container not yet available, rate limiting disabled")

    # -------------------------------------------------------------------------
    # Per-workspace limit helpers
    # -------------------------------------------------------------------------

    async def _get_workspace_limits_from_db(self, workspace_id: str) -> dict[str, int]:
        """Query per-workspace rate limit columns from the database.

        Falls back to system defaults when:
        - No session factory configured
        - Workspace not found
        - Column value is NULL

        Args:
            workspace_id: UUID string of the workspace.

        Returns:
            Dict with keys ``standard_rpm`` and ``ai_rpm``.
        """
        defaults: dict[str, int] = {
            "standard_rpm": _DEFAULT_STANDARD_RPM,
            "ai_rpm": _DEFAULT_AI_RPM,
        }

        if self._session_factory is None:
            return defaults

        try:
            # Import here to avoid circular imports at module load time
            import uuid as _uuid

            from pilot_space.infrastructure.database.models.workspace import Workspace

            ws_uuid = _uuid.UUID(workspace_id)

            async with self._session_factory() as session:  # type: ignore[attr-defined]
                result = await session.execute(
                    select(
                        Workspace.rate_limit_standard_rpm,
                        Workspace.rate_limit_ai_rpm,
                    ).where(
                        Workspace.id == ws_uuid,
                        Workspace.is_deleted == False,  # noqa: E712
                    )
                )
                row = result.first()
                if row is None:
                    return defaults

                standard_rpm, ai_rpm = row
                return {
                    "standard_rpm": standard_rpm
                    if standard_rpm is not None
                    else _DEFAULT_STANDARD_RPM,
                    "ai_rpm": ai_rpm if ai_rpm is not None else _DEFAULT_AI_RPM,
                }
        except Exception:
            logger.exception(
                "Rate limiter: DB lookup failed for workspace %s, using defaults",
                workspace_id,
            )
            return defaults

    async def _get_effective_limit(self, workspace_id: str, endpoint_type: str) -> int:
        """Return the effective RPM limit for a workspace and endpoint type.

        Lookup order:
        1. Redis cache key ``ws_limits:{workspace_id}`` (JSON, 60 s TTL)
        2. DB query → populate cache → return value
        3. System default on any error (fail-open)

        Args:
            workspace_id: Workspace UUID string.
            endpoint_type: ``"standard"`` or ``"ai"``.

        Returns:
            Requests-per-minute integer limit.
        """
        if self.redis is None:
            return RATE_LIMIT_CONFIGS[endpoint_type].requests_per_minute

        cache_key = f"ws_limits:{workspace_id}"
        rpm_field = f"{endpoint_type}_rpm"

        try:
            cached = await self.redis.get(cache_key)
            if cached is not None:
                limits: dict[str, int] = json.loads(cached)
                return limits.get(rpm_field, RATE_LIMIT_CONFIGS[endpoint_type].requests_per_minute)

            # Cache miss — fetch from DB and populate cache
            limits = await self._get_workspace_limits_from_db(workspace_id)
            await self.redis.set(cache_key, json.dumps(limits), ex=_WS_LIMITS_TTL)
            return limits.get(rpm_field, RATE_LIMIT_CONFIGS[endpoint_type].requests_per_minute)

        except Exception:
            logger.exception(
                "Rate limiter: Redis error in _get_effective_limit, using system default"
            )
            return RATE_LIMIT_CONFIGS[endpoint_type].requests_per_minute

    async def _increment_violation_counter(self, workspace_id: str) -> None:
        """Increment the daily violation counter in Redis.

        Key pattern: ``rl_violations:{workspace_id}:{YYYYMMDD}``
        Expires after 7 days.

        Args:
            workspace_id: Workspace UUID string.
        """
        if self.redis is None:
            return
        try:
            today = datetime.now(UTC).strftime("%Y%m%d")
            violation_key = f"rl_violations:{workspace_id}:{today}"
            await self.redis.incr(violation_key)
            await self.redis.expire(violation_key, _VIOLATION_TTL)
        except Exception:
            logger.exception(
                "Rate limiter: failed to increment violation counter for %s",
                workspace_id,
            )

    # -------------------------------------------------------------------------
    # Middleware dispatch
    # -------------------------------------------------------------------------

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """Process request with rate limiting.

        Args:
            request: Incoming request.
            call_next: Next middleware/handler.

        Returns:
            Response with rate limit headers.

        Raises:
            HTTPException: 429 if rate limit exceeded.
        """
        self._resolve_redis(request)
        if not self.enabled or self.redis is None:
            return await call_next(request)

        # Skip rate limiting for health checks
        if request.url.path in ("/health", "/api/v1/health"):
            return await call_next(request)

        workspace_id = _get_workspace_id(request)
        if not workspace_id:
            # No workspace context - use IP-based limiting
            workspace_id = request.client.host if request.client else "unknown"

        endpoint_type = _get_endpoint_type(request.url.path)
        config = RATE_LIMIT_CONFIGS[endpoint_type]

        # Resolve effective limit (per-workspace override or system default)
        effective_limit = await self._get_effective_limit(workspace_id, endpoint_type)

        # Redis key: ratelimit:{workspace_id}:{endpoint_type}:{minute}
        current_minute = int(time.time() // 60)
        redis_key = f"ratelimit:{workspace_id}:{config.key_prefix}:{current_minute}"

        # Check rate limit and process request
        rate_limit_result = await self._check_rate_limit(
            redis_key, effective_limit, workspace_id, endpoint_type
        )

        if rate_limit_result is None:
            # Redis error - allow request through
            return await call_next(request)

        current_count, remaining, reset_time = rate_limit_result

        # Limit exceeded - increment violation counter and return 429
        if current_count > effective_limit:
            await self._increment_violation_counter(workspace_id)
            return self._rate_limit_exceeded_response(effective_limit, reset_time)

        # Process request and add rate limit headers
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(effective_limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_time)
        return response

    async def _check_rate_limit(
        self,
        redis_key: str,
        limit: int,
        workspace_id: str,
        endpoint_type: str,
    ) -> tuple[int, int, int] | None:
        """Check rate limit counter in Redis.

        Args:
            redis_key: Redis key for rate limit counter.
            limit: Maximum requests per minute.
            workspace_id: Workspace identifier for logging.
            endpoint_type: Endpoint type for logging.

        Returns:
            Tuple of (current_count, remaining, reset_time) or None on Redis error.
        """
        if self.redis is None:
            return None

        current_count: int = 0
        remaining: int = 0
        reset_time: int = 0

        try:
            current_count = await self.redis.incr(redis_key)
            if current_count == 1:
                await self.redis.expire(redis_key, 120)

            current_minute = int(time.time() // 60)
            remaining = max(0, limit - current_count)
            reset_time = (current_minute + 1) * 60

            if current_count > limit:
                logger.warning(
                    "Rate limit exceeded",
                    extra={
                        "workspace_id": workspace_id,
                        "endpoint_type": endpoint_type,
                        "count": current_count,
                        "limit": limit,
                    },
                )
        except Exception:
            logger.exception("Rate limiter error - allowing request")
            return None

        return current_count, remaining, reset_time

    def _raise_rate_limit_exceeded(self, limit: int, reset_time: int) -> None:
        """Raise HTTPException for rate limit exceeded (used by unit tests).

        Args:
            limit: Maximum requests per minute.
            reset_time: Unix timestamp when rate limit resets.

        Raises:
            HTTPException: 429 Too Many Requests.
        """
        retry_after = reset_time - int(time.time())
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Retry after {retry_after} seconds.",
            headers={
                "Retry-After": str(retry_after),
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(reset_time),
            },
        )

    def _rate_limit_exceeded_response(self, limit: int, reset_time: int) -> JSONResponse:
        """Return a 429 JSONResponse for rate limit exceeded.

        Used by dispatch() — BaseHTTPMiddleware must return a Response, not
        raise HTTPException, so that Starlette's ExceptionMiddleware does not
        convert the 429 to a 500 via the collapse_excgroups mechanism.

        Args:
            limit: Maximum requests per minute.
            reset_time: Unix timestamp when rate limit resets.

        Returns:
            JSONResponse with status 429 and Retry-After header.
        """
        retry_after = reset_time - int(time.time())
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "detail": f"Rate limit exceeded. Retry after {retry_after} seconds.",
            },
            headers={
                "Retry-After": str(retry_after),
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(reset_time),
            },
        )


__all__ = ["RATE_LIMIT_CONFIGS", "RateLimitMiddleware"]
