"""Ghost text agent for inline text suggestions.

Uses Gemini Flash for low-latency (<500ms target) completions.
Provides Tab-to-accept inline suggestions while typing.

T084: GhostTextAgent implementation.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import google.generativeai as genai  # type: ignore[import-untyped]

from pilot_space.ai.agents.base import (
    AgentContext,
    AgentResult,
    BaseAgent,
    Provider,
    TaskType,
)
from pilot_space.ai.exceptions import (
    AIConfigurationError,
    RateLimitError,
)
from pilot_space.ai.prompts.ghost_text import (
    GHOST_TEXT_CODE_SYSTEM_PROMPT,
    GHOST_TEXT_SYSTEM_PROMPT,
    GhostTextPromptConfig,
    build_code_ghost_text_prompt,
    build_ghost_text_prompt,
)
from pilot_space.ai.telemetry import AIOperation
from pilot_space.ai.utils.retry import RetryConfig

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


class GhostTextAgent(BaseAgent[GhostTextInput, GhostTextOutput]):
    """Agent for generating ghost text completions.

    Uses Gemini Flash for sub-500ms latency target.
    Rate limited to 10 requests/minute per user.

    Attributes:
        task_type: LATENCY_SENSITIVE for Gemini routing.
        operation: GHOST_TEXT for telemetry.
        max_output_tokens: Maximum tokens in completion.
    """

    task_type = TaskType.LATENCY_SENSITIVE
    operation = AIOperation.GHOST_TEXT
    retry_config = RetryConfig(max_retries=1, initial_delay_seconds=0.5)

    # Gemini Flash model for low latency
    DEFAULT_MODEL = "gemini-2.0-flash"
    MAX_OUTPUT_TOKENS = 50

    def __init__(
        self,
        model: str | None = None,
        max_output_tokens: int = 50,
    ) -> None:
        """Initialize ghost text agent.

        Args:
            model: Override default Gemini model.
            max_output_tokens: Maximum tokens in completion.
        """
        super().__init__(model or self.DEFAULT_MODEL)
        self.max_output_tokens = min(max_output_tokens, self.MAX_OUTPUT_TOKENS)
        self._prompt_config = GhostTextPromptConfig(max_output_tokens=self.max_output_tokens)

    def validate_input(self, input_data: GhostTextInput) -> None:
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

    async def _execute_impl(
        self,
        input_data: GhostTextInput,
        context: AgentContext,
    ) -> AgentResult[GhostTextOutput]:
        """Execute ghost text generation.

        Args:
            input_data: Ghost text input.
            context: Agent execution context.

        Returns:
            AgentResult with ghost text output.
        """
        self.validate_input(input_data)

        # Get API key for Gemini
        api_key = context.get_api_key(Provider.GEMINI)
        if not api_key:
            raise AIConfigurationError(
                "Google API key not configured for ghost text",
                provider="google",
                missing_fields=["api_key"],
            )

        # Configure Gemini
        genai.configure(api_key=api_key)  # pyright: ignore[reportUnknownMemberType,reportPrivateImportUsage]

        # Build prompt based on content type
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

        # Call Gemini
        try:
            model = genai.GenerativeModel(  # pyright: ignore[reportPrivateImportUsage]
                model_name=self.model,
                system_instruction=system_prompt,
                generation_config=genai.GenerationConfig(  # pyright: ignore[reportPrivateImportUsage]
                    max_output_tokens=self.max_output_tokens,
                    temperature=0.3,  # Lower temperature for more consistent completions
                    top_p=0.9,
                ),
            )

            response = await model.generate_content_async(  # pyright: ignore[reportUnknownMemberType]
                user_prompt,
                request_options={"timeout": 5},  # 5 second timeout
            )

            # Extract suggestion
            suggestion = self._extract_suggestion(response)

            # Calculate token usage (approximate for Gemini)
            input_tokens = len(user_prompt.split()) * 1.3  # Rough estimate
            output_tokens = len(suggestion.split()) * 1.3 if suggestion else 0

            return AgentResult(
                output=GhostTextOutput(
                    suggestion=suggestion,
                    cursor_offset=len(suggestion),
                    is_empty=not suggestion,
                ),
                input_tokens=int(input_tokens),
                output_tokens=int(output_tokens),
                model=self.model,
                provider=Provider.GEMINI,
            )

        except Exception as e:
            error_str = str(e).lower()

            if "rate" in error_str or "quota" in error_str:
                raise RateLimitError(
                    "Gemini rate limit exceeded",
                    retry_after_seconds=60,
                    provider="google",
                ) from e

            logger.warning(
                "Ghost text generation failed",
                extra={
                    "error": str(e),
                    "correlation_id": context.correlation_id,
                },
            )

            # Return empty suggestion on error (graceful degradation)
            return AgentResult(
                output=GhostTextOutput.empty(),
                model=self.model,
                provider=Provider.GEMINI,
            )

    def _extract_suggestion(self, response: Any) -> str:
        """Extract suggestion text from Gemini response.

        Args:
            response: Gemini API response.

        Returns:
            Cleaned suggestion text.
        """
        if not response or not response.text:
            return ""

        suggestion = response.text.strip()

        # Clean up common artifacts
        # Remove quotes if the entire suggestion is quoted
        if suggestion.startswith('"') and suggestion.endswith('"'):
            suggestion = suggestion[1:-1]
        if suggestion.startswith("'") and suggestion.endswith("'"):
            suggestion = suggestion[1:-1]

        # Remove common prefixes
        prefixes_to_remove = [
            "Here's the completion:",
            "Completion:",
            "Suggestion:",
            "...",
        ]
        for prefix in prefixes_to_remove:
            if suggestion.startswith(prefix):
                suggestion = suggestion[len(prefix) :].strip()

        # Limit length (safety check)
        max_chars = self.max_output_tokens * 4  # ~4 chars per token
        if len(suggestion) > max_chars:
            # Find last word boundary
            truncated = suggestion[:max_chars]
            last_space = truncated.rfind(" ")
            suggestion = truncated[:last_space] if last_space > max_chars // 2 else truncated

        return suggestion


class GhostTextStreamingAgent(GhostTextAgent):
    """Ghost text agent with streaming support.

    Streams tokens as they're generated for perceived latency improvement.
    """

    async def stream(
        self,
        input_data: GhostTextInput,
        context: AgentContext,
    ):
        """Stream ghost text tokens.

        Args:
            input_data: Ghost text input.
            context: Agent execution context.

        Yields:
            Tokens as they're generated.
        """
        self.validate_input(input_data)

        api_key = context.get_api_key(Provider.GEMINI)
        if not api_key:
            raise AIConfigurationError(
                "Google API key not configured",
                provider="google",
            )

        genai.configure(api_key=api_key)  # pyright: ignore[reportUnknownMemberType,reportPrivateImportUsage]

        # Build prompt
        if input_data.is_code:
            system_prompt = GHOST_TEXT_CODE_SYSTEM_PROMPT
            user_prompt = build_code_ghost_text_prompt(
                current_text=input_data.current_text,
                cursor_position=input_data.cursor_position,
                language=input_data.language,
                context=input_data.context,
            )
        else:
            system_prompt = GHOST_TEXT_SYSTEM_PROMPT
            user_prompt = build_ghost_text_prompt(
                current_text=input_data.current_text,
                cursor_position=input_data.cursor_position,
                context=input_data.context,
            )

        model = genai.GenerativeModel(  # pyright: ignore[reportPrivateImportUsage]
            model_name=self.model,
            system_instruction=system_prompt,
            generation_config=genai.GenerationConfig(  # pyright: ignore[reportPrivateImportUsage]
                max_output_tokens=self.max_output_tokens,
                temperature=0.3,
            ),
        )

        # Stream response
        response = await model.generate_content_async(  # pyright: ignore[reportUnknownMemberType]
            user_prompt,
            stream=True,
        )

        async for chunk in response:
            if chunk.text:
                yield chunk.text


__all__ = [
    "GhostTextAgent",
    "GhostTextInput",
    "GhostTextOutput",
    "GhostTextStreamingAgent",
]
