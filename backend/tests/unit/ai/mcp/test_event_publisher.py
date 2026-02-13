"""Unit tests for EventPublisher (event_publisher.py)."""

from __future__ import annotations

import asyncio
import json

import pytest

from pilot_space.ai.mcp.event_publisher import EventPublisher


def _parse_sse(raw: str) -> dict:
    """Parse SSE event string into {event, data} dict."""
    lines = raw.strip().split("\n")
    event_type = ""
    data_str = ""
    for line in lines:
        if line.startswith("event: "):
            event_type = line[7:]
        elif line.startswith("data: "):
            data_str = line[6:]
    return {"event": event_type, "data": json.loads(data_str)}


class TestPublishContentUpdate:
    @pytest.mark.asyncio
    async def test_emits_content_update_event(self) -> None:
        queue: asyncio.Queue[str] = asyncio.Queue()
        pub = EventPublisher(queue)

        await pub.publish_content_update({"op": "replace", "id": "123"})

        raw = queue.get_nowait()
        parsed = _parse_sse(raw)
        assert parsed["event"] == "content_update"
        assert parsed["data"]["op"] == "replace"


class TestPublishApprovalRequest:
    @pytest.mark.asyncio
    async def test_emits_approval_request_event(self) -> None:
        queue: asyncio.Queue[str] = asyncio.Queue()
        pub = EventPublisher(queue)

        await pub.publish_approval_request({"action": "delete"})

        raw = queue.get_nowait()
        parsed = _parse_sse(raw)
        assert parsed["event"] == "approval_request"
        assert parsed["data"]["action"] == "delete"


class TestPublishFocusBlock:
    @pytest.mark.asyncio
    async def test_emits_focus_block_with_block_id(self) -> None:
        queue: asyncio.Queue[str] = asyncio.Queue()
        pub = EventPublisher(queue)

        await pub.publish_focus_block("note-1", "block-1")

        raw = queue.get_nowait()
        parsed = _parse_sse(raw)
        assert parsed["event"] == "focus_block"
        assert parsed["data"]["noteId"] == "note-1"
        assert parsed["data"]["blockId"] == "block-1"
        assert parsed["data"]["scrollToEnd"] is False

    @pytest.mark.asyncio
    async def test_emits_focus_block_with_scroll_to_end(self) -> None:
        queue: asyncio.Queue[str] = asyncio.Queue()
        pub = EventPublisher(queue)

        await pub.publish_focus_block("note-1", None, scroll_to_end=True)

        raw = queue.get_nowait()
        parsed = _parse_sse(raw)
        assert parsed["event"] == "focus_block"
        assert parsed["data"]["scrollToEnd"] is True

    @pytest.mark.asyncio
    async def test_skips_when_no_block_and_no_scroll(self) -> None:
        queue: asyncio.Queue[str] = asyncio.Queue()
        pub = EventPublisher(queue)

        await pub.publish_focus_block("note-1", None, scroll_to_end=False)

        assert queue.empty()


class TestPublishFocusAndContent:
    @pytest.mark.asyncio
    async def test_emits_focus_then_content_atomically(self) -> None:
        queue: asyncio.Queue[str] = asyncio.Queue()
        pub = EventPublisher(queue)

        await pub.publish_focus_and_content("note-1", "block-1", {"op": "replace"})

        events = []
        while not queue.empty():
            events.append(_parse_sse(queue.get_nowait()))

        assert len(events) == 2
        assert events[0]["event"] == "focus_block"
        assert events[1]["event"] == "content_update"

    @pytest.mark.asyncio
    async def test_skips_focus_when_no_block_and_no_scroll(self) -> None:
        queue: asyncio.Queue[str] = asyncio.Queue()
        pub = EventPublisher(queue)

        await pub.publish_focus_and_content("note-1", None, {"op": "replace"})

        events = []
        while not queue.empty():
            events.append(_parse_sse(queue.get_nowait()))

        assert len(events) == 1
        assert events[0]["event"] == "content_update"

    @pytest.mark.asyncio
    async def test_scroll_to_end_with_null_block(self) -> None:
        queue: asyncio.Queue[str] = asyncio.Queue()
        pub = EventPublisher(queue)

        await pub.publish_focus_and_content("note-1", None, {"op": "append"}, scroll_to_end=True)

        events = []
        while not queue.empty():
            events.append(_parse_sse(queue.get_nowait()))

        assert len(events) == 2
        assert events[0]["event"] == "focus_block"
        assert events[0]["data"]["scrollToEnd"] is True
        assert events[1]["event"] == "content_update"


class TestPublishRaw:
    @pytest.mark.asyncio
    async def test_publish_raw_string(self) -> None:
        queue: asyncio.Queue[str] = asyncio.Queue()
        pub = EventPublisher(queue)

        raw = "event: custom\ndata: {}\n\n"
        await pub.publish(raw)

        assert queue.get_nowait() == raw
