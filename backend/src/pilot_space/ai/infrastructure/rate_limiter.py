"""Redis-based rate limiter for AI operations.

Implements sliding window rate limiting with Redis for distributed systems.

Note: This implementation requires Redis sorted set operations (zadd, zcard, zremrangebyscore)
which are not yet in the RedisClient interface. For now, this serves as a reference
implementation for testing. The actual rate limiting is handled by the in-memory
RateLimiter in orchestrator.py.

T321: Rate limiter implementation for testing purposes.
"""

from __future__ import annotations

import logging
from typing import Protocol

logger = logging.getLogger(__name__)


class RedisClientProtocol(Protocol):
    """Protocol for Redis client with sorted set operations."""

    async def zadd(self, key: str, mapping: dict[str, float]) -> int:
        """Add members to sorted set."""
        ...

    async def zcard(self, key: str) -> int:
        """Get cardinality of sorted set."""
        ...

    async def zremrangebyscore(self, key: str, min_score: float, max_score: float) -> int:
        """Remove members by score range."""
        ...

    async def expire(self, key: str, seconds: int) -> bool:
        """Set key expiration."""
        ...

    async def delete(self, key: str) -> int:
        """Delete key."""
        ...


class RateLimiter:
    """Redis-based sliding window rate limiter.

    Uses Redis sorted sets for sliding window rate limiting.
    Each request is timestamped and old requests are removed based on the window.

    Note: This is a reference implementation for testing. Production code
    uses the RateLimiter in orchestrator.py which works with the existing
    RedisClient interface.

    Example:
        limiter = RateLimiter(redis_client, requests_per_minute=60)
        allowed = await limiter.acquire("workspace:123:ghost_text")
        if not allowed:
            # Rate limit exceeded
            return False
    """

    def __init__(
        self,
        redis: RedisClientProtocol,
        requests_per_minute: int = 60,
        window_seconds: int = 60,
    ) -> None:
        """Initialize rate limiter.

        Args:
            redis: Redis client with sorted set support.
            requests_per_minute: Maximum requests allowed per window.
            window_seconds: Window size in seconds (default 60 for per-minute).
        """
        self._redis = redis
        self._max_requests = requests_per_minute
        self._window_seconds = window_seconds

    async def acquire(self, key: str) -> bool:
        """Attempt to acquire permission for a request.

        Args:
            key: Rate limit key (e.g., "workspace:123:operation").

        Returns:
            True if request is allowed, False if rate limit exceeded.
        """
        import time

        now = time.time()
        window_start = now - self._window_seconds

        # Redis key for this rate limit
        redis_key = f"ratelimit:{key}"

        # Remove old entries outside the window
        await self._redis.zremrangebyscore(redis_key, 0, window_start)

        # Count current requests in window
        current_count = await self._redis.zcard(redis_key)

        if current_count >= self._max_requests:
            logger.warning(
                "Rate limit exceeded",
                extra={
                    "key": key,
                    "current_count": current_count,
                    "max_requests": self._max_requests,
                },
            )
            return False

        # Add current request to window
        await self._redis.zadd(redis_key, {str(now): now})

        # Set expiration to prevent memory leaks
        await self._redis.expire(redis_key, self._window_seconds * 2)

        return True

    async def check(self, key: str) -> tuple[int, int]:
        """Check current rate limit status without incrementing.

        Args:
            key: Rate limit key.

        Returns:
            Tuple of (current_count, max_requests).
        """
        import time

        now = time.time()
        window_start = now - self._window_seconds
        redis_key = f"ratelimit:{key}"

        # Remove old entries
        await self._redis.zremrangebyscore(redis_key, 0, window_start)

        # Count current requests
        current_count = await self._redis.zcard(redis_key)

        return (current_count, self._max_requests)

    async def reset(self, key: str) -> None:
        """Reset rate limit for a key.

        Args:
            key: Rate limit key to reset.
        """
        redis_key = f"ratelimit:{key}"
        await self._redis.delete(redis_key)
        logger.info("Rate limit reset", extra={"key": key})


__all__ = ["RateLimiter", "RedisClientProtocol"]
