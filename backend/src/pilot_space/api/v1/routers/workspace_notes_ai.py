"""Workspace-scoped Notes AI API router.

AI-specific endpoints for notes (content updates, etc.).
Supports both UUID and slug for workspace identification.
"""

from __future__ import annotations

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, status

from pilot_space.api.v1.schemas.note import AIUpdateRequest, AIUpdateResponse
from pilot_space.dependencies import CurrentUserId, DbSession
from pilot_space.infrastructure.database.repositories.note_repository import (
    NoteRepository,
)
from pilot_space.infrastructure.database.repositories.workspace_repository import (
    WorkspaceRepository,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def get_note_repository(session: DbSession) -> NoteRepository:
    """Get note repository with session."""
    return NoteRepository(session=session)


def get_workspace_repository(session: DbSession) -> WorkspaceRepository:
    """Get workspace repository with session."""
    return WorkspaceRepository(session=session)


NoteRepo = Annotated[NoteRepository, Depends(get_note_repository)]
WorkspaceRepo = Annotated[WorkspaceRepository, Depends(get_workspace_repository)]

WorkspaceIdOrSlug = Annotated[str, Path(description="Workspace ID (UUID) or slug")]
NoteIdPath = Annotated[UUID, Path(description="Note ID")]


def _is_valid_uuid(value: str) -> bool:
    """Check if a string is a valid UUID."""
    try:
        UUID(value)
        return True
    except ValueError:
        return False


async def _resolve_workspace(
    workspace_id_or_slug: str,
    workspace_repo: WorkspaceRepository,
):
    """Resolve workspace by UUID or slug."""
    from pilot_space.infrastructure.database.models.workspace import Workspace

    workspace: Workspace | None
    if _is_valid_uuid(workspace_id_or_slug):
        workspace = await workspace_repo.get_by_id(UUID(workspace_id_or_slug))
    else:
        workspace = await workspace_repo.get_by_slug(workspace_id_or_slug)

    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )
    return workspace


@router.patch(
    "/{workspace_id}/notes/{note_id}/ai-update",
    response_model=AIUpdateResponse,
    tags=["workspace-notes-ai"],
    summary="Apply AI-generated content update to a note",
)
async def ai_update_workspace_note(
    workspace_id: WorkspaceIdOrSlug,
    note_id: NoteIdPath,
    update_data: AIUpdateRequest,
    current_user_id: CurrentUserId,
    session: DbSession,
    note_repo: NoteRepo,
    workspace_repo: WorkspaceRepo,
) -> AIUpdateResponse:
    """Apply AI-generated content update to a note.

    Separate endpoint from user autosave for audit trail and conflict detection.
    Supports three operations:
    - replace_block: Replace a block's content by ID
    - append_blocks: Insert blocks after a specified position
    - insert_inline_issue: Add an inlineIssue node to a block

    Args:
        workspace_id: The workspace ID (UUID) or slug.
        note_id: The note ID.
        update_data: AI update request data.
        current_user_id: Current user ID.
        session: Database session.
        note_repo: Note repository.
        workspace_repo: Workspace repository.

    Returns:
        AI update response with affected blocks.

    Raises:
        HTTPException: If note not found or validation fails.
    """
    from pilot_space.application.services.note.ai_update_service import (
        AIUpdateOperation,
        AIUpdatePayload,
        NoteAIUpdateService,
    )

    workspace = await _resolve_workspace(workspace_id, workspace_repo)

    # Verify note exists and belongs to workspace
    note = await note_repo.get_by_id(note_id)
    if not note or note.workspace_id != workspace.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Note not found",
        )

    # Convert operation string to enum
    try:
        operation = AIUpdateOperation(update_data.operation)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid operation: {update_data.operation}",
        ) from None

    # Create payload
    payload = AIUpdatePayload(
        note_id=note_id,
        operation=operation,
        block_id=update_data.block_id,
        content=update_data.content,
        after_block_id=update_data.after_block_id,
        issue_data=update_data.issue_data,
        agent_session_id=update_data.agent_session_id,
        source_tool=update_data.source_tool,
        user_id=current_user_id,
    )

    # Execute update
    service = NoteAIUpdateService(session=session)
    try:
        result = await service.execute(payload)
        await session.commit()

        logger.info(
            "AI note update applied",
            extra={
                "note_id": str(note_id),
                "operation": update_data.operation,
                "affected_blocks": len(result.affected_block_ids),
                "agent_session": update_data.agent_session_id,
            },
        )

        return AIUpdateResponse(
            success=result.success,
            note_id=str(result.note_id),
            affected_block_ids=result.affected_block_ids,
            conflict=result.conflict,
        )
    except ValueError as e:
        logger.warning(
            "AI note update failed",
            extra={"note_id": str(note_id), "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


__all__ = ["router"]
