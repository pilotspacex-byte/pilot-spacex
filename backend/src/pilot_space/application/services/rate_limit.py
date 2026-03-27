"""Reusable Redis-based rate limiting service.

Extracts the duplicated INCR+EXPIRE rate-limit pattern from ghost_text.py,
issues_ai_context.py, and issues_ai_context_streaming.py into a single service
registered in the DI container.

Usage:
    rate_limit_service = RateLimitService(redis=redis_client)
    await rate_limit_service.check_rate_limit(
        key="ghost_text_rate_limit:user-uuid",
        max_requests=10,
        window_seconds=1,
    )
"""

from __future__ import annotations

from redis.asyncio import Redis

from pilot_space.domain.exceptions import AppError


class RateLimitExceededError(AppError):
    """Raised when a rate limit is exceeded (HTTP 429)."""

    error_code = "rate_limit_exceeded"
    http_status = 429


class RateLimitUnavailableError(AppError):
    """Raised when the rate limiter backend (Redis) is unreachable (HTTP 503)."""

    error_code = "rate_limit_unavailable"
    http_status = 503


class RateLimitService:
    """Redis-backed rate limiter using atomic INCR + EXPIRE.

    Each call to :meth:`check_rate_limit` atomically increments a counter
    for the given key and sets an expiry on first hit.  If the counter
    exceeds ``max_requests`` within the window, a
    :class:`RateLimitExceededError` is raised.
    """

    def __init__(self, redis: Redis) -> None:  # type: ignore[type-arg]
        self._redis = redis

    async def check_rate_limit(
        self,
        key: str,
        max_requests: int,
        window_seconds: int,
    ) -> None:
        """Enforce a rate limit using Redis INCR + EXPIRE.

        Args:
            key: Fully-qualified Redis key (e.g. ``"ghost_text_rate_limit:<user_id>"``).
            max_requests: Maximum allowed requests within the window.
            window_seconds: Sliding-window duration in seconds.

        Raises:
            RateLimitUnavailableError: Redis returned ``None`` for INCR.
            RateLimitExceededError: Counter exceeds ``max_requests``.
        """
        count = await self._redis.incr(key)
        if count is None:
            raise RateLimitUnavailableError("Rate limiter unavailable. Please try again later.")
        if count == 1:
            await self._redis.expire(key, window_seconds)
        if count > max_requests:
            raise RateLimitExceededError(
                f"Rate limit exceeded: {max_requests} requests per {window_seconds} second(s)"
            )
