"""Stream utility functions for PilotSpaceAgent.

Extracted from pilotspace_agent.py for file size compliance.
Contains SSE content capture, structured content building,
effort classification, skill detection, token estimation,
and concurrent SDK+queue stream merging.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import re
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pilot_space.ai.agents.pilotspace_agent import ChatInput

logger = logging.getLogger(__name__)


_SIMPLE_PATTERNS = [
    re.compile(r"^(hi|hello|hey|thanks|thank you|ok|okay)\b"),
    re.compile(r"^what (can you|do you) do"),
    re.compile(r"^help\b"),
    re.compile(r"^(yes|no|sure|yep|nope)\b"),
]
_COMPLEX_PATTERNS = [
    re.compile(r"\b(analy[sz]e|audit|review|refactor|architect)\b"),
    re.compile(r"\b(compare|contrast|evaluate|assess)\b"),
    re.compile(r"\b(explain.{0,20}(in detail|thoroughly|step by step))\b"),
    re.compile(r"\b(design|implement|migrate|optimize)\b"),
    re.compile(r"\b(security|vulnerability|performance)\s+(review|audit|check)\b"),
]


def classify_effort(message: str) -> str | None:
    """Return 'low' for greetings, 'high' for complex queries, None for default."""
    msg_lower = message.strip().lower()
    if len(msg_lower) < 50:
        for p in _SIMPLE_PATTERNS:
            if p.match(msg_lower):
                return "low"
    if len(msg_lower) > 200:
        return "high"
    for p in _COMPLEX_PATTERNS:
        if p.search(msg_lower):
            return "high"
    return None


def detect_skill_from_message(message: str) -> str | None:
    """Detect slash-command skill invocation, returning skill name or None."""
    msg_stripped = message.strip()
    if msg_stripped.startswith("/"):
        parts = msg_stripped[1:].split(None, 1)
        return parts[0] if parts else None
    return None


def estimate_tokens(input_data: ChatInput) -> int:
    """Rough token estimate (~4 chars/token) for context size detection (T62)."""
    total_chars = len(input_data.message)
    total_chars += sum(len(str(v)) for v in input_data.context.values())
    return total_chars // 4


def capture_content_from_sse(
    sse_event: str,
    content_blocks: dict[str, dict[str, Any]],
) -> None:
    """Capture structured content from SSE events for session persistence.

    Extracts text_delta, thinking_delta, tool_use, and tool_result events
    and accumulates them into content_blocks dictionary.

    Args:
        sse_event: SSE-formatted event string (may contain multiple events)
        content_blocks: Mutable dict to accumulate content by block key
    """
    for event_line in sse_event.split("\n\n"):
        if not event_line.strip():
            continue

        lines = event_line.split("\n")
        event_type = ""
        data_str = ""

        for line in lines:
            if line.startswith("event: "):
                event_type = line[7:].strip()
            elif line.startswith("data: "):
                data_str = line[6:]

        if not event_type or not data_str:
            continue

        try:
            data = json.loads(data_str)
        except (json.JSONDecodeError, TypeError):
            continue

        block_idx = data.get("blockIndex", 0)

        if event_type == "text_delta":
            key = f"text_{block_idx}"
            if key not in content_blocks:
                content_blocks[key] = {"type": "text", "text": "", "index": block_idx}
            content_blocks[key]["text"] += data.get("delta", "")

        elif event_type == "thinking_delta":
            key = f"thinking_{block_idx}"
            if key not in content_blocks:
                content_blocks[key] = {"type": "thinking", "thinking": "", "index": block_idx}
            content_blocks[key]["thinking"] += data.get("delta", "")
            if "signature" in data:
                content_blocks[key]["signature"] = data["signature"]

        elif event_type == "tool_use":
            tool_id = data.get("toolCallId", "")
            if tool_id:
                key = f"tool_use_{tool_id}"
                content_blocks[key] = {
                    "type": "tool_use",
                    "id": tool_id,
                    "name": data.get("toolName", ""),
                    "input": data.get("toolInput", {}),
                    "index": len(content_blocks),
                }

        elif event_type == "tool_result":
            tool_id = data.get("toolCallId", "")
            if tool_id:
                key = f"tool_result_{tool_id}"
                content_blocks[key] = {
                    "type": "tool_result",
                    "tool_use_id": tool_id,
                    "content": data.get("output", data.get("errorMessage", "")),
                    "is_error": data.get("status") == "failed",
                    "index": len(content_blocks),
                }


def build_structured_content(
    content_blocks: dict[str, dict[str, Any]],
) -> list[dict[str, Any]] | str:
    """Build structured content list from captured blocks.

    Sorts blocks by their index and returns as a list of content blocks
    in Claude message format. Falls back to plain text if only text content.

    Args:
        content_blocks: Dict of captured content blocks

    Returns:
        List of content block dicts, or plain text string if only text
    """
    if not content_blocks:
        return ""

    sorted_blocks = sorted(
        content_blocks.values(),
        key=lambda b: b.get("index", 0),
    )

    has_non_text = any(b["type"] in ("thinking", "tool_use", "tool_result") for b in sorted_blocks)

    if not has_non_text:
        text_parts = [b.get("text", "") for b in sorted_blocks if b["type"] == "text"]
        return "".join(text_parts)

    result: list[dict[str, Any]] = []
    for block in sorted_blocks:
        clean_block = {k: v for k, v in block.items() if k != "index"}
        # Drop thinking blocks without signatures — they cause
        # "Missing required field: 'signature'" on session resume
        if clean_block.get("type") == "thinking" and "signature" not in clean_block:
            continue
        result.append(clean_block)

    return result


# ---------------------------------------------------------------------------
# Concurrent SDK + Queue stream merge
# ---------------------------------------------------------------------------

# Sentinel used to signal the SDK iterator is exhausted.
_SDK_DONE = object()


async def _feed_sdk(sdk_iter: AsyncIterator[Any], out: asyncio.Queue[Any]) -> None:
    """Drain *sdk_iter* into *out*, appending _SDK_DONE when finished."""
    try:
        async for msg in sdk_iter:
            await out.put(msg)
    except Exception as exc:
        logger.error("[StreamMerge] SDK feed error: %s", exc, exc_info=True)
    finally:
        await out.put(_SDK_DONE)


async def merge_sdk_and_queue(
    sdk_iter: AsyncIterator[Any],
    tool_queue: asyncio.Queue[str],
) -> AsyncIterator[tuple[str, Any]]:
    """Yield items from both the SDK response stream and tool_event_queue.

    Produces ``("sdk", message)`` for SDK messages and ``("queue", event)``
    for tool-queue events (e.g. ``approval_request`` SSE strings).

    A background task feeds the SDK iterator into an internal queue so both
    sources can be awaited concurrently with ``asyncio.wait``.  This prevents
    the deadlock where a blocking PreToolUse hook (``wait_for_approval``)
    stops the SDK from producing messages, which in turn prevents the main
    stream loop from draining the tool_event_queue.

    The generator finishes when the SDK iterator is exhausted.  Any remaining
    tool_queue items should be drained by the caller after this returns.
    """
    sdk_queue: asyncio.Queue[Any] = asyncio.Queue()
    feeder = asyncio.create_task(_feed_sdk(sdk_iter, sdk_queue))

    sdk_task: asyncio.Task[Any] | None = None
    queue_task: asyncio.Task[str] | None = None

    try:
        while True:
            if sdk_task is None:
                sdk_task = asyncio.create_task(sdk_queue.get())
            if queue_task is None:
                queue_task = asyncio.create_task(tool_queue.get())

            done, _ = await asyncio.wait(
                {sdk_task, queue_task},
                return_when=asyncio.FIRST_COMPLETED,
            )

            for task in done:
                if task is sdk_task:
                    item = task.result()
                    sdk_task = None
                    if item is _SDK_DONE:
                        return  # SDK stream finished
                    yield ("sdk", item)
                elif task is queue_task:
                    yield ("queue", task.result())
                    queue_task = None
    finally:
        # Cancel any pending tasks
        for task in (sdk_task, queue_task):
            if task is not None and not task.done():
                task.cancel()
        feeder.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await feeder
