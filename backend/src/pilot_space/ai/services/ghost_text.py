"""GhostText fast path service for real-time completions.

Provides sub-500ms latency text completions bypassing full agent orchestration.
Uses Claude Haiku for lowest latency on Anthropic's infrastructure.

Reference: T080-T083 (GhostText Independent Fast Path)
Design Decisions: DD-011 (Model Selection for Latency)
"""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING, Any
from uuid import UUID

from anthropic.types import TextBlock
from fastapi import HTTPException

from pilot_space.ai.providers.provider_selector import TaskType
from pilot_space.config import get_settings
from pilot_space.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from pilot_space.ai.infrastructure.anthropic_client_pool import AnthropicClientPool
    from pilot_space.ai.infrastructure.cost_tracker import CostTracker
    from pilot_space.ai.infrastructure.key_storage import SecureKeyStorage
    from pilot_space.ai.infrastructure.resilience import ResilientExecutor
    from pilot_space.ai.providers.provider_selector import ProviderSelector
    from pilot_space.infrastructure.cache.redis import RedisClient

logger = get_logger(__name__)

# Cache configuration
GHOST_TEXT_CACHE_TTL = 3600  # 1 hour
GHOST_TEXT_CACHE_PREFIX = "ghost_text"

# Completion generation constants
MAX_TOKENS = 50
TEMPERATURE = 0.3

# Haiku system prompt — directive, no padding (Haiku follows system constraints precisely)
_SYSTEM_PROMPT = "Complete text naturally. Output ONLY the completion—no explanations, no quotes."


class GhostTextService:
    """Fast path service for real-time text completions.

    Bypasses full agent orchestration for sub-500ms latency.
    Uses workspace-scoped Redis caching for common completions.
    All dependencies are injected via get_ghost_text_service() in dependencies/ai.py.

    Example:
        service = GhostTextService(redis, executor, selector, pool, key_storage, tracker)
        result = await service.generate_completion(
            context="def calculate_sum(a, b):",
            prefix="    return ",
            workspace_id=workspace_id,
            user_id=user_id,
        )
        print(result["suggestion"])  # "a + b"
    """

    def __init__(
        self,
        redis: RedisClient,
        resilient_executor: ResilientExecutor,
        provider_selector: ProviderSelector,
        client_pool: AnthropicClientPool,
        key_storage: SecureKeyStorage,
        cost_tracker: CostTracker,
    ) -> None:
        """Initialize service with all AI infrastructure dependencies.

        Args:
            redis: Redis client for caching.
            resilient_executor: Shared executor with circuit breaker config.
            provider_selector: Routing table for model selection.
            client_pool: DI-managed pool of AsyncAnthropic clients.
            key_storage: Workspace BYOK key resolver.
            cost_tracker: Request-scoped cost tracker.
        """
        self._redis = redis
        self._executor = resilient_executor
        self._provider_selector = provider_selector
        self._client_pool = client_pool
        self._key_storage = key_storage
        self._cost_tracker = cost_tracker

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
        # Length-prefixed format avoids ambiguity when context contains the separator.
        # e.g. context="a|b", prefix="c" → "3:a|bc" ≠ context="a", prefix="|bc" → "1:a|bc"
        content = f"{len(context)}:{context}{prefix}"
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]

        return f"{GHOST_TEXT_CACHE_PREFIX}:{workspace_id}:{content_hash}"

    async def generate_completion(
        self,
        context: str,
        prefix: str,
        workspace_id: UUID,
        user_id: UUID,
        use_cache: bool = True,
    ) -> dict[str, Any]:
        """Generate text completion for ghost text.

        Args:
            context: Context text (previous paragraphs).
            prefix: Prefix to complete (current line).
            workspace_id: Workspace UUID for context and caching.
            user_id: User UUID for cost attribution.
            use_cache: Whether to use/store in cache (default: True).

        Returns:
            Dictionary with suggestion and confidence:
            {
                "suggestion": str,
                "confidence": float (0.0-1.0),
                "cached": bool,
            }

        Raises:
            HTTPException: 402 if no Anthropic API key is configured.
            Exception: If API call fails after retries.
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

        # BYOK key resolution
        api_key = await self._key_storage.get_api_key(workspace_id, "anthropic")
        if not api_key:
            settings = get_settings()
            api_key = (
                settings.anthropic_api_key.get_secret_value()
                if settings.anthropic_api_key
                else None
            )
        if not api_key:
            raise HTTPException(
                status_code=402,
                detail="No Anthropic API key configured for this workspace",
            )

        # Model from routing table (respects circuit breaker state)
        _, model = self._provider_selector.select(TaskType.GHOST_TEXT)

        # Client from DI-managed pool — hashed key, reused connection pool
        client = self._client_pool.get_client(api_key)

        # API call via ResilientExecutor (retry + circuit breaker)
        try:
            response = await self._executor.execute(
                provider="anthropic",
                operation=lambda: client.messages.create(
                    model=model,
                    max_tokens=MAX_TOKENS,
                    temperature=TEMPERATURE,
                    system=_SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": self._build_prompt(context, prefix)}],
                ),
                timeout_sec=2.5,
            )
        except Exception:
            logger.exception("Failed to generate ghost text completion")
            raise

        # Guard against non-text block types (ThinkingBlock, ToolUseBlock, etc.)
        suggestion = next(
            (block.text for block in response.content if isinstance(block, TextBlock)),
            "",
        ).strip()

        # Confidence heuristic:
        # - "max_tokens" → model was truncated mid-completion, cap at 0.6
        # - "end_turn"   → natural completion, score by length (longer = more certain)
        if response.stop_reason == "max_tokens":
            confidence = 0.6
        else:
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

        # Cost tracking — non-fatal; completion already served if this raises
        try:
            await self._cost_tracker.track(
                workspace_id=workspace_id,
                user_id=user_id,
                agent_name="ghost_text",
                provider="anthropic",
                model=model,
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
            )
        except Exception:
            logger.warning("ghost_text_cost_tracking_failed", workspace_id=str(workspace_id))

        logger.info(
            "ghost_text_completion_generated",
            workspace_id=str(workspace_id),
            model=model,
            suggestion_length=len(suggestion),
            confidence=confidence,
        )

        return result

    @staticmethod
    def _build_prompt(context: str, prefix: str) -> str:
        """Build user message for Haiku completion.

        Haiku receives this as the user turn; the system prompt sets behavior.
        Keep it short — Haiku excels with minimal, structured input.

        Args:
            context: Previous paragraphs (writing style reference).
            prefix: Current line to continue.

        Returns:
            User message string.
        """
        parts = []
        if context:
            parts.append(f"Context: {context}")
        parts.append(f"Complete: {prefix}")
        return "\n\n".join(parts)

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
            await self._redis.delete(*keys)

        logger.info(
            "ghost_text_cache_cleared",
            workspace_id=str(workspace_id),
            keys_cleared=len(keys),
        )

        return len(keys)


__all__ = ["GhostTextService"]
