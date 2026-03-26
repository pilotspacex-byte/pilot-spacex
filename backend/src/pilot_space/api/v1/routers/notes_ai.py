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

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, HTTPException, Path, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select

from pilot_space.ai.agents.agent_base import AgentContext
from pilot_space.ai.agents.pilotspace_agent import ChatInput, PilotSpaceAgent
from pilot_space.api.v1.schemas.ghost_text import GhostTextStreamRequest
from pilot_space.api.v1.streaming import create_sse_response
from pilot_space.container import Container
from pilot_space.dependencies.auth import SessionDep, get_current_user_id
from pilot_space.infrastructure.database.models.note import Note

router = APIRouter(prefix="/notes", tags=["notes-ai"])


# DI bridge: @inject makes Provide[] resolvable; FastAPI sees a plain callable.
@inject
def _get_pilotspace_agent(
    agent: PilotSpaceAgent = Depends(Provide[Container.pilotspace_agent]),
) -> PilotSpaceAgent:
    return agent


PilotSpaceAgentDep = Annotated[PilotSpaceAgent, Depends(_get_pilotspace_agent)]


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
    request_body: GhostTextStreamRequest,
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
