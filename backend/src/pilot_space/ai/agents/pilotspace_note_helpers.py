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
    """Map TodoWrite results to task_progress SSE events."""
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


def _map_todo_status(status: str) -> str:
    """Map SDK todo status to frontend TaskStatus."""
    return {
        "pending": "pending",
        "in_progress": "in_progress",
        "completed": "completed",
        "done": "completed",
    }.get(status, "pending")
