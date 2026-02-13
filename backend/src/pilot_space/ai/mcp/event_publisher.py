"""Centralized SSE event publisher for MCP tool servers.

Wraps a raw ``asyncio.Queue[str]`` with typed helpers and an
``asyncio.Lock`` that guarantees atomic focus_block + content_update
pairs — no interleaving from concurrent tool calls.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any


class EventPublisher:
    """Thread-safe pub/sub for SSE events with atomic focus+content pairs."""

    __slots__ = ("_lock", "_queue")

    def __init__(self, queue: asyncio.Queue[str]) -> None:
        self._queue = queue
        self._lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # Low-level helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _format_sse(event_type: str, data: dict[str, Any]) -> str:
        return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"

    async def publish(self, event: str) -> None:
        """Publish a pre-formatted SSE event string."""
        await self._queue.put(event)

    # ------------------------------------------------------------------
    # Typed publish helpers
    # ------------------------------------------------------------------

    async def publish_content_update(self, data: dict[str, Any]) -> None:
        """Publish a ``content_update`` SSE event."""
        await self._queue.put(self._format_sse("content_update", data))

    async def publish_approval_request(self, data: dict[str, Any]) -> None:
        """Publish an ``approval_request`` SSE event."""
        await self._queue.put(self._format_sse("approval_request", data))

    async def publish_focus_block(
        self,
        note_id: str,
        block_id: str | None,
        *,
        scroll_to_end: bool = False,
    ) -> None:
        """Publish a ``focus_block`` SSE event.

        Skipped when *block_id* is ``None`` and *scroll_to_end* is ``False``.
        """
        if not block_id and not scroll_to_end:
            return
        await self._queue.put(
            self._format_sse(
                "focus_block",
                {
                    "noteId": note_id,
                    "blockId": block_id,
                    "scrollToEnd": scroll_to_end,
                },
            )
        )

    # ------------------------------------------------------------------
    # Atomic compound event
    # ------------------------------------------------------------------

    async def publish_focus_and_content(
        self,
        note_id: str,
        focus_block_id: str | None,
        content_data: dict[str, Any],
        *,
        scroll_to_end: bool = False,
    ) -> None:
        """Atomically emit focus_block + content_update as a pair.

        The ``asyncio.Lock`` prevents another coroutine from inserting
        events between focus and content — the frontend receives them
        back-to-back.
        """
        async with self._lock:
            await self.publish_focus_block(note_id, focus_block_id, scroll_to_end=scroll_to_end)
            await self.publish_content_update(content_data)
