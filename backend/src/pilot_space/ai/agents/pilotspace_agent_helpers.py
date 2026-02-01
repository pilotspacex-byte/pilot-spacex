"""Helper functions for PilotSpace Agent.

SSE event emission and message transformation utilities.
Extracted from pilotspace_agent.py for modularity (file size quality gate).
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any
from uuid import uuid4

if TYPE_CHECKING:
    from claude_agent_sdk import Message

    from pilot_space.ai.agents.pilotspace_agent import ChatInput

logger = logging.getLogger(__name__)


def build_contextual_message(input_data: ChatInput) -> str:
    """Enrich user message with note/issue context for the SDK.

    Includes note_id and block_ids so the model can call note tools
    (extract_issues, update_note_block, etc.) with correct parameters.
    """
    parts: list[str] = []

    note = input_data.context.get("note")
    note_id = input_data.context.get("note_id")
    if note is not None:
        note_title = getattr(note, "title", "Untitled") or "Untitled"
        note_content = getattr(note, "content", {})

        note_header = f"# {note_title}"
        if note_id:
            note_header += f"\nnote_id: {note_id}"

        selected_block_ids = input_data.context.get("selected_block_ids", [])
        if selected_block_ids:
            note_header += (
                f"\nselected_block_ids: {', '.join(str(bid) for bid in selected_block_ids)}"
            )

        if note_content:
            from pilot_space.application.services.note.content_converter import (
                ContentConverter,
            )

            converter = ContentConverter()
            markdown = converter.tiptap_to_markdown(note_content)
            if markdown.strip():
                parts.append(f"<note_context>\n{note_header}\n\n{markdown}\n</note_context>")
        else:
            parts.append(f"<note_context>\n{note_header}\n\n(empty note)\n</note_context>")

    selected_text = input_data.context.get("selected_text")
    if selected_text:
        parts.append(f"<selected_text>\n{selected_text}\n</selected_text>")

    if parts:
        context_block = "\n\n".join(parts)
        return f"{context_block}\n\n{input_data.message}"
    return input_data.message


def transform_sdk_message(  # noqa: PLR0911
    message: Message,
    current_message_id_holder: dict[str, str | None],
) -> str | None:
    """Transform Claude SDK message to frontend SSE event.

    SDK Message Types (actual attributes from claude-agent-sdk):
    - SystemMessage: data(dict), subtype — init message with session_id
    - AssistantMessage: content(list[TextBlock]), error, model — AI response
    - ResultMessage: session_id, is_error, result, usage — completion signal
    - ToolResultMessage: tool_name, result — MCP tool execution result

    Output format matches frontend SSEEvent expectations:
    - ``event: <type>\\ndata: <json>\\n\\n`` (proper SSE with event prefix)
    - camelCase field names (messageId, sessionId, delta, stopReason)

    For MCP tool results from note tools, emits content_update events.

    Args:
        message: SDK message object
        current_message_id_holder: Mutable dict with "_current_message_id" key for state

    Returns:
        SSE-formatted string or None if message should be ignored
    """
    msg_type = type(message).__name__

    if msg_type in ("ToolResultMessage", "ToolResult"):
        return transform_tool_result(message)

    if msg_type == "SystemMessage":
        raw_data = getattr(message, "data", None)
        if isinstance(raw_data, dict) and raw_data.get("type") == "system":
            subtype = raw_data.get("subtype")
            if subtype == "init":
                session_id = raw_data.get("session_id", "")
                current_message_id_holder["_current_message_id"] = str(uuid4())
                data = {
                    "messageId": current_message_id_holder["_current_message_id"],
                    "sessionId": str(session_id),
                }
                return f"event: message_start\ndata: {json.dumps(data)}\n\n"
        return None

    if msg_type == "AssistantMessage":
        content = getattr(message, "content", None)
        if content is None:
            return None
        if isinstance(content, list):
            parts = []
            for block in content:
                if isinstance(block, dict):
                    parts.append(block.get("text", ""))
                elif hasattr(block, "text"):
                    parts.append(block.text)
            text_content = " ".join(parts)
        else:
            text_content = str(content)

        if not text_content.strip():
            return None
        message_id_value = current_message_id_holder.get("_current_message_id")
        message_id = message_id_value if message_id_value else str(uuid4())
        data = {
            "messageId": message_id,
            "delta": text_content,
        }
        return f"event: text_delta\ndata: {json.dumps(data)}\n\n"

    if msg_type == "ResultMessage":
        session_id = getattr(message, "session_id", "")
        is_error = getattr(message, "is_error", False)
        usage = getattr(message, "usage", None)
        message_id_value = current_message_id_holder.get("_current_message_id")
        message_id = message_id_value if message_id_value else str(uuid4())

        if is_error:
            result = getattr(message, "result", "")
            error_data: dict[str, Any] = {
                "errorCode": "api_error",
                "message": str(result) if result else "Unknown error",
                "retryable": False,
            }
            return f"event: error\ndata: {json.dumps(error_data)}\n\n"

        data_stop: dict[str, Any] = {
            "messageId": message_id,
            "stopReason": "end_turn",
        }
        if usage:
            data_stop["usage"] = {
                "inputTokens": getattr(usage, "input_tokens", 0),
                "outputTokens": getattr(usage, "output_tokens", 0),
                "totalTokens": (
                    getattr(usage, "input_tokens", 0) + getattr(usage, "output_tokens", 0)
                ),
            }
            total_cost = getattr(usage, "total_cost_usd", None)
            if total_cost is not None:
                data_stop["costUsd"] = total_cost
        return f"event: message_stop\ndata: {json.dumps(data_stop)}\n\n"

    return None


def transform_tool_result(message: Message) -> str | None:
    """Transform MCP tool result to content_update SSE event.

    Intercepts tool results from note tools and emits content_update events
    with appropriate operation types.

    Args:
        message: Tool result message from SDK

    Returns:
        SSE-formatted content_update event or None for non-content operations
    """
    result_data = getattr(message, "result", {})

    if not isinstance(result_data, dict) or result_data.get("status") != "pending_apply":
        return None

    operation = result_data.get("operation")
    note_id = result_data.get("note_id")

    if not note_id or not isinstance(note_id, str):
        logger.warning(
            f"Tool result missing valid note_id: operation={operation}, note_id={note_id}"
        )
        return None

    if not operation or not isinstance(operation, str):
        return None

    operation_handlers = {
        "replace_block": emit_replace_block_event,
        "append_blocks": emit_append_blocks_event,
        "create_issues": emit_issue_creation_events,
        "create_single_issue": emit_issue_creation_events,
    }

    handler = operation_handlers.get(operation)
    if handler:
        return handler(result_data, note_id)

    return None


def emit_replace_block_event(result_data: dict[str, Any], note_id: str) -> str:
    """Emit content_update SSE event for replace_block operation.

    Args:
        result_data: Tool result data
        note_id: Note ID

    Returns:
        SSE-formatted content_update event
    """
    event_data = {
        "noteId": note_id,
        "operation": "replace_block",
        "blockId": result_data.get("block_id"),
        "markdown": result_data.get("markdown"),
        "content": None,
        "issueData": None,
        "afterBlockId": None,
    }
    return f"event: content_update\ndata: {json.dumps(event_data)}\n\n"


def emit_append_blocks_event(result_data: dict[str, Any], note_id: str) -> str:
    """Emit content_update SSE event for append_blocks operation.

    Args:
        result_data: Tool result data
        note_id: Note ID

    Returns:
        SSE-formatted content_update event
    """
    event_data = {
        "noteId": note_id,
        "operation": "append_blocks",
        "blockId": result_data.get("block_id"),
        "markdown": result_data.get("markdown"),
        "content": None,
        "issueData": None,
        "afterBlockId": result_data.get("after_block_id"),
    }
    return f"event: content_update\ndata: {json.dumps(event_data)}\n\n"


def emit_issue_creation_events(result_data: dict[str, Any], note_id: str) -> str:
    """Emit content_update SSE events for issue creation.

    For multiple issues, creates one event with all issue data.
    Frontend will handle inserting multiple inline issue nodes.

    Args:
        result_data: Tool result data
        note_id: Note ID

    Returns:
        SSE-formatted content_update event(s)
    """
    operation = result_data.get("operation")

    if operation == "create_single_issue":
        issue_data = result_data.get("issue", {})
        event_data = {
            "noteId": note_id,
            "operation": "insert_inline_issue",
            "blockId": result_data.get("block_id"),
            "markdown": None,
            "content": None,
            "issueData": issue_data,
            "afterBlockId": None,
        }
        return f"event: content_update\ndata: {json.dumps(event_data)}\n\n"

    issues = result_data.get("issues", [])
    if not issues:
        return ""

    events = []
    block_ids = result_data.get("block_ids", [])

    for idx, issue in enumerate(issues):
        block_id = block_ids[idx] if idx < len(block_ids) else None
        event_data = {
            "noteId": note_id,
            "operation": "insert_inline_issue",
            "blockId": block_id,
            "markdown": None,
            "content": None,
            "issueData": issue,
            "afterBlockId": None,
        }
        events.append(f"event: content_update\ndata: {json.dumps(event_data)}\n\n")

    return "".join(events)
