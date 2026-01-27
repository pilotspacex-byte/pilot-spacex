"""GhostText fast path service for real-time completions.

Provides sub-500ms latency text completions bypassing full agent orchestration.
Uses Gemini 2.0 Flash for lowest latency per DD-011.

Reference: T080-T083 (GhostText Independent Fast Path)
Design Decisions: DD-011 (Model Selection for Latency)
"""

from __future__ import annotations

import hashlib
import logging
from typing import TYPE_CHECKING, Any
from uuid import UUID

if TYPE_CHECKING:
    from pilot_space.infrastructure.cache.redis import RedisClient

logger = logging.getLogger(__name__)

# Cache configuration
GHOST_TEXT_CACHE_TTL = 3600  # 1 hour
GHOST_TEXT_CACHE_PREFIX = "ghost_text"

# Model configuration (Gemini 2.0 Flash for latency)
GHOST_TEXT_MODEL = "gemini-2.0-flash-exp"
MAX_TOKENS = 50
TEMPERATURE = 0.3


class GhostTextService:
    """Fast path service for real-time text completions.

    Bypasses full agent orchestration for sub-500ms latency.
    Uses workspace-scoped Redis caching for common completions.

    Example:
        service = GhostTextService(redis_client)
        result = await service.generate_completion(
            context="def calculate_sum(a, b):",
            prefix="    return ",
            workspace_id=workspace_id,
        )
        print(result["suggestion"])  # "a + b"
    """

    def __init__(self, redis: RedisClient) -> None:
        """Initialize service with Redis client.

        Args:
            redis: Redis client for caching.
        """
        self._redis = redis

    @staticmethod
    def _build_cache_key(
        context: str,
        prefix: str,
        workspace_id: UUID,
    ) -> str:
        """Build cache key for completion.

        Args:
            context: Context text.
            prefix: Prefix to complete.
            workspace_id: Workspace UUID for scoping.

        Returns:
            Cache key string.
        """
        # Hash context + prefix for fixed-length key
        content = f"{context}|{prefix}"
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]

        return f"{GHOST_TEXT_CACHE_PREFIX}:{workspace_id}:{content_hash}"

    async def generate_completion(
        self,
        context: str,
        prefix: str,
        workspace_id: UUID,
        use_cache: bool = True,
    ) -> dict[str, Any]:
        """Generate text completion for ghost text.

        Args:
            context: Context text (previous paragraphs).
            prefix: Prefix to complete (current line).
            workspace_id: Workspace UUID for context and caching.
            use_cache: Whether to use/store in cache (default: True).

        Returns:
            Dictionary with suggestion and confidence:
            {
                "suggestion": str,
                "confidence": float (0.0-1.0),
                "cached": bool,
            }

        Raises:
            Exception: If API call fails.
        """
        # Check cache first
        cache_key = self._build_cache_key(context, prefix, workspace_id)
        if use_cache:
            cached = await self._redis.get(cache_key)

            if cached:
                logger.debug("Cache hit for ghost text completion")
                return {
                    "suggestion": cached["suggestion"],
                    "confidence": cached["confidence"],
                    "cached": True,
                }

        # Generate completion using Gemini 2.0 Flash
        try:
            import google.generativeai as genai

            # Build prompt
            prompt = self._build_prompt(context, prefix)

            # Call Gemini API (types not exported in genai module)
            model = genai.GenerativeModel(GHOST_TEXT_MODEL)  # type: ignore[attr-defined]
            response = await model.generate_content_async(
                prompt,
                generation_config=genai.GenerationConfig(  # type: ignore[attr-defined]
                    max_output_tokens=MAX_TOKENS,
                    temperature=TEMPERATURE,
                ),
            )

            # Extract suggestion
            suggestion = response.text.strip()

            # Calculate confidence (heuristic: based on response length)
            confidence = min(0.9, len(suggestion) / 100.0 + 0.5)

            result = {
                "suggestion": suggestion,
                "confidence": round(confidence, 2),
                "cached": False,
            }

            # Store in cache
            if use_cache:
                await self._redis.set(
                    cache_key,
                    {
                        "suggestion": suggestion,
                        "confidence": confidence,
                    },
                    ttl=GHOST_TEXT_CACHE_TTL,
                )

            logger.info(
                "Generated ghost text completion",
                extra={
                    "workspace_id": str(workspace_id),
                    "suggestion_length": len(suggestion),
                    "confidence": confidence,
                },
            )

            return result

        except Exception:
            logger.exception("Failed to generate ghost text completion")
            raise

    @staticmethod
    def _build_prompt(context: str, prefix: str) -> str:
        """Build prompt for completion.

        Args:
            context: Previous paragraphs.
            prefix: Current line prefix.

        Returns:
            Prompt string for model.
        """
        return f"""Complete the following text naturally and concisely (max 3 sentences).
Match the writing style and tone of the context.

Context:
{context}

Complete this:
{prefix}"""

    async def clear_workspace_cache(self, workspace_id: UUID) -> int:
        """Clear all cached completions for a workspace.

        Args:
            workspace_id: Workspace UUID.

        Returns:
            Number of keys cleared.
        """
        pattern = f"{GHOST_TEXT_CACHE_PREFIX}:{workspace_id}:*"
        keys = await self._redis.scan_keys(pattern, max_keys=1000)

        if keys:
            for key in keys:
                await self._redis.delete(key)

        logger.info(
            "Cleared ghost text cache",
            extra={
                "workspace_id": str(workspace_id),
                "keys_cleared": len(keys),
            },
        )

        return len(keys)


__all__ = ["GhostTextService"]
