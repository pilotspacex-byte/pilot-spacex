"""Rate limiter for magic-link invitation requests.

Implements a Redis fixed-window counter to limit magic link requests
to 3 per hour per email address (CL-004, research.md RES-002).

Key pattern: invite_magiclink:{YYYYMMDDHH}:{sha256(email.lower())[:12]}
TTL: 7200s (2x the 1-hour window to handle hour-boundary overlap)
Limit: 3 requests per hour per email
Fail-open: Redis errors are logged as warnings and the request is allowed.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from pilot_space.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from pilot_space.infrastructure.cache.redis import RedisClient

logger = get_logger(__name__)

RATE_LIMIT = 3
WINDOW_TTL_SECONDS = 7200  # 2x the 1-hour window for boundary safety


class InviteRateLimiter:
    """Fixed-window rate limiter for magic-link invitation requests.

    Limits magic link sends to RATE_LIMIT (3) per hour per email address.
    Uses Redis INCR + EXPIRE for atomic counter management.

    Fail-open policy: if Redis is unavailable, the request is allowed
    and a warning is logged (prefer availability over strictness for
    invitation flows).
    """

    def __init__(self, redis_client: RedisClient) -> None:
        self._redis = redis_client

    def _make_key(self, email: str) -> str:
        """Build the rate-limit key for an email in the current hour bucket.

        Format: invite_magiclink:{YYYYMMDDHH}:{sha256(email.lower())[:12]}
        The hour bucket (YYYYMMDDHH) resets the counter every hour.
        Email is hashed to avoid storing PII in Redis keys.
        """
        hour_bucket = datetime.now(tz=UTC).strftime("%Y%m%d%H")
        email_hash = hashlib.sha256(email.lower().encode()).hexdigest()[:12]
        return f"invite_magiclink:{hour_bucket}:{email_hash}"

    async def check_and_increment(self, email: str) -> bool:
        """Check rate limit and increment the counter if allowed.

        Atomically increments the Redis counter for this email+hour.
        Sets TTL on the first increment. Returns True if the request
        is within the rate limit, False if the limit is exceeded.

        On Redis error: logs a warning and returns True (fail-open).

        Args:
            email: The email address being rate-limited.

        Returns:
            True if the request is allowed, False if rate limit exceeded.
        """
        key = self._make_key(email)
        try:
            count = await self._redis.incr(key)
            if count is None:
                logger.warning("invite_rate_limiter_incr_returned_none", key=key)
                return True

            # Set TTL only on first increment to avoid resetting the window
            if count == 1:
                await self._redis.expire(key, WINDOW_TTL_SECONDS)

            if count > RATE_LIMIT:
                logger.info(
                    "invite_rate_limit_exceeded",
                    email_hash=key.split(":")[-1],
                    count=count,
                    limit=RATE_LIMIT,
                )
                return False

            return True
        except Exception as exc:
            logger.warning(
                "invite_rate_limiter_redis_error",
                error=str(exc),
                email_hash=hashlib.sha256(email.lower().encode()).hexdigest()[:12],
            )
            return True  # Fail-open


__all__ = ["InviteRateLimiter"]
