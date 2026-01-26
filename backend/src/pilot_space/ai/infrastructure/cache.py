"""AI response caching for repeated queries.

Redis-based caching layer to reduce costs and improve latency
for identical or similar AI requests.

T319: Response caching implementation.
"""

from __future__ import annotations

import hashlib
import logging
from typing import TYPE_CHECKING, Any

import orjson

if TYPE_CHECKING:
    from pilot_space.infrastructure.cache.redis import RedisClient

logger = logging.getLogger(__name__)

# Default cache TTL (1 hour)
DEFAULT_CACHE_TTL_SECONDS = 3600


class AIResponseCache:
    """Redis-based cache for AI responses.

    Caches AI agent responses to avoid redundant API calls for
    identical inputs. Uses content-based hashing for cache keys.

    Example:
        cache = AIResponseCache(redis_client)

        # Try cache first
        cached = await cache.get("ghost_text", {"context": "..."})
        if cached:
            return cached

        # Generate and cache response
        response = await agent.execute(...)
        await cache.set("ghost_text", {"context": "..."}, response)
    """

    def __init__(
        self,
        redis: RedisClient,
        *,
        ttl_seconds: int = DEFAULT_CACHE_TTL_SECONDS,
        enabled: bool = True,
    ) -> None:
        """Initialize AI response cache.

        Args:
            redis: Connected Redis client.
            ttl_seconds: Time-to-live for cached responses (default 1 hour).
            enabled: Whether caching is enabled (can disable for testing).
        """
        self._redis = redis
        self._ttl = ttl_seconds
        self._enabled = enabled

    @staticmethod
    def _make_key(agent_name: str, input_hash: str) -> str:
        """Build Redis key for cached response.

        Args:
            agent_name: Name of the agent.
            input_hash: Hash of the input data.

        Returns:
            Redis key string.
        """
        return f"ai:cache:{agent_name}:{input_hash}"

    @staticmethod
    def _hash_input(input_data: Any) -> str:
        """Generate hash from input data.

        Uses SHA256 hash of JSON-serialized input for deterministic keys.
        Truncated to 16 characters for readability.

        Args:
            input_data: Input data to hash (must be JSON-serializable).

        Returns:
            16-character hex hash string.
        """
        # Serialize with sorted keys for deterministic output
        serialized = orjson.dumps(
            input_data,
            option=orjson.OPT_SORT_KEYS,
        )
        hash_obj = hashlib.sha256(serialized)
        return hash_obj.hexdigest()[:16]

    async def get(
        self,
        agent_name: str,
        input_data: Any,
    ) -> Any | None:
        """Retrieve cached response if available.

        Args:
            agent_name: Name of the agent.
            input_data: Input data (must match exactly for cache hit).

        Returns:
            Cached response if found, None otherwise.
        """
        if not self._enabled:
            return None

        try:
            input_hash = self._hash_input(input_data)
            key = self._make_key(agent_name, input_hash)

            cached_value = await self._redis.get(key)
            if cached_value is None:
                logger.debug(
                    "AI cache miss",
                    extra={"agent": agent_name, "hash": input_hash},
                )
                return None

            logger.info(
                "AI cache hit",
                extra={"agent": agent_name, "hash": input_hash},
            )

            # Deserialize JSON response
            if isinstance(cached_value, bytes):
                return orjson.loads(cached_value)
            if isinstance(cached_value, str):
                return orjson.loads(cached_value.encode())
            # Already deserialized by Redis client
            return cached_value

        except Exception as e:
            logger.warning(
                "Failed to retrieve from AI cache",
                extra={"agent": agent_name, "error": str(e)},
            )
            return None

    async def set(
        self,
        agent_name: str,
        input_data: Any,
        response: Any,
    ) -> bool:
        """Cache a response for future requests.

        Args:
            agent_name: Name of the agent.
            input_data: Input data (for hash generation).
            response: Response to cache (must be JSON-serializable).

        Returns:
            True if cached successfully, False otherwise.
        """
        if not self._enabled:
            return False

        try:
            input_hash = self._hash_input(input_data)
            key = self._make_key(agent_name, input_hash)

            # Serialize response
            serialized = orjson.dumps(response)

            success = await self._redis.set(
                key,
                serialized,
                ttl=self._ttl,
            )

            if success:
                logger.debug(
                    "AI response cached",
                    extra={
                        "agent": agent_name,
                        "hash": input_hash,
                        "ttl": self._ttl,
                    },
                )

            return success

        except Exception as e:
            logger.warning(
                "Failed to cache AI response",
                extra={"agent": agent_name, "error": str(e)},
            )
            return False

    async def invalidate(
        self,
        agent_name: str,
        input_data: Any,
    ) -> bool:
        """Invalidate a cached response.

        Args:
            agent_name: Name of the agent.
            input_data: Input data (must match for invalidation).

        Returns:
            True if invalidated, False if not found or error.
        """
        if not self._enabled:
            return False

        try:
            input_hash = self._hash_input(input_data)
            key = self._make_key(agent_name, input_hash)

            deleted = await self._redis.delete(key)
            if deleted > 0:
                logger.info(
                    "AI cache entry invalidated",
                    extra={"agent": agent_name, "hash": input_hash},
                )
                return True

            return False

        except Exception as e:
            logger.warning(
                "Failed to invalidate AI cache",
                extra={"agent": agent_name, "error": str(e)},
            )
            return False

    async def invalidate_agent(self, agent_name: str) -> int:
        """Invalidate all cached responses for an agent.

        Args:
            agent_name: Name of the agent.

        Returns:
            Number of cache entries invalidated.
        """
        if not self._enabled:
            return 0

        try:
            pattern = f"ai:cache:{agent_name}:*"
            keys = await self._redis.scan_keys(pattern, max_keys=1000)

            if not keys:
                return 0

            deleted = 0
            for key in keys:
                if await self._redis.delete(key) > 0:
                    deleted += 1

            logger.info(
                "AI cache invalidated for agent",
                extra={"agent": agent_name, "count": deleted},
            )

            return deleted

        except Exception as e:
            logger.warning(
                "Failed to invalidate agent cache",
                extra={"agent": agent_name, "error": str(e)},
            )
            return 0

    async def clear_all(self) -> int:
        """Clear all AI response cache entries.

        Returns:
            Number of cache entries cleared.
        """
        if not self._enabled:
            return 0

        try:
            pattern = "ai:cache:*"
            keys = await self._redis.scan_keys(pattern, max_keys=10000)

            if not keys:
                return 0

            deleted = 0
            for key in keys:
                if await self._redis.delete(key) > 0:
                    deleted += 1

            logger.info(
                "AI cache cleared",
                extra={"count": deleted},
            )

            return deleted

        except Exception as e:
            logger.warning(
                "Failed to clear AI cache",
                extra={"error": str(e)},
            )
            return 0

    async def get_cache_stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache metrics (entry count, etc.).
        """
        if not self._enabled:
            return {"enabled": False, "entry_count": 0}

        try:
            pattern = "ai:cache:*"
            keys = await self._redis.scan_keys(pattern, max_keys=10000)

            return {
                "enabled": True,
                "entry_count": len(keys),
                "ttl_seconds": self._ttl,
            }

        except Exception as e:
            logger.warning(
                "Failed to get cache stats",
                extra={"error": str(e)},
            )
            return {"enabled": True, "entry_count": 0, "error": str(e)}


__all__ = [
    "DEFAULT_CACHE_TTL_SECONDS",
    "AIResponseCache",
]
