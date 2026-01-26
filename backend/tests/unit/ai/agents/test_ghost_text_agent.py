"""Unit tests for GhostTextAgent.

Tests cover:
- Input validation
- Prompt building (code vs prose)
- Word boundary truncation (DD-067)
- Timeout handling
- Error handling and graceful degradation
- Streaming output
- Token usage tracking

T044-T049: GhostTextAgent test suite.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from pilot_space.ai.agents.ghost_text_agent import GhostTextAgent, GhostTextInput
from pilot_space.ai.agents.sdk_base import AgentContext


@pytest.fixture
def mock_tool_registry() -> AsyncMock:
    """Mock ToolRegistry."""
    return AsyncMock()


@pytest.fixture
def mock_provider_selector() -> AsyncMock:
    """Mock ProviderSelector."""
    selector = AsyncMock()
    selector.select.return_value = ("anthropic", "claude-3-5-haiku-20241022")
    return selector


@pytest.fixture
def mock_cost_tracker() -> AsyncMock:
    """Mock CostTracker."""
    tracker = AsyncMock()
    tracker.track.return_value = MagicMock(cost_usd=0.001)
    return tracker


@pytest.fixture
def mock_resilient_executor() -> AsyncMock:
    """Mock ResilientExecutor."""
    return AsyncMock()


@pytest.fixture
def agent(
    mock_tool_registry: AsyncMock,
    mock_provider_selector: AsyncMock,
    mock_cost_tracker: AsyncMock,
    mock_resilient_executor: AsyncMock,
) -> GhostTextAgent:
    """Create GhostTextAgent instance with mocked dependencies."""
    return GhostTextAgent(
        tool_registry=mock_tool_registry,
        provider_selector=mock_provider_selector,
        cost_tracker=mock_cost_tracker,
        resilient_executor=mock_resilient_executor,
    )


@pytest.fixture
def agent_context() -> AgentContext:
    """Create test AgentContext."""
    return AgentContext(
        workspace_id=uuid4(),
        user_id=uuid4(),
        metadata={"anthropic_api_key": "sk-ant-test-key"},
    )


class TestGhostTextAgentValidation:
    """Test input validation."""

    def test_validate_empty_text_raises_error(self, agent: GhostTextAgent) -> None:
        """Verify empty text is rejected."""
        input_data = GhostTextInput(current_text="", cursor_position=0)

        with pytest.raises(ValueError, match="current_text cannot be empty"):
            agent._validate_input(input_data)

    def test_validate_negative_cursor_position_raises_error(
        self, agent: GhostTextAgent
    ) -> None:
        """Verify negative cursor position is rejected."""
        input_data = GhostTextInput(current_text="Hello", cursor_position=-1)

        with pytest.raises(ValueError, match="cursor_position must be non-negative"):
            agent._validate_input(input_data)

    def test_validate_cursor_exceeds_length_raises_error(
        self, agent: GhostTextAgent
    ) -> None:
        """Verify cursor position beyond text length is rejected."""
        input_data = GhostTextInput(current_text="Hello", cursor_position=10)

        with pytest.raises(ValueError, match="cursor_position exceeds text length"):
            agent._validate_input(input_data)

    def test_validate_valid_input_passes(self, agent: GhostTextAgent) -> None:
        """Verify valid input passes validation."""
        input_data = GhostTextInput(current_text="Hello world", cursor_position=5)

        # Should not raise
        agent._validate_input(input_data)


class TestGhostTextAgentPrompts:
    """Test prompt building."""

    def test_build_prose_prompt(self, agent: GhostTextAgent) -> None:
        """Verify prose prompt is built correctly."""
        input_data = GhostTextInput(
            current_text="The project will",
            cursor_position=16,
            context="We are building a new feature.",
            is_code=False,
        )

        system_prompt, user_prompt = agent._build_prompt(input_data)

        assert "writing assistant" in system_prompt.lower()
        assert "The project will" in user_prompt
        assert "We are building a new feature." in user_prompt

    def test_build_code_prompt(self, agent: GhostTextAgent) -> None:
        """Verify code prompt is built correctly."""
        input_data = GhostTextInput(
            current_text="def calculate_sum(",
            cursor_position=17,
            context="# Utility functions\n",
            language="python",
            is_code=True,
        )

        system_prompt, user_prompt = agent._build_prompt(input_data)

        assert "technical" in system_prompt.lower() or "code" in system_prompt.lower()
        assert "python" in user_prompt.lower()
        # Text before cursor is truncated
        assert "def calculate_sum" in user_prompt


class TestGhostTextAgentTruncation:
    """Test word boundary truncation (DD-067)."""

    def test_truncate_short_text_unchanged(self, agent: GhostTextAgent) -> None:
        """Verify short text is not truncated."""
        text = "Hello world"
        result = agent._truncate_at_word_boundary(text)

        assert result == text

    def test_truncate_long_text_at_word_boundary(self, agent: GhostTextAgent) -> None:
        """Verify long text is truncated at word boundary."""
        # Create text longer than max_chars (50 tokens * 4 chars = 200 chars)
        text = "word " * 60  # 300 characters

        result = agent._truncate_at_word_boundary(text)

        # Should be truncated
        assert len(result) < len(text)
        # Should end at word boundary (space after word)
        assert result.endswith(" ") or result.endswith("word")

    def test_truncate_respects_punctuation_boundaries(
        self, agent: GhostTextAgent
    ) -> None:
        """Verify truncation at punctuation boundaries."""
        # Create long text with punctuation
        text = "word, " * 60  # 360 characters

        result = agent._truncate_at_word_boundary(text)

        # Should end at comma or space, not mid-word
        assert result.endswith(",") or result.endswith(" ") or result.endswith("word")

    def test_truncate_empty_text_returns_empty(self, agent: GhostTextAgent) -> None:
        """Verify empty text returns empty."""
        assert agent._truncate_at_word_boundary("") == ""


class TestGhostTextAgentCleaning:
    """Test suggestion cleaning."""

    def test_clean_removes_quotes(self, agent: GhostTextAgent) -> None:
        """Verify quoted suggestions are unquoted."""
        assert agent._clean_suggestion('"Hello world"') == "Hello world"
        assert agent._clean_suggestion("'Hello world'") == "Hello world"

    def test_clean_removes_common_prefixes(self, agent: GhostTextAgent) -> None:
        """Verify common prefixes are removed."""
        assert agent._clean_suggestion("Completion: Hello") == "Hello"
        assert (
            agent._clean_suggestion("Here's the completion: Hello world")
            == "Hello world"
        )
        assert agent._clean_suggestion("Suggestion: Test") == "Test"

    def test_clean_applies_truncation(self, agent: GhostTextAgent) -> None:
        """Verify cleaning applies word boundary truncation."""
        # Create long text
        long_text = "word " * 100

        result = agent._clean_suggestion(long_text)

        # Should be truncated
        assert len(result) < len(long_text)

    def test_clean_empty_returns_empty(self, agent: GhostTextAgent) -> None:
        """Verify empty text returns empty."""
        assert agent._clean_suggestion("") == ""
        assert agent._clean_suggestion("   ") == ""


class TestGhostTextAgentStreaming:
    """Test streaming functionality."""

    @pytest.mark.asyncio
    async def test_stream_without_api_key_returns_empty(
        self,
        agent: GhostTextAgent,
    ) -> None:
        """Verify streaming without API key returns empty."""
        input_data = GhostTextInput(
            current_text="Hello",
            cursor_position=5,
        )
        context = AgentContext(
            workspace_id=uuid4(),
            user_id=uuid4(),
            metadata={},  # No API key
        )

        chunks: list[str] = []
        async for chunk in agent.stream(input_data, context):
            chunks.append(chunk)

        assert chunks == []

    @pytest.mark.asyncio
    async def test_stream_with_timeout_returns_empty(
        self,
        agent: GhostTextAgent,
        agent_context: AgentContext,
    ) -> None:
        """Verify streaming with timeout returns empty (graceful degradation)."""
        input_data = GhostTextInput(
            current_text="Hello",
            cursor_position=5,
        )

        # Mock Anthropic client to simulate timeout
        with patch("pilot_space.ai.agents.ghost_text_agent.AsyncAnthropic") as mock_anthropic:
            mock_stream = AsyncMock()
            mock_stream.__aenter__.side_effect = TimeoutError()
            mock_client = AsyncMock()
            mock_client.messages.stream.return_value = mock_stream
            mock_anthropic.return_value = mock_client

            chunks: list[str] = []

            # Use short timeout for test
            agent._timeout_ms = 100

            async for chunk in agent.stream(input_data, agent_context):
                chunks.append(chunk)

            # Should return empty on timeout (graceful degradation)
            assert chunks == []

    @pytest.mark.asyncio
    async def test_stream_with_error_returns_empty(
        self,
        agent: GhostTextAgent,
        agent_context: AgentContext,
    ) -> None:
        """Verify streaming with error returns empty (graceful degradation)."""
        input_data = GhostTextInput(
            current_text="Hello",
            cursor_position=5,
        )

        # Mock Anthropic client to simulate error
        with patch("pilot_space.ai.agents.ghost_text_agent.AsyncAnthropic") as mock_anthropic:
            mock_client = AsyncMock()
            mock_client.messages.stream.side_effect = Exception("API Error")
            mock_anthropic.return_value = mock_client

            chunks: list[str] = []
            async for chunk in agent.stream(input_data, agent_context):
                chunks.append(chunk)

            # Should return empty on error (graceful degradation)
            assert chunks == []

    @pytest.mark.asyncio
    async def test_stream_yields_chunks(
        self,
        agent: GhostTextAgent,
        agent_context: AgentContext,
    ) -> None:
        """Verify streaming yields text chunks."""
        input_data = GhostTextInput(
            current_text="Hello",
            cursor_position=5,
        )

        # Mock Anthropic streaming response
        class MockDelta:
            def __init__(self, text: str):
                self.text = text

        class MockEvent:
            def __init__(self, text: str, event_type: str = "content_block_delta"):
                self.type = event_type
                self.delta = MockDelta(text)

        async def mock_stream_iter() -> AsyncIterator[MockEvent]:
            yield MockEvent(" world")
            yield MockEvent("!")

        class MockStream:
            async def __aenter__(self) -> MockStream:
                return self

            async def __aexit__(self, *args: object) -> None:
                pass

            def __aiter__(self) -> AsyncIterator[MockEvent]:
                return mock_stream_iter()

        with patch("pilot_space.ai.agents.ghost_text_agent.AsyncAnthropic") as mock_anthropic:
            # Create a proper mock client
            mock_messages = MagicMock()
            mock_messages.stream = MagicMock(return_value=MockStream())

            mock_client = MagicMock()
            mock_client.messages = mock_messages

            mock_anthropic.return_value = mock_client

            chunks: list[str] = []
            async for chunk in agent.stream(input_data, agent_context):
                chunks.append(chunk)

            assert chunks == [" world", "!"]


class TestGhostTextAgentExecution:
    """Test non-streaming execution."""

    @pytest.mark.asyncio
    async def test_execute_collects_and_cleans_chunks(
        self,
        agent: GhostTextAgent,
        agent_context: AgentContext,
    ) -> None:
        """Verify execute collects and cleans streaming output."""
        input_data = GhostTextInput(
            current_text="Hello",
            cursor_position=5,
        )

        # Mock stream to return chunks with quotes that will be cleaned
        async def mock_stream(
            *args: object, **kwargs: object
        ) -> AsyncIterator[str]:
            yield '" world'
            yield '!"'

        agent.stream = mock_stream  # type: ignore[method-assign]

        result = await agent.execute(input_data, agent_context)

        # Quotes should be removed by _clean_suggestion
        assert result == "world!"

    @pytest.mark.asyncio
    async def test_execute_with_empty_stream_returns_empty(
        self,
        agent: GhostTextAgent,
        agent_context: AgentContext,
    ) -> None:
        """Verify execute with empty stream returns empty string."""
        input_data = GhostTextInput(
            current_text="Hello",
            cursor_position=5,
        )

        # Mock empty stream
        async def mock_stream(
            *args: object, **kwargs: object
        ) -> AsyncIterator[str]:
            if False:  # pragma: no cover
                yield ""

        agent.stream = mock_stream  # type: ignore[method-assign]

        result = await agent.execute(input_data, agent_context)

        assert result == ""


class TestGhostTextAgentConfiguration:
    """Test agent configuration."""

    def test_get_model_returns_haiku(self, agent: GhostTextAgent) -> None:
        """Verify get_model returns Claude Haiku."""
        provider, model = agent.get_model()

        assert provider == "anthropic"
        assert model == "claude-3-5-haiku-20241022"

    def test_agent_name_is_ghost_text(self, agent: GhostTextAgent) -> None:
        """Verify agent name is correct."""
        assert agent.AGENT_NAME == "ghost_text"

    def test_default_max_tokens_is_50(self, agent: GhostTextAgent) -> None:
        """Verify default max tokens is 50."""
        assert agent._max_tokens == 50

    def test_default_timeout_is_2000ms(self, agent: GhostTextAgent) -> None:
        """Verify default timeout is 2000ms."""
        assert agent._timeout_ms == 2000

    def test_custom_max_tokens_respected(
        self,
        mock_tool_registry: AsyncMock,
        mock_provider_selector: AsyncMock,
        mock_cost_tracker: AsyncMock,
        mock_resilient_executor: AsyncMock,
    ) -> None:
        """Verify custom max_tokens is respected."""
        custom_agent = GhostTextAgent(
            tool_registry=mock_tool_registry,
            provider_selector=mock_provider_selector,
            cost_tracker=mock_cost_tracker,
            resilient_executor=mock_resilient_executor,
            max_tokens=30,
        )

        assert custom_agent._max_tokens == 30

    def test_max_tokens_capped_at_limit(
        self,
        mock_tool_registry: AsyncMock,
        mock_provider_selector: AsyncMock,
        mock_cost_tracker: AsyncMock,
        mock_resilient_executor: AsyncMock,
    ) -> None:
        """Verify max_tokens is capped at MAX_TOKENS."""
        custom_agent = GhostTextAgent(
            tool_registry=mock_tool_registry,
            provider_selector=mock_provider_selector,
            cost_tracker=mock_cost_tracker,
            resilient_executor=mock_resilient_executor,
            max_tokens=100,  # Over limit
        )

        assert custom_agent._max_tokens == GhostTextAgent.MAX_TOKENS


class TestGhostTextAgentIntegration:
    """Integration tests for full workflow."""

    @pytest.mark.asyncio
    async def test_run_returns_agent_result(
        self,
        agent: GhostTextAgent,
        agent_context: AgentContext,
        mock_resilient_executor: AsyncMock,
    ) -> None:
        """Verify run() returns AgentResult."""
        input_data = GhostTextInput(
            current_text="Hello",
            cursor_position=5,
        )

        # Mock resilient executor to call the wrapped function
        async def mock_execute_wrapper(
            provider: str, operation: object
        ) -> str:
            # Call the operation function
            return await operation()  # type: ignore[misc]

        mock_resilient_executor.execute = mock_execute_wrapper  # type: ignore[method-assign]

        # Mock stream to return result
        async def mock_stream(
            *args: object, **kwargs: object
        ) -> AsyncIterator[str]:
            yield "world"

        agent.stream = mock_stream  # type: ignore[method-assign]

        result = await agent.run(input_data, agent_context)

        assert result.success is True
        # Note: _clean_suggestion strips the output
        assert result.output == "world"

    @pytest.mark.asyncio
    async def test_run_stream_wraps_stream(
        self,
        agent: GhostTextAgent,
        agent_context: AgentContext,
    ) -> None:
        """Verify run_stream() wraps stream()."""
        input_data = GhostTextInput(
            current_text="Hello",
            cursor_position=5,
        )

        # Mock stream
        async def mock_stream(
            *args: object, **kwargs: object
        ) -> AsyncIterator[str]:
            yield " world"

        agent.stream = mock_stream  # type: ignore[method-assign]

        chunks: list[str] = []
        async for chunk in agent.run_stream(input_data, agent_context):
            chunks.append(chunk)

        assert chunks == [" world"]
