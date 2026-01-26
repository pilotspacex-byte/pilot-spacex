"""Unit tests for SSE streaming utilities."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from pilot_space.api.v1.streaming import (
    create_json_sse_response,
    create_sse_response,
    format_sse_event,
    sse_json_stream_generator,
    sse_stream_generator,
)


class TestFormatSSEEvent:
    """Test suite for format_sse_event function."""

    def test_creates_valid_sse_format(self) -> None:
        """Verify SSE format with event and data fields."""
        event = format_sse_event("token", {"content": "hello"})

        assert event.startswith("event: token\n")
        assert "data: " in event
        assert event.endswith("\n\n")

    def test_json_encodes_data(self) -> None:
        """Verify data payload is JSON-encoded."""
        event = format_sse_event("done", {"status": "complete", "count": 42})

        assert '"status": "complete"' in event
        assert '"count": 42' in event

    def test_handles_unicode(self) -> None:
        """Verify unicode characters are preserved."""
        event = format_sse_event("token", {"content": "こんにちは"})

        assert "こんにちは" in event

    def test_handles_empty_data(self) -> None:
        """Verify empty data dict is handled."""
        event = format_sse_event("ping", {})

        assert "event: ping\n" in event
        assert "data: {}\n\n" in event

    def test_handles_nested_objects(self) -> None:
        """Verify nested objects are serialized."""
        event = format_sse_event(
            "data",
            {
                "user": {"id": 123, "name": "Test"},
                "metadata": {"tags": ["a", "b"]},
            },
        )

        assert '"user"' in event
        assert '"id": 123' in event
        assert '"tags": ["a", "b"]' in event


class TestSSEStreamGenerator:
    """Test suite for sse_stream_generator function."""

    @pytest.mark.asyncio
    async def test_yields_token_events(self) -> None:
        """Verify token events are generated for each chunk."""

        async def mock_stream() -> AsyncIterator[str]:
            yield "hello"
            yield " world"

        request = MagicMock()
        request.is_disconnected = AsyncMock(return_value=False)

        events = []
        async for event in sse_stream_generator(mock_stream(), request):
            events.append(event)

        assert len(events) == 3  # 2 tokens + 1 done
        assert '"content": "hello"' in events[0]
        assert '"content": " world"' in events[1]
        assert '"status": "complete"' in events[2]

    @pytest.mark.asyncio
    async def test_emits_done_event_on_completion(self) -> None:
        """Verify done event is emitted after stream completes."""

        async def mock_stream() -> AsyncIterator[str]:
            yield "data"

        request = MagicMock()
        request.is_disconnected = AsyncMock(return_value=False)

        events = []
        async for event in sse_stream_generator(mock_stream(), request):
            events.append(event)

        last_event = events[-1]
        assert "event: done\n" in last_event
        assert '"status": "complete"' in last_event

    @pytest.mark.asyncio
    async def test_stops_on_client_disconnect(self) -> None:
        """Verify streaming stops when client disconnects (no done event)."""

        async def mock_stream() -> AsyncIterator[str]:
            yield "chunk1"
            yield "chunk2"
            yield "chunk3"

        request = MagicMock()
        # Disconnect is checked after each yield
        # So all 3 chunks will be yielded, but done event is suppressed
        disconnect_sequence = [False, False, True]
        request.is_disconnected = AsyncMock(side_effect=disconnect_sequence)

        events = []
        async for event in sse_stream_generator(mock_stream(), request):
            events.append(event)

        # All 3 chunks yielded, but NO done event (that's the key test)
        assert len(events) == 3
        assert all("event: token" in e for e in events)
        # Verify no done event was emitted
        assert not any("event: done" in e for e in events)

    @pytest.mark.asyncio
    async def test_handles_error_chunks(self) -> None:
        """Verify ERROR: prefixed chunks are converted to error events."""

        async def mock_stream() -> AsyncIterator[str]:
            yield "hello"
            yield "ERROR: Something went wrong"

        request = MagicMock()
        request.is_disconnected = AsyncMock(return_value=False)

        events = []
        async for event in sse_stream_generator(mock_stream(), request):
            events.append(event)

        assert len(events) == 2
        assert "event: token" in events[0]
        assert "event: error" in events[1]
        assert "Something went wrong" in events[1]
        assert '"type": "agent_error"' in events[1]

    @pytest.mark.asyncio
    async def test_error_chunk_terminates_stream(self) -> None:
        """Verify ERROR: chunk stops streaming without done event."""

        async def mock_stream() -> AsyncIterator[str]:
            yield "hello"
            yield "ERROR: Failed"
            yield "should not reach"

        request = MagicMock()
        request.is_disconnected = AsyncMock(return_value=False)

        events = []
        async for event in sse_stream_generator(mock_stream(), request):
            events.append(event)

        # Should get token + error, no done event
        assert len(events) == 2
        assert "event: error" in events[1]

    @pytest.mark.asyncio
    async def test_handles_exception(self) -> None:
        """Verify exceptions are converted to error events."""

        async def mock_stream() -> AsyncIterator[str]:
            yield "hello"
            raise ValueError("Test error")

        request = MagicMock()
        request.is_disconnected = AsyncMock(return_value=False)

        events = []
        async for event in sse_stream_generator(mock_stream(), request):
            events.append(event)

        assert len(events) == 2
        assert "event: token" in events[0]
        assert "event: error" in events[1]
        assert "Test error" in events[1]
        assert "ValueError" in events[1]

    @pytest.mark.asyncio
    async def test_handles_empty_stream(self) -> None:
        """Verify empty stream only emits done event."""

        async def mock_stream() -> AsyncIterator[str]:
            return
            yield  # Make it an async generator

        request = MagicMock()
        request.is_disconnected = AsyncMock(return_value=False)

        events = []
        async for event in sse_stream_generator(mock_stream(), request):
            events.append(event)

        assert len(events) == 1
        assert "event: done" in events[0]

    @pytest.mark.asyncio
    async def test_handles_multiple_error_chunks(self) -> None:
        """Verify only first ERROR: chunk is processed."""

        async def mock_stream() -> AsyncIterator[str]:
            yield "ERROR: First error"
            yield "ERROR: Second error"

        request = MagicMock()
        request.is_disconnected = AsyncMock(return_value=False)

        events = []
        async for event in sse_stream_generator(mock_stream(), request):
            events.append(event)

        # Should only get first error
        assert len(events) == 1
        assert "First error" in events[0]


class TestSSEJSONStreamGenerator:
    """Test suite for sse_json_stream_generator function."""

    @pytest.mark.asyncio
    async def test_yields_json_events(self) -> None:
        """Verify structured data events are generated."""

        async def mock_stream() -> AsyncIterator[dict[str, object]]:
            yield {"value": "hello", "count": 1}
            yield {"value": "world", "count": 2}

        request = MagicMock()
        request.is_disconnected = AsyncMock(return_value=False)

        events = []
        async for event in sse_json_stream_generator(mock_stream(), request):
            events.append(event)

        assert len(events) == 3  # 2 data + 1 done
        assert '"value": "hello"' in events[0]
        assert '"count": 1' in events[0]
        assert '"value": "world"' in events[1]

    @pytest.mark.asyncio
    async def test_respects_event_type_field(self) -> None:
        """Verify _event field controls event type."""

        async def mock_stream() -> AsyncIterator[dict[str, object]]:
            yield {"_event": "progress", "percent": 50}
            yield {"_event": "result", "value": "done"}

        request = MagicMock()
        request.is_disconnected = AsyncMock(return_value=False)

        events = []
        async for event in sse_json_stream_generator(mock_stream(), request):
            events.append(event)

        assert "event: progress\n" in events[0]
        assert '"percent": 50' in events[0]
        assert "event: result\n" in events[1]
        assert '"value": "done"' in events[1]

    @pytest.mark.asyncio
    async def test_removes_event_field_from_data(self) -> None:
        """Verify _event field is removed from payload."""

        async def mock_stream() -> AsyncIterator[dict[str, object]]:
            yield {"_event": "custom", "data": "value"}

        request = MagicMock()
        request.is_disconnected = AsyncMock(return_value=False)

        events = []
        async for event in sse_json_stream_generator(mock_stream(), request):
            events.append(event)

        # _event should not appear in data
        assert '"_event"' not in events[0]
        assert '"data": "value"' in events[0]

    @pytest.mark.asyncio
    async def test_defaults_to_data_event_type(self) -> None:
        """Verify default event type is 'data'."""

        async def mock_stream() -> AsyncIterator[dict[str, object]]:
            yield {"value": "test"}

        request = MagicMock()
        request.is_disconnected = AsyncMock(return_value=False)

        events = []
        async for event in sse_json_stream_generator(mock_stream(), request):
            events.append(event)

        assert "event: data\n" in events[0]

    @pytest.mark.asyncio
    async def test_stops_on_client_disconnect(self) -> None:
        """Verify JSON stream stops on disconnect (no done event)."""

        async def mock_stream() -> AsyncIterator[dict[str, object]]:
            yield {"value": 1}
            yield {"value": 2}
            yield {"value": 3}

        request = MagicMock()
        disconnect_sequence = [False, False, True]
        request.is_disconnected = AsyncMock(side_effect=disconnect_sequence)

        events = []
        async for event in sse_json_stream_generator(mock_stream(), request):
            events.append(event)

        # All 3 data events yielded, but NO done event
        assert len(events) == 3
        assert all("event: data" in e for e in events)
        # Verify no done event was emitted
        assert not any("event: done" in e for e in events)

    @pytest.mark.asyncio
    async def test_handles_exception(self) -> None:
        """Verify exceptions in JSON stream are handled."""

        async def mock_stream() -> AsyncIterator[dict[str, object]]:
            yield {"value": "test"}
            raise RuntimeError("Stream failed")

        request = MagicMock()
        request.is_disconnected = AsyncMock(return_value=False)

        events = []
        async for event in sse_json_stream_generator(mock_stream(), request):
            events.append(event)

        assert len(events) == 2
        assert "event: error" in events[1]
        assert "Stream failed" in events[1]
        assert "RuntimeError" in events[1]


class TestCreateSSEResponse:
    """Test suite for create_sse_response function."""

    @pytest.mark.asyncio
    async def test_returns_streaming_response(self) -> None:
        """Verify StreamingResponse is created with correct config."""

        async def mock_stream() -> AsyncIterator[str]:
            yield "test"

        request = MagicMock()
        request.is_disconnected = AsyncMock(return_value=False)

        response = create_sse_response(mock_stream(), request)

        assert response.media_type == "text/event-stream"
        assert response.headers.get("Cache-Control") == "no-cache"
        assert response.headers.get("Connection") == "keep-alive"
        assert response.headers.get("X-Accel-Buffering") == "no"

    @pytest.mark.asyncio
    async def test_wraps_stream_generator(self) -> None:
        """Verify response wraps sse_stream_generator."""

        async def mock_stream() -> AsyncIterator[str]:
            yield "hello"

        request = MagicMock()
        request.is_disconnected = AsyncMock(return_value=False)

        response = create_sse_response(mock_stream(), request)

        # Consume response body
        chunks = []
        async for chunk in response.body_iterator:
            chunks.append(chunk)

        assert len(chunks) == 2  # 1 token + 1 done
        assert '"content": "hello"' in chunks[0]
        assert '"status": "complete"' in chunks[1]


class TestCreateJSONSSEResponse:
    """Test suite for create_json_sse_response function."""

    @pytest.mark.asyncio
    async def test_returns_streaming_response(self) -> None:
        """Verify StreamingResponse is created for JSON stream."""

        async def mock_stream() -> AsyncIterator[dict[str, object]]:
            yield {"value": "test"}

        request = MagicMock()
        request.is_disconnected = AsyncMock(return_value=False)

        response = create_json_sse_response(mock_stream(), request)

        assert response.media_type == "text/event-stream"
        assert response.headers.get("Cache-Control") == "no-cache"
        assert response.headers.get("Connection") == "keep-alive"

    @pytest.mark.asyncio
    async def test_wraps_json_stream_generator(self) -> None:
        """Verify response wraps sse_json_stream_generator."""

        async def mock_stream() -> AsyncIterator[dict[str, object]]:
            yield {"data": "hello"}

        request = MagicMock()
        request.is_disconnected = AsyncMock(return_value=False)

        response = create_json_sse_response(mock_stream(), request)

        # Consume response body
        chunks = []
        async for chunk in response.body_iterator:
            chunks.append(chunk)

        assert len(chunks) == 2  # 1 data + 1 done
        assert '"data": "hello"' in chunks[0]
