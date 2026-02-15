"""Stream utility functions for PilotSpaceAgent.

Extracted from pilotspace_agent.py for file size compliance.
Contains SSE content capture, structured content building,
effort classification, skill detection, token estimation,
MCP server factory, concurrent SDK+queue stream merging,
and dynamic system prompt assembly.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import re
from collections.abc import AsyncIterator
from pathlib import Path
from typing import TYPE_CHECKING, Any

from claude_agent_sdk import McpServerConfig
from claude_agent_sdk._internal import message_parser as _sdk_parser

from pilot_space.ai.mcp.comment_server import (
    SERVER_NAME as COMMENT_SERVER_NAME,
    create_comment_tools_server,
)
from pilot_space.ai.mcp.event_publisher import EventPublisher
from pilot_space.ai.mcp.interaction_server import (
    SERVER_NAME as INTERACTION_SERVER_NAME,
    create_interaction_server,
)
from pilot_space.ai.mcp.issue_relation_server import (
    SERVER_NAME as ISSUE_REL_SERVER_NAME,
    create_issue_relation_tools_server,
)
from pilot_space.ai.mcp.issue_server import (
    SERVER_NAME as ISSUE_SERVER_NAME,
    create_issue_tools_server,
)
from pilot_space.ai.mcp.note_content_server import (
    SERVER_NAME as NOTE_CONTENT_SERVER_NAME,
    create_note_content_server,
)
from pilot_space.ai.mcp.note_server import (
    SERVER_NAME as NOTE_SERVER_NAME,
    create_note_tools_server,
)
from pilot_space.ai.mcp.project_server import (
    SERVER_NAME as PROJECT_SERVER_NAME,
    create_project_tools_server,
)
from pilot_space.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from pilot_space.ai.agents.pilotspace_agent import ChatInput
    from pilot_space.ai.mcp.block_ref_map import BlockRefMap
    from pilot_space.ai.tools.mcp_server import ToolContext

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Monkey-patch: SDK 0.1.x crashes on thinking blocks without 'signature'
# (KeyError → MessageParseError).  Patch the parser to default signature="".
# Remove once claude-agent-sdk ships a fix.
# ---------------------------------------------------------------------------
_original_parse_message = _sdk_parser.parse_message


def _patched_parse_message(data: dict[str, Any]) -> Any:
    """Wrap SDK parse_message to tolerate missing 'signature' in thinking blocks."""
    if data.get("type") == "assistant":
        for block in data.get("message", {}).get("content", []):
            if block.get("type") == "thinking" and "signature" not in block:
                block["signature"] = ""
    return _original_parse_message(data)


_sdk_parser.parse_message = _patched_parse_message  # type: ignore[assignment]


def build_mcp_servers(
    tool_event_queue: asyncio.Queue[str],
    tool_context: ToolContext,
    input_data: ChatInput,
) -> tuple[dict[str, McpServerConfig], BlockRefMap | None]:
    """Build the MCP server dict and block-reference map for an SDK session.

    Constructs a ¶N block reference map from the note context (if present)
    and instantiates all 7 MCP tool servers (6 domain + 1 interaction).

    Returns:
        Tuple of (mcp_servers dict keyed by server name, block_ref_map or None).
    """
    from pilot_space.ai.mcp.block_ref_map import BlockRefMap

    _note_obj = input_data.context.get("note")
    _note_raw = getattr(_note_obj, "content", {}) if _note_obj else {}
    ref_map: BlockRefMap | None = BlockRefMap.from_tiptap(_note_raw) if _note_raw else None
    if ref_map is not None and ref_map.is_empty:
        ref_map = None

    context_note_id = input_data.context.get("note_id")

    publisher = EventPublisher(tool_event_queue)

    servers: dict[str, McpServerConfig] = {
        NOTE_SERVER_NAME: create_note_tools_server(
            publisher,
            context_note_id=str(context_note_id) if context_note_id else None,
            tool_context=tool_context,
            block_ref_map=ref_map,
        ),
        NOTE_CONTENT_SERVER_NAME: create_note_content_server(
            publisher,
            tool_context=tool_context,
            block_ref_map=ref_map,
        ),
        ISSUE_SERVER_NAME: create_issue_tools_server(
            publisher,
            tool_context=tool_context,
        ),
        ISSUE_REL_SERVER_NAME: create_issue_relation_tools_server(
            publisher,
            tool_context=tool_context,
        ),
        PROJECT_SERVER_NAME: create_project_tools_server(
            publisher=publisher,
            tool_context=tool_context,
        ),
        COMMENT_SERVER_NAME: create_comment_tools_server(
            publisher,
            tool_context=tool_context,
        ),
        INTERACTION_SERVER_NAME: create_interaction_server(
            publisher,
            user_id=input_data.user_id,
        ),
    }

    return servers, ref_map


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
                logger.debug(
                    "content_capture_tool_use",
                    tool_name=data.get("toolName", ""),
                    tool_id=tool_id,
                    total_blocks=len(content_blocks),
                )

        elif event_type == "tool_result":
            tool_id = data.get("toolCallId", "")
            if tool_id:
                key = f"tool_result_{tool_id}"
                is_error = data.get("status") == "failed"
                content_blocks[key] = {
                    "type": "tool_result",
                    "tool_use_id": tool_id,
                    "content": data.get("output", data.get("errorMessage", "")),
                    "is_error": is_error,
                    "index": len(content_blocks),
                }
                logger.debug(
                    "content_capture_tool_result",
                    tool_id=tool_id,
                    is_error=is_error,
                    total_blocks=len(content_blocks),
                )


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


def extract_question_data_from_blocks(
    content_blocks: dict[str, dict[str, Any]],
) -> list[dict[str, Any]] | None:
    """Extract question_data from content_blocks if ask_user questions are pending.

    Scans tool_result blocks for ask_user pending_answer results, extracts
    the questionIds, and looks up the full question data from QuestionAdapter.
    Supports multiple ask_user calls in a single turn.

    Args:
        content_blocks: Dict of captured content blocks from the stream.

    Returns:
        List of question_data dicts [{questionId, questions}, ...] if found, None otherwise.
    """
    from uuid import UUID

    from pilot_space.ai.sdk.question_adapter import get_question_adapter

    results: list[dict[str, Any]] = []

    for block in content_blocks.values():
        if block.get("type") != "tool_result":
            continue

        content = block.get("content", "")

        # Content may be a dict (from SSE capture) or a JSON string
        parsed: dict[str, Any] | None = None
        if isinstance(content, dict):
            parsed = content
        elif isinstance(content, str) and "pending_answer" in content:
            try:
                parsed = json.loads(content)
            except (json.JSONDecodeError, TypeError):
                continue
        else:
            continue

        if not parsed or parsed.get("status") != "pending_answer":
            continue
        question_id_str = parsed.get("questionId")
        if not question_id_str:
            continue

        try:
            question_id = UUID(question_id_str)
        except ValueError:
            continue

        adapter = get_question_adapter()
        pending = adapter.get_question(question_id)
        if pending is None:
            continue

        results.append(
            {
                "questionId": str(question_id),
                "questions": [q.model_dump() for q in pending.questions],
            }
        )

    return results if results else None


def extract_tool_calls_from_blocks(
    content_blocks: dict[str, dict[str, Any]],
) -> list[dict[str, Any]] | None:
    """Extract structured tool call records from content_blocks for session persistence.

    Pairs tool_use and tool_result blocks by tool call ID to build
    a complete list of tool call records with name, input, output, and status.

    Args:
        content_blocks: Dict of captured content blocks from the stream.

    Returns:
        List of tool call dicts [{id, name, input, output, status}, ...] or None.
    """
    # Collect tool_use entries keyed by tool call ID
    tool_uses: dict[str, dict[str, Any]] = {}
    for block in content_blocks.values():
        if block.get("type") == "tool_use":
            tid = block.get("id", "")
            if tid:
                tool_uses[tid] = block

    if not tool_uses:
        return None

    # Build tool call records by pairing with tool_result blocks
    results: list[dict[str, Any]] = []
    for tid, use_block in tool_uses.items():
        result_key = f"tool_result_{tid}"
        result_block = content_blocks.get(result_key)

        record: dict[str, Any] = {
            "id": tid,
            "name": use_block.get("name", ""),
            "input": use_block.get("input", {}),
        }

        if result_block:
            is_error = result_block.get("is_error", False)
            record["status"] = "failed" if is_error else "completed"
            record["output"] = result_block.get("content", "")
            if is_error:
                record["error_message"] = result_block.get("content", "")
        else:
            record["status"] = "pending"

        results.append(record)

    return results if results else None


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


# ---------------------------------------------------------------------------
# Dynamic System Prompt Assembly
# ---------------------------------------------------------------------------

# Template directories
_TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
_ROLE_TEMPLATES_DIR = _TEMPLATES_DIR / "role_templates"
_RULES_DIR = _TEMPLATES_DIR / "rules"

# Rules to inject (compact ones only; ai-confidence.md is 415 lines, too large)
_INJECTED_RULES = ("issues.md", "notes.md", "pm_blocks.md")

# Max characters per rule file to prevent prompt bloat
_MAX_RULE_CHARS = 4000


def _load_role_template(role_type: str) -> str | None:
    """Load a role template markdown file by role type.

    Args:
        role_type: Role type string (e.g., 'developer', 'architect').

    Returns:
        Template content (body only, YAML frontmatter stripped) or None.
    """
    template_path = _ROLE_TEMPLATES_DIR / f"{role_type}.md"
    if not template_path.is_file():
        logger.debug("Role template not found: %s", template_path)
        return None

    content = template_path.read_text(encoding="utf-8")

    # Strip YAML frontmatter (--- ... ---)
    if content.startswith("---"):
        end_idx = content.find("---", 3)
        if end_idx != -1:
            content = content[end_idx + 3 :].strip()

    return content


def _load_rules() -> str:
    """Load compact rule files for system prompt injection.

    Returns:
        Combined rules as a single string, truncated per file.
    """
    parts: list[str] = []
    for filename in _INJECTED_RULES:
        rule_path = _RULES_DIR / filename
        if not rule_path.is_file():
            logger.debug("Rule file not found: %s", rule_path)
            continue

        content = rule_path.read_text(encoding="utf-8")
        if len(content) > _MAX_RULE_CHARS:
            content = content[:_MAX_RULE_CHARS] + "\n... (truncated)"
        parts.append(content)

    return "\n\n".join(parts)


def build_dynamic_system_prompt(
    base_prompt: str,
    role_type: str | None = None,
    workspace_name: str | None = None,
    project_names: list[str] | None = None,
) -> str:
    """Assemble a dynamic system prompt from base + role + rules.

    Extends the static SYSTEM_PROMPT_BASE with:
    1. User's primary role template (behavioral adaptation)
    2. Workspace/project context (entity awareness)
    3. Compact operational rules (issues.md, notes.md)

    Args:
        base_prompt: The static SYSTEM_PROMPT_BASE string.
        role_type: User's primary role (e.g., 'developer', 'architect').
        workspace_name: Current workspace name for context.
        project_names: Active project names in the workspace.

    Returns:
        Assembled system prompt string.
    """
    sections: list[str] = [base_prompt]

    # 1. Role-specific section
    if role_type:
        role_content = _load_role_template(role_type)
        if role_content:
            sections.append(f"\n\n## Your User's Role\n{role_content}")

    # 2. Workspace context
    if workspace_name or project_names:
        ctx_parts: list[str] = ["## Workspace Context"]
        if workspace_name:
            ctx_parts.append(f"Workspace: {workspace_name}")
        if project_names:
            ctx_parts.append(f"Active projects: {', '.join(project_names[:10])}")
        sections.append("\n\n" + "\n".join(ctx_parts))

    # 3. Operational rules
    rules = _load_rules()
    if rules:
        sections.append(f"\n\n## Operational Rules\n{rules}")

    return "".join(sections)
