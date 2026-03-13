"""SSE streaming utilities for AI endpoints.

Provides reusable Server-Sent Events streaming for FastAPI.
Used by AI endpoints that return streaming responses.

Reference: DD-066 SSE for AI streaming
Design Pattern: 45-pilot-space-patterns.md (SSE for AI streaming)
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

import structlog
from fastapi import Request
from fastapi.responses import StreamingResponse

_logger = structlog.get_logger(__name__)


def format_sse_event(event: str, data: dict[str, Any]) -> str:
    """Format a Server-Sent Event.

    Args:
        event: Event type (e.g., "token", "done", "error")
        data: Event payload (will be JSON-encoded)

    Returns:
        Formatted SSE event string with newlines
    """
    json_data = json.dumps(data, ensure_ascii=False)
    return f"event: {event}\ndata: {json_data}\n\n"


async def sse_stream_generator(
    stream: AsyncIterator[str],
    request: Request,
) -> AsyncIterator[str]:
    """Generate SSE events from an async token stream.

    Handles:
    - Token events for each chunk
    - Done event on completion
    - Error events on exceptions
    - Client disconnect detection

    Args:
        stream: Async iterator yielding string chunks
        request: FastAPI request for disconnect detection

    Yields:
        Formatted SSE events
    """
    try:
        disconnected = False
        async for chunk in stream:
            # Handle error chunks from agent
            if chunk.startswith("ERROR:"):
                yield format_sse_event(
                    "error",
                    {
                        "message": chunk[6:].strip(),
                        "type": "agent_error",
                    },
                )
                return

            # Emit token event
            yield format_sse_event("token", {"content": chunk})

            # Check if client disconnected after yielding
            if await request.is_disconnected():
                disconnected = True
                break

        # Only emit done event if not disconnected
        if not disconnected:
            yield format_sse_event("done", {"status": "complete"})

    except Exception:
        _logger.exception("sse_stream_error")
        yield format_sse_event(
            "error",
            {
                "message": "An internal error occurred during streaming.",
                "type": "stream_error",
            },
        )


def create_sse_response(
    stream: AsyncIterator[str],
    request: Request,
) -> StreamingResponse:
    """Create SSE streaming response from async iterator.

    Usage:
        @router.post("/ai/notes/{note_id}/ghost-text")
        async def ghost_text(note_id: UUID, request: Request):
            stream = orchestrator.stream("ghost_text", input_data, context)
            return create_sse_response(stream, request)

    Args:
        stream: Async iterator yielding string chunks
        request: FastAPI request

    Returns:
        StreamingResponse configured for SSE
    """
    return StreamingResponse(
        sse_stream_generator(stream, request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


# Additional helpers for structured streaming


async def sse_json_stream_generator(
    stream: AsyncIterator[dict[str, Any]],
    request: Request,
) -> AsyncIterator[str]:
    """Generate SSE events from structured data stream.

    Similar to sse_stream_generator but for JSON payloads
    instead of raw text chunks.

    Args:
        stream: Async iterator yielding dicts
        request: FastAPI request

    Yields:
        Formatted SSE events
    """
    try:
        disconnected = False
        async for item in stream:
            # Determine event type from item
            event_type = item.pop("_event", "data")
            yield format_sse_event(event_type, item)

            # Check if client disconnected after yielding
            if await request.is_disconnected():
                disconnected = True
                break

        # Only emit done event if not disconnected
        if not disconnected:
            yield format_sse_event("done", {"status": "complete"})

    except Exception:
        _logger.exception("sse_json_stream_error")
        yield format_sse_event(
            "error",
            {
                "message": "An internal error occurred during streaming.",
                "type": "stream_error",
            },
        )


def create_json_sse_response(
    stream: AsyncIterator[dict[str, Any]],
    request: Request,
) -> StreamingResponse:
    """Create SSE response from structured JSON stream.

    Args:
        stream: Async iterator yielding dicts
        request: FastAPI request

    Returns:
        StreamingResponse configured for SSE
    """
    return StreamingResponse(
        sse_json_stream_generator(stream, request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


__all__ = [
    "create_json_sse_response",
    "create_sse_response",
    "format_sse_event",
    "sse_json_stream_generator",
    "sse_stream_generator",
]
