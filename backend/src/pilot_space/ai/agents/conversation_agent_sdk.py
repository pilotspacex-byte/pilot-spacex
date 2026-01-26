"""Conversation agent for multi-turn AI discussions using Claude Agent SDK.

Uses Claude Sonnet for threaded conversations about notes and issues.
Supports context management and streaming.

Architecture:
- Extends StreamingSDKBaseAgent for streaming support
- Uses claude-sonnet-4 for quality conversational responses
- Manages conversation history with token limits
- Streams responses for real-time UI updates

T091f: ConversationAgent SDK migration.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

from anthropic import (
    APIError,
    AsyncAnthropic,
    RateLimitError as AnthropicRateLimitError,
)

from pilot_space.ai.agents.sdk_base import (
    AgentContext,
    StreamingSDKBaseAgent,
)
from pilot_space.ai.exceptions import (
    AIConfigurationError,
    RateLimitError,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from pilot_space.ai.infrastructure.cost_tracker import CostTracker
    from pilot_space.ai.infrastructure.key_storage import SecureKeyStorage
    from pilot_space.ai.infrastructure.resilience import ResilientExecutor
    from pilot_space.ai.providers.provider_selector import ProviderSelector
    from pilot_space.ai.tools.mcp_server import ToolRegistry

logger = logging.getLogger(__name__)


class MessageRole(Enum):
    """Role in conversation."""

    USER = "user"
    ASSISTANT = "assistant"


@dataclass
class ConversationMessage:
    """A message in the conversation.

    Attributes:
        role: Message role (user/assistant).
        content: Message content.
        metadata: Optional metadata.
    """

    role: MessageRole
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, str]:
        """Convert to API format."""
        return {
            "role": self.role.value,
            "content": self.content,
        }


@dataclass
class ConversationInput:
    """Input for conversation turn.

    Attributes:
        message: New user message.
        history: Previous conversation history.
        system_context: Additional context for the system prompt.
        max_history_messages: Maximum messages to include.
        max_history_tokens: Maximum tokens in history.
    """

    message: str
    history: list[ConversationMessage] = field(default_factory=list)
    system_context: str | None = None
    max_history_messages: int = 10
    max_history_tokens: int = 4000


@dataclass
class ConversationOutput:
    """Output from conversation turn.

    Attributes:
        response: Assistant response.
        updated_history: Full conversation history.
        truncated: Whether history was truncated.
        input_tokens: Input tokens used.
        output_tokens: Output tokens generated.
    """

    response: str
    updated_history: list[ConversationMessage] = field(default_factory=list)
    truncated: bool = False
    input_tokens: int = 0
    output_tokens: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "response": self.response,
            "message_count": len(self.updated_history),
            "truncated": self.truncated,
        }


# Default system prompt for conversations
CONVERSATION_SYSTEM_PROMPT = """You are an AI assistant embedded in Pilot Space, a project management platform.
You help users:
1. Refine their notes and ideas
2. Clarify issue descriptions
3. Plan implementation approaches
4. Answer questions about their projects

Be helpful, concise, and focused on actionable insights.
When discussing code or technical topics, be specific and practical.
If you're unsure about something, ask clarifying questions.

{additional_context}"""


class ConversationAgent(StreamingSDKBaseAgent[ConversationInput, ConversationOutput]):
    """Agent for multi-turn conversations using Claude Agent SDK.

    Uses Claude Sonnet for quality responses.
    Manages conversation history with token limits.
    Supports streaming for real-time UI updates.

    Attributes:
        AGENT_NAME: Unique identifier for cost tracking.
        DEFAULT_MODEL: Claude Sonnet for quality.
    """

    AGENT_NAME = "conversation"
    DEFAULT_MODEL = "claude-sonnet-4-20250514"
    MAX_OUTPUT_TOKENS = 2048

    def __init__(
        self,
        tool_registry: ToolRegistry,
        provider_selector: ProviderSelector,
        cost_tracker: CostTracker,
        resilient_executor: ResilientExecutor,
        key_storage: SecureKeyStorage,
        max_output_tokens: int = MAX_OUTPUT_TOKENS,
    ) -> None:
        """Initialize conversation agent.

        Args:
            tool_registry: Registry for MCP tool access
            provider_selector: Provider/model selection service
            cost_tracker: Cost tracking service
            resilient_executor: Retry and circuit breaker service
            key_storage: Secure API key storage
            max_output_tokens: Maximum response tokens.
        """
        super().__init__(
            tool_registry=tool_registry,
            provider_selector=provider_selector,
            cost_tracker=cost_tracker,
            resilient_executor=resilient_executor,
        )
        self._key_storage = key_storage
        self._max_output_tokens = max_output_tokens

    def get_model(self) -> tuple[str, str]:
        """Get provider and model for conversations.

        Returns:
            Tuple of (provider, model) for Claude Sonnet.
        """
        return ("anthropic", self.DEFAULT_MODEL)

    def _validate_input(self, input_data: ConversationInput) -> None:
        """Validate input before processing.

        Args:
            input_data: The input to validate.

        Raises:
            ValueError: If input is invalid.
        """
        if not input_data.message or not input_data.message.strip():
            raise ValueError("message cannot be empty")

    async def _get_api_key(self, context: AgentContext) -> str:
        """Get Anthropic API key from secure storage.

        Args:
            context: Agent execution context.

        Returns:
            API key string.

        Raises:
            AIConfigurationError: If key not configured.
        """
        api_key = await self._key_storage.get_api_key(
            workspace_id=context.workspace_id,
            provider="anthropic",
        )
        if not api_key:
            raise AIConfigurationError(
                "Anthropic API key not configured for conversations",
                provider="anthropic",
                missing_fields=["api_key"],
            )
        return api_key

    def _truncate_history(
        self,
        history: list[ConversationMessage],
        max_messages: int,
        max_tokens: int,
    ) -> tuple[list[ConversationMessage], bool]:
        """Truncate history to fit within limits.

        Args:
            history: Full conversation history.
            max_messages: Maximum messages to keep.
            max_tokens: Maximum tokens to keep.

        Returns:
            Tuple of (truncated_history, was_truncated).
        """
        if not history:
            return [], False

        # First limit by message count
        truncated = history[-max_messages:]
        was_truncated = len(truncated) < len(history)

        # Then estimate tokens and truncate further if needed
        total_chars = sum(len(msg.content) for msg in truncated)
        estimated_tokens = total_chars // 4  # Rough estimate

        while estimated_tokens > max_tokens and len(truncated) > 2:
            truncated = truncated[2:]  # Remove oldest pair
            total_chars = sum(len(msg.content) for msg in truncated)
            estimated_tokens = total_chars // 4
            was_truncated = True

        return truncated, was_truncated

    def _build_messages(
        self,
        history: list[ConversationMessage],
        new_message: str,
    ) -> list[dict[str, str]]:
        """Build messages array for Anthropic API.

        Args:
            history: Truncated conversation history.
            new_message: New user message.

        Returns:
            Messages in Anthropic format.
        """
        messages: list[dict[str, str]] = [
            {"role": msg.role.value, "content": msg.content}
            for msg in history
        ]
        messages.append({"role": "user", "content": new_message})
        return messages

    async def execute(
        self,
        input_data: ConversationInput,
        context: AgentContext,
    ) -> ConversationOutput:
        """Execute conversation turn.

        Args:
            input_data: Conversation input.
            context: Agent execution context.

        Returns:
            ConversationOutput with response and updated history.
        """
        self._validate_input(input_data)

        api_key = await self._get_api_key(context)

        # Build system prompt
        additional_context = input_data.system_context or ""
        system_prompt = CONVERSATION_SYSTEM_PROMPT.format(
            additional_context=additional_context,
        )

        # Truncate history if needed
        history, truncated = self._truncate_history(
            input_data.history,
            input_data.max_history_messages,
            input_data.max_history_tokens,
        )

        # Build messages
        messages = self._build_messages(history, input_data.message)

        try:
            client = AsyncAnthropic(api_key=api_key)

            response = await client.messages.create(
                model=self.DEFAULT_MODEL,
                max_tokens=self._max_output_tokens,
                system=system_prompt,
                messages=messages,  # type: ignore[arg-type]
            )

            # Extract response text
            response_text = ""
            for block in response.content:
                if block.type == "text":
                    response_text = block.text
                    break

            # Build updated history
            updated_history = list(history)
            updated_history.append(
                ConversationMessage(
                    role=MessageRole.USER,
                    content=input_data.message,
                )
            )
            updated_history.append(
                ConversationMessage(
                    role=MessageRole.ASSISTANT,
                    content=response_text,
                )
            )

            # Track usage
            await self.track_usage(
                context=context,
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
            )

            return ConversationOutput(
                response=response_text,
                updated_history=updated_history,
                truncated=truncated,
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
            )

        except AnthropicRateLimitError as e:
            raise RateLimitError(
                "Anthropic rate limit exceeded",
                retry_after_seconds=60,
                provider="anthropic",
            ) from e

        except APIError as e:
            logger.exception(
                "Anthropic API error in conversation",
                extra={
                    "error": str(e),
                    "workspace_id": str(context.workspace_id),
                },
            )
            raise

    async def stream(
        self,
        input_data: ConversationInput,
        context: AgentContext,
    ) -> AsyncIterator[str]:
        """Stream conversation response.

        Args:
            input_data: Conversation input.
            context: Agent execution context.

        Yields:
            Response chunks as they're generated.
        """
        self._validate_input(input_data)

        api_key = await self._get_api_key(context)

        # Build system prompt
        additional_context = input_data.system_context or ""
        system_prompt = CONVERSATION_SYSTEM_PROMPT.format(
            additional_context=additional_context,
        )

        # Truncate history
        history, _ = self._truncate_history(
            input_data.history,
            input_data.max_history_messages,
            input_data.max_history_tokens,
        )

        # Build messages
        messages = self._build_messages(history, input_data.message)

        # Stream response
        client = AsyncAnthropic(api_key=api_key)

        async with client.messages.stream(
            model=self.DEFAULT_MODEL,
            max_tokens=self._max_output_tokens,
            system=system_prompt,
            messages=messages,  # type: ignore[arg-type]
        ) as stream:
            async for text in stream.text_stream:
                yield text


class ConversationManager:
    """Helper for managing conversation state.

    Maintains conversation history and provides a simpler interface.
    """

    def __init__(
        self,
        agent: ConversationAgent,
        max_history: int = 10,
        system_context: str | None = None,
    ) -> None:
        """Initialize conversation manager.

        Args:
            agent: Configured ConversationAgent instance.
            max_history: Maximum messages to keep.
            system_context: Context for system prompt.
        """
        self._agent = agent
        self._history: list[ConversationMessage] = []
        self._max_history = max_history
        self._system_context = system_context

    @property
    def history(self) -> list[ConversationMessage]:
        """Get current conversation history."""
        return list(self._history)

    def clear_history(self) -> None:
        """Clear conversation history."""
        self._history.clear()

    def add_context(self, context_text: str) -> None:
        """Add context to system prompt.

        Args:
            context_text: Additional context.
        """
        if self._system_context:
            self._system_context = f"{self._system_context}\n\n{context_text}"
        else:
            self._system_context = context_text

    async def chat(
        self,
        message: str,
        context: AgentContext,
    ) -> str:
        """Send a message and get response.

        Args:
            message: User message.
            context: Agent context.

        Returns:
            Assistant response.
        """
        input_data = ConversationInput(
            message=message,
            history=self._history,
            system_context=self._system_context,
            max_history_messages=self._max_history,
        )

        result = await self._agent.run(input_data, context)
        if result.success and result.output:
            self._history = result.output.updated_history
            return result.output.response

        raise RuntimeError(result.error or "Conversation failed")

    async def stream_chat(
        self,
        message: str,
        context: AgentContext,
    ) -> AsyncIterator[str]:
        """Stream a chat response.

        Args:
            message: User message.
            context: Agent context.

        Yields:
            Response chunks.
        """
        input_data = ConversationInput(
            message=message,
            history=self._history,
            system_context=self._system_context,
            max_history_messages=self._max_history,
        )

        full_response = ""
        async for chunk in self._agent.stream(input_data, context):
            full_response += chunk
            yield chunk

        # Update history after streaming completes
        self._history.append(ConversationMessage(role=MessageRole.USER, content=message))
        self._history.append(
            ConversationMessage(role=MessageRole.ASSISTANT, content=full_response)
        )

        # Trim history if needed
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]


__all__ = [
    "ConversationAgent",
    "ConversationInput",
    "ConversationManager",
    "ConversationMessage",
    "ConversationOutput",
    "MessageRole",
]
