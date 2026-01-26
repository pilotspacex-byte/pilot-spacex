"""Tests for AI response caching.

T319: Response caching tests.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import orjson
import pytest

from pilot_space.ai.infrastructure.cache import AIResponseCache

if TYPE_CHECKING:
    from pilot_space.infrastructure.cache.redis import RedisClient


@pytest.fixture
def mock_redis() -> RedisClient:
    """Create mock Redis client."""
    redis = MagicMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock(return_value=True)
    redis.delete = AsyncMock(return_value=1)
    redis.scan_keys = AsyncMock(return_value=[])
    return redis


@pytest.fixture
def ai_cache(mock_redis: RedisClient) -> AIResponseCache:
    """Create AI response cache with mock Redis."""
    return AIResponseCache(mock_redis, ttl_seconds=3600)


class TestAIResponseCacheGet:
    """Tests for AIResponseCache.get method."""

    @pytest.mark.asyncio
    async def test_returns_none_on_cache_miss(
        self,
        ai_cache: AIResponseCache,
        mock_redis: RedisClient,
    ) -> None:
        """Verify None is returned when cache entry doesn't exist."""
        mock_redis.get.return_value = None

        result = await ai_cache.get(
            "ghost_text",
            {"context": "test"},
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_cached_response_on_hit(
        self,
        ai_cache: AIResponseCache,
        mock_redis: RedisClient,
    ) -> None:
        """Verify cached response is returned on cache hit."""
        cached_data = {"suggestion": "test completion"}
        mock_redis.get.return_value = orjson.dumps(cached_data)

        result = await ai_cache.get(
            "ghost_text",
            {"context": "test"},
        )

        assert result == cached_data

    @pytest.mark.asyncio
    async def test_handles_string_cached_value(
        self,
        ai_cache: AIResponseCache,
        mock_redis: RedisClient,
    ) -> None:
        """Verify handles string cached values (JSON strings)."""
        cached_data = {"suggestion": "test"}
        mock_redis.get.return_value = json.dumps(cached_data)

        result = await ai_cache.get(
            "ghost_text",
            {"context": "test"},
        )

        assert result == cached_data

    @pytest.mark.asyncio
    async def test_returns_none_when_disabled(
        self,
        mock_redis: RedisClient,
    ) -> None:
        """Verify returns None when caching is disabled."""
        cache = AIResponseCache(mock_redis, enabled=False)

        result = await cache.get(
            "ghost_text",
            {"context": "test"},
        )

        assert result is None
        mock_redis.get.assert_not_called()

    @pytest.mark.asyncio
    async def test_gracefully_handles_redis_errors(
        self,
        ai_cache: AIResponseCache,
        mock_redis: RedisClient,
    ) -> None:
        """Verify returns None on Redis errors instead of raising."""
        mock_redis.get.side_effect = Exception("Redis connection error")

        result = await ai_cache.get(
            "ghost_text",
            {"context": "test"},
        )

        assert result is None


class TestAIResponseCacheSet:
    """Tests for AIResponseCache.set method."""

    @pytest.mark.asyncio
    async def test_caches_response_successfully(
        self,
        ai_cache: AIResponseCache,
        mock_redis: RedisClient,
    ) -> None:
        """Verify response is cached with correct TTL."""
        response = {"suggestion": "test completion"}
        mock_redis.set.return_value = True

        success = await ai_cache.set(
            "ghost_text",
            {"context": "test"},
            response,
        )

        assert success is True
        mock_redis.set.assert_called_once()

        # Verify TTL was set
        call_kwargs = mock_redis.set.call_args.kwargs
        assert call_kwargs["ttl"] == 3600

    @pytest.mark.asyncio
    async def test_serializes_response_as_json(
        self,
        ai_cache: AIResponseCache,
        mock_redis: RedisClient,
    ) -> None:
        """Verify response is serialized to JSON."""
        response = {"key": "value", "number": 123}
        mock_redis.set.return_value = True

        await ai_cache.set(
            "test_agent",
            {"input": "data"},
            response,
        )

        # Verify set was called with serialized data
        call_args = mock_redis.set.call_args.args
        serialized = call_args[1]

        # Should be bytes (orjson output)
        assert isinstance(serialized, bytes)
        deserialized = orjson.loads(serialized)
        assert deserialized == response

    @pytest.mark.asyncio
    async def test_returns_false_when_disabled(
        self,
        mock_redis: RedisClient,
    ) -> None:
        """Verify returns False when caching is disabled."""
        cache = AIResponseCache(mock_redis, enabled=False)

        success = await cache.set(
            "ghost_text",
            {"context": "test"},
            {"result": "data"},
        )

        assert success is False
        mock_redis.set.assert_not_called()

    @pytest.mark.asyncio
    async def test_gracefully_handles_redis_errors(
        self,
        ai_cache: AIResponseCache,
        mock_redis: RedisClient,
    ) -> None:
        """Verify returns False on Redis errors instead of raising."""
        mock_redis.set.side_effect = Exception("Redis connection error")

        success = await ai_cache.set(
            "ghost_text",
            {"context": "test"},
            {"result": "data"},
        )

        assert success is False


class TestAIResponseCacheInvalidate:
    """Tests for AIResponseCache.invalidate method."""

    @pytest.mark.asyncio
    async def test_invalidates_specific_entry(
        self,
        ai_cache: AIResponseCache,
        mock_redis: RedisClient,
    ) -> None:
        """Verify specific cache entry is invalidated."""
        mock_redis.delete.return_value = 1

        success = await ai_cache.invalidate(
            "ghost_text",
            {"context": "test"},
        )

        assert success is True
        mock_redis.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_false_when_entry_not_found(
        self,
        ai_cache: AIResponseCache,
        mock_redis: RedisClient,
    ) -> None:
        """Verify returns False when entry doesn't exist."""
        mock_redis.delete.return_value = 0

        success = await ai_cache.invalidate(
            "ghost_text",
            {"context": "test"},
        )

        assert success is False

    @pytest.mark.asyncio
    async def test_returns_false_when_disabled(
        self,
        mock_redis: RedisClient,
    ) -> None:
        """Verify returns False when caching is disabled."""
        cache = AIResponseCache(mock_redis, enabled=False)

        success = await cache.invalidate(
            "ghost_text",
            {"context": "test"},
        )

        assert success is False
        mock_redis.delete.assert_not_called()


class TestAIResponseCacheInvalidateAgent:
    """Tests for AIResponseCache.invalidate_agent method."""

    @pytest.mark.asyncio
    async def test_invalidates_all_entries_for_agent(
        self,
        ai_cache: AIResponseCache,
        mock_redis: RedisClient,
    ) -> None:
        """Verify all cache entries for agent are invalidated."""
        mock_redis.scan_keys.return_value = [
            "ai:cache:ghost_text:abc123",
            "ai:cache:ghost_text:def456",
            "ai:cache:ghost_text:ghi789",
        ]
        mock_redis.delete.return_value = 1

        count = await ai_cache.invalidate_agent("ghost_text")

        assert count == 3
        assert mock_redis.delete.call_count == 3

    @pytest.mark.asyncio
    async def test_returns_zero_when_no_entries_found(
        self,
        ai_cache: AIResponseCache,
        mock_redis: RedisClient,
    ) -> None:
        """Verify returns 0 when no entries exist for agent."""
        mock_redis.scan_keys.return_value = []

        count = await ai_cache.invalidate_agent("ghost_text")

        assert count == 0
        mock_redis.delete.assert_not_called()


class TestAIResponseCacheClearAll:
    """Tests for AIResponseCache.clear_all method."""

    @pytest.mark.asyncio
    async def test_clears_all_cache_entries(
        self,
        ai_cache: AIResponseCache,
        mock_redis: RedisClient,
    ) -> None:
        """Verify all AI cache entries are cleared."""
        mock_redis.scan_keys.return_value = [
            "ai:cache:ghost_text:abc123",
            "ai:cache:pr_review:def456",
            "ai:cache:ai_context:ghi789",
        ]
        mock_redis.delete.return_value = 1

        count = await ai_cache.clear_all()

        assert count == 3
        assert mock_redis.delete.call_count == 3


class TestAIResponseCacheStats:
    """Tests for AIResponseCache.get_cache_stats method."""

    @pytest.mark.asyncio
    async def test_returns_cache_statistics(
        self,
        ai_cache: AIResponseCache,
        mock_redis: RedisClient,
    ) -> None:
        """Verify returns accurate cache statistics."""
        mock_redis.scan_keys.return_value = [
            "ai:cache:agent1:key1",
            "ai:cache:agent2:key2",
        ]

        stats = await ai_cache.get_cache_stats()

        assert stats["enabled"] is True
        assert stats["entry_count"] == 2
        assert stats["ttl_seconds"] == 3600

    @pytest.mark.asyncio
    async def test_returns_disabled_status_when_disabled(
        self,
        mock_redis: RedisClient,
    ) -> None:
        """Verify returns disabled status when caching is disabled."""
        cache = AIResponseCache(mock_redis, enabled=False)

        stats = await cache.get_cache_stats()

        assert stats["enabled"] is False
        assert stats["entry_count"] == 0


class TestCacheKeyGeneration:
    """Tests for cache key generation and hashing."""

    def test_same_input_generates_same_hash(
        self,
        ai_cache: AIResponseCache,
    ) -> None:
        """Verify identical inputs generate identical cache keys."""
        input1 = {"context": "test", "cursor": 10}
        input2 = {"context": "test", "cursor": 10}

        hash1 = ai_cache._hash_input(input1)  # noqa: SLF001
        hash2 = ai_cache._hash_input(input2)  # noqa: SLF001

        assert hash1 == hash2

    def test_different_input_generates_different_hash(
        self,
        ai_cache: AIResponseCache,
    ) -> None:
        """Verify different inputs generate different cache keys."""
        input1 = {"context": "test1"}
        input2 = {"context": "test2"}

        hash1 = ai_cache._hash_input(input1)  # noqa: SLF001
        hash2 = ai_cache._hash_input(input2)  # noqa: SLF001

        assert hash1 != hash2

    def test_order_independent_hashing(
        self,
        ai_cache: AIResponseCache,
    ) -> None:
        """Verify key order doesn't affect hash (sorted keys)."""
        input1 = {"a": 1, "b": 2, "c": 3}
        input2 = {"c": 3, "a": 1, "b": 2}

        hash1 = ai_cache._hash_input(input1)  # noqa: SLF001
        hash2 = ai_cache._hash_input(input2)  # noqa: SLF001

        assert hash1 == hash2

    def test_cache_key_includes_agent_name(
        self,
        ai_cache: AIResponseCache,
    ) -> None:
        """Verify cache keys include agent name for isolation."""
        hash_value = "abc123"

        key = ai_cache._make_key("ghost_text", hash_value)  # noqa: SLF001

        assert "ghost_text" in key
        assert hash_value in key
        assert key.startswith("ai:cache:")
