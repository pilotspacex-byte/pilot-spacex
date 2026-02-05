"""Note-specific SSE event helpers for PilotSpace Agent.

Emit content_update events for note operations (replace, append, issue creation)
and utility functions for todo/structured output handling.

Extracted from pilotspace_agent_helpers.py for file size quality gate (700 lines).
"""

from __future__ import annotations

import json
import logging
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


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


def transform_todo_to_task_progress(
    tool_name: str, result_data: Any, tool_use_id: Any
) -> str | None:
    """Map TodoWrite results to task_progress + tool_result SSE events.

    Emits task_progress for each todo item, plus a companion tool_result
    event so the frontend ToolCallCard can transition from pending to completed.
    """
    if tool_name not in ("TodoWrite", "mcp__TodoWrite", "TodoRead", "mcp__TodoRead"):
        return None
    if not isinstance(result_data, dict):
        return None

    todos = result_data.get("todos", [])
    if not todos:
        return None

    events = []
    for todo in todos:
        status = todo.get("status", "pending")
        task_data = {
            "taskId": todo.get("id", str(uuid4())),
            "subject": todo.get("content", "Task"),
            "status": _map_todo_status(status),
            "progress": 100 if status in ("completed", "done") else 0,
        }
        events.append(f"event: task_progress\ndata: {json.dumps(task_data)}\n\n")

    # Companion tool_result so ToolCallCard transitions from pending → completed
    tool_result_data = {
        "toolCallId": str(tool_use_id) if tool_use_id else str(uuid4()),
        "status": "completed",
    }
    events.append(f"event: tool_result\ndata: {json.dumps(tool_result_data)}\n\n")

    return "".join(events) if events else None


def validate_structured_output(
    schema_type: str, result_data: dict[str, Any]
) -> dict[str, Any] | None:
    """Validate structured output against registered Pydantic schema (G-03).

    Returns validated dict (model_dump) on success, None on failure.
    Unknown schema types pass through without validation.
    """
    from pilot_space.ai.sdk.output_schemas import get_output_schema

    schema_cls = get_output_schema(schema_type)
    if schema_cls is None:
        # Unknown schema type — pass through raw data
        return result_data
    try:
        validated = schema_cls.model_validate(result_data)
        return validated.model_dump(by_alias=True)
    except Exception:
        logger.warning(
            "Structured output validation failed for schema_type=%s, falling back to plain message",
            schema_type,
            exc_info=True,
        )
        return None


def transform_user_message_tool_results(message: Any) -> str | None:
    """Extract ToolResultBlock entries from a UserMessage and emit tool_result SSE events.

    The Claude Agent SDK v1.x emits tool results as UserMessage objects with
    ToolResultBlock content blocks (not as standalone ToolResultMessage).
    Each ToolResultBlock contains the tool_use_id, content, and is_error flag.

    For note tools with pending_apply results, emits content_update + tool_result events.
    For TodoWrite results, emits both task_progress and tool_result events.
    For all other tools, emits a standard tool_result SSE event.

    Args:
        message: UserMessage from Claude Agent SDK

    Returns:
        SSE-formatted event string(s) or None if no tool results found
    """
    from claude_agent_sdk.types import ToolResultBlock

    content = getattr(message, "content", None)
    if not isinstance(content, list):
        return None

    events: list[str] = []
    for block in content:
        if not isinstance(block, ToolResultBlock):
            continue

        tool_use_id = block.tool_use_id
        block_content = block.content
        is_error = block.is_error or False

        # Parse content: str, list[dict], or None
        result_data: Any = block_content
        if isinstance(block_content, str):
            # Try to parse JSON string (note tools return JSON dicts as strings)
            try:
                result_data = json.loads(block_content)
            except (json.JSONDecodeError, TypeError):
                result_data = block_content
        elif isinstance(block_content, list):
            # list[dict] content — use first text entry or the whole list
            text_parts = []
            for entry in block_content:
                if entry.get("type") == "text":
                    text_parts.append(entry.get("text", ""))
            if text_parts:
                combined = "\n".join(text_parts)
                try:
                    result_data = json.loads(combined)
                except (json.JSONDecodeError, TypeError):
                    result_data = combined
            else:
                result_data = block_content

        # Check for note tool pending_apply operations
        if isinstance(result_data, dict) and result_data.get("status") == "pending_apply":
            operation = result_data.get("operation")
            note_id = result_data.get("note_id")

            if note_id and isinstance(note_id, str) and operation and isinstance(operation, str):
                operation_handlers = {
                    "replace_block": emit_replace_block_event,
                    "append_blocks": emit_append_blocks_event,
                    "create_issues": emit_issue_creation_events,
                    "create_single_issue": emit_issue_creation_events,
                }
                handler = operation_handlers.get(operation)
                content_update_event = handler(result_data, note_id) if handler else None
                if content_update_event:
                    events.append(content_update_event)
                # Also emit tool_result so ToolCallCard shows completion
                tool_result_event_data = {
                    "toolCallId": str(tool_use_id) if tool_use_id else str(uuid4()),
                    "status": "completed",
                }
                events.append(f"event: tool_result\ndata: {json.dumps(tool_result_event_data)}\n\n")
                continue

        # Check for TodoWrite results → emit task_progress + tool_result
        tool_use_result = getattr(message, "tool_use_result", None)
        tool_name = ""
        if isinstance(tool_use_result, dict):
            tool_name = tool_use_result.get("tool_name", "")
        todo_event = transform_todo_to_task_progress(tool_name, result_data, tool_use_id)
        if todo_event:
            events.append(todo_event)
            # Companion tool_result so ToolCallCard transitions from pending
            companion_data = {
                "toolCallId": str(tool_use_id) if tool_use_id else str(uuid4()),
                "status": "completed",
            }
            events.append(f"event: tool_result\ndata: {json.dumps(companion_data)}\n\n")
            continue

        # Generic tool_result event
        error_message: str | None = None
        if is_error:
            error_message = str(result_data) if result_data else "Tool execution failed"

        tool_result_data: dict[str, Any] = {
            "toolCallId": str(tool_use_id) if tool_use_id else str(uuid4()),
            "status": "failed" if is_error else "completed",
        }
        if not is_error and result_data is not None:
            tool_result_data["output"] = result_data
        if error_message:
            tool_result_data["errorMessage"] = error_message

        events.append(f"event: tool_result\ndata: {json.dumps(tool_result_data, default=str)}\n\n")

    return "".join(events) if events else None


def _map_todo_status(status: str) -> str:
    """Map SDK todo status to frontend TaskStatus."""
    return {
        "pending": "pending",
        "in_progress": "in_progress",
        "completed": "completed",
        "done": "completed",
    }.get(status, "pending")
