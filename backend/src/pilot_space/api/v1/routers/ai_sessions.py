"""AI Session Management API endpoints.

Provides endpoints for listing, resuming, and managing AI conversation sessions.

Reference: T077-T079 (Session Persistence and Resumption)
Design Decisions: DD-058 (Session Management)
"""

from __future__ import annotations

import json
import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from pilot_space.dependencies import CurrentUserId, DbSession, SessionManagerDep
from pilot_space.infrastructure.database.rls import set_rls_context

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai/sessions", tags=["ai-sessions"])


class ContextHistoryEntry(BaseModel):
    """Context history entry for multi-context sessions.

    Attributes:
        turn: Conversation turn when context was used.
        note_id: Note ID if context was a note.
        note_title: Note title if available.
        issue_id: Issue ID if context was an issue.
        block_ids: Block IDs if specific blocks were selected.
        selected_text: Selected text if available.
        timestamp: When the context was used.
    """

    turn: int = Field(..., ge=0, description="Turn number")
    note_id: str | None = Field(None, description="Note ID")
    note_title: str | None = Field(None, description="Note title")
    issue_id: str | None = Field(None, description="Issue ID")
    block_ids: list[str] | None = Field(None, description="Block IDs")
    selected_text: str | None = Field(None, description="Selected text")
    timestamp: str = Field(..., description="Timestamp")


class SessionListItem(BaseModel):
    """Session list item.

    Attributes:
        id: Session UUID.
        workspace_id: Workspace UUID.
        agent_name: Agent name.
        context_id: Optional initial context entity ID.
        title: Auto-generated session title.
        context_history: History of contexts used in this session.
        turn_count: Number of conversation turns.
        total_cost_usd: Accumulated cost.
        created_at: Creation timestamp (ISO 8601).
        updated_at: Last update timestamp (ISO 8601).
        expires_at: Expiration timestamp (ISO 8601).
    """

    id: UUID = Field(..., description="Session ID")
    workspace_id: UUID = Field(..., description="Workspace ID")
    agent_name: str = Field(..., description="Agent name")
    context_id: UUID | None = Field(None, description="Initial context entity ID")
    title: str | None = Field(None, description="Auto-generated session title")
    context_history: list[ContextHistoryEntry] = Field(
        default_factory=list, description="History of contexts used"
    )
    turn_count: int = Field(..., ge=0, description="Number of turns")
    total_cost_usd: float = Field(..., ge=0, description="Total cost in USD")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")
    expires_at: str = Field(..., description="Expiration timestamp")


class SessionGroup(BaseModel):
    """Group of sessions by date.

    Attributes:
        date: Group label (Today, Yesterday, weekday, or ISO date).
        sessions: Sessions in this group.
    """

    date: str = Field(..., description="Date label")
    sessions: list[SessionListItem] = Field(..., description="Sessions in group")


class SessionListResponse(BaseModel):
    """Session list response.

    Attributes:
        sessions: List of sessions (flat).
        groups: Optional grouped sessions by date.
        total: Total count.
    """

    sessions: list[SessionListItem] = Field(..., description="List of sessions")
    groups: list[SessionGroup] | None = Field(None, description="Sessions grouped by date")
    total: int = Field(..., ge=0, description="Total session count")


class SessionResumeResponse(BaseModel):
    """Session resume response.

    Attributes:
        session_id: Resumed session ID.
        messages: Conversation history (paginated, chronological order).
        context: Session context data.
        turn_count: Number of turns.
        total_messages: Total message count in session.
        has_more: Whether older messages exist (for scroll-up loading).
    """

    session_id: UUID = Field(..., description="Session ID")
    messages: list[dict[str, Any]] = Field(..., description="Message history")
    context: dict[str, Any] = Field(default_factory=dict, description="Session context")
    turn_count: int = Field(..., ge=0, description="Number of turns")
    total_messages: int = Field(..., ge=0, description="Total message count")
    has_more: bool = Field(..., description="Whether older messages exist")


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
    """
    # Check if content is a JSON array of structured blocks
    if not content or not content.strip().startswith("["):
        return {"content": content, "content_blocks": None, "thinking_blocks": None}

    try:
        blocks = json.loads(content)
        if not isinstance(blocks, list):
            return {"content": content, "content_blocks": None, "thinking_blocks": None}
    except (json.JSONDecodeError, TypeError):
        return {"content": content, "content_blocks": None, "thinking_blocks": None}

    # Parse structured blocks
    text_parts: list[str] = []
    content_blocks: list[dict[str, Any]] = []
    thinking_blocks: list[dict[str, Any]] = []

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
            thinking_blocks.append({
                "content": thinking,
                "blockIndex": idx,
                "redacted": False,
            })
            content_blocks.append({
                "type": "thinking",
                "blockIndex": idx,
                "content": thinking,
            })

        elif block_type == "tool_use":
            tool_id = block.get("id", "")
            content_blocks.append({
                "type": "tool_call",
                "toolCallId": tool_id,
            })

    return {
        "content": "".join(text_parts),
        "content_blocks": content_blocks if content_blocks else None,
        "thinking_blocks": thinking_blocks if thinking_blocks else None,
    }


@router.get("")
async def list_sessions(
    user_id: CurrentUserId,
    db_session: DbSession,
    session_manager: SessionManagerDep,
    workspace_id: UUID | None = Query(None, description="Filter by workspace"),
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
        workspace_id: Optional workspace filter.
        agent_name: Optional agent filter.
        search: Optional search query (matches title and context_history).
        group_by: 'date' to group sessions by date (Today, Yesterday, weekday, date).
        limit: Maximum sessions to return.

    Returns:
        List of sessions with metadata, optionally grouped by date.

    Raises:
        HTTPException: If session manager is not available.
    """
    if session_manager is None:
        raise HTTPException(status_code=503, detail="Session manager not available")

    # Set RLS context so PostgreSQL policies allow access
    await set_rls_context(db_session, user_id)

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
            context_history=[
                ContextHistoryEntry(**ctx) for ctx in s.get("context_history", [])
            ],
            turn_count=s["turn_count"],
            total_cost_usd=s["total_cost_usd"],
            created_at=s["created_at"],
            updated_at=s["updated_at"],
            expires_at=s["expires_at"],
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
    order = ["Today", "Yesterday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
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
        HTTPException: 503 if session manager not available.
    """
    if session_manager is None:
        raise HTTPException(status_code=503, detail="Session manager not available")

    # Set RLS context so PostgreSQL policies allow access
    await set_rls_context(db_session, user_id)

    from pilot_space.ai.sdk.session_store import SessionStore

    store = SessionStore(session_manager, db_session)

    # Load from database (also restores to Redis)
    session = await store.load_from_db(session_id)

    if not session:
        raise HTTPException(
            status_code=404,
            detail="Session not found or expired",
        )

    # Verify ownership
    if session.user_id != user_id:
        raise HTTPException(
            status_code=403,
            detail="Access denied to this session",
        )

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
        else:
            msg_dict["content"] = msg.content

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
        HTTPException: 503 if session manager not available.
    """
    if session_manager is None:
        raise HTTPException(status_code=503, detail="Session manager not available")

    # Set RLS context so PostgreSQL policies allow access
    await set_rls_context(db_session, user_id)

    from pilot_space.ai.sdk.session_store import SessionStore

    store = SessionStore(session_manager, db_session)

    # Verify ownership first (load from DB)
    session = await store.load_from_db(session_id)
    if session and session.user_id != user_id:
        raise HTTPException(
            status_code=403,
            detail="Access denied to this session",
        )

    # Delete from both stores
    deleted = await store.delete_session(session_id)

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Session not found",
        )

    return {"message": "Session deleted successfully"}


__all__ = ["router"]
