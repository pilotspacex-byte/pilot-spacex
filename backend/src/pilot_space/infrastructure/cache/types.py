"""Shared types and constants for Redis cache infrastructure.

Provides CacheResult wrapper, TTL constants, and cache key builder functions
used across the cache module.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypeVar

T = TypeVar("T")

# Default TTL values for different cache types
DEFAULT_TTL_SECONDS = 3600  # 1 hour
SESSION_TTL_SECONDS = 86400  # 24 hours
AI_CACHE_TTL_SECONDS = 1800  # 30 minutes


@dataclass(frozen=True)
class CacheResult[T]:
    """Result wrapper for cache operations.

    Attributes:
        value: The cached value if found and valid.
        hit: Whether the cache lookup was successful.
        error: Error message if operation failed.
    """

    value: T | None
    hit: bool
    error: str | None = None

    @classmethod
    def cache_hit(cls, value: T) -> CacheResult[T]:
        """Create a cache hit result."""
        return cls(value=value, hit=True)

    @classmethod
    def cache_miss(cls) -> CacheResult[T]:
        """Create a cache miss result."""
        return cls(value=None, hit=False)

    @classmethod
    def cache_error(cls, error: str) -> CacheResult[T]:
        """Create a cache error result."""
        return cls(value=None, hit=False, error=error)


def session_key(session_id: str) -> str:
    """Build session cache key."""
    return f"session:{session_id}"


def user_key(user_id: str) -> str:
    """Build user cache key."""
    return f"user:{user_id}"


def ai_response_key(workspace_id: str, prompt_hash: str) -> str:
    """Build AI response cache key."""
    return f"ai:response:{workspace_id}:{prompt_hash}"


def rate_limit_key(user_id: str, endpoint: str) -> str:
    """Build rate limit counter key."""
    return f"rate:{user_id}:{endpoint}"


def presence_key(workspace_id: str, user_id: str) -> str:
    """Build presence cache key."""
    return f"presence:{workspace_id}:{user_id}"


__all__ = [
    "AI_CACHE_TTL_SECONDS",
    "DEFAULT_TTL_SECONDS",
    "SESSION_TTL_SECONDS",
    "CacheResult",
    "ai_response_key",
    "presence_key",
    "rate_limit_key",
    "session_key",
    "user_key",
]
