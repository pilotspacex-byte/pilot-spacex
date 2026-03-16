"""AI endpoints for notes - ghost text suggestions.

Provides SSE streaming endpoint for AI-powered inline text completion.

Related:
- T113: GhostText SSE endpoint
- DD-066: SSE for AI streaming
- frontend/src/stores/ai/GhostTextStore.ts
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select

from pilot_space.ai.agents.agent_base import AgentContext
from pilot_space.ai.agents.pilotspace_agent import ChatInput, PilotSpaceAgent
from pilot_space.api.v1.streaming import create_sse_response
from pilot_space.container import Container
from pilot_space.dependencies.auth import SessionDep, get_current_user_id
from pilot_space.infrastructure.database.models.note import Note

router = APIRouter(prefix="/notes", tags=["notes-ai"])

# Type alias for dependency injection
PilotSpaceAgentDep = Annotated[
    PilotSpaceAgent,
    Depends(Container.pilotspace_agent),
]


class GhostTextRequest(BaseModel):
    """Request schema for ghost text generation.

    Attributes:
        context: Text content before cursor.
        cursor_position: Cursor position in document.
    """

    context: str = Field(
        ...,
        description="Text content before cursor for context",
        min_length=1,
        max_length=10000,
    )
    cursor_position: int = Field(
        ...,
        description="Cursor position in document",
        ge=0,
    )


@router.post(
    "/{note_id}/ghost-text",
    response_class=StreamingResponse,
    summary="Stream ghost text suggestions",
    description="""
    Generate AI-powered inline text completion suggestions.

    Returns SSE stream with:
    - `token` events: Incremental text chunks
    - `done` event: Completion signal
    - `error` event: Error information

    The ghost text agent provides context-aware completions based on:
    - Text before cursor
    - Document structure
    - Writing style
    """,
)
async def ghost_text_stream(
    note_id: Annotated[UUID, Path(description="Note UUID")],
    request_body: GhostTextRequest,
    request: Request,
    session: SessionDep,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    agent: PilotSpaceAgentDep,
):
    """Stream ghost text suggestions for note editing.

    Args:
        note_id: UUID of the note being edited.
        request_body: Ghost text request with context and cursor position.
        request: FastAPI request for SSE disconnect detection.
        agent: PilotSpace agent for execution.
        user_id: Current authenticated user ID.
        session: Database session for note lookup.

    Returns:
        SSE streaming response with text suggestions.

    Raises:
        HTTPException: 404 if note not found, 403 if not authorized.
    """
    # Verify note exists and get workspace_id (RLS handles permission check)
    stmt = select(Note.workspace_id).where(
        Note.id == note_id,
        Note.deleted_at.is_(None),
    )
    result = await session.execute(stmt)
    workspace_id = result.scalar_one_or_none()

    if workspace_id is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Note {note_id} not found or access denied",
        )

    # Create agent context
    context = AgentContext(
        workspace_id=workspace_id,
        user_id=user_id,
    )

    # Prepare chat input for ghost text via PilotSpaceAgent
    chat_input = ChatInput(
        message=f"Generate ghost text completion after this context:\n\n{request_body.context}\n\nCursor position: {request_body.cursor_position}",
        context={
            "note_id": str(note_id),
            "cursor_position": request_body.cursor_position,
        },
        workspace_id=workspace_id,
        user_id=user_id,
    )

    # Stream ghost text suggestions
    stream = agent.stream(chat_input, context)
    return create_sse_response(stream, request)


__all__ = ["router"]
