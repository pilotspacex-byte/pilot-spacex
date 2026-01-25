"""Base AI agent class for Pilot Space.

Provides abstract base class for all AI agents with:
- Provider routing based on task type (DD-011)
- Rate limiting with exponential backoff
- Circuit breaker integration
- Structured logging with correlation ID

T083: Create base AI agent class.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

from pilot_space.ai.circuit_breaker import CircuitBreaker
from pilot_space.ai.exceptions import (
    AgentExecutionError,
    AIConfigurationError,
)
from pilot_space.ai.providers.mock import MockProvider
from pilot_space.ai.telemetry import (
    AIOperation,
    AIProvider,
    track_ai_operation,
)
from pilot_space.ai.utils.retry import RetryConfig, with_retry

if TYPE_CHECKING:
    from uuid import UUID

logger = logging.getLogger(__name__)


class TaskType(Enum):
    """Task type for provider routing (DD-011).

    Determines which AI provider to use based on task requirements.

    Attributes:
        CODE_ANALYSIS: Code understanding, PR review - use Claude.
        LATENCY_SENSITIVE: Ghost text, quick suggestions - use Gemini Flash.
        EMBEDDINGS: Vector embeddings - use OpenAI.
        COMPLEX_REASONING: Multi-step reasoning - use Claude Opus.
        CONVERSATION: Multi-turn chat - use Claude Sonnet.
    """

    CODE_ANALYSIS = "code_analysis"
    LATENCY_SENSITIVE = "latency_sensitive"
    EMBEDDINGS = "embeddings"
    COMPLEX_REASONING = "complex_reasoning"
    CONVERSATION = "conversation"


class Provider(Enum):
    """AI provider identifiers.

    Maps to actual provider implementations and API configurations.
    """

    CLAUDE = "claude"
    GEMINI = "gemini"
    OPENAI = "openai"


# Provider routing table (DD-011)
PROVIDER_ROUTING: dict[TaskType, Provider] = {
    TaskType.CODE_ANALYSIS: Provider.CLAUDE,
    TaskType.LATENCY_SENSITIVE: Provider.GEMINI,
    TaskType.EMBEDDINGS: Provider.OPENAI,
    TaskType.COMPLEX_REASONING: Provider.CLAUDE,
    TaskType.CONVERSATION: Provider.CLAUDE,
}

# Default models per provider
DEFAULT_MODELS: dict[Provider, str] = {
    Provider.CLAUDE: "claude-sonnet-4-20250514",
    Provider.GEMINI: "gemini-2.0-flash",
    Provider.OPENAI: "text-embedding-3-large",
}

# Operation type mapping for telemetry
TASK_TO_OPERATION: dict[TaskType, AIOperation] = {
    TaskType.CODE_ANALYSIS: AIOperation.PR_REVIEW,
    TaskType.LATENCY_SENSITIVE: AIOperation.GHOST_TEXT,
    TaskType.EMBEDDINGS: AIOperation.EMBEDDING,
    TaskType.COMPLEX_REASONING: AIOperation.CONTEXT_GENERATION,
    TaskType.CONVERSATION: AIOperation.CONVERSATION,
}


@dataclass
class AgentContext:
    """Context for agent execution.

    Provides workspace and user context for the agent,
    along with configuration and correlation tracking.

    Attributes:
        workspace_id: Workspace where agent is executing.
        user_id: User who triggered the agent.
        correlation_id: Request correlation ID for tracing.
        api_keys: Provider API keys from workspace config.
        extra: Additional context data.
    """

    workspace_id: UUID
    user_id: UUID
    correlation_id: str
    api_keys: dict[Provider, str] = field(default_factory=dict)  # pyright: ignore[reportUnknownVariableType]
    extra: dict[str, Any] = field(default_factory=dict)  # pyright: ignore[reportUnknownVariableType]

    def get_api_key(self, provider: Provider) -> str | None:
        """Get API key for a provider.

        Args:
            provider: The provider to get key for.

        Returns:
            API key if configured, None otherwise.
        """
        return self.api_keys.get(provider)

    def require_api_key(self, provider: Provider) -> str:
        """Get required API key for a provider.

        Args:
            provider: The provider to get key for.

        Returns:
            API key.

        Raises:
            AIConfigurationError: If key is not configured.
        """
        key = self.get_api_key(provider)
        if not key:
            raise AIConfigurationError(
                f"API key for provider '{provider.value}' is not configured",
                provider=provider.value,
                missing_fields=["api_key"],
            )
        return key


@dataclass
class AgentResult[OutputT]:
    """Result from agent execution.

    Wraps the output with metadata about the execution.

    Attributes:
        output: The agent's output.
        input_tokens: Number of input tokens used.
        output_tokens: Number of output tokens generated.
        model: Model that was used.
        provider: Provider that was used.
        cached: Whether result was from cache.
        metadata: Additional result metadata.
    """

    output: OutputT
    input_tokens: int = 0
    output_tokens: int = 0
    model: str = ""
    provider: Provider = Provider.CLAUDE
    cached: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)  # pyright: ignore[reportUnknownVariableType]


class BaseAgent[InputT, OutputT](ABC):
    """Abstract base class for all AI agents.

    Provides common functionality:
    - Provider routing based on task type
    - Retry with exponential backoff
    - Circuit breaker integration
    - Telemetry and logging

    Type Parameters:
        InputT: Input type for the agent.
        OutputT: Output type from the agent.

    Class Attributes:
        task_type: Task type for provider routing.
        operation: Operation type for telemetry.
        retry_config: Retry configuration.
    """

    # Subclasses should override these
    task_type: TaskType = TaskType.CODE_ANALYSIS
    operation: AIOperation = AIOperation.CONTEXT_GENERATION
    retry_config: RetryConfig = RetryConfig(max_retries=3)

    def __init__(self, model: str | None = None) -> None:
        """Initialize the agent.

        Args:
            model: Override default model for this agent.
        """
        self._model_override = model

    @property
    def provider(self) -> Provider:
        """Get the provider for this agent's task type.

        Returns:
            Provider to use for execution.
        """
        return PROVIDER_ROUTING.get(self.task_type, Provider.CLAUDE)

    @property
    def model(self) -> str:
        """Get the model to use for this agent.

        Returns:
            Model identifier.
        """
        if self._model_override:
            return self._model_override
        return DEFAULT_MODELS.get(self.provider, "claude-sonnet-4-20250514")

    @property
    def circuit_breaker(self) -> CircuitBreaker:
        """Get circuit breaker for this agent's provider.

        Returns:
            CircuitBreaker instance.
        """
        return CircuitBreaker.get_or_create(self.provider.value)

    def get_telemetry_provider(self) -> AIProvider:
        """Map provider enum to telemetry provider.

        Returns:
            AIProvider for telemetry.
        """
        mapping = {
            Provider.CLAUDE: AIProvider.ANTHROPIC,
            Provider.GEMINI: AIProvider.GOOGLE,
            Provider.OPENAI: AIProvider.OPENAI,
        }
        return mapping.get(self.provider, AIProvider.ANTHROPIC)

    @abstractmethod
    async def _execute_impl(
        self,
        input_data: InputT,
        context: AgentContext,
    ) -> AgentResult[OutputT]:
        """Implement the actual agent logic.

        Subclasses must implement this method with their specific logic.

        Args:
            input_data: The input data for the agent.
            context: Execution context.

        Returns:
            AgentResult with output and metadata.
        """
        ...

    async def execute(
        self,
        input_data: InputT,
        context: AgentContext,
    ) -> AgentResult[OutputT]:
        """Execute the agent with full middleware stack.

        Applies:
        1. Telemetry tracking
        2. Circuit breaker protection
        3. Retry with backoff

        Args:
            input_data: The input data for the agent.
            context: Execution context.

        Returns:
            AgentResult with output and metadata.

        Raises:
            AgentExecutionError: If execution fails after retries.
        """
        agent_name = self.__class__.__name__

        # Check for mock mode (development only)
        mock_provider = MockProvider.get_instance()
        if mock_provider.is_enabled():
            # Import generators to register them (side-effect import)
            import pilot_space.ai.providers.mock_generators as _mock_generators

            del _mock_generators  # Explicitly mark as used
            return await mock_provider.execute(self, input_data, context)

        logger.info(
            "Agent execution starting",
            extra={
                "agent": agent_name,
                "correlation_id": context.correlation_id,
                "workspace_id": str(context.workspace_id),
                "user_id": str(context.user_id),
                "provider": self.provider.value,
                "model": self.model,
            },
        )

        async with track_ai_operation(
            operation=self.operation,
            provider=self.get_telemetry_provider(),
            model=self.model,
            workspace_id=context.workspace_id,
            user_id=context.user_id,
            correlation_id=context.correlation_id,
            agent=agent_name,
        ) as metrics:
            try:
                # Execute with circuit breaker and retry
                result = await self._execute_with_resilience(input_data, context)

                # Update metrics
                metrics.complete(
                    input_tokens=result.input_tokens,
                    output_tokens=result.output_tokens,
                    success=True,
                    cached=result.cached,
                )

                logger.info(
                    "Agent execution completed",
                    extra={
                        "agent": agent_name,
                        "correlation_id": context.correlation_id,
                        "input_tokens": result.input_tokens,
                        "output_tokens": result.output_tokens,
                    },
                )

                return result

            except Exception as e:
                logger.exception(
                    "Agent execution failed",
                    extra={
                        "agent": agent_name,
                        "correlation_id": context.correlation_id,
                        "error_type": type(e).__name__,
                        "error": str(e),
                    },
                )
                raise AgentExecutionError(agent_name, cause=e) from e

    async def _execute_with_resilience(
        self,
        input_data: InputT,
        context: AgentContext,
    ) -> AgentResult[OutputT]:
        """Execute with circuit breaker and retry.

        Args:
            input_data: The input data for the agent.
            context: Execution context.

        Returns:
            AgentResult from execution.
        """

        @with_retry(config=self.retry_config)
        async def _resilient_execute() -> AgentResult[OutputT]:
            return await self.circuit_breaker.execute(
                self._execute_impl,
                input_data,
                context,
            )

        return await _resilient_execute()

    def validate_input(self, input_data: InputT) -> None:
        """Validate input data before execution.

        Subclasses can override to add input validation.
        Default implementation does nothing (validation is optional).

        Args:
            input_data: The input data to validate.

        Raises:
            ValueError: If input is invalid.
        """
        _ = input_data  # Default no-op, subclasses override as needed

    def __repr__(self) -> str:
        """Return string representation."""
        return f"<{self.__class__.__name__}(provider={self.provider.value}, model={self.model})>"


def get_provider_for_task(task_type: TaskType) -> Provider:
    """Get the recommended provider for a task type.

    Args:
        task_type: The type of task.

    Returns:
        Recommended provider.
    """
    return PROVIDER_ROUTING.get(task_type, Provider.CLAUDE)


def get_default_model(provider: Provider) -> str:
    """Get the default model for a provider.

    Args:
        provider: The AI provider.

    Returns:
        Default model identifier.
    """
    return DEFAULT_MODELS.get(provider, "claude-sonnet-4-20250514")


__all__ = [
    "AgentContext",
    "AgentResult",
    "BaseAgent",
    "Provider",
    "TaskType",
    "get_default_model",
    "get_provider_for_task",
]
