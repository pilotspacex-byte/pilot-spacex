"""Unit tests for SDKBaseAgent."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from pilot_space.ai.agents.agent_base import (
    AgentContext,
    AgentResult,
    SDKBaseAgent,
    StreamingSDKBaseAgent,
)


class ConcreteAgent(SDKBaseAgent[str, str]):
    """Test implementation of SDKBaseAgent."""

    AGENT_NAME = "test_agent"
    DEFAULT_MODEL = "claude-sonnet-4-20250514"

    async def execute(self, input_data: str, context: AgentContext) -> str:
        """Process input and return output."""
        return f"processed: {input_data}"


class ConcreteStreamingAgent(StreamingSDKBaseAgent[str, str]):
    """Test implementation of StreamingSDKBaseAgent."""

    AGENT_NAME = "test_streaming_agent"
    DEFAULT_MODEL = "claude-sonnet-4-20250514"

    async def stream(self, input_data: str, context: AgentContext):
        """Stream output word by word."""
        for word in input_data.split():
            yield word + " "


@pytest.fixture
def mock_deps():
    """Create mock dependencies."""
    return {
        "provider_selector": MagicMock(),
        "cost_tracker": MagicMock(),
        "resilient_executor": MagicMock(),
    }


@pytest.fixture
def context():
    """Create test context."""
    return AgentContext(
        workspace_id=uuid4(),
        user_id=uuid4(),
        operation_id=uuid4(),
    )


class TestAgentContext:
    """Test AgentContext dataclass."""

    def test_creates_with_required_fields(self):
        """Verify AgentContext creation with required fields."""
        workspace_id = uuid4()
        user_id = uuid4()

        ctx = AgentContext(workspace_id=workspace_id, user_id=user_id)

        assert ctx.workspace_id == workspace_id
        assert ctx.user_id == user_id
        assert ctx.operation_id is None
        assert ctx.metadata == {}

    def test_creates_with_optional_fields(self):
        """Verify AgentContext creation with optional fields."""
        workspace_id = uuid4()
        user_id = uuid4()
        operation_id = uuid4()
        metadata = {"key": "value"}

        ctx = AgentContext(
            workspace_id=workspace_id,
            user_id=user_id,
            operation_id=operation_id,
            metadata=metadata,
        )

        assert ctx.workspace_id == workspace_id
        assert ctx.user_id == user_id
        assert ctx.operation_id == operation_id
        assert ctx.metadata == metadata

    def test_is_frozen(self):
        """Verify AgentContext is immutable."""
        ctx = AgentContext(workspace_id=uuid4(), user_id=uuid4())

        with pytest.raises(AttributeError):
            ctx.workspace_id = uuid4()  # type: ignore[misc]


class TestAgentResult:
    """Test AgentResult dataclass."""

    def test_ok_creates_success(self):
        """Verify AgentResult.ok creates successful result."""
        result = AgentResult.ok("output", cost_usd=0.001)

        assert result.success is True
        assert result.output == "output"
        assert result.cost_usd == 0.001
        assert result.error is None

    def test_ok_with_token_counts(self):
        """Verify AgentResult.ok with token counts."""
        result = AgentResult.ok(
            "output",
            cost_usd=0.002,
            input_tokens=100,
            output_tokens=50,
        )

        assert result.success is True
        assert result.output == "output"
        assert result.cost_usd == 0.002
        assert result.input_tokens == 100
        assert result.output_tokens == 50

    def test_fail_creates_failure(self):
        """Verify AgentResult.fail creates failed result."""
        result = AgentResult.fail("error message")

        assert result.success is False
        assert result.output is None
        assert result.error == "error message"

    def test_fail_with_token_counts(self):
        """Verify AgentResult.fail can include token counts."""
        result = AgentResult.fail(
            "error message",
            input_tokens=100,
            output_tokens=0,
        )

        assert result.success is False
        assert result.error == "error message"
        assert result.input_tokens == 100
        assert result.output_tokens == 0


class TestSDKBaseAgent:
    """Test SDKBaseAgent abstract class."""

    def test_init_stores_dependencies(self, mock_deps):
        """Verify agent initialization stores dependencies."""
        agent = ConcreteAgent(**mock_deps)

        assert agent._provider_selector is mock_deps["provider_selector"]
        assert agent._cost_tracker is mock_deps["cost_tracker"]
        assert agent._resilient_executor is mock_deps["resilient_executor"]

    def test_get_model_returns_default(self, mock_deps):
        """Verify get_model returns default provider and model."""
        agent = ConcreteAgent(**mock_deps)

        provider, model = agent.get_model()

        assert provider == "anthropic"
        assert model == "claude-sonnet-4-20250514"

    @pytest.mark.asyncio
    async def test_track_usage_calls_cost_tracker(self, mock_deps, context):
        """Verify track_usage calls cost tracker."""
        mock_cost_record = MagicMock()
        mock_cost_record.cost_usd = 0.003
        mock_deps["cost_tracker"].track = AsyncMock(return_value=mock_cost_record)
        mock_deps["provider_selector"].select.return_value = (
            "anthropic",
            "claude-sonnet-4-20250514",
        )
        agent = ConcreteAgent(**mock_deps)

        cost = await agent.track_usage(context, input_tokens=100, output_tokens=50)

        mock_deps["cost_tracker"].track.assert_awaited_once_with(
            workspace_id=context.workspace_id,
            user_id=context.user_id,
            agent_name="test_agent",
            provider="anthropic",
            model="claude-sonnet-4-20250514",
            input_tokens=100,
            output_tokens=50,
        )
        assert cost == 0.003

    @pytest.mark.asyncio
    async def test_run_calls_execute(self, mock_deps, context):
        """Verify run calls execute with resilient executor."""

        async def mock_execute(provider, operation):
            return await operation()

        mock_deps["resilient_executor"].execute = AsyncMock(side_effect=mock_execute)
        agent = ConcreteAgent(**mock_deps)

        result = await agent.run("test input", context)

        assert result.success is True
        assert result.output == "processed: test input"
        mock_deps["resilient_executor"].execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_run_handles_exception(self, mock_deps, context):
        """Verify run handles exceptions from execute."""
        mock_deps["resilient_executor"].execute = AsyncMock(side_effect=ValueError("test error"))
        mock_deps["provider_selector"].select.return_value = (
            "anthropic",
            "claude-sonnet-4-20250514",
        )
        agent = ConcreteAgent(**mock_deps)

        result = await agent.run("test input", context)

        assert result.success is False
        assert "test error" in result.error
        assert result.output is None

    @pytest.mark.asyncio
    async def test_run_uses_correct_provider(self, mock_deps, context):
        """Verify run passes correct provider to resilient executor."""
        executed_provider = None

        async def mock_execute(provider, operation):
            nonlocal executed_provider
            executed_provider = provider
            return await operation()

        mock_deps["resilient_executor"].execute = AsyncMock(side_effect=mock_execute)
        agent = ConcreteAgent(**mock_deps)

        await agent.run("test input", context)

        # Default provider is anthropic
        assert executed_provider == "anthropic"


class TestStreamingSDKBaseAgent:
    """Test StreamingSDKBaseAgent abstract class."""

    @pytest.mark.asyncio
    async def test_stream_yields_chunks(self, mock_deps, context):
        """Verify stream yields chunks correctly."""
        agent = ConcreteStreamingAgent(**mock_deps)

        chunks = []
        async for chunk in agent.stream("hello world", context):
            chunks.append(chunk)

        assert chunks == ["hello ", "world "]

    @pytest.mark.asyncio
    async def test_execute_collects_stream(self, mock_deps, context):
        """Verify execute collects stream into final output."""
        agent = ConcreteStreamingAgent(**mock_deps)

        result = await agent.execute("hello world", context)

        assert result == "hello world "

    @pytest.mark.asyncio
    async def test_run_stream_yields_chunks(self, mock_deps, context):
        """Verify run_stream yields chunks from stream."""
        agent = ConcreteStreamingAgent(**mock_deps)

        chunks = []
        async for chunk in agent.run_stream("hello world", context):
            chunks.append(chunk)

        assert chunks == ["hello ", "world "]

    @pytest.mark.asyncio
    async def test_run_stream_handles_exception(self, mock_deps, context):
        """Verify run_stream handles exceptions and yields error."""

        class FailingStreamAgent(StreamingSDKBaseAgent[str, str]):
            AGENT_NAME = "failing_agent"
            DEFAULT_MODEL = "claude-sonnet-4-20250514"

            async def stream(self, _input_data: str, _context: AgentContext):
                yield "start "
                raise ValueError("stream error")

        agent = FailingStreamAgent(**mock_deps)

        chunks = []
        async for chunk in agent.run_stream("test", context):
            chunks.append(chunk)

        assert chunks[0] == "start "
        assert "ERROR: stream error" in chunks[1]

    @pytest.mark.asyncio
    async def test_execute_returns_concatenated_string(self, mock_deps, context):
        """Verify execute concatenates stream chunks."""

        class MultiChunkAgent(StreamingSDKBaseAgent[str, str]):
            AGENT_NAME = "multi_chunk_agent"
            DEFAULT_MODEL = "claude-sonnet-4-20250514"

            async def stream(self, input_data: str, _context: AgentContext):
                for char in input_data:
                    yield char

        agent = MultiChunkAgent(**mock_deps)

        result = await agent.execute("abc", context)

        assert result == "abc"


class TestAgentIntegration:
    """Integration tests for agent workflows."""

    @pytest.mark.asyncio
    async def test_full_workflow_with_tracking(self, mock_deps, context):
        """Verify full agent execution workflow with cost tracking."""
        mock_cost_record = MagicMock()
        mock_cost_record.cost_usd = 0.005
        mock_deps["cost_tracker"].track = AsyncMock(return_value=mock_cost_record)

        async def mock_execute(provider, operation):
            return await operation()

        mock_deps["resilient_executor"].execute = AsyncMock(side_effect=mock_execute)

        agent = ConcreteAgent(**mock_deps)

        # Execute agent
        result = await agent.run("test input", context)
        assert result.success is True
        assert result.output == "processed: test input"

        # Track usage
        cost = await agent.track_usage(context, input_tokens=100, output_tokens=50)
        assert cost == 0.005

        # Verify cost tracker was called
        mock_deps["cost_tracker"].track.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_streaming_workflow(self, mock_deps, context):
        """Verify streaming agent workflow."""
        agent = ConcreteStreamingAgent(**mock_deps)

        # Stream output
        chunks = []
        async for chunk in agent.run_stream("hello world", context):
            chunks.append(chunk)

        assert chunks == ["hello ", "world "]

        # Also verify execute works
        full_output = await agent.execute("hello world", context)
        assert full_output == "hello world "
