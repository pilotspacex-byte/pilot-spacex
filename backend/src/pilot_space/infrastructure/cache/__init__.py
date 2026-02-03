"""Redis cache infrastructure for Pilot Space.

Use cases:
- Session caching
- AI response caching
- Rate limiting counters
- Real-time presence
"""

from pilot_space.infrastructure.cache.redis import (
    RedisClient,
)
from pilot_space.infrastructure.cache.types import (
    AI_CACHE_TTL_SECONDS,
    DEFAULT_TTL_SECONDS,
    SESSION_TTL_SECONDS,
    CacheResult,
    ai_response_key,
    presence_key,
    rate_limit_key,
    session_key,
    user_key,
)

__all__ = [
    "AI_CACHE_TTL_SECONDS",
    "DEFAULT_TTL_SECONDS",
    "SESSION_TTL_SECONDS",
    "CacheResult",
    "RedisClient",
    "ai_response_key",
    "presence_key",
    "rate_limit_key",
    "session_key",
    "user_key",
]
