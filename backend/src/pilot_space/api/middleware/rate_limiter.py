"""Rate limiting middleware.

Implements per-workspace rate limiting using Redis (NFR-019):
- Standard endpoints: 1000 requests/minute
- AI endpoints: 100 requests/minute
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

from fastapi import HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

if TYPE_CHECKING:
    from redis.asyncio import Redis
    from starlette.responses import Response

logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """Rate limit configuration."""

    requests_per_minute: int
    key_prefix: str


# Endpoint type configurations
RATE_LIMIT_CONFIGS = {
    "ai": RateLimitConfig(requests_per_minute=100, key_prefix="ai"),
    "standard": RateLimitConfig(requests_per_minute=1000, key_prefix="standard"),
}

# AI endpoint path prefixes
AI_ENDPOINT_PREFIXES = (
    "/api/v1/ai/",
    "/api/v1/notes/",  # Ghost text generation
    "/api/v1/issues/ai/",
    "/api/v1/pr-review/",
)


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
    """

    def __init__(
        self,
        app: object,
        redis_client: Redis | None = None,
        *,
        enabled: bool = True,
    ) -> None:
        """Initialize rate limiter.

        Args:
            app: ASGI application.
            redis_client: Redis async client. If None, rate limiting is disabled.
            enabled: Whether rate limiting is enabled.
        """
        super().__init__(app)  # type: ignore[arg-type]
        self.redis = redis_client
        self.enabled = enabled and redis_client is not None

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

        # Redis key: ratelimit:{workspace_id}:{endpoint_type}:{minute}
        current_minute = int(time.time() // 60)
        redis_key = f"ratelimit:{workspace_id}:{config.key_prefix}:{current_minute}"

        # Check rate limit and process request
        rate_limit_result = await self._check_rate_limit(
            redis_key, config.requests_per_minute, workspace_id, endpoint_type
        )

        if rate_limit_result is None:
            # Redis error - allow request through
            return await call_next(request)

        current_count, remaining, reset_time = rate_limit_result

        # Limit exceeded - raise 429
        if current_count > config.requests_per_minute:
            self._raise_rate_limit_exceeded(config.requests_per_minute, reset_time)

        # Process request and add rate limit headers
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(config.requests_per_minute)
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
        """Raise HTTPException for rate limit exceeded.

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


__all__ = ["RATE_LIMIT_CONFIGS", "RateLimitMiddleware"]
