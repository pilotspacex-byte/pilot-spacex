"""AI Session Management API endpoints.

Provides endpoints for listing, resuming, and managing AI conversation sessions.

Reference: T077-T079 (Session Persistence and Resumption)
Design Decisions: DD-058 (Session Management)
"""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Query

from pilot_space.api.middleware.request_context import WorkspaceId
from pilot_space.api.v1.schemas.ai_sessions import (
    ContextHistoryEntry,
    SessionGroup,
    SessionListItem,
    SessionListResponse,
    SessionResumeResponse,
)
from pilot_space.dependencies import CurrentUserId, DbSession, SessionManagerDep
from pilot_space.domain.exceptions import ForbiddenError, NotFoundError
from pilot_space.infrastructure.database.rls import set_rls_context
from pilot_space.infrastructure.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/ai/sessions", tags=["ai-sessions"])


def _parse_message_content(content: str) -> dict[str, Any]:
    """Parse message content, handling JSON-serialized structured blocks.

    When messages are persisted with structured content (thinking/text/tool blocks),
    they're stored as JSON strings. This function detects and parses them back to
    the format expected by the frontend.

    Args:
        content: Raw message content (string or JSON-serialized list)

    Returns:
        Dict with:
        - content: Plain text content (concatenated from text blocks)
        - content_blocks: Ordered content blocks for interleaved rendering
        - thinking_blocks: Extracted thinking block entries
        - tool_calls: Tool call records extracted from content (fallback for pre-persist sessions)
    """
    empty = {
        "content": content,
        "content_blocks": None,
        "thinking_blocks": None,
        "tool_calls": None,
    }
    if not content or not content.strip().startswith("["):
        return empty

    try:
        blocks = json.loads(content)
        if not isinstance(blocks, list):
            return empty
    except (json.JSONDecodeError, TypeError):
        return empty

    # Parse structured blocks
    text_parts: list[str] = []
    content_blocks: list[dict[str, Any]] = []
    thinking_blocks: list[dict[str, Any]] = []
    # Collect tool_use/tool_result for pairing
    tool_use_map: dict[str, dict[str, Any]] = {}
    tool_result_map: dict[str, dict[str, Any]] = {}

    for idx, block in enumerate(blocks):
        if not isinstance(block, dict):
            continue

        block_type = block.get("type")

        if block_type == "text":
            text = block.get("text", "")
            text_parts.append(text)
            content_blocks.append({"type": "text", "content": text})

        elif block_type == "thinking":
            thinking = block.get("thinking", "")
            thinking_blocks.append({"content": thinking, "blockIndex": idx, "redacted": False})
            content_blocks.append({"type": "thinking", "blockIndex": idx, "content": thinking})

        elif block_type == "tool_use":
            tool_id = block.get("id", "")
            content_blocks.append({"type": "tool_call", "toolCallId": tool_id})
            if tool_id:
                tool_use_map[tool_id] = block

        elif block_type == "tool_result":
            tid = block.get("tool_use_id", "")
            if tid:
                tool_result_map[tid] = block

    # Build tool_calls by pairing tool_use + tool_result
    tool_calls: list[dict[str, Any]] = []
    for tid, use_block in tool_use_map.items():
        record: dict[str, Any] = {
            "id": tid,
            "name": use_block.get("name", ""),
            "input": use_block.get("input", {}),
        }
        res = tool_result_map.get(tid)
        if res:
            is_error = res.get("is_error", False)
            record["status"] = "failed" if is_error else "completed"
            record["output"] = res.get("content", "")
            if is_error:
                record["error_message"] = res.get("content", "")
        else:
            record["status"] = "pending"
        tool_calls.append(record)

    return {
        "content": "".join(text_parts),
        "content_blocks": content_blocks if content_blocks else None,
        "thinking_blocks": thinking_blocks if thinking_blocks else None,
        "tool_calls": tool_calls if tool_calls else None,
    }


@router.get("")
async def list_sessions(
    user_id: CurrentUserId,
    db_session: DbSession,
    session_manager: SessionManagerDep,
    workspace_id: WorkspaceId,
    agent_name: str | None = Query(None, description="Filter by agent"),
    context_id: UUID | None = Query(
        None, description="Filter by context entity (note_id, issue_id)"
    ),
    search: str | None = Query(None, description="Search by title or context"),
    group_by: str | None = Query(None, description="'date' to group by date"),
    limit: int = Query(50, ge=1, le=100, description="Max results"),
) -> SessionListResponse:
    """List AI sessions for the current user.

    Args:
        user_id: Current user ID (from auth).
        db_session: Database session.
        session_manager: Session manager.
        workspace_id: Workspace ID from X-Workspace-Id header.
        agent_name: Optional agent filter.
        search: Optional search query (matches title and context_history).
        group_by: 'date' to group sessions by date (Today, Yesterday, weekday, date).
        limit: Maximum sessions to return.

    Returns:
        List of sessions with metadata, optionally grouped by date.

    Raises:
        HTTPException: If session manager is not available.
    """
    # Set RLS context so PostgreSQL policies allow access
    await set_rls_context(db_session, user_id, workspace_id)

    from pilot_space.ai.sdk.session_store import SessionStore

    store = SessionStore(session_manager, db_session)

    sessions_data = await store.list_sessions_for_user(
        user_id=user_id,
        workspace_id=workspace_id,
        agent_name=agent_name,
        context_id=context_id,
        search=search,
        limit=limit,
    )

    sessions = [
        SessionListItem(
            id=UUID(s["id"]),
            workspace_id=UUID(s["workspace_id"]),
            agent_name=s["agent_name"],
            context_id=UUID(s["context_id"]) if s["context_id"] else None,
            title=s.get("title"),
            context_history=[ContextHistoryEntry(**ctx) for ctx in s.get("context_history", [])],
            turn_count=s["turn_count"],
            total_cost_usd=s["total_cost_usd"],
            created_at=s["created_at"],
            updated_at=s["updated_at"],
            expires_at=s["expires_at"],
            is_expired=s.get("is_expired", False),
        )
        for s in sessions_data
    ]

    # Optionally group by date
    groups: list[SessionGroup] | None = None
    if group_by == "date":
        groups = _group_sessions_by_date(sessions)

    return SessionListResponse(
        sessions=sessions,
        groups=groups,
        total=len(sessions),
    )


def _group_sessions_by_date(sessions: list[SessionListItem]) -> list[SessionGroup]:
    """Group sessions by date label (Today, Yesterday, weekday, date).

    Args:
        sessions: List of sessions to group.

    Returns:
        List of session groups.
    """
    from collections import defaultdict
    from datetime import UTC, datetime, timedelta

    now = datetime.now(UTC)
    today = now.date()
    yesterday = today - timedelta(days=1)

    groups_dict: dict[str, list[SessionListItem]] = defaultdict(list)

    for session in sessions:
        session_date = datetime.fromisoformat(session.updated_at).date()

        if session_date == today:
            label = "Today"
        elif session_date == yesterday:
            label = "Yesterday"
        elif (today - session_date).days < 7:
            # Within last week, use weekday name
            label = session_date.strftime("%A")
        else:
            # Older, use date format
            label = session_date.strftime("%B %d, %Y")

        groups_dict[label].append(session)

    # Preserve order: Today, Yesterday, weekdays, then older dates
    order = [
        "Today",
        "Yesterday",
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]
    result: list[SessionGroup] = []

    # Add known labels in order
    for label in order:
        if label in groups_dict:
            result.append(SessionGroup(date=label, sessions=groups_dict.pop(label)))

    # Add remaining date-based groups (sorted by date descending)
    for label in sorted(groups_dict.keys(), reverse=True):
        result.append(SessionGroup(date=label, sessions=groups_dict[label]))

    return result


@router.post("/{session_id}/resume")
async def resume_session(
    session_id: UUID,
    user_id: CurrentUserId,
    db_session: DbSession,
    session_manager: SessionManagerDep,
    workspace_id: WorkspaceId,
    limit: int = Query(3, ge=1, le=100, description="Max messages to return (latest first)"),
    offset: int = Query(0, ge=0, description="Skip N most recent messages (for loading older)"),
) -> SessionResumeResponse:
    """Resume an existing session with paginated message history.

    Loads session from database if not in Redis cache. Messages are paginated
    to support scroll-up loading in the frontend (load 3 latest initially,
    then load more when scrolling up).

    Args:
        session_id: Session UUID to resume.
        user_id: Current user ID (from auth).
        db_session: Database session.
        session_manager: Session manager.
        limit: Max messages to return (default 3 for initial load).
        offset: Skip N most recent messages (0=latest, 3=skip 3 newest).

    Returns:
        Session data with paginated message history.

    Raises:
        HTTPException: 404 if session not found or expired.

    """
    # Set RLS context so PostgreSQL policies allow access
    await set_rls_context(db_session, user_id, workspace_id)

    from pilot_space.ai.sdk.session_store import SessionStore

    store = SessionStore(session_manager, db_session)

    # Load from database (also restores to Redis, extends TTL if expired)
    session = await store.load_from_db(session_id)

    if not session:
        raise NotFoundError("Session not found")

    # Verify ownership
    if session.user_id != user_id:
        raise ForbiddenError("Access denied to this session")

    # Paginate messages: offset=0 means latest messages
    # Messages are stored chronologically (oldest first), we want latest first for pagination
    all_messages = session.messages
    total = len(all_messages)

    # Calculate slice indices for "offset from end" pagination
    # offset=0, limit=3 → last 3 messages → slice[total-3:total]
    # offset=3, limit=5 → messages before last 3 → slice[total-8:total-3]
    end_idx = total - offset
    start_idx = max(0, end_idx - limit)

    # Clamp indices
    if end_idx <= 0:
        paginated_messages: list[Any] = []
    else:
        paginated_messages = all_messages[start_idx:end_idx]

    # Convert messages to response format (maintaining chronological order)
    # Parse structured content for assistant messages to restore content blocks
    messages: list[dict[str, Any]] = []
    for msg in paginated_messages:
        msg_dict: dict[str, Any] = {
            "id": getattr(msg, "id", None),
            "role": msg.role,
            "timestamp": msg.timestamp.isoformat(),
            "tokens": msg.tokens,
            "cost_usd": msg.cost_usd,
            "metadata": getattr(msg, "metadata", None),
        }

        # Parse structured content for assistant messages
        if msg.role == "assistant" and msg.content:
            parsed = _parse_message_content(msg.content)
            msg_dict["content"] = parsed["content"]
            if parsed["content_blocks"]:
                msg_dict["content_blocks"] = parsed["content_blocks"]
            if parsed["thinking_blocks"]:
                msg_dict["thinking_blocks"] = parsed["thinking_blocks"]
            # Prefer persisted tool_calls; fall back to content-extracted ones
            persisted_tc = getattr(msg, "tool_calls", None)
            tool_calls = persisted_tc or parsed["tool_calls"]
            if tool_calls:
                msg_dict["tool_calls"] = tool_calls
        else:
            msg_dict["content"] = msg.content

        # Include question_data for session resume Q&A rendering
        question_data = getattr(msg, "question_data", None)
        if question_data is not None:
            msg_dict["question_data"] = question_data

        messages.append(msg_dict)

    # has_more is true if there are older messages beyond what we returned
    has_more = start_idx > 0

    return SessionResumeResponse(
        session_id=session.id,
        messages=messages,
        context=session.context,
        turn_count=session.turn_count,
        total_messages=total,
        has_more=has_more,
    )


@router.delete("/{session_id}")
async def delete_session(
    session_id: UUID,
    user_id: CurrentUserId,
    db_session: DbSession,
    session_manager: SessionManagerDep,
    workspace_id: WorkspaceId,
) -> dict[str, str]:
    """Delete a session.

    Removes from both Redis and database.

    Args:
        session_id: Session UUID to delete.
        user_id: Current user ID (from auth).
        db_session: Database session.
        session_manager: Session manager.

    Returns:
        Success message.

    Raises:
        HTTPException: 404 if session not found.

    """
    # Set RLS context so PostgreSQL policies allow access
    await set_rls_context(db_session, user_id, workspace_id)

    from pilot_space.ai.sdk.session_store import SessionStore

    store = SessionStore(session_manager, db_session)

    # Verify ownership first (load from DB)
    session = await store.load_from_db(session_id)
    if session and session.user_id != user_id:
        raise ForbiddenError("Access denied to this session")

    # Delete from both stores
    deleted = await store.delete_session(session_id)

    if not deleted:
        raise NotFoundError("Session not found")

    return {"message": "Session deleted successfully"}


__all__ = ["router"]
