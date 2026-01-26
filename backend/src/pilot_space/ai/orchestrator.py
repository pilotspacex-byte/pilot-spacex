"""AI Orchestrator for routing and managing AI tasks.

Central coordinator for all AI operations:
- Agent registry and routing
- Context building and management
- Rate limiting per workspace
- Task prioritization

T091: AI orchestrator implementation.

DEPRECATED: This legacy orchestrator is deprecated and will be removed in Wave 12.
Use SDKOrchestrator (sdk_orchestrator.py) instead for SDK-based agent execution.
This file remains only for backward compatibility during migration.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, TypeVar

from pilot_space.ai.agents import (
    ConversationAgent,
    ConversationInput,
    ConversationOutput,
    GhostTextAgent,
    GhostTextInput,
    GhostTextOutput,
    IssueExtractionInput,
    IssueExtractionOutput,
    IssueExtractorAgent,
    LegacyAgentContext as AgentContext,
    LegacyAgentResult as AgentResult,
    MarginAnnotationAgent,
    MarginAnnotationInput,
    MarginAnnotationOutput,
    Provider,
)
from pilot_space.ai.circuit_breaker import CircuitBreaker
from pilot_space.ai.exceptions import (
    AIConfigurationError,
    RateLimitError,
)
from pilot_space.ai.telemetry import AIOperation

if TYPE_CHECKING:
    from collections.abc import AsyncIterator
    from uuid import UUID

logger = logging.getLogger(__name__)

T = TypeVar("T")
InputT = TypeVar("InputT")
OutputT = TypeVar("OutputT")


@dataclass
class RateLimitConfig:
    """Rate limit configuration per operation.

    Attributes:
        requests_per_minute: Maximum requests per minute.
        requests_per_hour: Maximum requests per hour.
    """

    requests_per_minute: int = 60
    requests_per_hour: int = 1000


# Default rate limits per operation type
DEFAULT_RATE_LIMITS: dict[AIOperation, RateLimitConfig] = {
    AIOperation.GHOST_TEXT: RateLimitConfig(requests_per_minute=10, requests_per_hour=300),
    AIOperation.MARGIN_ANNOTATION: RateLimitConfig(requests_per_minute=5, requests_per_hour=100),
    AIOperation.ISSUE_EXTRACTION: RateLimitConfig(requests_per_minute=5, requests_per_hour=100),
    AIOperation.CONVERSATION: RateLimitConfig(requests_per_minute=20, requests_per_hour=500),
    AIOperation.PR_REVIEW: RateLimitConfig(requests_per_minute=2, requests_per_hour=20),
    AIOperation.EMBEDDING: RateLimitConfig(requests_per_minute=30, requests_per_hour=1000),
}


@dataclass
class WorkspaceAIConfig:
    """AI configuration for a workspace.

    Attributes:
        workspace_id: Workspace identifier.
        api_keys: Provider API keys.
        enabled_features: Enabled AI features.
        rate_limits: Custom rate limits (overrides defaults).
    """

    workspace_id: UUID
    api_keys: dict[Provider, str] = field(default_factory=dict)  # pyright: ignore[reportUnknownVariableType]
    enabled_features: set[AIOperation] = field(
        default_factory=lambda: {
            AIOperation.GHOST_TEXT,
            AIOperation.MARGIN_ANNOTATION,
            AIOperation.ISSUE_EXTRACTION,
            AIOperation.CONVERSATION,
        }
    )
    rate_limits: dict[AIOperation, RateLimitConfig] = field(default_factory=dict)  # pyright: ignore[reportUnknownVariableType]

    def get_rate_limit(self, operation: AIOperation) -> RateLimitConfig:
        """Get rate limit for operation.

        Args:
            operation: The AI operation.

        Returns:
            Rate limit configuration.
        """
        if operation in self.rate_limits:
            return self.rate_limits[operation]
        return DEFAULT_RATE_LIMITS.get(
            operation,
            RateLimitConfig(),
        )

    def is_feature_enabled(self, operation: AIOperation) -> bool:
        """Check if an AI feature is enabled.

        Args:
            operation: The AI operation.

        Returns:
            True if feature is enabled.
        """
        return operation in self.enabled_features


class RateLimiter:
    """In-memory rate limiter for AI operations.

    Tracks request counts per workspace and operation.
    For production, this should use Redis.
    """

    def __init__(self) -> None:
        """Initialize rate limiter."""
        # workspace_id -> operation -> (minute_count, minute_timestamp)
        self._minute_counts: dict[str, dict[str, tuple[int, float]]] = {}
        # workspace_id -> operation -> (hour_count, hour_timestamp)
        self._hour_counts: dict[str, dict[str, tuple[int, float]]] = {}

    async def check_and_increment(
        self,
        workspace_id: UUID,
        operation: AIOperation,
        config: RateLimitConfig,
    ) -> None:
        """Check rate limit and increment counter.

        Args:
            workspace_id: Workspace identifier.
            operation: AI operation being performed.
            config: Rate limit configuration.

        Raises:
            RateLimitError: If rate limit exceeded.
        """
        import time

        ws_key = str(workspace_id)
        op_key = operation.value
        now = time.time()

        # Initialize workspace tracking
        if ws_key not in self._minute_counts:
            self._minute_counts[ws_key] = {}
            self._hour_counts[ws_key] = {}

        # Check minute limit
        if op_key in self._minute_counts[ws_key]:
            count, timestamp = self._minute_counts[ws_key][op_key]
            if now - timestamp < 60:
                if count >= config.requests_per_minute:
                    raise RateLimitError(
                        f"Rate limit exceeded for {operation.value}",
                        retry_after_seconds=int(60 - (now - timestamp)),
                    )
                self._minute_counts[ws_key][op_key] = (count + 1, timestamp)
            else:
                self._minute_counts[ws_key][op_key] = (1, now)
        else:
            self._minute_counts[ws_key][op_key] = (1, now)

        # Check hour limit
        if op_key in self._hour_counts[ws_key]:
            count, timestamp = self._hour_counts[ws_key][op_key]
            if now - timestamp < 3600:
                if count >= config.requests_per_hour:
                    raise RateLimitError(
                        f"Hourly rate limit exceeded for {operation.value}",
                        retry_after_seconds=int(3600 - (now - timestamp)),
                    )
                self._hour_counts[ws_key][op_key] = (count + 1, timestamp)
            else:
                self._hour_counts[ws_key][op_key] = (1, now)
        else:
            self._hour_counts[ws_key][op_key] = (1, now)

    def reset_workspace(self, workspace_id: UUID) -> None:
        """Reset rate limits for a workspace.

        Args:
            workspace_id: Workspace to reset.
        """
        ws_key = str(workspace_id)
        self._minute_counts.pop(ws_key, None)
        self._hour_counts.pop(ws_key, None)


class AIOrchestrator:
    """Central orchestrator for AI operations.

    Manages agent lifecycle, routing, and rate limiting.

    Usage:
        orchestrator = AIOrchestrator()

        # Configure workspace
        config = WorkspaceAIConfig(
            workspace_id=workspace_id,
            api_keys={Provider.CLAUDE: "sk-..."},
        )
        orchestrator.configure_workspace(config)

        # Generate ghost text
        result = await orchestrator.generate_ghost_text(
            input_data=GhostTextInput(...),
            workspace_id=workspace_id,
            user_id=user_id,
            correlation_id="req-123",
        )
    """

    def __init__(self) -> None:
        """Initialize orchestrator."""
        self._workspace_configs: dict[UUID, WorkspaceAIConfig] = {}
        self._rate_limiter = RateLimiter()

        # Initialize agents
        # DEPRECATED: Legacy orchestrator will be removed in Wave 12 cleanup
        # These agents now require SDK infrastructure dependencies
        self._ghost_text_agent = GhostTextAgent()  # type: ignore[call-arg]
        self._margin_annotation_agent = MarginAnnotationAgent()  # type: ignore[call-arg]
        self._issue_extractor_agent = IssueExtractorAgent()  # type: ignore[call-arg]
        self._conversation_agent = ConversationAgent()  # type: ignore[call-arg]

        logger.info("AI Orchestrator initialized")

    def configure_workspace(self, config: WorkspaceAIConfig) -> None:
        """Configure AI for a workspace.

        Args:
            config: Workspace AI configuration.
        """
        self._workspace_configs[config.workspace_id] = config
        logger.info(
            "Workspace AI configured",
            extra={
                "workspace_id": str(config.workspace_id),
                "enabled_features": [f.value for f in config.enabled_features],
            },
        )

    def get_workspace_config(self, workspace_id: UUID) -> WorkspaceAIConfig | None:
        """Get workspace AI configuration.

        Args:
            workspace_id: Workspace identifier.

        Returns:
            Configuration if exists, None otherwise.
        """
        return self._workspace_configs.get(workspace_id)

    def _build_context(
        self,
        workspace_id: UUID,
        user_id: UUID,
        correlation_id: str,
        **extra: Any,
    ) -> AgentContext:
        """Build agent context from workspace configuration.

        Args:
            workspace_id: Workspace identifier.
            user_id: User identifier.
            correlation_id: Request correlation ID.
            **extra: Additional context data.

        Returns:
            AgentContext for agent execution.

        Raises:
            AIConfigurationError: If workspace not configured.
        """
        config = self._workspace_configs.get(workspace_id)
        if not config:
            raise AIConfigurationError(
                f"Workspace {workspace_id} is not configured for AI",
                missing_fields=["workspace_config"],
            )

        return AgentContext(
            workspace_id=workspace_id,
            user_id=user_id,
            correlation_id=correlation_id,
            api_keys=config.api_keys,
            extra=extra,
        )

    async def _check_rate_limit(
        self,
        workspace_id: UUID,
        operation: AIOperation,
    ) -> None:
        """Check rate limit for operation.

        Args:
            workspace_id: Workspace identifier.
            operation: AI operation.

        Raises:
            RateLimitError: If limit exceeded.
            AIConfigurationError: If feature disabled.
        """
        config = self._workspace_configs.get(workspace_id)
        if not config:
            raise AIConfigurationError(
                f"Workspace {workspace_id} is not configured",
            )

        if not config.is_feature_enabled(operation):
            raise AIConfigurationError(
                f"AI feature {operation.value} is not enabled for this workspace",
            )

        await self._rate_limiter.check_and_increment(
            workspace_id,
            operation,
            config.get_rate_limit(operation),
        )

    # Ghost Text API

    async def generate_ghost_text(
        self,
        input_data: GhostTextInput,
        workspace_id: UUID,
        user_id: UUID,
        correlation_id: str,
    ) -> AgentResult[GhostTextOutput]:
        """Generate ghost text suggestion.

        Args:
            input_data: Ghost text input.
            workspace_id: Workspace identifier.
            user_id: User identifier.
            correlation_id: Request correlation ID.

        Returns:
            Ghost text result.
        """
        await self._check_rate_limit(workspace_id, AIOperation.GHOST_TEXT)

        context = self._build_context(
            workspace_id,
            user_id,
            correlation_id,
        )

        # DEPRECATED: Legacy orchestrator will be removed in Wave 12 cleanup
        # SDK orchestrator in sdk_orchestrator.py is the replacement
        return await self._ghost_text_agent.execute(input_data, context)  # type: ignore[return-value, arg-type]

    async def stream_ghost_text(
        self,
        input_data: GhostTextInput,
        workspace_id: UUID,
        user_id: UUID,
        correlation_id: str,
    ) -> AsyncIterator[str]:
        """Stream ghost text tokens.

        Args:
            input_data: Ghost text input.
            workspace_id: Workspace identifier.
            user_id: User identifier.
            correlation_id: Request correlation ID.

        Yields:
            Ghost text tokens.
        """
        from pilot_space.ai.agents.ghost_text_agent import GhostTextStreamingAgent

        await self._check_rate_limit(workspace_id, AIOperation.GHOST_TEXT)

        context = self._build_context(
            workspace_id,
            user_id,
            correlation_id,
        )

        # DEPRECATED: Legacy orchestrator will be removed in Wave 12 cleanup
        streaming_agent = GhostTextStreamingAgent()  # type: ignore[call-arg]
        async for token in streaming_agent.stream(input_data, context):  # type: ignore[arg-type]
            yield token

    # Margin Annotation API

    async def analyze_note(
        self,
        input_data: MarginAnnotationInput,
        workspace_id: UUID,
        user_id: UUID,
        correlation_id: str,
    ) -> AgentResult[MarginAnnotationOutput]:
        """Analyze note and generate margin annotations.

        Args:
            input_data: Margin annotation input.
            workspace_id: Workspace identifier.
            user_id: User identifier.
            correlation_id: Request correlation ID.

        Returns:
            Margin annotation result.
        """
        await self._check_rate_limit(workspace_id, AIOperation.MARGIN_ANNOTATION)

        context = self._build_context(
            workspace_id,
            user_id,
            correlation_id,
        )

        return await self._margin_annotation_agent.execute(input_data, context)

    # Issue Extraction API

    async def extract_issues(
        self,
        input_data: IssueExtractionInput,
        workspace_id: UUID,
        user_id: UUID,
        correlation_id: str,
    ) -> AgentResult[IssueExtractionOutput]:
        """Extract issues from note content.

        Args:
            input_data: Issue extraction input.
            workspace_id: Workspace identifier.
            user_id: User identifier.
            correlation_id: Request correlation ID.

        Returns:
            Issue extraction result.
        """
        await self._check_rate_limit(workspace_id, AIOperation.ISSUE_EXTRACTION)

        context = self._build_context(
            workspace_id,
            user_id,
            correlation_id,
        )

        return await self._issue_extractor_agent.execute(input_data, context)

    # Conversation API

    async def chat(
        self,
        input_data: ConversationInput,
        workspace_id: UUID,
        user_id: UUID,
        correlation_id: str,
    ) -> AgentResult[ConversationOutput]:
        """Process conversation turn.

        Args:
            input_data: Conversation input.
            workspace_id: Workspace identifier.
            user_id: User identifier.
            correlation_id: Request correlation ID.

        Returns:
            Conversation result.
        """
        await self._check_rate_limit(workspace_id, AIOperation.CONVERSATION)

        context = self._build_context(
            workspace_id,
            user_id,
            correlation_id,
        )

        # Type ignore: Legacy AgentContext incompatible with SDK AgentContext
        # This orchestrator is deprecated - use SDKOrchestrator instead
        return await self._conversation_agent.execute(input_data, context)  # type: ignore[arg-type, return-value]

    async def stream_chat(
        self,
        input_data: ConversationInput,
        workspace_id: UUID,
        user_id: UUID,
        correlation_id: str,
    ) -> AsyncIterator[str]:
        """Stream conversation response.

        Args:
            input_data: Conversation input.
            workspace_id: Workspace identifier.
            user_id: User identifier.
            correlation_id: Request correlation ID.

        Yields:
            Response chunks.
        """
        await self._check_rate_limit(workspace_id, AIOperation.CONVERSATION)

        context = self._build_context(
            workspace_id,
            user_id,
            correlation_id,
        )

        # Type ignore: Legacy AgentContext incompatible with SDK AgentContext
        # This orchestrator is deprecated - use SDKOrchestrator instead
        async for chunk in self._conversation_agent.stream(input_data, context):  # type: ignore[arg-type]
            yield chunk

    # Health and Metrics

    def get_provider_health(self) -> dict[str, Any]:
        """Get health status of AI providers.

        Returns:
            Dictionary with provider health information.
        """
        providers = [Provider.CLAUDE, Provider.GEMINI, Provider.OPENAI]
        health: dict[str, Any] = {}

        for provider in providers:
            breaker = CircuitBreaker.get_or_create(provider.value)
            health[provider.value] = {
                "status": "healthy" if breaker.is_closed else "degraded",
                "circuit_state": breaker.state.value,
                "metrics": breaker.get_metrics(),
            }

        return health


# Global singleton
_orchestrator: AIOrchestrator | None = None


def get_orchestrator() -> AIOrchestrator:
    """Get global AI orchestrator instance.

    Returns:
        AIOrchestrator singleton.
    """
    global _orchestrator  # noqa: PLW0603
    if _orchestrator is None:
        _orchestrator = AIOrchestrator()
    return _orchestrator


__all__ = [
    "AIOrchestrator",
    "RateLimitConfig",
    "RateLimiter",
    "WorkspaceAIConfig",
    "get_orchestrator",
]
