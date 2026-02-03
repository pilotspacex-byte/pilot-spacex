"""Unit tests for Phase 2 SDK features: Code Execution (T61), Streaming Input (T62).

Tests verify SDKConfiguration correctly handles code_execution_enabled and
streaming_input_mode flags, and that _estimate_tokens produces accurate
token counts for streaming input auto-detection.

References:
- T61: Sandboxed code execution via CodeExecution tool
- T62: Streaming input mode for large document contexts
"""

from __future__ import annotations

from pathlib import Path

from pilot_space.ai.agents.pilotspace_agent import ChatInput, _estimate_tokens
from pilot_space.ai.sdk.sandbox_config import configure_sdk_for_space
from pilot_space.spaces.base import SpaceContext


class TestCodeExecutionConfig:
    """T61: CodeExecution tool and code_execution SDK param."""

    def test_code_execution_adds_tool_to_allowed_tools(self, tmp_path: Path) -> None:
        """CodeExecution tool added to allowed_tools when enabled."""
        space_context = SpaceContext(
            id="test-code-exec-001",
            path=tmp_path,
            env={},
        )

        config = configure_sdk_for_space(
            space_context,
            code_execution_enabled=True,
        )

        assert "CodeExecution" in config.allowed_tools

    def test_code_execution_disabled_by_default(self, tmp_path: Path) -> None:
        """CodeExecution tool NOT in allowed_tools by default."""
        space_context = SpaceContext(
            id="test-code-exec-002",
            path=tmp_path,
            env={},
        )

        config = configure_sdk_for_space(space_context)

        assert "CodeExecution" not in config.allowed_tools

    def test_code_execution_to_sdk_params(self, tmp_path: Path) -> None:
        """to_sdk_params() includes code_execution=True when enabled."""
        space_context = SpaceContext(
            id="test-code-exec-003",
            path=tmp_path,
            env={},
        )

        config = configure_sdk_for_space(
            space_context,
            code_execution_enabled=True,
        )
        params = config.to_sdk_params()

        assert params["code_execution"] is True

    def test_code_execution_omitted_when_disabled(self, tmp_path: Path) -> None:
        """to_sdk_params() does NOT contain code_execution key when disabled."""
        space_context = SpaceContext(
            id="test-code-exec-004",
            path=tmp_path,
            env={},
        )

        config = configure_sdk_for_space(
            space_context,
            code_execution_enabled=False,
        )
        params = config.to_sdk_params()

        assert "code_execution" not in params


class TestStreamingInputMode:
    """T62: Streaming input SDK param for large document contexts."""

    def test_streaming_input_to_sdk_params(self, tmp_path: Path) -> None:
        """to_sdk_params() includes streaming_input=True when enabled."""
        space_context = SpaceContext(
            id="test-streaming-001",
            path=tmp_path,
            env={},
        )

        config = configure_sdk_for_space(
            space_context,
            streaming_input_mode=True,
        )
        params = config.to_sdk_params()

        assert params["streaming_input"] is True

    def test_streaming_input_omitted_when_disabled(self, tmp_path: Path) -> None:
        """to_sdk_params() does NOT contain streaming_input key by default."""
        space_context = SpaceContext(
            id="test-streaming-002",
            path=tmp_path,
            env={},
        )

        config = configure_sdk_for_space(space_context)
        params = config.to_sdk_params()

        assert "streaming_input" not in params


class TestEstimateTokens:
    """T62: Token estimation for streaming input auto-detection."""

    def test_estimate_tokens_small_message(self) -> None:
        """Short message (100 chars) estimates ~25 tokens."""
        # 100 chars / 4 chars per token = 25 tokens
        input_data = ChatInput(message="x" * 100)

        result = _estimate_tokens(input_data)

        assert result == 25

    def test_estimate_tokens_large_context(self) -> None:
        """Message with large context values exceeds 30K token threshold."""
        # 150_000 chars / 4 = 37_500 tokens (> 30_000 threshold)
        input_data = ChatInput(
            message="Analyze this document",
            context={"document": "a" * 150_000},
        )

        result = _estimate_tokens(input_data)

        assert result > 30_000

    def test_estimate_tokens_empty_context(self) -> None:
        """Empty context dict counts only message tokens."""
        message = "Hello, how are you?"  # 19 chars -> 4 tokens
        input_data = ChatInput(message=message, context={})

        result = _estimate_tokens(input_data)

        assert result == len(message) // 4
