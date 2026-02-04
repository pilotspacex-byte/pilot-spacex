"""AI Session Management API endpoints.

Provides endpoints for listing, resuming, and managing AI conversation sessions.

Reference: T077-T079 (Session Persistence and Resumption)
Design Decisions: DD-058 (Session Management)
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from pilot_space.dependencies import CurrentUserId, DbSession, SessionManagerDep
from pilot_space.infrastructure.database.rls import set_rls_context

router = APIRouter(prefix="/ai/sessions", tags=["ai-sessions"])


class SessionListItem(BaseModel):
    """Session list item.

    Attributes:
        id: Session UUID.
        workspace_id: Workspace UUID.
        agent_name: Agent name.
        context_id: Optional context entity ID.
        turn_count: Number of conversation turns.
        total_cost_usd: Accumulated cost.
        created_at: Creation timestamp (ISO 8601).
        updated_at: Last update timestamp (ISO 8601).
        expires_at: Expiration timestamp (ISO 8601).
    """

    id: UUID = Field(..., description="Session ID")
    workspace_id: UUID = Field(..., description="Workspace ID")
    agent_name: str = Field(..., description="Agent name")
    context_id: UUID | None = Field(None, description="Context entity ID")
    turn_count: int = Field(..., ge=0, description="Number of turns")
    total_cost_usd: float = Field(..., ge=0, description="Total cost in USD")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")
    expires_at: str = Field(..., description="Expiration timestamp")


class SessionListResponse(BaseModel):
    """Session list response.

    Attributes:
        sessions: List of sessions.
        total: Total count.
    """

    sessions: list[SessionListItem] = Field(..., description="List of sessions")
    total: int = Field(..., ge=0, description="Total session count")


class SessionResumeResponse(BaseModel):
    """Session resume response.

    Attributes:
        session_id: Resumed session ID.
        messages: Conversation history.
        context: Session context data.
        turn_count: Number of turns.
    """

    session_id: UUID = Field(..., description="Session ID")
    messages: list[dict[str, Any]] = Field(..., description="Message history")
    context: dict[str, Any] = Field(default_factory=dict, description="Session context")
    turn_count: int = Field(..., ge=0, description="Number of turns")


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
    limit: int = Query(50, ge=1, le=100, description="Max results"),
) -> SessionListResponse:
    """List AI sessions for the current user.

    Args:
        user_id: Current user ID (from auth).
        db_session: Database session.
        session_manager: Session manager.
        workspace_id: Optional workspace filter.
        agent_name: Optional agent filter.
        limit: Maximum sessions to return.

    Returns:
        List of sessions with metadata.

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
        limit=limit,
    )

    sessions = [
        SessionListItem(
            id=UUID(s["id"]),
            workspace_id=UUID(s["workspace_id"]),
            agent_name=s["agent_name"],
            context_id=UUID(s["context_id"]) if s["context_id"] else None,
            turn_count=s["turn_count"],
            total_cost_usd=s["total_cost_usd"],
            created_at=s["created_at"],
            updated_at=s["updated_at"],
            expires_at=s["expires_at"],
        )
        for s in sessions_data
    ]

    return SessionListResponse(
        sessions=sessions,
        total=len(sessions),
    )


@router.post("/{session_id}/resume")
async def resume_session(
    session_id: UUID,
    user_id: CurrentUserId,
    db_session: DbSession,
    session_manager: SessionManagerDep,
) -> SessionResumeResponse:
    """Resume an existing session.

    Loads session from database if not in Redis cache.

    Args:
        session_id: Session UUID to resume.
        user_id: Current user ID (from auth).
        db_session: Database session.
        session_manager: Session manager.

    Returns:
        Session data with message history.

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

    # Convert messages to response format
    messages = [
        {
            "role": msg.role,
            "content": msg.content,
            "timestamp": msg.timestamp.isoformat(),
            "tokens": msg.tokens,
            "cost_usd": msg.cost_usd,
        }
        for msg in session.messages
    ]

    return SessionResumeResponse(
        session_id=session.id,
        messages=messages,
        context=session.context,
        turn_count=session.turn_count,
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
