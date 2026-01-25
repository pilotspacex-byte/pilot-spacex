"""AI response caching with content-based keys.

T334: Redis Caching for AI Responses
- Cache ghost text suggestions (5 min TTL)
- Cache issue enhancements (10 min TTL)
- Cache duplicate detection results (15 min TTL)
- Cache invalidation on content change
- Cache key includes content hash
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from enum import IntEnum
from typing import TYPE_CHECKING, Any, TypeVar

from pilot_space.infrastructure.cache.redis import RedisClient

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable
    from uuid import UUID

logger = logging.getLogger(__name__)

T = TypeVar("T")


class AICacheTTL(IntEnum):
    """TTL values for different AI cache types in seconds."""

    GHOST_TEXT = 300  # 5 minutes
    ISSUE_ENHANCEMENT = 600  # 10 minutes
    DUPLICATE_DETECTION = 900  # 15 minutes
    ISSUE_SIMILARITY = 1800  # 30 minutes
    ISSUE_CONTEXT = 600  # 10 minutes
    NOTE_ANALYSIS = 600  # 10 minutes


@dataclass(frozen=True)
class AICacheStats:
    """Statistics for AI cache operations."""

    hits: int
    misses: int
    errors: int

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate percentage."""
        total = self.hits + self.misses
        if total == 0:
            return 0.0
        return (self.hits / total) * 100


class AICache:
    """Redis cache for AI responses with content-based keys.

    Uses content hashing for cache keys to enable cache sharing
    across similar content while maintaining proper isolation.

    Example:
        cache = AICache(redis_client)

        # Get or generate ghost text
        suggestion = await cache.get_or_generate_ghost_text(
            workspace_id=workspace_id,
            context="User is typing about...",
            generator=lambda: ai_service.generate_ghost_text(context),
        )

        # Invalidate on content change
        await cache.invalidate_ghost_text(workspace_id, old_context)
    """

    # Cache key prefixes
    PREFIX_GHOST_TEXT = "ai:ghost"
    PREFIX_ENHANCEMENT = "ai:enhance"
    PREFIX_DUPLICATE = "ai:duplicate"
    PREFIX_SIMILARITY = "ai:similarity"
    PREFIX_CONTEXT = "ai:context"
    PREFIX_NOTE_ANALYSIS = "ai:note"

    def __init__(self, redis: RedisClient) -> None:
        """Initialize AI cache with Redis client.

        Args:
            redis: Connected Redis client instance.
        """
        self._redis = redis
        self._hits = 0
        self._misses = 0
        self._errors = 0

    @staticmethod
    def _content_hash(content: str, length: int = 16) -> str:
        """Generate content hash for cache key.

        Uses SHA-256 for good distribution and collision resistance.
        Truncated to specified length for reasonable key sizes.

        Args:
            content: Content to hash.
            length: Number of hex characters to include (default 16).

        Returns:
            Truncated hexadecimal hash string.
        """
        return hashlib.sha256(content.encode("utf-8")).hexdigest()[:length]

    def _build_key(self, prefix: str, workspace_id: UUID | str, *parts: str) -> str:
        """Build a cache key with workspace isolation.

        Args:
            prefix: Cache key prefix.
            workspace_id: Workspace UUID for isolation.
            *parts: Additional key parts.

        Returns:
            Formatted cache key string.
        """
        key_parts = [prefix, str(workspace_id), *parts]
        return ":".join(key_parts)

    async def get_or_generate(
        self,
        key_prefix: str,
        workspace_id: UUID | str,
        content: str,
        generator: Callable[[], Awaitable[T]],
        ttl_seconds: int,
        *,
        include_hash: bool = True,
    ) -> T:
        """Get cached result or generate and cache.

        Pattern: Cache-aside with content-based key.

        Args:
            key_prefix: Cache key prefix.
            workspace_id: Workspace UUID for isolation.
            content: Content to hash for cache key.
            generator: Async function to generate value on cache miss.
            ttl_seconds: Time-to-live in seconds.
            include_hash: Whether to include content hash in key.

        Returns:
            Cached or freshly generated result.
        """
        if include_hash:
            content_hash = self._content_hash(content)
            cache_key = self._build_key(key_prefix, workspace_id, content_hash)
        else:
            cache_key = self._build_key(key_prefix, workspace_id, content)

        # Try cache first
        cached = await self._redis.get(cache_key)
        if cached is not None:
            self._hits += 1
            logger.debug("AI cache hit for %s", cache_key)
            return cached  # type: ignore[return-value]

        self._misses += 1
        logger.debug("AI cache miss for %s", cache_key)

        # Generate and cache
        try:
            result = await generator()
            success = await self._redis.set(cache_key, result, ttl=ttl_seconds)
            if not success:
                self._errors += 1
                logger.warning("Failed to cache AI result for %s", cache_key)
        except Exception as e:
            self._errors += 1
            logger.exception("Error generating AI result for %s: %s", cache_key, e)
            raise

        return result

    async def invalidate_for_content(
        self,
        key_prefix: str,
        workspace_id: UUID | str,
        content: str,
    ) -> bool:
        """Invalidate cache for specific content.

        Args:
            key_prefix: Cache key prefix.
            workspace_id: Workspace UUID.
            content: Content that was cached.

        Returns:
            True if key was deleted, False otherwise.
        """
        content_hash = self._content_hash(content)
        cache_key = self._build_key(key_prefix, workspace_id, content_hash)
        deleted = await self._redis.delete(cache_key)
        if deleted:
            logger.debug("Invalidated AI cache for %s", cache_key)
        return deleted > 0

    async def invalidate_pattern(
        self,
        key_prefix: str,
        workspace_id: UUID | str,
    ) -> int:
        """Invalidate all cache entries matching pattern.

        Args:
            key_prefix: Cache key prefix.
            workspace_id: Workspace UUID.

        Returns:
            Number of keys deleted.
        """
        pattern = f"{key_prefix}:{workspace_id}:*"
        deleted = await self._redis.delete_pattern(pattern)
        if deleted:
            logger.info("Invalidated %d AI cache entries for pattern %s", deleted, pattern)
        return deleted

    # =========================================================================
    # Ghost Text Caching
    # =========================================================================

    async def get_or_generate_ghost_text(
        self,
        workspace_id: UUID | str,
        context: str,
        generator: Callable[[], Awaitable[str]],
    ) -> str:
        """Get or generate ghost text suggestion.

        Args:
            workspace_id: Workspace UUID.
            context: Text context for suggestion.
            generator: Async function to generate suggestion.

        Returns:
            Ghost text suggestion.
        """
        return await self.get_or_generate(
            self.PREFIX_GHOST_TEXT,
            workspace_id,
            context,
            generator,
            AICacheTTL.GHOST_TEXT,
        )

    async def invalidate_ghost_text(
        self,
        workspace_id: UUID | str,
        context: str,
    ) -> bool:
        """Invalidate ghost text cache for content.

        Args:
            workspace_id: Workspace UUID.
            context: Original context that was cached.

        Returns:
            True if invalidated.
        """
        return await self.invalidate_for_content(
            self.PREFIX_GHOST_TEXT,
            workspace_id,
            context,
        )

    # =========================================================================
    # Issue Enhancement Caching
    # =========================================================================

    async def get_or_generate_enhancement(
        self,
        workspace_id: UUID | str,
        issue_content: str,
        generator: Callable[[], Awaitable[dict[str, Any]]],
    ) -> dict[str, Any]:
        """Get or generate issue enhancement.

        Args:
            workspace_id: Workspace UUID.
            issue_content: Issue title + description for key.
            generator: Async function to generate enhancement.

        Returns:
            Issue enhancement data.
        """
        return await self.get_or_generate(
            self.PREFIX_ENHANCEMENT,
            workspace_id,
            issue_content,
            generator,
            AICacheTTL.ISSUE_ENHANCEMENT,
        )

    async def invalidate_enhancement(
        self,
        workspace_id: UUID | str,
        issue_content: str,
    ) -> bool:
        """Invalidate issue enhancement cache.

        Args:
            workspace_id: Workspace UUID.
            issue_content: Original issue content.

        Returns:
            True if invalidated.
        """
        return await self.invalidate_for_content(
            self.PREFIX_ENHANCEMENT,
            workspace_id,
            issue_content,
        )

    # =========================================================================
    # Duplicate Detection Caching
    # =========================================================================

    async def get_or_generate_duplicates(
        self,
        workspace_id: UUID | str,
        issue_content: str,
        generator: Callable[[], Awaitable[list[dict[str, Any]]]],
    ) -> list[dict[str, Any]]:
        """Get or generate duplicate detection results.

        Args:
            workspace_id: Workspace UUID.
            issue_content: Issue title + description.
            generator: Async function to detect duplicates.

        Returns:
            List of potential duplicate issues.
        """
        return await self.get_or_generate(
            self.PREFIX_DUPLICATE,
            workspace_id,
            issue_content,
            generator,
            AICacheTTL.DUPLICATE_DETECTION,
        )

    async def invalidate_duplicates(
        self,
        workspace_id: UUID | str,
    ) -> int:
        """Invalidate all duplicate detection cache for workspace.

        Call this when new issues are created that could be duplicates.

        Args:
            workspace_id: Workspace UUID.

        Returns:
            Number of keys deleted.
        """
        return await self.invalidate_pattern(
            self.PREFIX_DUPLICATE,
            workspace_id,
        )

    # =========================================================================
    # Similarity Search Caching
    # =========================================================================

    async def get_or_generate_similar(
        self,
        workspace_id: UUID | str,
        query: str,
        generator: Callable[[], Awaitable[list[dict[str, Any]]]],
    ) -> list[dict[str, Any]]:
        """Get or generate similar items from vector search.

        Args:
            workspace_id: Workspace UUID.
            query: Search query text.
            generator: Async function to find similar items.

        Returns:
            List of similar items with scores.
        """
        return await self.get_or_generate(
            self.PREFIX_SIMILARITY,
            workspace_id,
            query,
            generator,
            AICacheTTL.ISSUE_SIMILARITY,
        )

    # =========================================================================
    # Issue Context Caching
    # =========================================================================

    async def get_or_generate_context(
        self,
        workspace_id: UUID | str,
        issue_id: str,
        generator: Callable[[], Awaitable[dict[str, Any]]],
    ) -> dict[str, Any]:
        """Get or generate AI context for issue.

        Args:
            workspace_id: Workspace UUID.
            issue_id: Issue UUID string.
            generator: Async function to build context.

        Returns:
            AI context data.
        """
        return await self.get_or_generate(
            self.PREFIX_CONTEXT,
            workspace_id,
            issue_id,
            generator,
            AICacheTTL.ISSUE_CONTEXT,
            include_hash=False,  # Use issue_id directly
        )

    async def invalidate_context(
        self,
        workspace_id: UUID | str,
        issue_id: str,
    ) -> bool:
        """Invalidate AI context cache for issue.

        Call when issue or related data changes.

        Args:
            workspace_id: Workspace UUID.
            issue_id: Issue UUID string.

        Returns:
            True if invalidated.
        """
        cache_key = self._build_key(self.PREFIX_CONTEXT, workspace_id, issue_id)
        deleted = await self._redis.delete(cache_key)
        return deleted > 0

    # =========================================================================
    # Note Analysis Caching
    # =========================================================================

    async def get_or_generate_note_analysis(
        self,
        workspace_id: UUID | str,
        note_content: str,
        generator: Callable[[], Awaitable[dict[str, Any]]],
    ) -> dict[str, Any]:
        """Get or generate note analysis results.

        Args:
            workspace_id: Workspace UUID.
            note_content: Note content for analysis.
            generator: Async function to analyze note.

        Returns:
            Note analysis results.
        """
        return await self.get_or_generate(
            self.PREFIX_NOTE_ANALYSIS,
            workspace_id,
            note_content,
            generator,
            AICacheTTL.NOTE_ANALYSIS,
        )

    # =========================================================================
    # Statistics and Monitoring
    # =========================================================================

    def get_stats(self) -> AICacheStats:
        """Get current cache statistics.

        Returns:
            Cache hit/miss statistics.
        """
        return AICacheStats(
            hits=self._hits,
            misses=self._misses,
            errors=self._errors,
        )

    def reset_stats(self) -> None:
        """Reset cache statistics."""
        self._hits = 0
        self._misses = 0
        self._errors = 0

    async def health_check(self) -> bool:
        """Check if cache is healthy.

        Returns:
            True if Redis is connected and responding.
        """
        return await self._redis.ping()


__all__ = ["AICache", "AICacheStats", "AICacheTTL"]
