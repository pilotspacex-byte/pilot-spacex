"""SDK Base Agent for Claude Agent SDK.

Abstract base class for all AI agents. Provides common infrastructure:
- Telemetry and cost tracking
- Provider/model selection
- Resilience with retry and circuit breaker
- MCP tool access

Reference: docs/architect/claude-agent-sdk-architecture.md
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any
from uuid import UUID

from pilot_space.ai.sdk.config import MODEL_SONNET

if TYPE_CHECKING:
    from pilot_space.ai.infrastructure.cost_tracker import CostTracker
    from pilot_space.ai.infrastructure.resilience import ResilientExecutor
    from pilot_space.ai.providers.provider_selector import ProviderSelector
    from pilot_space.ai.tools.mcp_server import ToolRegistry


@dataclass(frozen=True)
class AgentContext:
    """Execution context for an agent.

    Provides workspace and user context for RLS enforcement
    and cost tracking attribution.

    Attributes:
        workspace_id: UUID of the current workspace
        user_id: UUID of the user invoking the agent
        operation_id: Optional operation ID for cost aggregation
        metadata: Optional extra context data
    """

    workspace_id: UUID
    user_id: UUID
    operation_id: UUID | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentResult[OutputT]:
    """Result from agent execution.

    Attributes:
        success: Whether execution completed successfully
        output: Agent-specific output data
        cost_usd: Estimated cost in USD
        input_tokens: Number of input tokens used
        output_tokens: Number of output tokens generated
        error: Error message if success is False
    """

    success: bool
    output: OutputT | None
    cost_usd: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    error: str | None = None

    @classmethod
    def ok(cls, output: OutputT, **kwargs: Any) -> AgentResult[OutputT]:
        """Create successful result."""
        return cls(success=True, output=output, **kwargs)

    @classmethod
    def fail(cls, error: str, **kwargs: Any) -> AgentResult[OutputT]:
        """Create failed result."""
        return cls(success=False, output=None, error=error, **kwargs)


class SDKBaseAgent[InputT, OutputT](ABC):
    """Abstract base class for Claude Agent SDK agents.

    All agents extend this class to inherit:
    - MCP tool access via tool_registry
    - Provider/model selection via provider_selector
    - Cost tracking via cost_tracker
    - Resilience via resilient_executor

    Subclasses must define:
    - AGENT_NAME: str - Unique identifier for this agent
    - DEFAULT_MODEL: str - Default model to use
    - execute(): Main execution logic

    Usage:
        class MyAgent(SDKBaseAgent[MyInput, MyOutput]):
            AGENT_NAME = "my_agent"
            DEFAULT_MODEL = "claude-sonnet-4-20250514"

            async def execute(self, input_data, context):
                ...
    """

    AGENT_NAME: str = "pilot_space_agent"  # Override in subclass
    DEFAULT_MODEL: str = MODEL_SONNET  # Override in subclass

    def __init__(
        self,
        tool_registry: ToolRegistry,
        provider_selector: ProviderSelector,
        cost_tracker: CostTracker,
        resilient_executor: ResilientExecutor,
    ) -> None:
        """Initialize agent with infrastructure dependencies.

        Args:
            tool_registry: Registry for MCP tool access
            provider_selector: Provider/model selection service
            cost_tracker: Cost_tracker service
            resilient_executor: Retry and circuit breaker service
        """
        self._tool_registry = tool_registry
        self._provider_selector = provider_selector
        self._cost_tracker = cost_tracker
        self._resilient_executor = resilient_executor

    @property
    def tools(self) -> ToolRegistry:
        """Access to MCP tool registry."""
        return self._tool_registry

    def get_model(self) -> tuple[str, str]:
        """Get provider and model for this agent.

        Returns:
            Tuple of (provider, model) based on routing table.
            Returns default (anthropic, DEFAULT_MODEL) if no task type mapping.
        """
        # Agents don't map directly to TaskType - subclasses can override
        # this method to provide proper TaskType selection
        return ("anthropic", self.DEFAULT_MODEL)

    async def track_usage(
        self,
        context: AgentContext,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        """Track token usage and return cost.

        Args:
            context: Execution context
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Estimated cost in USD
        """
        provider, model = self.get_model()
        cost_record = await self._cost_tracker.track(
            workspace_id=context.workspace_id,
            user_id=context.user_id,
            agent_name=self.AGENT_NAME,
            provider=provider,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
        return cost_record.cost_usd

    async def run(
        self,
        input_data: InputT,
        context: AgentContext,
    ) -> AgentResult[OutputT]:
        """Execute agent with resilience wrapper.

        This is the public entry point. It wraps execute() with
        retry logic and circuit breaker protection.

        Args:
            input_data: Agent-specific input data
            context: Execution context

        Returns:
            AgentResult with output or error
        """
        try:
            provider, _model = self.get_model()

            async def _execute() -> OutputT:
                return await self.execute(input_data, context)

            output = await self._resilient_executor.execute(
                provider=provider,
                operation=_execute,
            )
            return AgentResult.ok(output)

        except Exception as e:
            return AgentResult.fail(str(e))

    @abstractmethod
    async def execute(
        self,
        input_data: InputT,
        context: AgentContext,
    ) -> OutputT:
        """Execute the agent logic.

        Subclasses implement this method with their specific logic.
        This method is called by run() with resilience protection.

        Args:
            input_data: Agent-specific input data
            context: Execution context

        Returns:
            Agent-specific output

        Raises:
            Any exception will be caught by run() and returned as error
        """
        ...


class StreamingSDKBaseAgent[InputT, OutputT](SDKBaseAgent[InputT, OutputT], ABC):
    """Base class for streaming agents.

    Extends SDKBaseAgent with streaming support for agents that
    output tokens incrementally (ghost text, AI context, etc.).

    Subclasses must implement stream() in addition to execute().
    """

    @abstractmethod
    async def stream(
        self,
        input_data: InputT,
        context: AgentContext,
    ) -> AsyncIterator[str]:
        """Stream output tokens as they're generated.

        Args:
            input_data: Agent-specific input data
            context: Execution context

        Yields:
            Output tokens/chunks as strings
        """
        ...
        # Ensure this is an async generator
        if False:  # pragma: no cover
            yield ""

    async def execute(
        self,
        input_data: InputT,
        context: AgentContext,
    ) -> OutputT:
        """Execute by collecting stream into final output.

        Default implementation collects all streamed tokens.
        Override if output format differs from concatenated stream.

        Args:
            input_data: Agent-specific input data
            context: Execution context

        Returns:
            Concatenated output from stream
        """
        chunks: list[str] = []
        async for chunk in self.stream(input_data, context):
            chunks.append(chunk)
        return "".join(chunks)  # type: ignore[return-value]

    async def run_stream(
        self,
        input_data: InputT,
        context: AgentContext,
    ) -> AsyncIterator[str]:
        """Stream with resilience wrapper.

        Unlike run(), this yields tokens as they're generated.
        Errors are yielded as error strings prefixed with "ERROR:".

        Args:
            input_data: Agent-specific input data
            context: Execution context

        Yields:
            Output tokens or error messages
        """
        try:
            async for chunk in self.stream(input_data, context):
                yield chunk
        except Exception as e:
            yield f"ERROR: {e}"


__all__ = [
    "AgentContext",
    "AgentResult",
    "SDKBaseAgent",
    "StreamingSDKBaseAgent",
]
