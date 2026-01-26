"""Unit tests for MarginAnnotationAgentSDK.

T071: Unit tests for SDK-based margin annotation agent.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from pilot_space.ai.agents.margin_annotation_agent_sdk import (
    Annotation,
    AnnotationType,
    MarginAnnotationAgentSDK,
    MarginAnnotationInput,
    MarginAnnotationOutput,
)
from pilot_space.ai.agents.sdk_base import AgentContext

if TYPE_CHECKING:
    from pilot_space.ai.infrastructure.cost_tracker import CostTracker
    from pilot_space.ai.infrastructure.resilience import ResilientExecutor
    from pilot_space.ai.providers.provider_selector import ProviderSelector
    from pilot_space.ai.tools.mcp_server import ToolRegistry


@pytest.fixture
def mock_tool_registry() -> ToolRegistry:
    """Mock tool registry."""
    return MagicMock()


@pytest.fixture
def mock_provider_selector() -> ProviderSelector:
    """Mock provider selector."""
    return MagicMock()


@pytest.fixture
def mock_cost_tracker() -> CostTracker:
    """Mock cost tracker."""
    tracker = MagicMock()
    tracker.track = AsyncMock(return_value=MagicMock(cost_usd=0.001))
    return tracker


@pytest.fixture
def mock_resilient_executor() -> ResilientExecutor:
    """Mock resilient executor."""
    executor = MagicMock()
    executor.execute = AsyncMock(side_effect=lambda **kwargs: kwargs["operation"]())
    return executor


@pytest.fixture
def agent(
    mock_tool_registry: ToolRegistry,
    mock_provider_selector: ProviderSelector,
    mock_cost_tracker: CostTracker,
    mock_resilient_executor: ResilientExecutor,
) -> MarginAnnotationAgentSDK:
    """Create agent instance."""
    return MarginAnnotationAgentSDK(
        tool_registry=mock_tool_registry,
        provider_selector=mock_provider_selector,
        cost_tracker=mock_cost_tracker,
        resilient_executor=mock_resilient_executor,
    )


@pytest.fixture
def context() -> AgentContext:
    """Create agent context."""
    return AgentContext(
        workspace_id=uuid4(),
        user_id=uuid4(),
    )


class TestMarginAnnotationAgentSDK:
    """Test suite for MarginAnnotationAgentSDK."""

    @pytest.mark.asyncio
    async def test_generates_annotations_for_blocks(
        self,
        agent: MarginAnnotationAgentSDK,
        context: AgentContext,
    ) -> None:
        """Verify agent generates annotations for specified blocks."""
        # Arrange
        input_data = MarginAnnotationInput(
            note_id=uuid4(),
            block_ids=["block-1", "block-2"],
            context_blocks=3,
        )

        # Create mock response with anthropic format
        mock_text_block = MagicMock()
        mock_text_block.text = """
        {
            "annotations": [
                {
                    "block_id": "block-1",
                    "type": "suggestion",
                    "title": "Add examples",
                    "content": "Consider adding code examples",
                    "confidence": 0.8
                },
                {
                    "block_id": "block-2",
                    "type": "warning",
                    "title": "Check syntax",
                    "content": "Verify JSON syntax is correct",
                    "confidence": 0.9,
                    "action_label": "Validate"
                }
            ]
        }
        """
        mock_response = MagicMock()
        mock_response.content = [mock_text_block]

        with patch("anthropic.AsyncAnthropic") as mock_anthropic:
            mock_client = MagicMock()
            mock_client.messages.create = AsyncMock(return_value=mock_response)
            mock_anthropic.return_value = mock_client

            with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
                # Act
                result = await agent.execute(input_data, context)

                # Assert
                assert isinstance(result, MarginAnnotationOutput)
                assert len(result.annotations) == 2
                assert result.processed_blocks == 2

                # Check first annotation
                assert result.annotations[0].block_id == "block-1"
                assert result.annotations[0].type == AnnotationType.SUGGESTION
                assert result.annotations[0].title == "Add examples"
                assert result.annotations[0].confidence == 0.8
                assert result.annotations[0].action_label is None

                # Check second annotation
                assert result.annotations[1].block_id == "block-2"
                assert result.annotations[1].type == AnnotationType.WARNING
                assert result.annotations[1].confidence == 0.9
                assert result.annotations[1].action_label == "Validate"

                # Verify anthropic was called
                mock_client.messages.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_handles_empty_annotations_response(
        self,
        agent: MarginAnnotationAgentSDK,
        context: AgentContext,
    ) -> None:
        """Verify agent handles empty annotations gracefully."""
        # Arrange
        input_data = MarginAnnotationInput(
            note_id=uuid4(),
            block_ids=["block-1"],
        )

        mock_text_block = MagicMock()
        mock_text_block.text = '{"annotations": []}'
        mock_response = MagicMock()
        mock_response.content = [mock_text_block]

        with patch("anthropic.AsyncAnthropic") as mock_anthropic:
            mock_client = MagicMock()
            mock_client.messages.create = AsyncMock(return_value=mock_response)
            mock_anthropic.return_value = mock_client

            with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
                # Act
                result = await agent.execute(input_data, context)

                # Assert
                assert isinstance(result, MarginAnnotationOutput)
                assert len(result.annotations) == 0
                assert result.processed_blocks == 1

    @pytest.mark.asyncio
    async def test_handles_markdown_json_response(
        self,
        agent: MarginAnnotationAgentSDK,
        context: AgentContext,
    ) -> None:
        """Verify agent extracts JSON from markdown code blocks."""
        # Arrange
        input_data = MarginAnnotationInput(
            note_id=uuid4(),
            block_ids=["block-1"],
        )

        mock_text_block = MagicMock()
        mock_text_block.text = """Here are the annotations:

```json
{
    "annotations": [
        {
            "block_id": "block-1",
            "type": "insight",
            "title": "Related pattern",
            "content": "Similar to repository pattern",
            "confidence": 0.75
        }
    ]
}
```
"""
        mock_response = MagicMock()
        mock_response.content = [mock_text_block]

        with patch("anthropic.AsyncAnthropic") as mock_anthropic:
            mock_client = MagicMock()
            mock_client.messages.create = AsyncMock(return_value=mock_response)
            mock_anthropic.return_value = mock_client

            with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
                # Act
                result = await agent.execute(input_data, context)

                # Assert
                assert len(result.annotations) == 1
                assert result.annotations[0].type == AnnotationType.INSIGHT

    @pytest.mark.asyncio
    async def test_skips_malformed_annotations(
        self,
        agent: MarginAnnotationAgentSDK,
        context: AgentContext,
    ) -> None:
        """Verify agent skips malformed annotations without failing."""
        # Arrange
        input_data = MarginAnnotationInput(
            note_id=uuid4(),
            block_ids=["block-1", "block-2"],
        )

        mock_text_block = MagicMock()
        mock_text_block.text = """
        {
            "annotations": [
                {
                    "block_id": "block-1",
                    "type": "suggestion",
                    "title": "Valid annotation",
                    "content": "This is valid",
                    "confidence": 0.8
                },
                {
                    "type": "invalid"
                },
                {
                    "block_id": "block-2",
                    "type": "question",
                    "title": "Another valid one",
                    "content": "Also valid",
                    "confidence": 0.7
                }
            ]
        }
        """
        mock_response = MagicMock()
        mock_response.content = [mock_text_block]

        with patch("anthropic.AsyncAnthropic") as mock_anthropic:
            mock_client = MagicMock()
            mock_client.messages.create = AsyncMock(return_value=mock_response)
            mock_anthropic.return_value = mock_client

            with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
                # Act
                result = await agent.execute(input_data, context)

                # Assert
                assert len(result.annotations) == 2  # Only valid ones
                assert result.annotations[0].block_id == "block-1"
                assert result.annotations[1].block_id == "block-2"

    @pytest.mark.asyncio
    async def test_validates_input_empty_block_ids(
        self,
        agent: MarginAnnotationAgentSDK,
        context: AgentContext,
    ) -> None:
        """Verify agent raises error for empty block_ids."""
        # Arrange
        input_data = MarginAnnotationInput(
            note_id=uuid4(),
            block_ids=[],
        )

        # Act & Assert
        with pytest.raises(ValueError, match="block_ids cannot be empty"):
            await agent.execute(input_data, context)

    @pytest.mark.asyncio
    async def test_validates_input_too_many_blocks(
        self,
        agent: MarginAnnotationAgentSDK,
        context: AgentContext,
    ) -> None:
        """Verify agent raises error for too many blocks."""
        # Arrange
        input_data = MarginAnnotationInput(
            note_id=uuid4(),
            block_ids=[f"block-{i}" for i in range(25)],  # More than 20
        )

        # Act & Assert
        with pytest.raises(ValueError, match="Cannot annotate more than 20 blocks"):
            await agent.execute(input_data, context)

    @pytest.mark.asyncio
    async def test_handles_invalid_json_response(
        self,
        agent: MarginAnnotationAgentSDK,
        context: AgentContext,
    ) -> None:
        """Verify agent handles invalid JSON gracefully."""
        # Arrange
        input_data = MarginAnnotationInput(
            note_id=uuid4(),
            block_ids=["block-1"],
        )

        mock_text_block = MagicMock()
        mock_text_block.text = "This is not JSON at all"
        mock_response = MagicMock()
        mock_response.content = [mock_text_block]

        with patch("anthropic.AsyncAnthropic") as mock_anthropic:
            mock_client = MagicMock()
            mock_client.messages.create = AsyncMock(return_value=mock_response)
            mock_anthropic.return_value = mock_client

            with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
                # Act
                result = await agent.execute(input_data, context)

                # Assert
                assert len(result.annotations) == 0  # Empty result, not error

    @pytest.mark.asyncio
    async def test_builds_correct_prompt(
        self,
        agent: MarginAnnotationAgentSDK,
        context: AgentContext,
    ) -> None:
        """Verify agent builds correct prompt structure."""
        # Arrange
        note_id = uuid4()
        block_ids = ["block-1", "block-2", "block-3"]
        input_data = MarginAnnotationInput(
            note_id=note_id,
            block_ids=block_ids,
            context_blocks=5,
        )

        mock_text_block = MagicMock()
        mock_text_block.text = '{"annotations": []}'
        mock_response = MagicMock()
        mock_response.content = [mock_text_block]

        with patch("anthropic.AsyncAnthropic") as mock_anthropic:
            mock_client = MagicMock()
            mock_client.messages.create = AsyncMock(return_value=mock_response)
            mock_anthropic.return_value = mock_client

            with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
                # Act
                await agent.execute(input_data, context)

                # Assert
                call_args = mock_client.messages.create.call_args
                # Check messages argument
                messages_arg = call_args.kwargs["messages"]
                user_message = messages_arg[0]["content"]
                assert str(note_id) in user_message
                assert "block-1" in user_message
                assert "block-2" in user_message
                assert "block-3" in user_message
                assert "5" in user_message  # context_blocks

    @pytest.mark.asyncio
    async def test_includes_action_payload_when_present(
        self,
        agent: MarginAnnotationAgentSDK,
        context: AgentContext,
    ) -> None:
        """Verify agent parses action_payload when present."""
        # Arrange
        input_data = MarginAnnotationInput(
            note_id=uuid4(),
            block_ids=["block-1"],
        )

        mock_text_block = MagicMock()
        mock_text_block.text = """
        {
            "annotations": [
                {
                    "block_id": "block-1",
                    "type": "reference",
                    "title": "See documentation",
                    "content": "Related docs available",
                    "confidence": 0.85,
                    "action_label": "Open docs",
                    "action_payload": {"url": "https://docs.example.com"}
                }
            ]
        }
        """
        mock_response = MagicMock()
        mock_response.content = [mock_text_block]

        with patch("anthropic.AsyncAnthropic") as mock_anthropic:
            mock_client = MagicMock()
            mock_client.messages.create = AsyncMock(return_value=mock_response)
            mock_anthropic.return_value = mock_client

            with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
                # Act
                result = await agent.execute(input_data, context)

                # Assert
                assert len(result.annotations) == 1
                annotation = result.annotations[0]
                assert annotation.action_label == "Open docs"
                assert annotation.action_payload == {"url": "https://docs.example.com"}


class TestAnnotationDataclass:
    """Test Annotation dataclass."""

    def test_annotation_is_immutable(self) -> None:
        """Verify Annotation instances are immutable."""
        annotation = Annotation(
            block_id="block-1",
            type=AnnotationType.SUGGESTION,
            title="Test",
            content="Content",
            confidence=0.8,
        )

        with pytest.raises(AttributeError):
            annotation.title = "New title"  # type: ignore[misc]

    def test_annotation_has_slots(self) -> None:
        """Verify Annotation uses slots for memory efficiency."""
        annotation = Annotation(
            block_id="block-1",
            type=AnnotationType.SUGGESTION,
            title="Test",
            content="Content",
            confidence=0.8,
        )

        # Should not have __dict__ due to slots
        assert not hasattr(annotation, "__dict__")
