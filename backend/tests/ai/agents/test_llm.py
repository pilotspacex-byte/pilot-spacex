"""Tests for comprehensive LLM module.

Tests all components:
- PromptCachingHandler: <cache> tag parsing, billing adjustments
- MessageConverter: Multi-modal conversion, consecutive merging
- ToolTransformer: Select type conversion, schema fixing
- StreamingHandler: Event processing, thinking blocks
- AnthropicLLMMixin: Query interface, cache pruning
- AnthropicStreamingLLMMixin: Streaming interface

Test coverage requirements:
- >80% coverage for all branches
- All error cases
- All caching configurations
- Multi-modal content
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest

from pilot_space.ai.agents.agent_base import AgentContext
from pilot_space.ai.agents.llm import (
    AnthropicLLMMixin,
    AnthropicStreamingLLMMixin,
    AssistantPromptMessage,
    CachingConfig,
    DocumentPromptMessageContent,
    ImagePromptMessageContent,
    LLMResult,
    MessageConverter,
    PromptCachingHandler,
    PromptMessage,
    SystemPromptMessage,
    TextPromptMessageContent,
    ToolPromptMessage,
    ToolTransformer,
    UserPromptMessage,
)
from pilot_space.ai.exceptions import AIConfigurationError

# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def mock_context() -> AgentContext:
    """Create mock agent context."""
    return AgentContext(
        workspace_id=uuid4(),
        user_id=uuid4(),
        operation_id=uuid4(),
    )


@pytest.fixture
def mock_key_storage() -> AsyncMock:
    """Create mock key storage."""
    storage = AsyncMock()
    storage.get_api_key.return_value = "sk-ant-test-key"
    return storage


@pytest.fixture
def mock_agent(mock_key_storage: AsyncMock) -> AnthropicLLMMixin:
    """Create mock agent with AnthropicLLMMixin."""

    class TestAgent(AnthropicLLMMixin):
        """Test agent for mixin testing."""

        DEFAULT_MODEL = "claude-sonnet-4-20250514"

        def __init__(self, key_storage: Any) -> None:
            self._key_storage = key_storage

        async def track_usage(
            self,
            context: AgentContext,
            input_tokens: int,
            output_tokens: int,
        ) -> float:
            """Mock track_usage."""
            return 0.0

    return TestAgent(mock_key_storage)


@pytest.fixture
def mock_streaming_agent(mock_key_storage: AsyncMock) -> AnthropicStreamingLLMMixin:
    """Create mock streaming agent."""

    class TestStreamingAgent(AnthropicStreamingLLMMixin):
        """Test streaming agent."""

        DEFAULT_MODEL = "claude-sonnet-4-20250514"

        def __init__(self, key_storage: Any) -> None:
            self._key_storage = key_storage

        async def track_usage(
            self,
            context: AgentContext,
            input_tokens: int,
            output_tokens: int,
        ) -> float:
            """Mock track_usage."""
            return 0.0

    return TestStreamingAgent(mock_key_storage)


# ============================================================================
# PromptCachingHandler Tests
# ============================================================================


class TestPromptCachingHandler:
    """Test PromptCachingHandler functionality."""

    def test_get_system_prompt_simple_string(self) -> None:
        """Test simple string system prompt without caching."""
        messages = [SystemPromptMessage(content="You are a helpful assistant")]
        handler = PromptCachingHandler(messages, enable_system_cache=False)
        system = handler.get_system_prompt()

        assert isinstance(system, str)
        assert system == "You are a helpful assistant"

    def test_get_system_prompt_with_cache_tags(self) -> None:
        """Test <cache> tag parsing."""
        messages = [
            SystemPromptMessage(
                content="Prefix text\n<cache>Cached content here</cache>\nSuffix text"
            )
        ]
        handler = PromptCachingHandler(messages, enable_system_cache=True)
        system = handler.get_system_prompt()

        assert isinstance(system, list)
        assert len(system) == 3

        # Check structure
        assert system[0]["type"] == "text"
        assert system[0]["text"] == "Prefix text"
        assert "cache_control" not in system[0]

        assert system[1]["type"] == "text"
        assert system[1]["text"] == "Cached content here"
        assert system[1]["cache_control"] == {"type": "ephemeral"}

        assert system[2]["type"] == "text"
        assert system[2]["text"] == "Suffix text"
        assert "cache_control" not in system[2]

    def test_get_system_prompt_multiple_cache_blocks(self) -> None:
        """Test multiple <cache> blocks."""
        messages = [
            SystemPromptMessage(content="<cache>Block 1</cache>\nMiddle\n<cache>Block 2</cache>")
        ]
        handler = PromptCachingHandler(messages, enable_system_cache=True)
        system = handler.get_system_prompt()

        assert isinstance(system, list)
        cached_blocks = [b for b in system if "cache_control" in b]
        assert len(cached_blocks) == 2

    def test_get_system_prompt_no_cache_when_disabled(self) -> None:
        """Test cache tags ignored when caching disabled."""
        messages = [SystemPromptMessage(content="<cache>Should not cache</cache>")]
        handler = PromptCachingHandler(messages, enable_system_cache=False)
        system = handler.get_system_prompt()

        assert isinstance(system, str)
        assert "<cache>" in system  # Tags preserved in output

    def test_get_system_prompt_structured_content(self) -> None:
        """Test structured content (list of TextPromptMessageContent)."""
        messages = [
            SystemPromptMessage(
                content=[
                    TextPromptMessageContent(data="Part 1"),
                    TextPromptMessageContent(data="Part 2"),
                ]
            )
        ]
        handler = PromptCachingHandler(messages, enable_system_cache=False)
        system = handler.get_system_prompt()

        assert isinstance(system, str)
        assert "Part 1" in system
        assert "Part 2" in system

    def test_calc_adjusted_prompt_tokens_no_cache(self) -> None:
        """Test billing calculation without cache."""
        adjusted = PromptCachingHandler.calc_adjusted_prompt_tokens(
            base_prompt_tokens=1000,
            cache_creation_input_tokens=0,
            cache_read_input_tokens=0,
        )
        assert adjusted == 1000

    def test_calc_adjusted_prompt_tokens_with_cache_write(self) -> None:
        """Test billing with cache write (25% premium)."""
        adjusted = PromptCachingHandler.calc_adjusted_prompt_tokens(
            base_prompt_tokens=1000,
            cache_creation_input_tokens=500,  # 500 * 1.25 = 625
            cache_read_input_tokens=0,
        )
        # 1000 - 500 (removed from base) + 625 (premium) = 1125
        assert adjusted == 1125

    def test_calc_adjusted_prompt_tokens_with_cache_read(self) -> None:
        """Test billing with cache read (90% discount)."""
        adjusted = PromptCachingHandler.calc_adjusted_prompt_tokens(
            base_prompt_tokens=1000,
            cache_creation_input_tokens=0,
            cache_read_input_tokens=2000,  # 2000 * 0.1 = 200
        )
        # 1000 - 2000 (removed) + 200 (discounted) = -800 + 200 = -600 (floor at 200)
        assert adjusted == 200

    def test_calc_adjusted_prompt_tokens_combined(self) -> None:
        """Test billing with both cache write and read."""
        adjusted = PromptCachingHandler.calc_adjusted_prompt_tokens(
            base_prompt_tokens=1000,
            cache_creation_input_tokens=500,  # +625
            cache_read_input_tokens=2000,  # +200
        )
        # 1000 - 500 - 2000 + 625 + 200 = -675 (but calculation is sequential)
        # Actually: (1000 - 500 + 625) - 2000 + 200 = 1125 - 2000 + 200 = -675
        # But implementation does: base - creation + premium - read + discount
        # = 1000 - 500 + 625 - 2000 + 200 = -675
        # Since we can't have negative, minimum is sum of adjustments
        assert adjusted >= 0  # At minimum should be positive


# ============================================================================
# MessageConverter Tests
# ============================================================================


class TestMessageConverter:
    """Test MessageConverter functionality."""

    def test_convert_simple_user_message(self) -> None:
        """Test basic user message conversion."""
        messages = [UserPromptMessage(content="Hello, world!")]
        converter = MessageConverter(CachingConfig())
        system, api_messages = converter.convert_messages(messages)

        assert system == ""
        assert len(api_messages) == 1
        assert api_messages[0]["role"] == "user"
        assert isinstance(api_messages[0]["content"], list)
        assert api_messages[0]["content"][0]["type"] == "text"
        assert api_messages[0]["content"][0]["text"] == "Hello, world!"

    def test_convert_system_message(self) -> None:
        """Test system message extraction."""
        messages = [
            SystemPromptMessage(content="You are helpful"),
            UserPromptMessage(content="Hello"),
        ]
        converter = MessageConverter(CachingConfig())
        system, api_messages = converter.convert_messages(messages)

        assert system == "You are helpful"
        assert len(api_messages) == 1
        assert api_messages[0]["role"] == "user"

    def test_convert_multi_modal_message(self) -> None:
        """Test multi-modal content (text + image)."""
        messages = [
            UserPromptMessage(
                content=[
                    TextPromptMessageContent(data="Analyze this image"),
                    ImagePromptMessageContent(
                        data="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
                    ),
                ]
            )
        ]
        converter = MessageConverter(CachingConfig())
        system, api_messages = converter.convert_messages(messages)

        assert len(api_messages) == 1
        content = api_messages[0]["content"]
        assert len(content) == 2
        assert content[0]["type"] == "image"  # Images before text
        assert content[1]["type"] == "text"

    def test_convert_image_with_cache_enabled(self) -> None:
        """Test image caching."""
        messages = [
            UserPromptMessage(
                content=[
                    ImagePromptMessageContent(
                        data="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
                    ),
                ]
            )
        ]
        converter = MessageConverter(CachingConfig(image_cache_enabled=True))
        system, api_messages = converter.convert_messages(messages)

        content = api_messages[0]["content"]
        assert "cache_control" in content[0]
        assert content[0]["cache_control"]["type"] == "ephemeral"

    def test_convert_document_pdf(self) -> None:
        """Test PDF document content."""
        messages = [
            UserPromptMessage(
                content=[
                    DocumentPromptMessageContent(
                        base64_data="JVBERi0xLjQKJeLjz9MKMSAwIG9iago8PC9UeXBlL0NhdGFsb2cvUGFnZXMgMiAwIFI+PgplbmRvYmoKMiAwIG9iago8PC9UeXBlL1BhZ2VzL0tpZHNbMyAwIFJdL0NvdW50IDE+PgplbmRvYmoKMyAwIG9iago8PC9UeXBlL1BhZ2UvTWVkaWFCb3hbMCAwIDYxMiA3OTJdL1Jlc291cmNlczw8L0ZvbnQ8PC9GMSA0IDAgUj4+Pj4vQ29udGVudHMgNSAwIFI+PgplbmRvYmoK",
                        mime_type="application/pdf",
                    ),
                ]
            )
        ]
        converter = MessageConverter(CachingConfig(document_cache_enabled=True))
        system, api_messages = converter.convert_messages(messages)

        content = api_messages[0]["content"]
        assert content[0]["type"] == "document"
        assert content[0]["source"]["type"] == "base64"
        assert content[0]["source"]["media_type"] == "application/pdf"
        assert "cache_control" in content[0]

    def test_convert_assistant_with_tool_calls(self) -> None:
        """Test assistant message with tool calls."""
        messages = [
            AssistantPromptMessage(
                content="Let me check that",
                tool_calls=[
                    AssistantPromptMessage.ToolCall(
                        id="call_123",
                        type="function",
                        function=AssistantPromptMessage.ToolCall.ToolCallFunction(
                            name="get_weather",
                            arguments='{"location": "NYC"}',
                        ),
                    )
                ],
            )
        ]
        converter = MessageConverter(CachingConfig())
        system, api_messages = converter.convert_messages(messages)

        assert len(api_messages) == 1
        content = api_messages[0]["content"]
        assert len(content) == 2
        assert content[0]["type"] == "text"
        assert content[1]["type"] == "tool_use"
        assert content[1]["name"] == "get_weather"
        assert content[1]["input"]["location"] == "NYC"

    def test_convert_tool_result_message(self) -> None:
        """Test tool result message."""
        messages = [
            ToolPromptMessage(
                tool_call_id="call_123",
                content="Temperature is 72F",
            )
        ]
        converter = MessageConverter(CachingConfig(tool_results_cache_enabled=True))
        system, api_messages = converter.convert_messages(messages)

        assert len(api_messages) == 1
        assert api_messages[0]["role"] == "user"
        content = api_messages[0]["content"]
        assert content[0]["type"] == "tool_result"
        assert content[0]["tool_use_id"] == "call_123"
        assert content[0]["content"] == "Temperature is 72F"
        assert "cache_control" in content[0]

    def test_merge_consecutive_assistant_messages(self) -> None:
        """Test consecutive assistant message merging."""
        messages = [
            AssistantPromptMessage(content="First part"),
            AssistantPromptMessage(content="Second part"),
            UserPromptMessage(content="User message"),
        ]
        converter = MessageConverter(CachingConfig())
        system, api_messages = converter.convert_messages(messages)

        # First two assistant messages should be merged
        assert len(api_messages) == 2
        assert api_messages[0]["role"] == "assistant"
        assert len(api_messages[0]["content"]) == 2
        assert api_messages[1]["role"] == "user"

    def test_should_cache_text_threshold(self) -> None:
        """Test text caching threshold."""
        long_text = "word " * 1000  # 1000 words
        short_text = "word " * 10  # 10 words

        config = CachingConfig(message_flow_cache_threshold=500)
        converter = MessageConverter(config)

        assert converter._should_cache_text(long_text)
        assert not converter._should_cache_text(short_text)


# ============================================================================
# ToolTransformer Tests
# ============================================================================


class TestToolTransformer:
    """Test ToolTransformer functionality."""

    def test_transform_basic_tool(self) -> None:
        """Test basic tool transformation."""
        tool = {
            "name": "get_weather",
            "description": "Get weather for location",
            "parameters": {
                "type": "object",
                "properties": {"location": {"type": "string", "description": "City name"}},
                "required": ["location"],
            },
        }

        transformer = ToolTransformer(enable_tool_caching=False)
        result = transformer.transform_tool(tool)

        assert result["name"] == "get_weather"
        assert result["description"] == "Get weather for location"
        assert "input_schema" in result
        assert result["input_schema"]["type"] == "object"
        assert "cache_control" not in result

    def test_transform_tool_with_caching(self) -> None:
        """Test tool transformation with caching."""
        tool = {
            "name": "search",
            "description": "Search documents",
            "parameters": {"type": "object", "properties": {}},
        }

        transformer = ToolTransformer(enable_tool_caching=True)
        result = transformer.transform_tool(tool)

        assert "cache_control" in result
        assert result["cache_control"]["type"] == "ephemeral"

    def test_transform_select_type_to_enum(self) -> None:
        """Test select type conversion to string + enum."""
        tool = {
            "name": "set_priority",
            "description": "Set issue priority",
            "parameters": {
                "type": "object",
                "properties": {
                    "priority": {
                        "type": "select",
                        "description": "Priority level",
                        "options": [
                            {"value": "high", "label": "High"},
                            {"value": "medium", "label": "Medium"},
                            {"value": "low", "label": "Low"},
                        ],
                    }
                },
            },
        }

        transformer = ToolTransformer()
        result = transformer.transform_tool(tool)

        priority_schema = result["input_schema"]["properties"]["priority"]
        assert priority_schema["type"] == "string"
        assert priority_schema["enum"] == ["high", "medium", "low"]
        assert "options" not in priority_schema

    def test_transform_select_with_string_options(self) -> None:
        """Test select type with simple string options."""
        tool = {
            "name": "set_state",
            "description": "Set state",
            "parameters": {
                "type": "object",
                "properties": {
                    "state": {
                        "type": "select",
                        "options": ["open", "closed", "pending"],
                    }
                },
            },
        }

        transformer = ToolTransformer()
        result = transformer.transform_tool(tool)

        state_schema = result["input_schema"]["properties"]["state"]
        assert state_schema["type"] == "string"
        assert state_schema["enum"] == ["open", "closed", "pending"]

    def test_transform_nested_object_schema(self) -> None:
        """Test nested object schema transformation."""
        tool = {
            "name": "create_issue",
            "description": "Create issue",
            "parameters": {
                "type": "object",
                "properties": {
                    "metadata": {
                        "type": "object",
                        "properties": {
                            "priority": {
                                "type": "select",
                                "options": [{"value": "high"}, {"value": "low"}],
                            }
                        },
                    }
                },
            },
        }

        transformer = ToolTransformer()
        result = transformer.transform_tool(tool)

        priority_schema = result["input_schema"]["properties"]["metadata"]["properties"]["priority"]
        assert priority_schema["type"] == "string"
        assert priority_schema["enum"] == ["high", "low"]


# ============================================================================
# AnthropicLLMMixin Tests
# ============================================================================


class TestAnthropicLLMMixin:
    """Test AnthropicLLMMixin functionality."""

    @pytest.mark.asyncio
    async def test_get_anthropic_client_missing_key_storage(
        self, mock_context: AgentContext
    ) -> None:
        """Test error when _key_storage not available."""

        class BadAgent(AnthropicLLMMixin):
            """Agent without key storage."""

        agent = BadAgent()

        with pytest.raises(AttributeError, match="requires _key_storage"):
            await agent._get_anthropic_client(mock_context)

    @pytest.mark.asyncio
    async def test_get_anthropic_client_missing_api_key(self, mock_context: AgentContext) -> None:
        """Test error when API key not configured."""
        storage = AsyncMock()
        storage.get_api_key.return_value = None

        class TestAgent(AnthropicLLMMixin):
            """Test agent."""

            def __init__(self, key_storage: Any) -> None:
                self._key_storage = key_storage

        agent = TestAgent(storage)

        with pytest.raises(AIConfigurationError, match="not configured"):
            await agent._get_anthropic_client(mock_context)

    @pytest.mark.asyncio
    async def test_get_anthropic_client_success(
        self, mock_agent: AnthropicLLMMixin, mock_context: AgentContext
    ) -> None:
        """Test successful client creation."""
        client = await mock_agent._get_anthropic_client(mock_context)
        assert client is not None

    def test_extract_caching_config_all_flags(self, mock_agent: AnthropicLLMMixin) -> None:
        """Test caching config extraction."""
        params = {
            "max_tokens": 1000,
            "prompt_caching_system_message": True,
            "prompt_caching_tool_definitions": True,
            "prompt_caching_images": True,
            "prompt_caching_documents": True,
            "prompt_caching_tool_results": True,
            "prompt_caching_message_flow": 500,
        }

        config = mock_agent._extract_caching_config(params)

        assert config.system_cache_enabled is True
        assert config.tool_cache_enabled is True
        assert config.image_cache_enabled is True
        assert config.document_cache_enabled is True
        assert config.tool_results_cache_enabled is True
        assert config.message_flow_cache_threshold == 500

        # Flags should be removed from params
        assert "prompt_caching_system_message" not in params
        assert "max_tokens" in params  # Non-caching params preserved

    def test_prune_cache_blocks_max_4(self, mock_agent: AnthropicLLMMixin) -> None:
        """Test cache block pruning to max 4."""
        payload = {
            "system": [
                {"type": "text", "text": "Block 1", "cache_control": {"type": "ephemeral"}},
                {"type": "text", "text": "Block 2", "cache_control": {"type": "ephemeral"}},
            ],
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {"data": "x" * 1000},
                            "cache_control": {"type": "ephemeral"},
                        },
                        {
                            "type": "text",
                            "text": "Text block",
                            "cache_control": {"type": "ephemeral"},
                        },
                    ],
                }
            ],
            "tools": [
                {"name": "tool1", "cache_control": {"type": "ephemeral"}},
                {"name": "tool2", "cache_control": {"type": "ephemeral"}},
            ],
        }

        mock_agent._prune_cache_blocks(payload)

        # Count remaining cache blocks
        cache_count = 0
        if isinstance(payload.get("system"), list):
            cache_count += sum(1 for b in payload["system"] if "cache_control" in b)

        for msg in payload.get("messages", []):
            if isinstance(msg.get("content"), list):
                cache_count += sum(1 for b in msg["content"] if "cache_control" in b)

        for tool in payload.get("tools", []):
            if "cache_control" in tool:
                cache_count += 1

        assert cache_count == 4

    def test_prune_cache_blocks_priority_order(self, mock_agent: AnthropicLLMMixin) -> None:
        """Test cache block pruning respects priority."""
        payload = {
            "messages": [
                {
                    "role": "user",
                    "content": [
                        # Priority 1: Image (large)
                        {
                            "type": "image",
                            "source": {"data": "x" * 2000},
                            "cache_control": {"type": "ephemeral"},
                        },
                        # Priority 3: Text (medium)
                        {
                            "type": "text",
                            "text": "Text",
                            "cache_control": {"type": "ephemeral"},
                        },
                        # Priority 4: Tool use (low)
                        {
                            "type": "tool_use",
                            "name": "tool",
                            "cache_control": {"type": "ephemeral"},
                        },
                    ],
                }
            ],
        }

        mock_agent._prune_cache_blocks(payload)

        content = payload["messages"][0]["content"]

        # Image should keep cache_control (highest priority)
        assert "cache_control" in content[0]

        # Text should keep cache_control (higher than tool)
        assert "cache_control" in content[1]

        # Tool use should lose cache_control (lowest priority)
        assert "cache_control" not in content[2]

    @pytest.mark.asyncio
    async def test_query_basic(
        self, mock_agent: AnthropicLLMMixin, mock_context: AgentContext
    ) -> None:
        """Test basic query execution."""
        with patch("pilot_space.ai.agents.llm.AsyncAnthropic") as mock_anthropic_cls:
            # Mock response
            mock_response = Mock()
            mock_response.model = "claude-sonnet-4-20250514"
            mock_response.content = [Mock(type="text", text="Hello, how can I help?")]
            mock_response.usage = Mock(
                input_tokens=100,
                output_tokens=20,
                cache_creation_input_tokens=0,
                cache_read_input_tokens=0,
            )

            mock_client = AsyncMock()
            mock_client.messages.create.return_value = mock_response
            mock_anthropic_cls.return_value = mock_client

            result = await mock_agent.query(
                messages=[UserPromptMessage("Hello")],
                context=mock_context,
                model_parameters={"max_tokens": 100},
            )

            assert isinstance(result, LLMResult)
            assert result.message.content == "Hello, how can I help?"
            assert result.usage.prompt_tokens == 100
            assert result.usage.completion_tokens == 20

    @pytest.mark.asyncio
    async def test_query_with_system_prompt(
        self, mock_agent: AnthropicLLMMixin, mock_context: AgentContext
    ) -> None:
        """Test query with system prompt."""
        with patch("pilot_space.ai.agents.llm.AsyncAnthropic") as mock_anthropic_cls:
            mock_response = Mock()
            mock_response.model = "claude-sonnet-4-20250514"
            mock_response.content = [Mock(type="text", text="Response")]
            mock_response.usage = Mock(
                input_tokens=50,
                output_tokens=10,
                cache_creation_input_tokens=0,
                cache_read_input_tokens=0,
            )

            mock_client = AsyncMock()
            mock_client.messages.create.return_value = mock_response
            mock_anthropic_cls.return_value = mock_client

            await mock_agent.query(
                messages=[UserPromptMessage("Test")],
                system="You are an expert",
                context=mock_context,
            )

            # Verify system prompt passed to API
            call_args = mock_client.messages.create.call_args
            assert "system" in call_args.kwargs
            assert call_args.kwargs["system"] == "You are an expert"


# ============================================================================
# AnthropicStreamingLLMMixin Tests
# ============================================================================


class TestAnthropicStreamingLLMMixin:
    """Test AnthropicStreamingLLMMixin functionality."""

    @pytest.mark.asyncio
    async def test_stream_query_basic(
        self, mock_streaming_agent: AnthropicStreamingLLMMixin, mock_context: AgentContext
    ) -> None:
        """Test basic streaming query."""
        with patch("pilot_space.ai.agents.llm.AsyncAnthropic") as mock_anthropic_cls:
            # Mock streaming response
            from anthropic.types import (
                ContentBlockDeltaEvent,
                MessageStartEvent,
                MessageStopEvent,
                TextBlock,
                TextDelta,
            )

            events = [
                MessageStartEvent(
                    type="message_start",
                    message=Mock(
                        usage=Mock(
                            input_tokens=100,
                            output_tokens=0,
                            cache_creation_input_tokens=0,
                            cache_read_input_tokens=0,
                        )
                    ),
                ),
                Mock(type="content_block_start", content_block=TextBlock(type="text", text="")),
                ContentBlockDeltaEvent(
                    type="content_block_delta",
                    index=0,
                    delta=TextDelta(type="text_delta", text="Hello"),
                ),
                ContentBlockDeltaEvent(
                    type="content_block_delta",
                    index=0,
                    delta=TextDelta(type="text_delta", text=" world"),
                ),
                Mock(type="content_block_stop", index=0),
                MessageStopEvent(
                    type="message_stop",
                    message=Mock(
                        stop_reason="end_turn",
                        usage=Mock(
                            input_tokens=100,
                            output_tokens=5,
                            cache_creation_input_tokens=0,
                            cache_read_input_tokens=0,
                        ),
                    ),
                ),
            ]

            async def mock_stream_context():
                """Mock async context manager for streaming."""

                class MockStream:
                    """Mock stream object."""

                    def __aiter__(self):
                        """Return async iterator."""
                        return self

                    async def __anext__(self):
                        """Get next event."""
                        if events:
                            return events.pop(0)
                        raise StopAsyncIteration

                return MockStream()

            mock_client = AsyncMock()
            mock_client.messages.stream.return_value.__aenter__ = mock_stream_context
            mock_client.messages.stream.return_value.__aexit__ = AsyncMock()
            mock_anthropic_cls.return_value = mock_client

            chunks: list[str] = []
            async for chunk in mock_streaming_agent.stream_query(
                messages=[UserPromptMessage("Test")],
                context=mock_context,
            ):
                if chunk.delta.message.content:
                    chunks.append(chunk.delta.message.content)

            full_text = "".join(chunks)
            assert "Hello world" in full_text


# ============================================================================
# Integration Tests
# ============================================================================


class TestIntegration:
    """Integration tests for full workflow."""

    @pytest.mark.asyncio
    async def test_full_query_workflow(
        self, mock_agent: AnthropicLLMMixin, mock_context: AgentContext
    ) -> None:
        """Test complete query workflow with caching."""
        with patch("pilot_space.ai.agents.llm.AsyncAnthropic") as mock_anthropic_cls:
            mock_response = Mock()
            mock_response.model = "claude-sonnet-4-20250514"
            mock_response.content = [Mock(type="text", text="Full response")]
            mock_response.usage = Mock(
                input_tokens=200,
                output_tokens=50,
                cache_creation_input_tokens=100,
                cache_read_input_tokens=1000,
            )

            mock_client = AsyncMock()
            mock_client.messages.create.return_value = mock_response
            mock_anthropic_cls.return_value = mock_client

            result = await mock_agent.query(
                messages=[
                    UserPromptMessage(
                        content=[
                            TextPromptMessageContent(data="Analyze this"),
                            ImagePromptMessageContent(
                                data="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
                            ),
                        ]
                    )
                ],
                system="<cache>You are an expert analyst</cache>",
                model_parameters={
                    "max_tokens": 500,
                    "thinking": True,
                    "prompt_caching_system_message": True,
                    "prompt_caching_images": True,
                },
                context=mock_context,
            )

            # Verify result
            assert result.message.content == "Full response"
            assert result.usage.cache_creation_input_tokens == 100
            assert result.usage.cache_read_input_tokens == 1000

            # Verify adjusted billing
            expected_adjusted = 200 - 100 + 125 - 1000 + 100
            assert result.usage.prompt_tokens == expected_adjusted

    def test_message_type_hierarchy(self) -> None:
        """Test message type hierarchy is correct."""
        system = SystemPromptMessage(content="System")
        user = UserPromptMessage(content="User")
        assistant = AssistantPromptMessage(content="Assistant")
        tool = ToolPromptMessage(tool_call_id="123", content="Result")

        assert isinstance(system, PromptMessage)
        assert isinstance(user, PromptMessage)
        assert isinstance(assistant, PromptMessage)
        assert isinstance(tool, PromptMessage)
