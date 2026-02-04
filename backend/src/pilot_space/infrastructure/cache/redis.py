"""Redis cache client for Pilot Space.

Provides async Redis operations with JSON serialization, connection pooling,
and graceful error handling for caching use cases:
- Session caching
- AI response caching
- Rate limiting counters
- Real-time presence tracking
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any, TypeVar

import orjson
from redis.asyncio import ConnectionPool, Redis
from redis.exceptions import (
    ConnectionError as RedisConnectionError,
    RedisError,
    TimeoutError as RedisTimeoutError,
)

from pilot_space.infrastructure.cache.types import (
    DEFAULT_TTL_SECONDS,
    CacheResult,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

logger = logging.getLogger(__name__)

T = TypeVar("T")


class RedisClient:
    """Async Redis client with connection pooling and JSON serialization.

    Provides high-level cache operations with graceful error handling.
    All operations return None or False on connection errors instead of raising,
    with errors logged as warnings for observability.

    Example:
        client = RedisClient(redis_url="redis://localhost:6379/0")
        await client.connect()

        # Basic operations
        await client.set("user:123", {"name": "Alice"}, ttl=3600)
        user = await client.get("user:123")

        # Atomic counters
        count = await client.incr("request:count")

        await client.disconnect()
    """

    def __init__(
        self,
        redis_url: str,
        *,
        max_connections: int = 10,
        socket_timeout: float = 5.0,
        socket_connect_timeout: float = 5.0,
        retry_on_timeout: bool = True,
        decode_responses: bool = False,
    ) -> None:
        """Initialize Redis client configuration.

        Args:
            redis_url: Redis connection URL (e.g., redis://localhost:6379/0).
            max_connections: Maximum connections in the pool.
            socket_timeout: Timeout for socket operations in seconds.
            socket_connect_timeout: Timeout for socket connection in seconds.
            retry_on_timeout: Whether to retry operations on timeout.
            decode_responses: Whether to decode byte responses to strings.
        """
        self._redis_url = redis_url
        self._max_connections = max_connections
        self._socket_timeout = socket_timeout
        self._socket_connect_timeout = socket_connect_timeout
        self._retry_on_timeout = retry_on_timeout
        self._decode_responses = decode_responses
        self._pool: ConnectionPool | None = None
        self._client: Redis | None = None  # type: ignore[type-arg]

    async def connect(self) -> None:
        """Establish connection pool to Redis.

        Creates a connection pool for efficient connection reuse.
        Safe to call multiple times; subsequent calls are no-ops.
        """
        if self._pool is not None:
            return

        try:
            self._pool = ConnectionPool.from_url(  # type: ignore[misc]
                self._redis_url,
                max_connections=self._max_connections,
                socket_timeout=self._socket_timeout,
                socket_connect_timeout=self._socket_connect_timeout,
                retry_on_timeout=self._retry_on_timeout,
                decode_responses=self._decode_responses,
            )
            self._client = Redis(connection_pool=self._pool)
            # Verify connection works
            await self._client.ping()  # type: ignore[misc]
            logger.info("Redis connection pool established")
        except (RedisConnectionError, RedisTimeoutError) as e:
            logger.warning("Failed to connect to Redis: %s", e)
            self._pool = None
            self._client = None

    async def disconnect(self) -> None:
        """Close connection pool and release resources.

        Safe to call multiple times; subsequent calls are no-ops.
        """
        if self._client is not None:
            await self._client.aclose()
            self._client = None
        if self._pool is not None:
            await self._pool.disconnect()
            self._pool = None
            logger.info("Redis connection pool closed")

    @asynccontextmanager
    async def connection(self) -> AsyncIterator[RedisClient]:
        """Context manager for connection lifecycle.

        Example:
            async with RedisClient(url).connection() as client:
                await client.set("key", "value")
        """
        await self.connect()
        try:
            yield self
        finally:
            await self.disconnect()

    @property
    def is_connected(self) -> bool:
        """Check if client has an active connection pool."""
        return self._client is not None

    async def ping(self) -> bool:
        """Check Redis connectivity.

        Returns:
            True if Redis is reachable, False otherwise.
        """
        if self._client is None:
            return False
        try:
            result = await self._client.ping()  # type: ignore[misc]
        except RedisError as e:
            logger.warning("Redis ping failed: %s", e)
            return False
        else:
            return result is True

    # =========================================================================
    # Core Key-Value Operations
    # =========================================================================

    async def get(self, key: str) -> Any | None:
        """Get value by key with JSON deserialization.

        Args:
            key: The cache key.

        Returns:
            Deserialized value if found, None if not found or on error.
        """
        if self._client is None:
            logger.warning("Redis client not connected for get(%s)", key)
            return None

        try:
            value = await self._client.get(key)
            if value is None:
                return None
            return orjson.loads(value)
        except orjson.JSONDecodeError as e:
            logger.warning("Failed to deserialize cache value for %s: %s", key, e)
            return None
        except RedisError as e:
            logger.warning("Redis get failed for %s: %s", key, e)
            return None

    async def get_typed(self, key: str, expected_type: type[T]) -> CacheResult[T]:
        """Get value by key with type validation.

        Args:
            key: The cache key.
            expected_type: Expected type of the cached value.

        Returns:
            CacheResult with typed value or error information.
        """
        value = await self.get(key)
        if value is None:
            return CacheResult[T].cache_miss()
        if not isinstance(value, expected_type):
            return CacheResult[T].cache_error(
                f"Type mismatch: expected {expected_type.__name__}, got {type(value).__name__}"
            )
        return CacheResult[T].cache_hit(value)

    async def set(
        self,
        key: str,
        value: Any,
        *,
        ttl: int | None = DEFAULT_TTL_SECONDS,
        if_not_exists: bool = False,
        if_exists: bool = False,
    ) -> bool:
        """Set value with JSON serialization and optional TTL.

        Args:
            key: The cache key.
            value: Value to cache (must be JSON-serializable).
            ttl: Time-to-live in seconds. None for no expiration.
            if_not_exists: Only set if key doesn't exist (NX flag).
            if_exists: Only set if key exists (XX flag).

        Returns:
            True if value was set, False on error or condition not met.
        """
        if self._client is None:
            logger.warning("Redis client not connected for set(%s)", key)
            return False

        try:
            serialized = orjson.dumps(value)
            result = await self._client.set(
                key,
                serialized,
                ex=ttl,
                nx=if_not_exists,
                xx=if_exists,
            )
        except (TypeError, orjson.JSONEncodeError) as e:
            logger.warning("Failed to serialize value for %s: %s", key, e)
            return False
        except RedisError as e:
            logger.warning("Redis set failed for %s: %s", key, e)
            return False
        else:
            return result is not None and result is not False

    async def delete(self, *keys: str) -> int:
        """Delete one or more keys.

        Args:
            *keys: Keys to delete.

        Returns:
            Number of keys deleted, 0 on error.
        """
        if not keys:
            return 0
        if self._client is None:
            logger.warning("Redis client not connected for delete(%s)", keys)
            return 0

        try:
            return await self._client.delete(*keys)
        except RedisError as e:
            logger.warning("Redis delete failed for %s: %s", keys, e)
            return 0

    async def exists(self, *keys: str) -> int:
        """Check if keys exist.

        Args:
            *keys: Keys to check.

        Returns:
            Number of keys that exist, 0 on error.
        """
        if not keys:
            return 0
        if self._client is None:
            logger.warning("Redis client not connected for exists(%s)", keys)
            return 0

        try:
            return await self._client.exists(*keys)
        except RedisError as e:
            logger.warning("Redis exists failed for %s: %s", keys, e)
            return 0

    async def expire(self, key: str, ttl: int) -> bool:
        """Set expiration on existing key.

        Args:
            key: The cache key.
            ttl: Time-to-live in seconds.

        Returns:
            True if expiration was set, False if key doesn't exist or on error.
        """
        if self._client is None:
            logger.warning("Redis client not connected for expire(%s)", key)
            return False

        try:
            return await self._client.expire(key, ttl)
        except RedisError as e:
            logger.warning("Redis expire failed for %s: %s", key, e)
            return False

    async def ttl(self, key: str) -> int:
        """Get remaining TTL for a key.

        Args:
            key: The cache key.

        Returns:
            TTL in seconds, -1 if no expiration, -2 if key doesn't exist.
        """
        if self._client is None:
            logger.warning("Redis client not connected for ttl(%s)", key)
            return -2

        try:
            return await self._client.ttl(key)
        except RedisError as e:
            logger.warning("Redis ttl failed for %s: %s", key, e)
            return -2

    # =========================================================================
    # Atomic Counter Operations
    # =========================================================================

    async def incr(self, key: str, amount: int = 1) -> int | None:
        """Atomically increment a counter.

        Args:
            key: The counter key.
            amount: Amount to increment by (default 1).

        Returns:
            New counter value, None on error.
        """
        if self._client is None:
            logger.warning("Redis client not connected for incr(%s)", key)
            return None

        try:
            if amount == 1:
                return await self._client.incr(key)
            return await self._client.incrby(key, amount)
        except RedisError as e:
            logger.warning("Redis incr failed for %s: %s", key, e)
            return None

    async def decr(self, key: str, amount: int = 1) -> int | None:
        """Atomically decrement a counter.

        Args:
            key: The counter key.
            amount: Amount to decrement by (default 1).

        Returns:
            New counter value, None on error.
        """
        if self._client is None:
            logger.warning("Redis client not connected for decr(%s)", key)
            return None

        try:
            if amount == 1:
                return await self._client.decr(key)
            return await self._client.decrby(key, amount)
        except RedisError as e:
            logger.warning("Redis decr failed for %s: %s", key, e)
            return None

    # =========================================================================
    # Batch Operations
    # =========================================================================

    async def mget(self, *keys: str) -> list[Any | None]:
        """Get multiple values by keys.

        Args:
            *keys: Keys to retrieve.

        Returns:
            List of values (None for missing keys), empty list on error.
        """
        if not keys:
            return []
        if self._client is None:
            logger.warning("Redis client not connected for mget(%s)", keys)
            return [None] * len(keys)

        try:
            values = await self._client.mget(keys)
            results: list[Any | None] = []
            for value in values:
                if value is None:
                    results.append(None)
                else:
                    try:
                        results.append(orjson.loads(value))
                    except orjson.JSONDecodeError:
                        results.append(None)
        except RedisError as e:
            logger.warning("Redis mget failed for %s: %s", keys, e)
            return [None] * len(keys)
        else:
            return results

    async def mset(self, mapping: dict[str, Any], *, ttl: int | None = None) -> bool:
        """Set multiple key-value pairs.

        Args:
            mapping: Dictionary of key-value pairs.
            ttl: Optional TTL for all keys (requires pipeline).

        Returns:
            True if all values were set, False on error.
        """
        if not mapping:
            return True
        if self._client is None:
            logger.warning("Redis client not connected for mset")
            return False

        try:
            serialized = {k: orjson.dumps(v) for k, v in mapping.items()}

            if ttl is None:
                await self._client.mset(serialized)
            else:
                # Use pipeline for atomic mset + expire
                async with self._client.pipeline(transaction=True) as pipe:
                    pipe.mset(serialized)
                    for key in mapping:
                        pipe.expire(key, ttl)
                    await pipe.execute()
        except (TypeError, orjson.JSONEncodeError) as e:
            logger.warning("Failed to serialize values for mset: %s", e)
            return False
        except RedisError as e:
            logger.warning("Redis mset failed: %s", e)
            return False
        else:
            return True

    # =========================================================================
    # Key Pattern Operations
    # =========================================================================

    async def keys(self, pattern: str) -> list[str]:
        """Find keys matching pattern.

        Warning: KEYS is O(N) and should be avoided in production
        for large keyspaces. Use SCAN for production workloads.

        Args:
            pattern: Glob-style pattern (e.g., "user:*").

        Returns:
            List of matching keys, empty list on error.
        """
        if self._client is None:
            logger.warning("Redis client not connected for keys(%s)", pattern)
            return []

        try:
            result = await self._client.keys(pattern)  # type: ignore[misc]
            return [k.decode() if isinstance(k, bytes) else str(k) for k in result]
        except RedisError as e:
            logger.warning("Redis keys failed for %s: %s", pattern, e)
            return []

    async def scan_keys(
        self,
        pattern: str,
        *,
        count: int = 100,
        max_keys: int = 1000,
    ) -> list[str]:
        """Iterate over keys matching pattern using SCAN (production-safe).

        Args:
            pattern: Glob-style pattern (e.g., "user:*").
            count: Hint for number of keys per iteration.
            max_keys: Maximum total keys to return.

        Returns:
            List of matching keys, empty list on error.
        """
        if self._client is None:
            logger.warning("Redis client not connected for scan_keys(%s)", pattern)
            return []

        try:
            keys: list[str] = []
            cursor = 0
            while True:
                cursor, batch = await self._client.scan(  # type: ignore[misc]
                    cursor=cursor, match=pattern, count=count
                )
                for key in batch:
                    decoded = key.decode() if isinstance(key, bytes) else key
                    keys.append(decoded)
                    if len(keys) >= max_keys:
                        return keys
                if cursor == 0:
                    break
        except RedisError as e:
            logger.warning("Redis scan failed for %s: %s", pattern, e)
            return []
        else:
            return keys

    async def delete_pattern(self, pattern: str, *, batch_size: int = 100) -> int:
        """Delete all keys matching pattern.

        Uses SCAN + DELETE for production-safe deletion.

        Args:
            pattern: Glob-style pattern (e.g., "session:*").
            batch_size: Number of keys to delete per batch.

        Returns:
            Total number of keys deleted.
        """
        if self._client is None:
            logger.warning("Redis client not connected for delete_pattern(%s)", pattern)
            return 0

        try:
            total_deleted = 0
            cursor = 0
            while True:
                cursor, batch = await self._client.scan(  # type: ignore[misc]
                    cursor=cursor, match=pattern, count=batch_size
                )
                if batch:
                    deleted = await self._client.delete(*batch)
                    total_deleted += deleted
                if cursor == 0:
                    break
        except RedisError as e:
            logger.warning("Redis delete_pattern failed for %s: %s", pattern, e)
            return 0
        else:
            return total_deleted

    # =========================================================================
    # Raw Value Operations (no JSON serialization)
    # =========================================================================

    async def get_raw(self, key: str) -> bytes | None:
        """Get raw bytes value (no JSON deserialization).

        Args:
            key: The cache key.

        Returns:
            Raw bytes if found, None if not found or on error.
        """
        if self._client is None:
            logger.warning("Redis client not connected for get_raw(%s)", key)
            return None

        try:
            return await self._client.get(key)
        except RedisError as e:
            logger.warning("Redis get_raw failed for %s: %s", key, e)
            return None

    async def setex(self, key: str, ttl: int, value: str) -> bool:
        """Set raw string value with TTL (no JSON serialization).

        Args:
            key: The cache key.
            ttl: Time-to-live in seconds.
            value: Raw string value.

        Returns:
            True if value was set, False on error.
        """
        if self._client is None:
            logger.warning("Redis client not connected for setex(%s)", key)
            return False

        try:
            await self._client.setex(key, ttl, value)
        except RedisError as e:
            logger.warning("Redis setex failed for %s: %s", key, e)
            return False
        else:
            return True

    # =========================================================================
    # List Operations
    # =========================================================================

    async def rpush(self, key: str, value: str) -> int | None:
        """Append value to Redis list.

        Args:
            key: The list key.
            value: Value to append.

        Returns:
            Length of list after push, None on error.
        """
        if self._client is None:
            logger.warning("Redis client not connected for rpush(%s)", key)
            return None

        try:
            return await self._client.rpush(key, value)  # type: ignore[misc]
        except RedisError as e:
            logger.warning("Redis rpush failed for %s: %s", key, e)
            return None

    async def lrange(self, key: str, start: int, stop: int) -> list[bytes]:
        """Get range from Redis list.

        Args:
            key: The list key.
            start: Start index (0-based).
            stop: Stop index (-1 for end of list).

        Returns:
            List of byte values, empty list on error.
        """
        if self._client is None:
            logger.warning("Redis client not connected for lrange(%s)", key)
            return []

        try:
            return await self._client.lrange(key, start, stop)  # type: ignore[misc]
        except RedisError as e:
            logger.warning("Redis lrange failed for %s: %s", key, e)
            return []

    # =========================================================================
    # Pub/Sub Operations
    # =========================================================================

    async def publish(self, channel: str, message: str) -> int:
        """Publish message to Redis pub/sub channel.

        Args:
            channel: Channel name.
            message: Message to publish.

        Returns:
            Number of subscribers that received the message, 0 on error.
        """
        if self._client is None:
            logger.warning("Redis client not connected for publish(%s)", channel)
            return 0

        try:
            return await self._client.publish(channel, message)
        except RedisError as e:
            logger.warning("Redis publish failed for %s: %s", channel, e)
            return 0

    async def subscribe(self, channel: str) -> Any:
        """Create pub/sub subscription.

        Args:
            channel: Channel name to subscribe to.

        Returns:
            Async pubsub object for listening to messages.

        Raises:
            RuntimeError: If Redis client not connected.
        """
        if self._client is None:
            msg = "Redis client not connected for subscribe"
            raise RuntimeError(msg)

        pubsub = self._client.pubsub()
        await pubsub.subscribe(channel)
        return pubsub
