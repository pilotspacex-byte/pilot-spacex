"""Unit tests for MockProvider and mock generators."""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from pilot_space.ai.agents import (
    ConversationAgent,
    ConversationInput,
    ConversationMessage,
    GhostTextAgent,
    GhostTextInput,
    IssueEnhancementInput,
    IssueEnhancerAgent,
    IssueExtractionInput,
    IssueExtractorAgent,
    LegacyAgentContext as AgentContext,
    MarginAnnotationAgent,
    MarginAnnotationInput,
    MessageRole,
    Provider,
)
from pilot_space.ai.providers.mock import (
    MockCallRecord,
    MockProvider,
    MockResponseRegistry,
    stream_mock_response,
)


@pytest.fixture
def mock_settings():
    """Enable mock mode in settings."""
    with patch("pilot_space.ai.providers.mock.get_settings") as mock_get:
        settings = MagicMock()
        settings.is_development = True
        settings.ai_fake_mode = True
        settings.ai_fake_latency_ms = 0  # No delay for tests
        settings.ai_fake_streaming_chunk_delay_ms = 0
        mock_get.return_value = settings
        yield settings


@pytest.fixture
def agent_context() -> AgentContext:
    """Create test agent context."""
    return AgentContext(
        workspace_id=uuid4(),
        user_id=uuid4(),
        correlation_id="test-correlation-123",
        api_keys={
            Provider.GEMINI: "fake-key",
            Provider.CLAUDE: "fake-key",
            Provider.OPENAI: "fake-key",
        },
    )


@pytest.fixture(autouse=True)
def reset_mock_provider():
    """Reset MockProvider singleton before each test."""
    MockProvider.reset_instance()
    MockResponseRegistry.clear_history()
    yield
    MockProvider.reset_instance()
    MockResponseRegistry.clear_history()


class TestMockProvider:
    """Tests for MockProvider core functionality."""

    def test_singleton_pattern(self, mock_settings):  # noqa: ARG002
        """Test that MockProvider follows singleton pattern."""
        provider1 = MockProvider.get_instance()
        provider2 = MockProvider.get_instance()

        assert provider1 is provider2

    def test_is_enabled_in_development_with_flag(self, mock_settings):  # noqa: ARG002
        """Test mock mode is enabled in development with flag."""
        provider = MockProvider()
        assert provider.is_enabled()

    def test_is_disabled_in_production(self):
        """Test mock mode is disabled in production."""
        with patch("pilot_space.ai.providers.mock.get_settings") as mock_get:
            settings = MagicMock()
            settings.is_development = False
            settings.ai_fake_mode = True
            mock_get.return_value = settings

            provider = MockProvider()
            assert not provider.is_enabled()

    def test_is_disabled_when_flag_false(self):
        """Test mock mode is disabled when flag is false."""
        with patch("pilot_space.ai.providers.mock.get_settings") as mock_get:
            settings = MagicMock()
            settings.is_development = True
            settings.ai_fake_mode = False
            mock_get.return_value = settings

            provider = MockProvider()
            assert not provider.is_enabled()

    @pytest.mark.asyncio
    async def test_execute_without_generator_raises(self, mock_settings, agent_context):  # noqa: ARG002
        """Test execute raises if no generator registered."""
        # Don't import generators, so none are registered
        provider = MockProvider()
        agent = GhostTextAgent()
        input_data = GhostTextInput(current_text="test", cursor_position=4)

        with pytest.raises(ValueError, match="No mock generator registered"):
            await provider.execute(agent, input_data, agent_context)


class TestMockResponseRegistry:
    """Tests for MockResponseRegistry."""

    def test_register_and_get_generator(self):
        """Test registering and retrieving generators."""

        @MockResponseRegistry.register("TestAgent")
        def test_generator(data):
            return {"result": f"processed-{data}"}

        gen = MockResponseRegistry.get_generator("TestAgent")
        assert gen is not None
        assert gen("input") == {"result": "processed-input"}

    def test_has_generator(self):
        """Test checking if generator exists."""

        @MockResponseRegistry.register("ExistingAgent")
        def test_gen(data):
            return data

        assert MockResponseRegistry.has_generator("ExistingAgent")
        assert not MockResponseRegistry.has_generator("NonExistentAgent")

    def test_list_registered(self):
        """Test listing all registered generators."""
        MockResponseRegistry._generators.clear()  # noqa: SLF001

        @MockResponseRegistry.register("Agent1")
        def gen1(data):
            return data

        @MockResponseRegistry.register("Agent2")
        def gen2(data):
            return data

        registered = MockResponseRegistry.list_registered()
        assert "Agent1" in registered
        assert "Agent2" in registered

    def test_record_and_get_history(self):
        """Test recording and retrieving call history."""
        MockResponseRegistry.clear_history()

        record1 = MockCallRecord(
            agent_name="Agent1",
            input_summary="input1",
            output_summary="output1",
            latency_ms=100,
        )
        record2 = MockCallRecord(
            agent_name="Agent2",
            input_summary="input2",
            output_summary="output2",
            latency_ms=200,
        )

        MockResponseRegistry.record_call(record1)
        MockResponseRegistry.record_call(record2)

        history = MockResponseRegistry.get_history()
        assert len(history) == 2
        assert history[0].agent_name == "Agent1"
        assert history[1].agent_name == "Agent2"

    def test_clear_history(self):
        """Test clearing call history."""
        record = MockCallRecord(
            agent_name="TestAgent",
            input_summary="test",
            output_summary="result",
            latency_ms=100,
        )
        MockResponseRegistry.record_call(record)
        assert len(MockResponseRegistry.get_history()) > 0

        MockResponseRegistry.clear_history()
        assert len(MockResponseRegistry.get_history()) == 0


class TestGhostTextMock:
    """Tests for ghost text mock generator."""

    @pytest.mark.asyncio
    async def test_code_completion_def(self, mock_settings, agent_context):  # noqa: ARG002
        """Test ghost text returns code completion for 'def '."""
        # Import to register generators
        import pilot_space.ai.providers.mock_generators  # noqa: F401

        agent = GhostTextAgent()
        result = await agent.execute(
            GhostTextInput(current_text="def ", cursor_position=4, is_code=True),
            agent_context,
        )

        assert result.output.suggestion is not None
        assert "function_name" in result.output.suggestion
        assert not result.output.is_empty
        assert result.model == "mock-model-v1"
        assert result.metadata.get("mock_mode") is True

    @pytest.mark.asyncio
    async def test_code_completion_class(self, mock_settings, agent_context):  # noqa: ARG002
        """Test ghost text returns code completion for 'class '."""
        import pilot_space.ai.providers.mock_generators  # noqa: F401

        agent = GhostTextAgent()
        result = await agent.execute(
            GhostTextInput(current_text="class ", cursor_position=6, is_code=True),
            agent_context,
        )

        assert result.output.suggestion is not None
        assert "__init__" in result.output.suggestion  # Contains class structure
        assert not result.output.is_empty

    @pytest.mark.asyncio
    async def test_text_completion(self, mock_settings, agent_context):  # noqa: ARG002
        """Test ghost text returns text completion for prose."""
        import pilot_space.ai.providers.mock_generators  # noqa: F401

        agent = GhostTextAgent()
        result = await agent.execute(
            GhostTextInput(current_text="The ", cursor_position=4, is_code=False),
            agent_context,
        )

        assert result.output.suggestion is not None
        assert len(result.output.suggestion) > 0

    @pytest.mark.asyncio
    async def test_empty_input_returns_empty(self, mock_settings, agent_context):  # noqa: ARG002
        """Test ghost text handles empty input."""
        import pilot_space.ai.providers.mock_generators  # noqa: F401

        agent = GhostTextAgent()
        result = await agent.execute(
            GhostTextInput(current_text="", cursor_position=0),
            agent_context,
        )

        assert result.output.is_empty


class TestIssueEnhancerMock:
    """Tests for issue enhancer mock generator."""

    @pytest.mark.asyncio
    async def test_enhancement_adds_structure(self, mock_settings, agent_context):  # noqa: ARG002
        """Test issue enhancement adds acceptance criteria."""
        import pilot_space.ai.providers.mock_generators  # noqa: F401

        agent = IssueEnhancerAgent()
        result = await agent.execute(
            IssueEnhancementInput(
                title="Fix login bug",
                description="Users can't login",
            ),
            agent_context,
        )

        assert "Acceptance Criteria" in result.output.enhanced_description
        assert result.output.description_expanded
        assert len(result.output.suggested_labels) > 0

    @pytest.mark.asyncio
    async def test_detects_bug_label(self, mock_settings, agent_context):  # noqa: ARG002
        """Test enhancement suggests bug label for bug-related issues."""
        import pilot_space.ai.providers.mock_generators  # noqa: F401

        agent = IssueEnhancerAgent()
        result = await agent.execute(
            IssueEnhancementInput(
                title="Bug: Application crashes on startup",
                available_labels=["bug", "feature", "enhancement"],
            ),
            agent_context,
        )

        label_names = [str(label["name"]) for label in result.output.suggested_labels]
        assert "bug" in label_names

    @pytest.mark.asyncio
    async def test_adds_title_prefix(self, mock_settings, agent_context):  # noqa: ARG002
        """Test enhancement adds prefix to unprefixed titles."""
        import pilot_space.ai.providers.mock_generators  # noqa: F401

        agent = IssueEnhancerAgent()
        result = await agent.execute(
            IssueEnhancementInput(title="Implement new feature"),
            agent_context,
        )

        assert result.output.title_enhanced
        assert "[" in result.output.enhanced_title


class TestIssueExtractorMock:
    """Tests for issue extractor mock generator."""

    @pytest.mark.asyncio
    async def test_extracts_todo_items(self, mock_settings, agent_context):  # noqa: ARG002
        """Test extractor finds TODO items."""
        import pilot_space.ai.providers.mock_generators  # noqa: F401

        agent = IssueExtractorAgent()
        result = await agent.execute(
            IssueExtractionInput(
                note_title="Project Planning",
                note_content="TODO: Implement user authentication. TODO: Add unit tests.",
            ),
            agent_context,
        )

        assert len(result.output.issues) > 0
        titles = [issue.title for issue in result.output.issues]
        assert any("authentication" in title.lower() for title in titles)

    @pytest.mark.asyncio
    async def test_extracts_requirements(self, mock_settings, agent_context):  # noqa: ARG002
        """Test extractor finds requirement statements."""
        import pilot_space.ai.providers.mock_generators  # noqa: F401

        agent = IssueExtractorAgent()
        result = await agent.execute(
            IssueExtractionInput(
                note_title="Requirements",
                note_content="We need to implement a payment gateway. Users should be able to export data.",
            ),
            agent_context,
        )

        assert len(result.output.issues) > 0


class TestMarginAnnotationMock:
    """Tests for margin annotation mock generator."""

    @pytest.mark.asyncio
    async def test_annotates_todo_blocks(self, mock_settings, agent_context):  # noqa: ARG002
        """Test annotator identifies TODO blocks."""
        import pilot_space.ai.providers.mock_generators  # noqa: F401

        agent = MarginAnnotationAgent()
        result = await agent.execute(
            MarginAnnotationInput(
                note_title="Implementation Plan",
                blocks=[
                    {"id": "block-1", "content": "TODO: Implement authentication logic"},
                    {"id": "block-2", "content": "This is a normal paragraph"},
                ],
            ),
            agent_context,
        )

        assert len(result.output.annotations) > 0
        todo_annotations = [a for a in result.output.annotations if a.block_id == "block-1"]
        assert len(todo_annotations) > 0


class TestConversationMock:
    """Tests for conversation mock generator."""

    @pytest.mark.asyncio
    async def test_greeting_response(self, mock_settings, agent_context):  # noqa: ARG002
        """Test conversation responds to greetings."""
        import pilot_space.ai.providers.mock_generators  # noqa: F401

        agent = ConversationAgent()
        result = await agent.execute(
            ConversationInput(message="Hello!"),
            agent_context,
        )

        assert "hello" in result.output.response.lower() or "hi" in result.output.response.lower()
        assert len(result.output.updated_history) == 2  # User + Assistant

    @pytest.mark.asyncio
    async def test_help_request(self, mock_settings, agent_context):  # noqa: ARG002
        """Test conversation responds to help requests."""
        import pilot_space.ai.providers.mock_generators  # noqa: F401

        agent = ConversationAgent()
        result = await agent.execute(
            ConversationInput(message="What can you help me with?"),
            agent_context,
        )

        assert "help" in result.output.response.lower()

    @pytest.mark.asyncio
    async def test_history_preserved(self, mock_settings, agent_context):  # noqa: ARG002
        """Test conversation preserves history."""
        import pilot_space.ai.providers.mock_generators  # noqa: F401

        agent = ConversationAgent()
        history = [
            ConversationMessage(role=MessageRole.USER, content="Previous message"),
            ConversationMessage(role=MessageRole.ASSISTANT, content="Previous response"),
        ]

        result = await agent.execute(
            ConversationInput(message="New message", history=history),
            agent_context,
        )

        assert len(result.output.updated_history) == 4  # 2 old + 2 new


class TestStreamMockResponse:
    """Tests for stream_mock_response utility."""

    @pytest.mark.asyncio
    async def test_streams_in_chunks(self):
        """Test streaming returns multiple chunks."""
        content = "Hello, this is a test response."
        chunks = []

        async for chunk in stream_mock_response(content, chunk_size=10, delay_ms=0):
            chunks.append(chunk)

        assert len(chunks) > 1  # Multiple chunks
        assert chunks[-1].endswith('"done": true}\n\n')  # Last chunk signals done

    @pytest.mark.asyncio
    async def test_complete_content_assembled(self):
        """Test streaming can be reassembled to complete content."""
        import json

        content = "Complete message"
        assembled = ""

        async for chunk in stream_mock_response(content, chunk_size=5, delay_ms=0):
            if "data: " in chunk:
                data = json.loads(chunk.replace("data: ", "").strip())
                assembled += data.get("chunk", "")

        assert assembled == content


class TestMockCallRecord:
    """Tests for MockCallRecord dataclass."""

    def test_to_dict(self):
        """Test MockCallRecord converts to dictionary."""
        record = MockCallRecord(
            agent_name="TestAgent",
            input_summary="input",
            output_summary="output",
            latency_ms=100,
            timestamp=1234567890.0,
        )

        result = record.to_dict()
        assert result["agent_name"] == "TestAgent"
        assert result["input_summary"] == "input"
        assert result["output_summary"] == "output"
        assert result["latency_ms"] == 100
        assert result["timestamp"] == 1234567890.0
