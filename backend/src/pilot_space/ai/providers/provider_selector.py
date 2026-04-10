"""Provider selection logic based on task type and provider health.

Implements DD-011 routing rules:
- Code-intensive tasks → Claude Opus/Sonnet (best code understanding)
- Latency-sensitive tasks → Claude Haiku (cost-optimized, <2s target)
- Embeddings → OpenAI (superior 3072-dim vectors)

All providers are Anthropic-only; Google/Gemini removed in favour of
Haiku for latency-sensitive paths (simpler dependency surface, single
API key, consistent billing model).

Integrates with CircuitBreaker for automatic failover on provider failures.

T015: ProviderSelector class with DD-011 routing table.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Final
from uuid import UUID

from pilot_space.ai.circuit_breaker import CircuitBreaker
from pilot_space.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)


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

    # Knowledge graph / contextual tasks (Claude Haiku — lightweight extraction)
    CONTEXTUAL_RETRIEVAL = "contextual_retrieval"
    GRAPH_EXTRACTION = "graph_extraction"
    INTENT_DETECTION = "intent_detection"
    ROLE_SKILL_GENERATION = "role_skill_generation"

    # Latency-sensitive tasks (Claude Haiku)
    GHOST_TEXT = "ghost_text"
    NOTIFICATION_PRIORITY = "notification_priority"
    ASSIGNEE_RECOMMENDATION = "assignee_recommendation"
    COMMIT_LINKING = "commit_linking"

    # Memory / summarization (Phase 70-06 — cheap tier, background)
    MEMORY_SUMMARIZATION = "memory_summarization"

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
        base_url: Custom base URL for provider API (workspace override).
    """

    provider: str
    model: str
    reason: str
    fallback_provider: str | None = None
    fallback_model: str | None = None
    base_url: str | None = None


@dataclass(frozen=True, slots=True)
class WorkspaceLLMConfig:
    """Resolved workspace LLM provider configuration.

    Attributes:
        provider: LLM provider name (anthropic, ollama, etc.).
        api_key: API key for the provider.
        base_url: Custom base URL for the provider API.
        model_name: Model name override from workspace config.
    """

    provider: str
    api_key: str
    base_url: str | None = None
    model_name: str | None = None


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
    ANTHROPIC_HAIKU: Final[str] = "claude-3-5-haiku-20241022"
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
            fallback_provider=Provider.ANTHROPIC.value,
            fallback_model=ANTHROPIC_HAIKU,
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
            fallback_provider=Provider.ANTHROPIC.value,
            fallback_model=ANTHROPIC_HAIKU,
        ),
        TaskType.TEMPLATE_FILLING: ProviderConfig(
            provider=Provider.ANTHROPIC.value,
            model=ANTHROPIC_SONNET,
            reason="AI-powered template completion",
            fallback_provider=Provider.ANTHROPIC.value,
            fallback_model=ANTHROPIC_HAIKU,
        ),
        # Knowledge graph / contextual tasks → Claude Haiku (lightweight extraction)
        TaskType.CONTEXTUAL_RETRIEVAL: ProviderConfig(
            provider=Provider.ANTHROPIC.value,
            model=ANTHROPIC_HAIKU,
            reason="Lightweight context prefix generation for chunk enrichment",
            fallback_provider=Provider.ANTHROPIC.value,
            fallback_model=ANTHROPIC_SONNET,
        ),
        TaskType.GRAPH_EXTRACTION: ProviderConfig(
            provider=Provider.ANTHROPIC.value,
            model=ANTHROPIC_HAIKU,
            reason="Lightweight graph knowledge extraction from conversations",
            fallback_provider=Provider.ANTHROPIC.value,
            fallback_model=ANTHROPIC_SONNET,
        ),
        TaskType.INTENT_DETECTION: ProviderConfig(
            provider=Provider.ANTHROPIC.value,
            model=ANTHROPIC_SONNET,
            reason="Structured intent detection with few-shot reasoning",
            fallback_provider=Provider.ANTHROPIC.value,
            fallback_model=ANTHROPIC_HAIKU,
        ),
        TaskType.ROLE_SKILL_GENERATION: ProviderConfig(
            provider=Provider.ANTHROPIC.value,
            model=ANTHROPIC_SONNET,
            reason="AI-powered skill profile generation with template context",
            fallback_provider=Provider.ANTHROPIC.value,
            fallback_model=ANTHROPIC_HAIKU,
        ),
        # Latency-sensitive → Claude Haiku (cost-optimized, <2s target)
        #
        # NOTE — same-provider fallback: both primary (Haiku) and fallback (Sonnet)
        # are on Anthropic. When the Anthropic circuit breaker opens, the fallback
        # is also unreachable and the selector returns the primary config unchanged.
        # The caller must handle APIError / connection failures directly.
        TaskType.GHOST_TEXT: ProviderConfig(
            provider=Provider.ANTHROPIC.value,
            model=ANTHROPIC_HAIKU,
            reason="Real-time completion requires <1.5s latency — Haiku on Anthropic infra",
            fallback_provider=Provider.ANTHROPIC.value,
            fallback_model=ANTHROPIC_SONNET,
        ),
        TaskType.NOTIFICATION_PRIORITY: ProviderConfig(
            provider=Provider.ANTHROPIC.value,
            model=ANTHROPIC_HAIKU,
            reason="Quick scoring for notification importance",
            fallback_provider=Provider.ANTHROPIC.value,
            fallback_model=ANTHROPIC_SONNET,
        ),
        TaskType.ASSIGNEE_RECOMMENDATION: ProviderConfig(
            provider=Provider.ANTHROPIC.value,
            model=ANTHROPIC_HAIKU,
            reason="Fast lookup for team member matching",
            fallback_provider=Provider.ANTHROPIC.value,
            fallback_model=ANTHROPIC_SONNET,
        ),
        TaskType.COMMIT_LINKING: ProviderConfig(
            provider=Provider.ANTHROPIC.value,
            model=ANTHROPIC_HAIKU,
            reason="Parse commit references quickly",
            fallback_provider=Provider.ANTHROPIC.value,
            fallback_model=ANTHROPIC_SONNET,
        ),
        # Phase 70-06: background note summarization — cheap tier (Haiku).
        # Runs off the ai_normal queue, never user-facing, so latency does
        # not matter but cost does.
        TaskType.MEMORY_SUMMARIZATION: ProviderConfig(
            provider=Provider.ANTHROPIC.value,
            model=ANTHROPIC_HAIKU,
            reason="Background memory summarization — cheap tier (cost-optimized)",
            fallback_provider=Provider.ANTHROPIC.value,
            fallback_model=ANTHROPIC_SONNET,
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
        workspace_override: WorkspaceLLMConfig | None = None,
    ) -> ProviderConfig:
        """Select provider with full configuration including fallback.

        Args:
            task_type: Type of AI task to perform.
            user_override: Optional (provider, model) override from user preferences.
            workspace_override: Optional workspace-level LLM config. When provided and
                model_name is set, overrides the static routing table model. Circuit
                breaker health checks still apply to the provider.

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
                    "provider_selected",
                    task_type=task_type.value,
                    provider=provider,
                    model=model,
                    reason="user_override",
                )
                return ProviderConfig(
                    provider=provider,
                    model=model,
                    reason="User preference override",
                    fallback_provider=self._ROUTING_TABLE[task_type].provider,
                    fallback_model=self._ROUTING_TABLE[task_type].model,
                )

        # Workspace override: use workspace provider/model/base_url when configured
        if workspace_override is not None:
            ws_provider = workspace_override.provider
            ws_model = workspace_override.model_name or self._ROUTING_TABLE[task_type].model
            ws_base_url = workspace_override.base_url
            static_config = self._ROUTING_TABLE[task_type]

            if self.is_provider_healthy(ws_provider):
                logger.info(
                    "provider_selected",
                    task_type=task_type.value,
                    provider=ws_provider,
                    model=ws_model,
                    reason="workspace_override",
                )
                return ProviderConfig(
                    provider=ws_provider,
                    model=ws_model,
                    reason="Workspace LLM provider override",
                    fallback_provider=static_config.provider,
                    fallback_model=static_config.model,
                    base_url=ws_base_url,
                )

            # Workspace provider unhealthy — fall back to static routing table
            logger.warning(
                "workspace_provider_unhealthy",
                task_type=task_type.value,
                workspace_provider=ws_provider,
                fallback_provider=static_config.provider,
            )
            if self.is_provider_healthy(static_config.provider):
                return ProviderConfig(
                    provider=static_config.provider,
                    model=static_config.model,
                    reason=f"Fallback from workspace provider {ws_provider} (circuit breaker open)",
                    fallback_provider=static_config.fallback_provider,
                    fallback_model=static_config.fallback_model,
                )

        config = self._ROUTING_TABLE[task_type]

        # Check if primary provider is healthy
        if not self.is_provider_healthy(config.provider):
            logger.warning(
                "provider_unhealthy",
                task_type=task_type.value,
                primary_provider=config.provider,
                fallback_provider=config.fallback_provider,
            )

            # Try fallback if available and healthy
            if config.fallback_provider and self.is_provider_healthy(config.fallback_provider):
                logger.info(
                    "provider_fallback_activated",
                    task_type=task_type.value,
                    from_provider=config.provider,
                    to_provider=config.fallback_provider,
                )
                return ProviderConfig(
                    provider=config.fallback_provider,
                    model=config.fallback_model or config.model,
                    reason=f"Fallback from {config.provider} (circuit breaker open)",
                    fallback_provider=None,
                    fallback_model=None,
                )

            logger.error(
                "provider_all_unavailable",
                task_type=task_type.value,
                primary=config.provider,
                fallback=config.fallback_provider,
            )

        logger.info(
            "provider_selected",
            task_type=task_type.value,
            provider=config.provider,
            model=config.model,
            reason=config.reason,
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
                "provider_circuit_breaker_open",
                provider=provider,
                state=breaker.state.value,
                metrics=breaker.get_metrics(),
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


async def resolve_workspace_llm_config(
    session: AsyncSession,
    workspace_id: UUID | None,
) -> WorkspaceLLMConfig | None:
    """Resolve the LLM provider configuration for a workspace.

    Shared helper that encapsulates the workspace LLM resolution pattern
    used across AI services (extraction, intent detection, skill generation).

    Resolution priority:
    1. Workspace's default_llm_provider setting + SecureKeyStorage key
    2. Any other configured LLM provider in the workspace
    3. App-level ANTHROPIC_API_KEY environment variable
    4. None (caller should handle gracefully)

    Args:
        session: Async database session.
        workspace_id: Workspace UUID, or None to skip workspace lookup.

    Returns:
        WorkspaceLLMConfig with provider, api_key, base_url, model_name or None.
    """
    if workspace_id is not None:
        try:
            from sqlalchemy import select as sa_select

            from pilot_space.ai.infrastructure.key_storage import SecureKeyStorage
            from pilot_space.config import get_settings
            from pilot_space.infrastructure.database.models.workspace import Workspace

            settings = get_settings()
            encryption_key = settings.encryption_key.get_secret_value()
            if not encryption_key:
                logger.debug(
                    "encryption_key empty — skipping workspace lookup, trying app-level fallback"
                )
                # Fall through to app-level Anthropic key below
            else:
                # Determine which LLM provider the workspace has selected
                stmt = sa_select(Workspace.settings).where(Workspace.id == workspace_id)
                result = await session.execute(stmt)
                ws_settings = result.scalar_one_or_none() or {}
                default_llm = ws_settings.get("default_llm_provider", "anthropic")

                storage = SecureKeyStorage(session, encryption_key)
                key_info = await storage.get_key_info(workspace_id, default_llm, "llm")

                if key_info is not None:
                    api_key = await storage.get_api_key(workspace_id, default_llm, "llm")
                    return WorkspaceLLMConfig(
                        provider=default_llm,
                        api_key=api_key or "",
                        base_url=key_info.base_url,
                        model_name=key_info.model_name,
                    )

                # If default provider has no key, try any configured LLM provider
                all_keys = await storage.get_all_key_infos(workspace_id)
                for ki in all_keys:
                    if ki.service_type == "llm":
                        api_key = await storage.get_api_key(workspace_id, ki.provider, "llm")
                        return WorkspaceLLMConfig(
                            provider=ki.provider,
                            api_key=api_key or "",
                            base_url=ki.base_url,
                            model_name=ki.model_name,
                        )

        except Exception:
            logger.debug("Could not retrieve workspace LLM provider", exc_info=True)

    # Fall back to app-level Anthropic key
    try:
        from pilot_space.config import get_settings

        settings = get_settings()
        if settings.anthropic_api_key:
            return WorkspaceLLMConfig(
                provider="anthropic",
                api_key=settings.anthropic_api_key.get_secret_value(),
                base_url=None,
                model_name=None,
            )
    except Exception:
        logger.debug("Could not retrieve app-level API key", exc_info=True)

    return None


__all__ = [
    "Provider",
    "ProviderConfig",
    "ProviderSelector",
    "TaskType",
    "WorkspaceLLMConfig",
    "resolve_workspace_llm_config",
]
