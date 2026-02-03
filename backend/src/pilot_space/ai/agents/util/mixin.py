"""Anthropic LLM mixins for agent integration.

Provides unified query() and stream_query() interfaces for all agents with:
- Automatic API key retrieval
- Prompt caching support
- Tool transformation
- Cache block pruning
- Extended thinking support
- Cost tracking with cache adjustments
"""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any

from anthropic import AsyncAnthropic

from pilot_space.ai.sdk.config import MODEL_SONNET

from .caching import CachingConfig, PromptCachingHandler
from .converter import MessageConverter
from .messages import (
    AssistantPromptMessage,
    LLMResult,
    LLMResultChunk,
    LLMUsage,
    PromptMessage,
    SystemPromptMessage,
)
from .streaming import StreamingHandler
from .transformer import ToolTransformer

if TYPE_CHECKING:
    from pilot_space.ai.agents.agent_base import AgentContext

logger = logging.getLogger(__name__)


class AnthropicLLMMixin:
    """Mixin providing non-streaming Anthropic API access.

    Features:
    - Unified query() interface for all agents
    - Automatic API key retrieval from secure storage
    - Prompt caching support with all flags
    - Tool transformation and cache block pruning
    - Extended thinking support
    - Cost tracking with cache adjustments

    Usage:
        class MyAgent(SDKBaseAgent, AnthropicLLMMixin):
            async def execute(self, input_data, context):
                result = await self.query(
                    messages=[UserPromptMessage("Analyze...")],
                    system="You are an expert",
                    model_parameters={
                        "max_tokens": 2048,
                        "thinking": True,
                        "prompt_caching_system_message": True,
                    },
                    context=context,
                )
                return result.message.content
    """

    async def query(
        self,
        messages: list[PromptMessage],
        context: AgentContext,
        system: str | None = None,
        tools: list[dict] | None = None,
        model_parameters: dict[str, Any] | None = None,
        stop: list[str] | None = None,
    ) -> LLMResult:
        """Execute non-streaming query.

        Args:
            messages: Conversation messages
            context: Agent context (workspace_id, user_id)
            system: System prompt (supports <cache> tags)
            tools: MCP tools to transform
            model_parameters: Model params + caching flags
            stop: Stop sequences

        Returns:
            LLMResult with response and usage
        """
        model_parameters = model_parameters or {}

        # Extract caching config
        caching_config = self._extract_caching_config(model_parameters)

        # Get API client
        client = await self._get_anthropic_client(context)

        # Prepare messages with system override if provided
        prep_messages = list(messages)
        if system:
            # Inject system message at start
            prep_messages = [SystemPromptMessage(content=system)] + [
                m for m in prep_messages if not isinstance(m, SystemPromptMessage)
            ]

        # Convert messages
        converter = MessageConverter(caching_config)
        system_prompt, api_messages = converter.convert_messages(prep_messages)

        # Transform tools
        transformed_tools = None
        if tools:
            transformer = ToolTransformer(caching_config.tool_cache_enabled)
            transformed_tools = [transformer.transform_tool(t) for t in tools]

        # Build request payload
        payload = {
            "model": self.DEFAULT_MODEL if hasattr(self, "DEFAULT_MODEL") else MODEL_SONNET,
            "messages": api_messages,
            **model_parameters,
        }

        if system_prompt:
            payload["system"] = system_prompt

        if transformed_tools:
            payload["tools"] = transformed_tools

        if stop:
            payload["stop_sequences"] = stop

        # Prune cache blocks to max 4
        self._prune_cache_blocks(payload)

        # Call API
        response = await client.messages.create(**payload)  # type: ignore[arg-type]

        # Extract response
        assistant_message = AssistantPromptMessage(content="", tool_calls=[])

        for content_block in response.content:
            if content_block.type == "text":
                assistant_message.content = content_block.text
            elif content_block.type == "tool_use":
                tool_call = AssistantPromptMessage.ToolCall(
                    id=content_block.id,
                    type="function",
                    function=AssistantPromptMessage.ToolCall.ToolCallFunction(
                        name=content_block.name, arguments=json.dumps(content_block.input)
                    ),
                )
                assistant_message.tool_calls.append(tool_call)

        # Calculate cache-adjusted usage
        cache_creation_tokens = 0
        cache_read_tokens = 0
        if response.usage:
            if hasattr(response.usage, "cache_creation_input_tokens"):
                cache_creation_tokens = response.usage.cache_creation_input_tokens or 0
            if hasattr(response.usage, "cache_read_input_tokens"):
                cache_read_tokens = response.usage.cache_read_input_tokens or 0

        input_tokens = response.usage.input_tokens if response.usage else 0
        output_tokens = response.usage.output_tokens if response.usage else 0

        adjusted_prompt_tokens = PromptCachingHandler.calc_adjusted_prompt_tokens(
            input_tokens,
            cache_creation_tokens,
            cache_read_tokens,
        )

        usage = LLMUsage(
            prompt_tokens=adjusted_prompt_tokens,
            completion_tokens=output_tokens,
            total_tokens=adjusted_prompt_tokens + output_tokens,
            cost_usd=0.0,  # Will be calculated by cost tracker
            cache_creation_input_tokens=cache_creation_tokens,
            cache_read_input_tokens=cache_read_tokens,
        )

        # Track usage if agent has cost tracking
        if hasattr(self, "track_usage"):
            await self.track_usage(  # type: ignore[attr-defined]
                context,
                adjusted_prompt_tokens,
                output_tokens,
            )

        return LLMResult(
            model=response.model,
            prompt_messages=list(messages),
            message=assistant_message,
            usage=usage,
        )

    async def _get_anthropic_client(self, context: AgentContext) -> AsyncAnthropic:
        """Get configured Anthropic client.

        Retrieves API key from self._key_storage (injected via __init__)
        """
        if not hasattr(self, "_key_storage"):
            raise AttributeError(
                "AnthropicLLMMixin requires _key_storage. Ensure agent __init__ stores key_storage."
            )

        from pilot_space.ai.exceptions import AIConfigurationError

        api_key = await self._key_storage.get_api_key(  # type: ignore[attr-defined]
            workspace_id=context.workspace_id,
            provider="anthropic",
        )
        if not api_key:
            raise AIConfigurationError(
                f"Anthropic API key not configured for workspace {context.workspace_id}",
                provider="anthropic",
                missing_fields=["api_key"],
            )

        return AsyncAnthropic(api_key=api_key)

    def _extract_caching_config(self, model_parameters: dict[str, Any]) -> CachingConfig:
        """Extract caching flags from model_parameters."""
        return CachingConfig(
            system_cache_enabled=model_parameters.pop("prompt_caching_system_message", False),
            tool_cache_enabled=model_parameters.pop("prompt_caching_tool_definitions", False),
            image_cache_enabled=model_parameters.pop("prompt_caching_images", False),
            document_cache_enabled=model_parameters.pop("prompt_caching_documents", False),
            tool_results_cache_enabled=model_parameters.pop("prompt_caching_tool_results", False),
            message_flow_cache_threshold=int(
                model_parameters.pop("prompt_caching_message_flow", 0) or 0
            ),
        )

    def _prune_cache_blocks(self, payload: dict) -> None:
        """Prune cache_control blocks to max 4 by priority.

        Priority (lower = higher):
        1. Images/Documents (large data)
        2. System message blocks
        3. Text content blocks
        4. Tool use/results/definitions
        """
        blocks: list[tuple[int, int, dict]] = []  # (priority, -length, block)

        # Collect all blocks with cache_control

        # 1. System blocks
        if isinstance(payload.get("system"), list):
            for block in payload["system"]:
                if isinstance(block, dict) and "cache_control" in block:
                    text_len = len(block.get("text", ""))
                    blocks.append((2, -text_len, block))

        # 2. Message content blocks
        for msg in payload.get("messages", []):
            content = msg.get("content")
            if isinstance(content, list):
                for block in content:
                    if not isinstance(block, dict) or "cache_control" not in block:
                        continue

                    btype = block.get("type")
                    if btype in {"image", "document"}:
                        data_len = len(block.get("source", {}).get("data", ""))
                        blocks.append((1, -data_len, block))
                    elif btype in {"tool_use", "tool_result"}:
                        blocks.append((4, 0, block))
                    else:  # text
                        text_len = len(block.get("text", ""))
                        blocks.append((3, -text_len, block))

        # 3. Tool definitions
        for tool in payload.get("tools", []):
            if isinstance(tool, dict) and "cache_control" in tool:
                blocks.append((4, 0, tool))

        # Sort by priority, then by length (descending)
        blocks.sort(key=lambda x: (x[0], x[1]))

        # Keep first 4, remove cache_control from rest
        for idx, (_, _, block) in enumerate(blocks):
            if idx >= 4:
                block.pop("cache_control", None)


class AnthropicStreamingLLMMixin(AnthropicLLMMixin):
    """Extends mixin with streaming support.

    Usage:
        class MyStreamingAgent(StreamingSDKBaseAgent, AnthropicStreamingLLMMixin):
            async def stream(self, input_data, context):
                async for chunk in self.stream_query(
                    messages=[UserPromptMessage("Generate...")],
                    system="You are an expert",
                    model_parameters={
                        "thinking": True,
                        "prompt_caching_system_message": True,
                    },
                    context=context,
                ):
                    yield chunk.delta.message.content
    """

    async def stream_query(
        self,
        messages: list[PromptMessage],
        context: AgentContext,
        system: str | None = None,
        tools: list[dict] | None = None,
        model_parameters: dict[str, Any] | None = None,
        stop: list[str] | None = None,
    ) -> AsyncIterator[LLMResultChunk]:
        """Execute streaming query.

        Args:
            Same as query()

        Yields:
            LLMResultChunk with incremental deltas
        """
        model_parameters = model_parameters or {}

        # Extract caching config
        caching_config = self._extract_caching_config(model_parameters)

        # Get API client
        client = await self._get_anthropic_client(context)

        # Prepare messages with system override if provided
        prep_messages = list(messages)
        if system:
            prep_messages = [SystemPromptMessage(content=system)] + [
                m for m in prep_messages if not isinstance(m, SystemPromptMessage)
            ]

        # Convert messages
        converter = MessageConverter(caching_config)
        system_prompt, api_messages = converter.convert_messages(prep_messages)

        # Transform tools
        transformed_tools = None
        if tools:
            transformer = ToolTransformer(caching_config.tool_cache_enabled)
            transformed_tools = [transformer.transform_tool(t) for t in tools]

        # Build request payload
        payload = {
            "model": self.DEFAULT_MODEL if hasattr(self, "DEFAULT_MODEL") else MODEL_SONNET,
            "messages": api_messages,
            "stream": True,
            **model_parameters,
        }

        if system_prompt:
            payload["system"] = system_prompt

        if transformed_tools:
            payload["tools"] = transformed_tools

        if stop:
            payload["stop_sequences"] = stop

        # Prune cache blocks to max 4
        self._prune_cache_blocks(payload)

        # Call API with streaming
        response = await client.messages.create(**payload)  # type: ignore[arg-type]

        # Handle streaming with StreamingHandler
        handler = StreamingHandler()
        final_usage = None

        async for chunk in handler.handle_stream(
            response,
            messages,
            payload["model"],
            {},  # credentials not needed for cost tracking here
        ):
            # Track final usage
            if chunk.delta.usage:
                final_usage = chunk.delta.usage

            yield chunk

        # Track usage if agent has cost tracking
        if final_usage and hasattr(self, "track_usage"):
            await self.track_usage(  # type: ignore[attr-defined]
                context,
                final_usage.prompt_tokens,
                final_usage.completion_tokens,
            )
