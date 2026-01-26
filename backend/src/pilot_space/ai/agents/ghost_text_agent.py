"""Ghost text agent for inline text suggestions using Claude Agent SDK.

Provides real-time text completions with <2s latency target using Claude Haiku.
Implements DD-067 word boundary truncation and graceful degradation.

Architecture:
- Extends StreamingSDKBaseAgent for streaming support
- Uses claude-3-5-haiku for fast responses (<2s target)
- Detects code vs prose context for appropriate prompting
- Truncates at word boundaries per DD-067
- Returns empty suggestion on timeout/error (graceful degradation)

T044-T049: GhostTextAgent migration to Claude Agent SDK.
"""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from anthropic import AsyncAnthropic

from pilot_space.ai.agents.sdk_base import (
    AgentContext,
    StreamingSDKBaseAgent,
)
from pilot_space.ai.prompts.ghost_text import (
    GHOST_TEXT_CODE_SYSTEM_PROMPT,
    GHOST_TEXT_SYSTEM_PROMPT,
    GhostTextPromptConfig,
    build_code_ghost_text_prompt,
    build_ghost_text_prompt,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from pilot_space.ai.infrastructure.cost_tracker import CostTracker
    from pilot_space.ai.infrastructure.resilience import ResilientExecutor
    from pilot_space.ai.providers.provider_selector import ProviderSelector
    from pilot_space.ai.tools.mcp_server import ToolRegistry

logger = logging.getLogger(__name__)


@dataclass
class GhostTextInput:
    """Input for ghost text generation.

    Attributes:
        current_text: The text being typed.
        cursor_position: Position of cursor in the text.
        context: Previous paragraphs for context.
        language: Programming language (for code context).
        is_code: Whether content is code-related.
    """

    current_text: str
    cursor_position: int
    context: str | None = None
    language: str | None = None
    is_code: bool = False


@dataclass
class GhostTextOutput:
    """Output from ghost text generation.

    Attributes:
        suggestion: The completion suggestion.
        cursor_offset: Offset to apply after accepting.
        is_empty: Whether suggestion is empty.
    """

    suggestion: str
    cursor_offset: int = 0
    is_empty: bool = False

    @classmethod
    def empty(cls) -> GhostTextOutput:
        """Create empty suggestion."""
        return cls(suggestion="", cursor_offset=0, is_empty=True)


class GhostTextAgent(StreamingSDKBaseAgent[GhostTextInput, str]):
    """Ghost Text Agent for real-time text suggestions.

    Provides inline text completions with <2s latency target.
    Uses claude-3-5-haiku for fast responses.

    Features:
    - Code vs prose context detection
    - Word boundary truncation (DD-067)
    - Empty fallback on timeout/error
    - Streaming output

    Architecture:
    - Extends StreamingSDKBaseAgent for streaming support
    - Uses Anthropic Python SDK directly (not Claude Agent SDK query)
    - Implements timeout with asyncio.timeout
    - Graceful degradation on all errors

    Usage:
        agent = GhostTextAgent(...)
        result = await agent.run(input_data, context)
        # Or streaming:
        async for chunk in agent.run_stream(input_data, context):
            process(chunk)
    """

    AGENT_NAME = "ghost_text"
    DEFAULT_MODEL = "claude-3-5-haiku-20241022"
    MAX_TOKENS = 50
    TIMEOUT_MS = 2000

    def __init__(
        self,
        tool_registry: ToolRegistry,
        provider_selector: ProviderSelector,
        cost_tracker: CostTracker,
        resilient_executor: ResilientExecutor,
        max_tokens: int = MAX_TOKENS,
        timeout_ms: int = TIMEOUT_MS,
    ) -> None:
        """Initialize ghost text agent.

        Args:
            tool_registry: Registry for MCP tool access
            provider_selector: Provider/model selection service
            cost_tracker: Cost tracking service
            resilient_executor: Retry and circuit breaker service
            max_tokens: Maximum tokens in completion (default 50)
            timeout_ms: Timeout in milliseconds (default 2000)
        """
        super().__init__(
            tool_registry=tool_registry,
            provider_selector=provider_selector,
            cost_tracker=cost_tracker,
            resilient_executor=resilient_executor,
        )
        self._max_tokens = min(max_tokens, self.MAX_TOKENS)
        self._timeout_ms = timeout_ms
        self._prompt_config = GhostTextPromptConfig(max_output_tokens=self._max_tokens)

    def get_model(self) -> tuple[str, str]:
        """Get provider and model for ghost text.

        Returns:
            Tuple of ("anthropic", "claude-3-5-haiku-20241022")
        """
        return ("anthropic", self.DEFAULT_MODEL)

    def _validate_input(self, input_data: GhostTextInput) -> None:
        """Validate input before processing.

        Args:
            input_data: The input to validate.

        Raises:
            ValueError: If input is invalid.
        """
        if not input_data.current_text:
            raise ValueError("current_text cannot be empty")

        if input_data.cursor_position < 0:
            raise ValueError("cursor_position must be non-negative")

        if input_data.cursor_position > len(input_data.current_text):
            raise ValueError("cursor_position exceeds text length")

    def _build_prompt(self, input_data: GhostTextInput) -> tuple[str, str]:
        """Build system and user prompts based on content type.

        Args:
            input_data: Ghost text input.

        Returns:
            Tuple of (system_prompt, user_prompt)
        """
        if input_data.is_code:
            system_prompt = GHOST_TEXT_CODE_SYSTEM_PROMPT
            user_prompt = build_code_ghost_text_prompt(
                current_text=input_data.current_text,
                cursor_position=input_data.cursor_position,
                language=input_data.language,
                context=input_data.context,
                config=self._prompt_config,
            )
        else:
            system_prompt = GHOST_TEXT_SYSTEM_PROMPT
            user_prompt = build_ghost_text_prompt(
                current_text=input_data.current_text,
                cursor_position=input_data.cursor_position,
                context=input_data.context,
                config=self._prompt_config,
            )

        return system_prompt, user_prompt

    def _truncate_at_word_boundary(self, text: str) -> str:
        """Truncate text at word boundary per DD-067.

        Ensures suggestions don't end mid-word for better UX.

        Args:
            text: Text to truncate.

        Returns:
            Text truncated at last word boundary.
        """
        if not text:
            return text

        # Max characters based on token limit (~4 chars per token)
        max_chars = self._max_tokens * 4

        if len(text) <= max_chars:
            return text

        # Truncate to max_chars
        truncated = text[:max_chars]

        # Find last word boundary (space, punctuation, or newline)
        # Use regex to find last word boundary
        match = re.search(r"[\s\.,;:\-\)\]\}\n]+[^\s]*$", truncated)

        if match and match.start() > max_chars // 2:
            # Found boundary in second half, use it
            return truncated[: match.start()].rstrip()

        # No good boundary found, use simple space split
        last_space = truncated.rfind(" ")
        if last_space > max_chars // 2:
            return truncated[:last_space]

        # Last resort: use full truncated text
        return truncated

    def _clean_suggestion(self, text: str) -> str:
        """Clean up suggestion text.

        Removes common artifacts and formatting issues.

        Args:
            text: Raw suggestion text.

        Returns:
            Cleaned suggestion text.
        """
        if not text:
            return ""

        suggestion = text.strip()

        # Remove quotes if the entire suggestion is quoted
        if (suggestion.startswith('"') and suggestion.endswith('"')) or (
            suggestion.startswith("'") and suggestion.endswith("'")
        ):
            suggestion = suggestion[1:-1].strip()

        # Remove common prefixes that Claude might add
        prefixes_to_remove = [
            "Here's the completion:",
            "Completion:",
            "Suggestion:",
            "...",
        ]
        for prefix in prefixes_to_remove:
            if suggestion.lower().startswith(prefix.lower()):
                suggestion = suggestion[len(prefix) :].strip()

        # Apply word boundary truncation and return
        return self._truncate_at_word_boundary(suggestion)

    async def stream(
        self,
        input_data: GhostTextInput,
        context: AgentContext,
    ) -> AsyncIterator[str]:
        """Stream ghost text tokens as they're generated.

        Implements timeout and graceful degradation per DD-067.

        Args:
            input_data: Ghost text input.
            context: Execution context.

        Yields:
            Output tokens/chunks as strings.

        Note:
            On timeout or error, yields empty string (graceful degradation).
        """
        try:
            # Validate input
            self._validate_input(input_data)

            # Get API key from context
            # For SDK agents, we need to get keys from infrastructure
            # This is a placeholder - actual implementation will use key_storage
            api_key = context.metadata.get("anthropic_api_key")
            if not api_key:
                logger.warning(
                    "No Anthropic API key in context",
                    extra={"context": context},
                )
                return

            # Build prompts
            system_prompt, user_prompt = self._build_prompt(input_data)

            # Create Anthropic client
            client = AsyncAnthropic(api_key=api_key)

            # Stream with timeout
            timeout_seconds = self._timeout_ms / 1000.0

            async with asyncio.timeout(timeout_seconds):
                # Track metrics
                accumulated = []
                input_tokens = 0
                output_tokens = 0

                async with client.messages.stream(
                    model=self.DEFAULT_MODEL,
                    max_tokens=self._max_tokens,
                    temperature=0.3,  # Lower temperature for consistent completions
                    system=system_prompt,
                    messages=[
                        {
                            "role": "user",
                            "content": user_prompt,
                        }
                    ],
                ) as stream:
                    async for event in stream:
                        # Track token usage
                        if hasattr(event, "message"):
                            msg = event.message  # type: ignore[attr-defined]
                            if hasattr(msg, "usage"):
                                input_tokens = msg.usage.input_tokens  # type: ignore[union-attr]
                                output_tokens = msg.usage.output_tokens  # type: ignore[union-attr]

                        # Yield text chunks
                        if event.type == "content_block_delta":
                            delta_event: Any = event
                            if hasattr(delta_event, "delta") and hasattr(delta_event.delta, "text"):
                                chunk = delta_event.delta.text
                                accumulated.append(chunk)
                                yield chunk

                # Track usage after streaming completes
                if input_tokens or output_tokens:
                    await self.track_usage(
                        context=context,
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                    )

        except TimeoutError:
            logger.info(
                "Ghost text timeout",
                extra={
                    "timeout_ms": self._timeout_ms,
                    "workspace_id": context.workspace_id,
                },
            )
            # Graceful degradation: yield empty
            return

        except Exception as e:
            logger.warning(
                "Ghost text generation failed",
                extra={
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "workspace_id": context.workspace_id,
                },
            )
            # Graceful degradation: yield empty
            return

    async def execute(
        self,
        input_data: GhostTextInput,
        context: AgentContext,
    ) -> str:
        """Execute ghost text generation (non-streaming).

        Collects all streamed chunks and returns cleaned suggestion.

        Args:
            input_data: Ghost text input.
            context: Execution context.

        Returns:
            Cleaned suggestion text (empty string on error).
        """
        chunks: list[str] = []
        async for chunk in self.stream(input_data, context):
            chunks.append(chunk)

        raw_suggestion = "".join(chunks)
        return self._clean_suggestion(raw_suggestion)


class GhostTextStreamingAgent(GhostTextAgent):
    """Alias for GhostTextAgent (already supports streaming).

    This class exists for backward compatibility.
    GhostTextAgent already extends StreamingSDKBaseAgent.
    """


__all__ = [
    "GhostTextAgent",
    "GhostTextInput",
    "GhostTextOutput",
    "GhostTextStreamingAgent",
]
