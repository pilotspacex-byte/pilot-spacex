"""Provider selection logic based on task type and provider health.

Implements DD-011 routing rules:
- Code-intensive tasks → Claude Opus/Sonnet (best code understanding)
- Latency-sensitive tasks → Claude Haiku (cost-optimized, <2s target)
- Embeddings → OpenAI (superior 3072-dim vectors)

Integrates with CircuitBreaker for automatic failover on provider failures.

T015: ProviderSelector class with DD-011 routing table.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Final

from pilot_space.ai.circuit_breaker import CircuitBreaker

logger = logging.getLogger(__name__)


class Provider(Enum):
    """Supported AI providers."""

    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    GOOGLE = "google"


class TaskType(Enum):
    """Task types for routing decisions per DD-011."""

    # Code-intensive tasks (Claude Opus)
    PR_REVIEW = "pr_review"
    AI_CONTEXT = "ai_context"
    TASK_DECOMPOSITION = "task_decomposition"
    PATTERN_DETECTION = "pattern_detection"

    # Standard tasks (Claude Sonnet)
    CODE_GENERATION = "code_generation"
    DOC_GENERATION = "doc_generation"
    ISSUE_ENHANCEMENT = "issue_enhancement"
    ISSUE_EXTRACTION = "issue_extraction"
    MARGIN_ANNOTATION = "margin_annotation"
    CONVERSATION = "conversation"
    DUPLICATE_DETECTION = "duplicate_detection"
    DIAGRAM_GENERATION = "diagram_generation"
    TEMPLATE_FILLING = "template_filling"

    # Latency-sensitive tasks (Claude Haiku)
    GHOST_TEXT = "ghost_text"
    NOTIFICATION_PRIORITY = "notification_priority"
    ASSIGNEE_RECOMMENDATION = "assignee_recommendation"
    COMMIT_LINKING = "commit_linking"

    # Embeddings (OpenAI)
    EMBEDDINGS = "embeddings"
    SEMANTIC_SEARCH = "semantic_search"


@dataclass(frozen=True, slots=True, kw_only=True)
class ProviderConfig:
    """Configuration for a selected provider.

    Attributes:
        provider: Selected AI provider.
        model: Model identifier for the provider.
        reason: Human-readable explanation for selection.
        fallback_provider: Alternative provider if primary fails.
        fallback_model: Model to use with fallback provider.
    """

    provider: str
    model: str
    reason: str
    fallback_provider: str | None = None
    fallback_model: str | None = None


class ProviderSelector:
    """Selects optimal AI provider based on task type and health.

    Implements DD-011 routing rules with circuit breaker integration
    for automatic failover on provider failures.

    Usage:
        selector = ProviderSelector()
        provider, model = selector.select(TaskType.PR_REVIEW)

        # Or get full config with fallback info
        config = selector.select_with_config(TaskType.PR_REVIEW)
    """

    # Model identifiers per provider
    ANTHROPIC_OPUS: Final[str] = "claude-opus-4-5"
    ANTHROPIC_SONNET: Final[str] = "claude-sonnet-4"
    ANTHROPIC_HAIKU: Final[str] = "claude-3-5-haiku"
    OPENAI_EMBEDDING: Final[str] = "text-embedding-3-large"
    GOOGLE_FLASH: Final[str] = "gemini-2.0-flash"
    GOOGLE_PRO: Final[str] = "gemini-2.0-pro"

    # Routing table per DD-011
    _ROUTING_TABLE: Final[dict[TaskType, ProviderConfig]] = {
        # Code-intensive → Claude Opus (best code understanding)
        TaskType.PR_REVIEW: ProviderConfig(
            provider=Provider.ANTHROPIC.value,
            model=ANTHROPIC_OPUS,
            reason="Architecture + security analysis requires deep code understanding",
            fallback_provider=Provider.ANTHROPIC.value,
            fallback_model=ANTHROPIC_SONNET,
        ),
        TaskType.AI_CONTEXT: ProviderConfig(
            provider=Provider.ANTHROPIC.value,
            model=ANTHROPIC_OPUS,
            reason="Multi-turn context building requires complex reasoning",
            fallback_provider=Provider.ANTHROPIC.value,
            fallback_model=ANTHROPIC_SONNET,
        ),
        TaskType.TASK_DECOMPOSITION: ProviderConfig(
            provider=Provider.ANTHROPIC.value,
            model=ANTHROPIC_OPUS,
            reason="Breaking features into subtasks requires complex reasoning",
            fallback_provider=Provider.ANTHROPIC.value,
            fallback_model=ANTHROPIC_SONNET,
        ),
        TaskType.PATTERN_DETECTION: ProviderConfig(
            provider=Provider.ANTHROPIC.value,
            model=ANTHROPIC_OPUS,
            reason="Finding knowledge patterns requires advanced analysis",
            fallback_provider=Provider.ANTHROPIC.value,
            fallback_model=ANTHROPIC_SONNET,
        ),
        # Standard tasks → Claude Sonnet (balanced performance)
        TaskType.CODE_GENERATION: ProviderConfig(
            provider=Provider.ANTHROPIC.value,
            model=ANTHROPIC_SONNET,
            reason="Quality code generation with balanced cost",
            fallback_provider=Provider.ANTHROPIC.value,
            fallback_model=ANTHROPIC_HAIKU,
        ),
        TaskType.DOC_GENERATION: ProviderConfig(
            provider=Provider.ANTHROPIC.value,
            model=ANTHROPIC_SONNET,
            reason="Documentation generation with code context",
            fallback_provider=Provider.ANTHROPIC.value,
            fallback_model=ANTHROPIC_HAIKU,
        ),
        TaskType.ISSUE_ENHANCEMENT: ProviderConfig(
            provider=Provider.ANTHROPIC.value,
            model=ANTHROPIC_SONNET,
            reason="Suggesting labels and priority requires moderate analysis",
            fallback_provider=Provider.ANTHROPIC.value,
            fallback_model=ANTHROPIC_HAIKU,
        ),
        TaskType.ISSUE_EXTRACTION: ProviderConfig(
            provider=Provider.ANTHROPIC.value,
            model=ANTHROPIC_SONNET,
            reason="Extracting issues from notes requires structured reasoning",
            fallback_provider=Provider.ANTHROPIC.value,
            fallback_model=ANTHROPIC_HAIKU,
        ),
        TaskType.MARGIN_ANNOTATION: ProviderConfig(
            provider=Provider.ANTHROPIC.value,
            model=ANTHROPIC_SONNET,
            reason="Generating inline suggestions with context",
            fallback_provider=Provider.GOOGLE.value,
            fallback_model=GOOGLE_FLASH,
        ),
        TaskType.CONVERSATION: ProviderConfig(
            provider=Provider.ANTHROPIC.value,
            model=ANTHROPIC_SONNET,
            reason="Multi-turn Q&A with context preservation",
            fallback_provider=Provider.ANTHROPIC.value,
            fallback_model=ANTHROPIC_HAIKU,
        ),
        TaskType.DUPLICATE_DETECTION: ProviderConfig(
            provider=Provider.ANTHROPIC.value,
            model=ANTHROPIC_SONNET,
            reason="Semantic similarity analysis",
            fallback_provider=Provider.OPENAI.value,
            fallback_model=OPENAI_EMBEDDING,
        ),
        TaskType.DIAGRAM_GENERATION: ProviderConfig(
            provider=Provider.ANTHROPIC.value,
            model=ANTHROPIC_SONNET,
            reason="Generating Mermaid/PlantUML diagrams",
            fallback_provider=Provider.GOOGLE.value,
            fallback_model=GOOGLE_FLASH,
        ),
        TaskType.TEMPLATE_FILLING: ProviderConfig(
            provider=Provider.ANTHROPIC.value,
            model=ANTHROPIC_SONNET,
            reason="AI-powered template completion",
            fallback_provider=Provider.ANTHROPIC.value,
            fallback_model=ANTHROPIC_HAIKU,
        ),
        # Latency-sensitive → Gemini Flash (DD-011: <1.5s response)
        TaskType.GHOST_TEXT: ProviderConfig(
            provider=Provider.GOOGLE.value,
            model=GOOGLE_FLASH,
            reason="Real-time completion requires <1.5s latency (DD-011)",
            fallback_provider=Provider.ANTHROPIC.value,
            fallback_model=ANTHROPIC_HAIKU,
        ),
        TaskType.NOTIFICATION_PRIORITY: ProviderConfig(
            provider=Provider.ANTHROPIC.value,
            model=ANTHROPIC_HAIKU,
            reason="Quick scoring for notification importance",
            fallback_provider=Provider.GOOGLE.value,
            fallback_model=GOOGLE_FLASH,
        ),
        TaskType.ASSIGNEE_RECOMMENDATION: ProviderConfig(
            provider=Provider.ANTHROPIC.value,
            model=ANTHROPIC_HAIKU,
            reason="Fast lookup for team member matching",
            fallback_provider=Provider.GOOGLE.value,
            fallback_model=GOOGLE_FLASH,
        ),
        TaskType.COMMIT_LINKING: ProviderConfig(
            provider=Provider.ANTHROPIC.value,
            model=ANTHROPIC_HAIKU,
            reason="Parse commit references quickly",
            fallback_provider=Provider.GOOGLE.value,
            fallback_model=GOOGLE_FLASH,
        ),
        # Embeddings → OpenAI (superior 3072-dim vectors)
        TaskType.EMBEDDINGS: ProviderConfig(
            provider=Provider.OPENAI.value,
            model=OPENAI_EMBEDDING,
            reason="Superior 3072-dimensional embeddings for RAG",
            fallback_provider=None,
            fallback_model=None,
        ),
        TaskType.SEMANTIC_SEARCH: ProviderConfig(
            provider=Provider.OPENAI.value,
            model=OPENAI_EMBEDDING,
            reason="High-quality embeddings for semantic search",
            fallback_provider=None,
            fallback_model=None,
        ),
    }

    def __init__(self) -> None:
        """Initialize provider selector."""
        self._circuit_breakers: dict[str, CircuitBreaker] = {}

    def select(
        self,
        task_type: TaskType,
        user_override: tuple[str, str] | None = None,
    ) -> tuple[str, str]:
        """Select optimal provider and model for task type.

        Args:
            task_type: Type of AI task to perform.
            user_override: Optional (provider, model) override from user preferences.

        Returns:
            Tuple of (provider, model) to use.

        Raises:
            ValueError: If task_type is not recognized.
        """
        config = self.select_with_config(task_type, user_override)
        return (config.provider, config.model)

    def select_with_config(
        self,
        task_type: TaskType,
        user_override: tuple[str, str] | None = None,
    ) -> ProviderConfig:
        """Select provider with full configuration including fallback.

        Args:
            task_type: Type of AI task to perform.
            user_override: Optional (provider, model) override from user preferences.

        Returns:
            ProviderConfig with selected provider and fallback information.

        Raises:
            ValueError: If task_type is not recognized.
        """
        if task_type not in self._ROUTING_TABLE:
            msg = f"Unknown task type: {task_type}"
            raise ValueError(msg)

        # User override takes precedence if provider is healthy
        if user_override:
            provider, model = user_override
            if self.is_provider_healthy(provider):
                logger.info(
                    "Using user override",
                    extra={
                        "task_type": task_type.value,
                        "provider": provider,
                        "model": model,
                    },
                )
                return ProviderConfig(
                    provider=provider,
                    model=model,
                    reason="User preference override",
                    fallback_provider=self._ROUTING_TABLE[task_type].provider,
                    fallback_model=self._ROUTING_TABLE[task_type].model,
                )

        config = self._ROUTING_TABLE[task_type]

        # Check if primary provider is healthy
        if not self.is_provider_healthy(config.provider):
            logger.warning(
                "Primary provider unhealthy, attempting fallback",
                extra={
                    "task_type": task_type.value,
                    "primary_provider": config.provider,
                    "fallback_provider": config.fallback_provider,
                },
            )

            # Try fallback if available and healthy
            if config.fallback_provider and self.is_provider_healthy(config.fallback_provider):
                return ProviderConfig(
                    provider=config.fallback_provider,
                    model=config.fallback_model or config.model,
                    reason=f"Fallback from {config.provider} (circuit breaker open)",
                    fallback_provider=None,
                    fallback_model=None,
                )

            logger.error(
                "Both primary and fallback providers unavailable",
                extra={
                    "task_type": task_type.value,
                    "primary": config.provider,
                    "fallback": config.fallback_provider,
                },
            )

        logger.info(
            "Selected provider",
            extra={
                "task_type": task_type.value,
                "provider": config.provider,
                "model": config.model,
                "reason": config.reason,
            },
        )

        return config

    def get_fallback(
        self,
        task_type: TaskType,
    ) -> tuple[str, str] | None:
        """Get fallback provider and model for task type.

        Args:
            task_type: Type of AI task.

        Returns:
            Tuple of (provider, model) for fallback, or None if no fallback available.

        Raises:
            ValueError: If task_type is not recognized.
        """
        if task_type not in self._ROUTING_TABLE:
            msg = f"Unknown task type: {task_type}"
            raise ValueError(msg)

        config = self._ROUTING_TABLE[task_type]
        if config.fallback_provider and config.fallback_model:
            return (config.fallback_provider, config.fallback_model)
        return None

    def is_provider_healthy(self, provider: str) -> bool:
        """Check if provider is healthy (circuit breaker not open).

        Args:
            provider: Provider name to check.

        Returns:
            True if provider is healthy, False if circuit breaker is open.
        """
        breaker = self._get_or_create_circuit_breaker(provider)
        is_healthy = not breaker.is_open

        if not is_healthy:
            logger.warning(
                "Provider circuit breaker is open",
                extra={
                    "provider": provider,
                    "state": breaker.state.value,
                    "metrics": breaker.get_metrics(),
                },
            )

        return is_healthy

    def get_all_task_types(self) -> list[TaskType]:
        """Get list of all supported task types.

        Returns:
            List of TaskType enum values.
        """
        return list(TaskType)

    def get_routing_info(self, task_type: TaskType) -> dict[str, str]:
        """Get routing information for a task type.

        Args:
            task_type: Type of AI task.

        Returns:
            Dictionary with routing information.

        Raises:
            ValueError: If task_type is not recognized.
        """
        if task_type not in self._ROUTING_TABLE:
            msg = f"Unknown task type: {task_type}"
            raise ValueError(msg)

        config = self._ROUTING_TABLE[task_type]
        return {
            "task_type": task_type.value,
            "provider": config.provider,
            "model": config.model,
            "reason": config.reason,
            "fallback_provider": config.fallback_provider or "None",
            "fallback_model": config.fallback_model or "None",
        }

    def _get_or_create_circuit_breaker(self, provider: str) -> CircuitBreaker:
        """Get or create circuit breaker for provider.

        Args:
            provider: Provider name.

        Returns:
            CircuitBreaker instance for the provider.
        """
        if provider not in self._circuit_breakers:
            self._circuit_breakers[provider] = CircuitBreaker.get_or_create(provider)
        return self._circuit_breakers[provider]


__all__ = [
    "Provider",
    "ProviderConfig",
    "ProviderSelector",
    "TaskType",
]
