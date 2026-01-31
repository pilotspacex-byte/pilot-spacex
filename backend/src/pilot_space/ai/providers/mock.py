"""Mock LLM provider for development and testing.

Provides deterministic AI responses without external API calls.
Active only when: app_env == "development" AND ai_fake_mode == True

Usage:
    # Generators are auto-registered via decorator
    @MockResponseRegistry.register("GhostTextAgent")
    def generate_ghost_text(input_data: GhostTextInput) -> GhostTextOutput:
        return GhostTextOutput(...)

    # BaseAgent checks MockProvider in execute()
    mock_provider = MockProvider.get_instance()
    if mock_provider.is_enabled():
        return await mock_provider.execute(self, input_data, context)
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, ClassVar, TypeVar

from pilot_space.config import get_settings

if TYPE_CHECKING:
    from pilot_space.ai.agents.agent_base import AgentContext, AgentResult, SDKBaseAgent

logger = logging.getLogger(__name__)

InputT = TypeVar("InputT")
OutputT = TypeVar("OutputT")


@dataclass
class MockCallRecord:
    """Record of a mock AI call for debugging.

    Attributes:
        agent_name: Name of the agent that was called.
        input_summary: Truncated summary of input data.
        output_summary: Truncated summary of output data.
        latency_ms: Simulated latency in milliseconds.
        timestamp: Unix timestamp when call was made.
    """

    agent_name: str
    input_summary: str
    output_summary: str
    latency_ms: int
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "agent_name": self.agent_name,
            "input_summary": self.input_summary,
            "output_summary": self.output_summary,
            "latency_ms": self.latency_ms,
            "timestamp": self.timestamp,
        }


class MockResponseRegistry:
    """Registry of mock response generators per agent class.

    Provides decorator-based registration of mock generators.
    Each agent class name maps to a generator function that
    produces deterministic output from input data.

    Usage:
        @MockResponseRegistry.register("GhostTextAgent")
        def generate_ghost_text(input_data: GhostTextInput) -> GhostTextOutput:
            return GhostTextOutput(...)
    """

    _generators: ClassVar[dict[str, Callable[..., Any]]] = {}
    _call_history: ClassVar[list[MockCallRecord]] = []
    _max_history: ClassVar[int] = 100

    @classmethod
    def register(cls, agent_name: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Register a mock response generator for an agent.

        Args:
            agent_name: Class name of the agent (e.g., "GhostTextAgent").

        Returns:
            Decorator function.
        """

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            cls._generators[agent_name] = func
            logger.debug(f"Registered mock generator for {agent_name}")
            return func

        return decorator

    @classmethod
    def get_generator(cls, agent_name: str) -> Callable[..., Any] | None:
        """Get registered generator for agent.

        Args:
            agent_name: Class name of the agent.

        Returns:
            Generator function or None if not registered.
        """
        return cls._generators.get(agent_name)

    @classmethod
    def has_generator(cls, agent_name: str) -> bool:
        """Check if generator exists for agent.

        Args:
            agent_name: Class name of the agent.

        Returns:
            True if generator is registered.
        """
        return agent_name in cls._generators

    @classmethod
    def list_registered(cls) -> list[str]:
        """List all registered agent names.

        Returns:
            List of registered agent class names.
        """
        return list(cls._generators.keys())

    @classmethod
    def record_call(cls, record: MockCallRecord) -> None:
        """Record a mock call for debugging.

        Maintains a rolling history of recent calls.

        Args:
            record: Call record to store.
        """
        cls._call_history.append(record)
        if len(cls._call_history) > cls._max_history:
            cls._call_history.pop(0)

    @classmethod
    def get_history(cls) -> list[MockCallRecord]:
        """Get call history.

        Returns:
            Copy of call history list.
        """
        return list(cls._call_history)

    @classmethod
    def clear_history(cls) -> None:
        """Clear call history."""
        cls._call_history.clear()


class MockProvider:
    """Mock LLM provider that returns fake responses.

    Singleton pattern - use MockProvider.get_instance().

    The provider only activates when both conditions are met:
    - app_env == "development"
    - ai_fake_mode == True

    This ensures mock responses are never used in production.
    """

    _instance: MockProvider | None = None

    def __init__(self) -> None:
        """Initialize the mock provider."""
        self._settings = get_settings()

    @classmethod
    def get_instance(cls) -> MockProvider:
        """Get singleton instance.

        Returns:
            MockProvider singleton.
        """
        if cls._instance is None:
            cls._instance = MockProvider()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton (for testing)."""
        cls._instance = None

    def is_enabled(self) -> bool:
        """Check if mock mode is enabled.

        Returns True only when:
        - app_env == "development"
        - ai_fake_mode == True

        Returns:
            True if mock mode should be used.
        """
        settings = get_settings()  # Fresh read for testing
        return settings.is_development and settings.ai_fake_mode

    async def execute(
        self,
        agent: SDKBaseAgent[InputT, OutputT],
        input_data: InputT,
        context: AgentContext,
    ) -> AgentResult[OutputT]:
        """Execute agent with mock response.

        Args:
            agent: The agent instance.
            input_data: Input data for the agent.
            context: Execution context.

        Returns:
            AgentResult with mock output.

        Raises:
            ValueError: If no generator registered for agent.
        """
        from pilot_space.ai.agents.agent_base import AgentResult

        agent_name = agent.__class__.__name__
        settings = get_settings()

        logger.info(
            "MockProvider executing agent",
            extra={
                "agent": agent_name,
                "workspace_id": str(context.workspace_id),
                "latency_ms": settings.ai_fake_latency_ms,
            },
        )

        # Simulate latency
        if settings.ai_fake_latency_ms > 0:
            await asyncio.sleep(settings.ai_fake_latency_ms / 1000)

        # Get generator
        generator = MockResponseRegistry.get_generator(agent_name)
        if not generator:
            registered = MockResponseRegistry.list_registered()
            raise ValueError(
                f"No mock generator registered for {agent_name}. "
                f"Register one with @MockResponseRegistry.register('{agent_name}'). "
                f"Currently registered: {registered}"
            )

        # Generate response
        output = generator(input_data)

        # Record call
        MockResponseRegistry.record_call(
            MockCallRecord(
                agent_name=agent_name,
                input_summary=str(input_data)[:200],
                output_summary=str(output)[:200],
                latency_ms=settings.ai_fake_latency_ms,
            )
        )

        # Estimate tokens (rough: 4 chars per token)
        input_tokens = max(1, len(str(input_data)) // 4)
        output_tokens = max(1, len(str(output)) // 4)

        # Calculate mock cost (very low for mock mode)
        cost_usd = (input_tokens * 0.00001) + (output_tokens * 0.00002)

        return AgentResult(
            success=True,
            output=output,
            cost_usd=cost_usd,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )


async def stream_mock_response(
    content: str,
    chunk_size: int = 15,
    delay_ms: int | None = None,
) -> AsyncIterator[str]:
    """Stream mock response as plain text chunks.

    Simulates streaming LLM output by chunking content
    and yielding with delays. SSE formatting is handled by
    the streaming utilities (sse_stream_generator).

    Args:
        content: Full content to stream.
        chunk_size: Characters per chunk.
        delay_ms: Delay between chunks (uses settings if None).

    Yields:
        Plain text chunks (not SSE-formatted).
    """
    if delay_ms is None:
        settings = get_settings()
        delay_ms = settings.ai_fake_streaming_chunk_delay_ms

    for i in range(0, len(content), chunk_size):
        chunk = content[i : i + chunk_size]
        yield chunk
        if delay_ms > 0:
            await asyncio.sleep(delay_ms / 1000)


__all__ = [
    "MockCallRecord",
    "MockProvider",
    "MockResponseRegistry",
    "stream_mock_response",
]
