"""Unit tests for LAZY-04 token instrumentation.

Verifies that build_contextual_message and assemble_system_prompt
emit structured logs and Langfuse metadata for before/after comparison.
"""

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from pilot_space.ai.agents.pilotspace_agent import ChatInput
from pilot_space.ai.agents.pilotspace_agent_helpers import build_contextual_message


class TestContextualMessageInstrumentation:
    """Tests for structured logging in build_contextual_message."""

    def test_logs_context_mode_lazy(self) -> None:
        """build_contextual_message logs context_mode=lazy."""
        input_data = ChatInput(message="hello", context={})
        with patch(
            "pilot_space.ai.agents.pilotspace_agent_helpers.logger"
        ) as mock_logger:
            build_contextual_message(input_data)
            mock_logger.info.assert_called()
            call_kwargs = mock_logger.info.call_args.kwargs
            assert call_kwargs.get("context_mode") == "lazy"

    def test_logs_estimated_tokens(self) -> None:
        """build_contextual_message logs estimated_tokens as len//4."""
        input_data = ChatInput(message="a" * 100, context={})
        with patch(
            "pilot_space.ai.agents.pilotspace_agent_helpers.logger"
        ) as mock_logger:
            build_contextual_message(input_data)
            call_kwargs = mock_logger.info.call_args.kwargs
            assert call_kwargs.get("estimated_tokens") == 25  # 100 // 4

    def test_logs_has_active_context_when_present(self) -> None:
        """Logs has_active_context=True when note context is present."""
        note = SimpleNamespace(title="Test", content={})
        input_data = ChatInput(
            message="test", context={"note": note, "note_id": "abc-123"}
        )
        with patch(
            "pilot_space.ai.agents.pilotspace_agent_helpers.logger"
        ) as mock_logger:
            build_contextual_message(input_data)
            call_kwargs = mock_logger.info.call_args.kwargs
            assert call_kwargs.get("has_active_context") is True

    def test_logs_has_active_context_false_when_absent(self) -> None:
        """Logs has_active_context=False when no context entities."""
        input_data = ChatInput(message="hello", context={})
        with patch(
            "pilot_space.ai.agents.pilotspace_agent_helpers.logger"
        ) as mock_logger:
            build_contextual_message(input_data)
            call_kwargs = mock_logger.info.call_args.kwargs
            assert call_kwargs.get("has_active_context") is False

    def test_logs_has_selected_text_when_present(self) -> None:
        """Logs has_selected_text=True when selected_text in context."""
        input_data = ChatInput(
            message="test", context={"selected_text": "some selected text"}
        )
        with patch(
            "pilot_space.ai.agents.pilotspace_agent_helpers.logger"
        ) as mock_logger:
            build_contextual_message(input_data)
            call_kwargs = mock_logger.info.call_args.kwargs
            assert call_kwargs.get("has_selected_text") is True

    def test_logs_event_name_contextual_message_built(self) -> None:
        """build_contextual_message logs with event name contextual_message_built."""
        input_data = ChatInput(message="hello", context={})
        with patch(
            "pilot_space.ai.agents.pilotspace_agent_helpers.logger"
        ) as mock_logger:
            build_contextual_message(input_data)
            call_args = mock_logger.info.call_args.args
            assert call_args[0] == "contextual_message_built"


class TestPromptAssemblerInstrumentation:
    """Tests for @observe decorator and metadata on assemble_system_prompt."""

    @pytest.mark.asyncio
    async def test_observe_decorator_applied(self) -> None:
        """assemble_system_prompt has the @observe decorator."""
        from pilot_space.ai.prompt.prompt_assembler import assemble_system_prompt

        # The observe decorator wraps the function; check __wrapped__ attribute
        assert hasattr(assemble_system_prompt, "__wrapped__"), (
            "assemble_system_prompt should be decorated with @observe "
            "(missing __wrapped__ attribute)"
        )

    @pytest.mark.asyncio
    async def test_assembler_returns_estimated_tokens(self) -> None:
        """AssembledPrompt includes estimated_tokens > 0."""
        from pilot_space.ai.prompt.models import PromptLayerConfig
        from pilot_space.ai.prompt.prompt_assembler import assemble_system_prompt

        config = PromptLayerConfig(user_message="test")
        result = await assemble_system_prompt(config)
        assert result.estimated_tokens > 0

    @pytest.mark.asyncio
    async def test_langfuse_metadata_graceful_degradation(self) -> None:
        """Langfuse metadata recording does not raise when Langfuse is unconfigured."""
        from pilot_space.ai.prompt.models import PromptLayerConfig
        from pilot_space.ai.prompt.prompt_assembler import assemble_system_prompt

        config = PromptLayerConfig(user_message="test graceful degradation")
        # Should not raise even though Langfuse is not configured
        result = await assemble_system_prompt(config)
        assert result.estimated_tokens > 0
        assert len(result.layers_loaded) > 0

    @pytest.mark.asyncio
    async def test_assembler_result_has_context_mode_lazy_metadata(self) -> None:
        """Langfuse update_current_span is called with context_mode=lazy metadata."""
        from pilot_space.ai.prompt.models import PromptLayerConfig
        from pilot_space.ai.prompt.prompt_assembler import assemble_system_prompt

        config = PromptLayerConfig(user_message="test metadata")
        with patch(
            "langfuse.Langfuse",
        ) as mock_langfuse_cls:
            mock_client = mock_langfuse_cls.return_value
            result = await assemble_system_prompt(config)

            mock_client.update_current_span.assert_called_once()
            call_kwargs = mock_client.update_current_span.call_args.kwargs
            metadata = call_kwargs["metadata"]
            assert metadata["context_mode"] == "lazy"
            assert metadata["estimated_prompt_tokens"] == result.estimated_tokens
            assert isinstance(metadata["layers_loaded"], list)
            assert isinstance(metadata["rules_loaded"], list)
