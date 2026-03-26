"""Pydantic schemas for AI session management endpoints.

Covers ContextHistoryEntry, SessionListItem, SessionGroup,
SessionListResponse, SessionResumeResponse.

Reference: T077-T079 (Session Persistence and Resumption)
Design Decisions: DD-058 (Session Management)
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


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
    is_expired: bool = Field(False, description="Whether this session has expired")


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


__all__ = [
    "ContextHistoryEntry",
    "SessionGroup",
    "SessionListItem",
    "SessionListResponse",
    "SessionResumeResponse",
]
