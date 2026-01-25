"""Server-Sent Events (SSE) utilities.

Provides helpers for streaming responses using SSE format.
Used for AI streaming features like ghost text.

T090: SSE response helper.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import TYPE_CHECKING, Any

from fastapi.responses import StreamingResponse

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

logger = logging.getLogger(__name__)

# SSE media type
SSE_CONTENT_TYPE = "text/event-stream"

# Default heartbeat interval (seconds)
DEFAULT_HEARTBEAT_INTERVAL = 15


def sse_event(
    data: str | dict[str, Any],
    event: str | None = None,
    event_id: str | None = None,
    retry: int | None = None,
) -> str:
    """Format data as SSE event.

    Args:
        data: Event data (string or dict to serialize as JSON).
        event: Optional event type name.
        event_id: Optional event ID for client tracking.
        retry: Optional retry interval in milliseconds.

    Returns:
        Formatted SSE event string.

    Example:
        >>> sse_event({"text": "hello"}, event="message")
        'event: message\\ndata: {"text": "hello"}\\n\\n'
    """
    lines: list[str] = []

    # Add event type if specified
    if event:
        lines.append(f"event: {event}")

    # Add event ID if specified
    if event_id:
        lines.append(f"id: {event_id}")

    # Add retry interval if specified
    if retry is not None:
        lines.append(f"retry: {retry}")

    # Serialize data
    data_str = json.dumps(data) if isinstance(data, dict) else str(data)

    # Handle multi-line data
    lines.extend(f"data: {line}" for line in data_str.split("\n"))

    # SSE events end with double newline
    return "\n".join(lines) + "\n\n"


def sse_comment(comment: str) -> str:
    """Format a comment line for SSE.

    Comments are used for keepalive/heartbeat.

    Args:
        comment: Comment text.

    Returns:
        Formatted SSE comment.
    """
    return f": {comment}\n\n"


def sse_heartbeat() -> str:
    """Generate heartbeat comment to keep connection alive.

    Returns:
        Formatted heartbeat comment.
    """
    return sse_comment("heartbeat")


async def async_generator_to_sse(
    async_gen: AsyncIterator[str | dict[str, Any]],
    event_type: str | None = None,
    include_heartbeat: bool = True,
    heartbeat_interval: float = DEFAULT_HEARTBEAT_INTERVAL,
) -> AsyncIterator[str]:
    """Convert async generator to SSE event stream.

    Wraps an async generator to produce properly formatted SSE events.
    Optionally includes heartbeat comments to keep connection alive.

    Args:
        async_gen: Async generator yielding data items.
        event_type: Optional event type for all events.
        include_heartbeat: Whether to include heartbeat comments.
        heartbeat_interval: Seconds between heartbeats.

    Yields:
        Formatted SSE event strings.

    Example:
        async def token_generator():
            for token in ["Hello", " ", "World"]:
                yield token

        async for event in async_generator_to_sse(token_generator(), "token"):
            yield event
    """
    event_id = 0

    if include_heartbeat:
        # Interleave data and heartbeats using timeout-based approach
        data_exhausted = False

        while not data_exhausted:
            # Use asyncio.wait with timeout for heartbeat
            try:
                # Try to get data with timeout
                data = await asyncio.wait_for(
                    async_gen.__anext__(),
                    timeout=heartbeat_interval,
                )
                event_id += 1
                yield sse_event(
                    data=data,
                    event=event_type,
                    event_id=str(event_id),
                )
            except TimeoutError:
                # Send heartbeat on timeout
                yield sse_heartbeat()
            except StopAsyncIteration:
                break

    else:
        # Simple mode without heartbeat
        async for data in async_gen:
            event_id += 1
            yield sse_event(
                data=data,
                event=event_type,
                event_id=str(event_id),
            )

    # Send done event
    yield sse_event(
        data={"done": True},
        event="done",
    )


class SSEResponse(StreamingResponse):
    """Streaming response for Server-Sent Events.

    Convenience class that sets correct headers and content type
    for SSE responses.

    Example:
        @app.get("/stream")
        async def stream_endpoint():
            async def generate():
                for i in range(10):
                    yield sse_event({"count": i})
                    await asyncio.sleep(1)

            return SSEResponse(generate())
    """

    def __init__(
        self,
        content: AsyncIterator[str],
        status_code: int = 200,
        headers: dict[str, str] | None = None,
    ) -> None:
        """Initialize SSE response.

        Args:
            content: Async iterator yielding SSE-formatted strings.
            status_code: HTTP status code.
            headers: Additional headers.
        """
        # Build headers for SSE
        sse_headers = {
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
        if headers:
            sse_headers.update(headers)

        super().__init__(
            content=content,
            status_code=status_code,
            headers=sse_headers,
            media_type=SSE_CONTENT_TYPE,
        )


async def create_sse_stream(
    async_gen: AsyncIterator[str | dict[str, Any]],
    event_type: str | None = None,
    include_heartbeat: bool = True,
) -> SSEResponse:
    """Create SSE response from async generator.

    Convenience function combining async_generator_to_sse and SSEResponse.

    Args:
        async_gen: Async generator yielding data items.
        event_type: Optional event type for all events.
        include_heartbeat: Whether to include heartbeat comments.

    Returns:
        SSEResponse ready to return from endpoint.
    """
    return SSEResponse(
        async_generator_to_sse(
            async_gen,
            event_type=event_type,
            include_heartbeat=include_heartbeat,
        )
    )


class SSEStreamBuilder:
    """Builder for complex SSE streams.

    Allows sending different event types and managing stream state.

    Example:
        builder = SSEStreamBuilder()

        async def generate():
            yield builder.event("start", {"status": "starting"})
            for chunk in process():
                yield builder.event("data", chunk)
            yield builder.event("end", {"status": "complete"})

        return SSEResponse(generate())
    """

    def __init__(self) -> None:
        """Initialize stream builder."""
        self._event_id = 0

    def event(
        self,
        event_type: str,
        data: str | dict[str, Any],
    ) -> str:
        """Create an SSE event.

        Args:
            event_type: Event type name.
            data: Event data.

        Returns:
            Formatted SSE event.
        """
        self._event_id += 1
        return sse_event(
            data=data,
            event=event_type,
            event_id=str(self._event_id),
        )

    def data(self, data: str | dict[str, Any]) -> str:
        """Create data event (default event type).

        Args:
            data: Event data.

        Returns:
            Formatted SSE event.
        """
        self._event_id += 1
        return sse_event(
            data=data,
            event_id=str(self._event_id),
        )

    def error(self, message: str, code: str | None = None) -> str:
        """Create error event.

        Args:
            message: Error message.
            code: Optional error code.

        Returns:
            Formatted SSE error event.
        """
        error_data: dict[str, Any] = {"error": message}
        if code:
            error_data["code"] = code

        return sse_event(
            data=error_data,
            event="error",
        )

    def done(self, metadata: dict[str, Any] | None = None) -> str:
        """Create done event to signal stream end.

        Args:
            metadata: Optional completion metadata.

        Returns:
            Formatted SSE done event.
        """
        data: dict[str, Any] = {"done": True}
        if metadata:
            data.update(metadata)

        return sse_event(
            data=data,
            event="done",
        )

    def heartbeat(self) -> str:
        """Create heartbeat comment.

        Returns:
            Formatted heartbeat.
        """
        return sse_heartbeat()


__all__ = [
    "DEFAULT_HEARTBEAT_INTERVAL",
    "SSE_CONTENT_TYPE",
    "SSEResponse",
    "SSEStreamBuilder",
    "async_generator_to_sse",
    "create_sse_stream",
    "sse_comment",
    "sse_event",
    "sse_heartbeat",
]
