"""Unit tests for PilotSpace stream utility functions.

Tests build_structured_content, capture_content_from_sse, helper functions
extracted from pilotspace_agent.py, and merge_sdk_and_queue concurrent merge.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from pilot_space.ai.agents.pilotspace_stream_utils import (
    build_structured_content,
    capture_content_from_sse,
    classify_effort,
    detect_skill_from_message,
    merge_sdk_and_queue,
)


class TestBuildStructuredContent:
    """Test structured content building for session persistence."""

    def test_empty_blocks_returns_empty_string(self) -> None:
        """No content blocks produces empty string."""
        assert build_structured_content({}) == ""

    def test_text_only_returns_plain_string(self) -> None:
        """Text-only blocks return concatenated plain text."""
        blocks: dict[str, dict[str, Any]] = {
            "text_0": {"type": "text", "text": "Hello ", "index": 0},
            "text_1": {"type": "text", "text": "world", "index": 1},
        }
        result = build_structured_content(blocks)
        assert result == "Hello world"

    def test_thinking_with_signature_preserved(self) -> None:
        """Thinking blocks WITH signatures are included in output."""
        blocks: dict[str, dict[str, Any]] = {
            "thinking_0": {
                "type": "thinking",
                "thinking": "Let me analyze...",
                "signature": "EqoB_valid",
                "index": 0,
            },
            "text_1": {"type": "text", "text": "Here is my answer", "index": 1},
        }
        result = build_structured_content(blocks)
        assert isinstance(result, list)
        types = [b["type"] for b in result]
        assert "thinking" in types

    def test_thinking_without_signature_stripped(self) -> None:
        """Thinking blocks WITHOUT signatures are dropped to prevent API errors."""
        blocks: dict[str, dict[str, Any]] = {
            "thinking_0": {
                "type": "thinking",
                "thinking": "Incomplete thinking...",
                "index": 0,
            },
            "text_1": {"type": "text", "text": "Answer", "index": 1},
            "tool_use_abc": {
                "type": "tool_use",
                "id": "abc",
                "name": "skill",
                "input": {},
                "index": 2,
            },
        }
        result = build_structured_content(blocks)
        assert isinstance(result, list)
        types = [b["type"] for b in result]
        assert "thinking" not in types
        assert "text" in types
        assert "tool_use" in types

    def test_tool_use_and_result_preserved(self) -> None:
        """Tool use and result blocks are always preserved."""
        blocks: dict[str, dict[str, Any]] = {
            "tool_use_t1": {
                "type": "tool_use",
                "id": "t1",
                "name": "extract_issues",
                "input": {},
                "index": 0,
            },
            "tool_result_t1": {
                "type": "tool_result",
                "tool_use_id": "t1",
                "content": "Success",
                "is_error": False,
                "index": 1,
            },
        }
        result = build_structured_content(blocks)
        assert isinstance(result, list)
        assert len(result) == 2

    def test_index_field_removed_from_output(self) -> None:
        """Internal index field is stripped from persisted blocks."""
        blocks: dict[str, dict[str, Any]] = {
            "text_0": {"type": "text", "text": "Hello", "index": 0},
            "tool_use_t1": {
                "type": "tool_use",
                "id": "t1",
                "name": "read",
                "input": {},
                "index": 1,
            },
        }
        result = build_structured_content(blocks)
        assert isinstance(result, list)
        for block in result:
            assert "index" not in block


class TestCaptureContentFromSSE:
    """Test SSE event capture for session persistence."""

    def test_capture_thinking_delta_with_signature(self) -> None:
        """Thinking delta with signature field captures signature."""
        blocks: dict[str, dict[str, Any]] = {}
        sse = (
            "event: thinking_delta\n"
            'data: {"messageId": "m1", "signature": "EqoB_sig", "blockIndex": 0}\n\n'
        )
        capture_content_from_sse(sse, blocks)

        assert "thinking_0" in blocks
        assert blocks["thinking_0"]["signature"] == "EqoB_sig"

    def test_capture_thinking_delta_text(self) -> None:
        """Thinking delta with text accumulates content."""
        blocks: dict[str, dict[str, Any]] = {}
        sse1 = 'event: thinking_delta\ndata: {"messageId": "m1", "delta": "Let me ", "blockIndex": 0}\n\n'
        sse2 = 'event: thinking_delta\ndata: {"messageId": "m1", "delta": "think...", "blockIndex": 0}\n\n'
        capture_content_from_sse(sse1, blocks)
        capture_content_from_sse(sse2, blocks)

        assert blocks["thinking_0"]["thinking"] == "Let me think..."

    def test_capture_tool_use(self) -> None:
        """Tool use events are captured with correct structure."""
        blocks: dict[str, dict[str, Any]] = {}
        sse = (
            "event: tool_use\n"
            'data: {"toolCallId": "t1", "toolName": "extract_issues", "toolInput": {"note_id": "n1"}}\n\n'
        )
        capture_content_from_sse(sse, blocks)

        assert "tool_use_t1" in blocks
        assert blocks["tool_use_t1"]["name"] == "extract_issues"

    def test_capture_tool_result_error(self) -> None:
        """Failed tool results capture error state."""
        blocks: dict[str, dict[str, Any]] = {}
        sse = (
            "event: tool_result\n"
            'data: {"toolCallId": "t1", "status": "failed", "errorMessage": "No such tool"}\n\n'
        )
        capture_content_from_sse(sse, blocks)

        assert "tool_result_t1" in blocks
        assert blocks["tool_result_t1"]["is_error"] is True


class TestClassifyEffort:
    """Test effort classification for SDK configuration."""

    def test_greeting_is_low(self) -> None:
        assert classify_effort("hello") == "low"

    def test_long_message_is_high(self) -> None:
        assert classify_effort("x" * 201) == "high"

    def test_complex_keyword_is_high(self) -> None:
        assert classify_effort("please analyze the codebase") == "high"

    def test_normal_message_is_none(self) -> None:
        assert classify_effort("update the title of this note") is None


class TestDetectSkill:
    """Test slash-command skill detection."""

    def test_detects_slash_command(self) -> None:
        assert detect_skill_from_message("/extract-issues from this note") == "extract-issues"

    def test_no_slash_returns_none(self) -> None:
        assert detect_skill_from_message("extract issues from this note") is None

    def test_empty_slash_returns_none(self) -> None:
        assert detect_skill_from_message("/") is None


# ---------------------------------------------------------------------------
# merge_sdk_and_queue
# ---------------------------------------------------------------------------


async def _async_iter_from_list(items: list[Any]):
    """Helper: create an async iterator from a list."""
    for item in items:
        yield item


class TestMergeSdkAndQueue:
    """Test concurrent SDK + queue stream merge."""

    @pytest.mark.asyncio
    async def test_sdk_items_yielded_as_sdk_source(self) -> None:
        """SDK messages appear with source='sdk'."""
        sdk_iter = _async_iter_from_list(["msg1", "msg2"])
        tool_queue: asyncio.Queue[str] = asyncio.Queue()

        results = []
        async for source, item in merge_sdk_and_queue(sdk_iter, tool_queue):
            results.append((source, item))

        assert ("sdk", "msg1") in results
        assert ("sdk", "msg2") in results

    @pytest.mark.asyncio
    async def test_queue_items_yielded_as_queue_source(self) -> None:
        """Queue events appear with source='queue'."""
        sdk_iter = _async_iter_from_list(["msg1"])
        tool_queue: asyncio.Queue[str] = asyncio.Queue()
        await tool_queue.put("approval_event_sse")

        results = []
        async for source, item in merge_sdk_and_queue(sdk_iter, tool_queue):
            results.append((source, item))

        assert ("queue", "approval_event_sse") in results
        assert ("sdk", "msg1") in results

    @pytest.mark.asyncio
    async def test_finishes_when_sdk_exhausted(self) -> None:
        """Generator stops when SDK iterator is done, even if queue has items."""
        sdk_iter = _async_iter_from_list([])
        tool_queue: asyncio.Queue[str] = asyncio.Queue()

        results = []
        async for source, item in merge_sdk_and_queue(sdk_iter, tool_queue):
            results.append((source, item))

        # Should terminate with no items since SDK is empty
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_interleaved_sdk_and_queue(self) -> None:
        """SDK and queue items can interleave."""

        async def _slow_sdk():
            yield "sdk_1"
            await asyncio.sleep(0.05)
            yield "sdk_2"

        tool_queue: asyncio.Queue[str] = asyncio.Queue()

        results: list[tuple[str, Any]] = []

        async def _producer():
            await asyncio.sleep(0.02)
            await tool_queue.put("queue_event")

        producer_task = asyncio.create_task(_producer())

        async for source, item in merge_sdk_and_queue(_slow_sdk(), tool_queue):
            results.append((source, item))

        await producer_task

        sources = [s for s, _ in results]
        assert "sdk" in sources
        assert "queue" in sources
