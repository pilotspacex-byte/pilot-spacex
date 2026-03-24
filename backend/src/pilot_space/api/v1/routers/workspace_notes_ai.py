"""Workspace-scoped Notes AI API router.

AI-specific endpoints for notes (content updates, etc.).
Supports both UUID and slug for workspace identification.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, status
from pydantic import BaseModel, Field

from pilot_space.api.v1.dependencies import (
    CreateIssueServiceDep,
    NoteAIUpdateServiceDep,
    WorkspaceRepositoryDep,
)
from pilot_space.api.v1.schemas.note import AIUpdateRequest, AIUpdateResponse
from pilot_space.dependencies.auth import CurrentUserId, SessionDep
from pilot_space.domain.exceptions import NotFoundError
from pilot_space.infrastructure.database.repositories.note_repository import (
    NoteRepository,
)
from pilot_space.infrastructure.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


def get_note_repository(session: SessionDep) -> NoteRepository:
    """Get note repository with session."""
    return NoteRepository(session=session)


NoteRepo = Annotated[NoteRepository, Depends(get_note_repository)]

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
    workspace_repo: WorkspaceRepositoryDep,
):
    """Resolve workspace by UUID or slug."""
    from pilot_space.infrastructure.database.models.workspace import Workspace

    workspace: Workspace | None
    if _is_valid_uuid(workspace_id_or_slug):
        workspace = await workspace_repo.get_by_id(UUID(workspace_id_or_slug))
    else:
        workspace = await workspace_repo.get_by_slug(workspace_id_or_slug)

    if not workspace:
        raise NotFoundError("Workspace not found")
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
    session: SessionDep,
    current_user_id: CurrentUserId,
    note_repo: NoteRepo,
    ai_update_service: NoteAIUpdateServiceDep,
    workspace_repo: WorkspaceRepositoryDep,
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
    )

    workspace = await _resolve_workspace(workspace_id, workspace_repo)

    # Verify note exists and belongs to workspace
    note = await note_repo.get_by_id(note_id)
    if not note or note.workspace_id != workspace.id:
        raise NotFoundError("Note not found")

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
    result = await ai_update_service.execute(payload)
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


class ExtractedIssueInput(BaseModel):
    """Single extracted issue to create."""

    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    priority: str = "medium"
    type: str = "task"
    source_block_id: str | None = None


class CreateExtractedIssuesRequest(BaseModel):
    """Request to create multiple extracted issues from a note."""

    issues: list[ExtractedIssueInput] = Field(..., min_length=1, max_length=50)


class CreateExtractedIssuesResponse(BaseModel):
    """Response with created issue IDs."""

    created_issue_ids: list[str]
    count: int


@router.post(
    "/{workspace_id}/notes/{note_id}/create-extracted-issues",
    response_model=CreateExtractedIssuesResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["workspace-notes-ai"],
    summary="Create issues from AI extraction results",
    description=(
        "Create multiple issues extracted by AI from note content. "
        "User has explicitly selected which issues to create — no approval needed."
    ),
)
async def create_extracted_issues(
    workspace_id: WorkspaceIdOrSlug,
    note_id: NoteIdPath,
    body: CreateExtractedIssuesRequest,
    session: SessionDep,
    current_user_id: CurrentUserId,
    note_repo: NoteRepo,
    create_issue_service: CreateIssueServiceDep,
    workspace_repo: WorkspaceRepositoryDep,
) -> CreateExtractedIssuesResponse:
    """Create issues from AI extraction and link them to the note.

    Args:
        workspace_id: Workspace ID (UUID) or slug.
        note_id: Note ID the issues were extracted from.
        body: Extracted issues to create.
        current_user_id: Current user ID.
        session: Database session.
        note_repo: Note repository.
        workspace_repo: Workspace repository.

    Returns:
        Created issue IDs and count.

    Raises:
        HTTPException: If note/workspace not found or validation fails.
    """
    from pilot_space.application.services.issue.create_issue_service import (
        CreateIssuePayload,
    )
    from pilot_space.infrastructure.database.models.issue import IssuePriority
    from pilot_space.infrastructure.database.models.note_issue_link import (
        NoteIssueLink,
        NoteLinkType,
    )
    from pilot_space.infrastructure.database.repositories.project_repository import (
        ProjectRepository,
    )

    workspace = await _resolve_workspace(workspace_id, workspace_repo)

    # Verify note exists and belongs to workspace
    note = await note_repo.get_by_id(note_id)
    if not note or note.workspace_id != workspace.id:
        raise NotFoundError("Note not found")

    # Get project_id from note or first workspace project
    project_id = note.project_id
    if not project_id:
        project_repo = ProjectRepository(session=session)
        projects = await project_repo.get_workspace_projects(workspace.id)
        if not projects:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Note has no project and workspace has no projects",
            )
        project_id = projects[0].id

    priority_map = {
        "urgent": IssuePriority.URGENT,
        "high": IssuePriority.HIGH,
        "medium": IssuePriority.MEDIUM,
        "low": IssuePriority.LOW,
        "none": IssuePriority.NONE,
    }

    created_ids: list[str] = []

    for extracted in body.issues:
        payload = CreateIssuePayload(
            workspace_id=workspace.id,
            project_id=project_id,
            reporter_id=current_user_id,
            name=extracted.title,
            description=extracted.description,
            priority=priority_map.get(extracted.priority, IssuePriority.MEDIUM),
            ai_enhanced=False,
        )
        result = await create_issue_service.execute(payload)
        created_ids.append(str(result.issue.id))

        # Create NoteIssueLink to track extraction traceability
        link = NoteIssueLink(
            note_id=note_id,
            issue_id=result.issue.id,
            link_type=NoteLinkType.EXTRACTED,
            block_id=extracted.source_block_id,
            workspace_id=workspace.id,
        )
        session.add(link)

    await session.commit()

    logger.info(
        "Created %d extracted issues from note %s",
        len(created_ids),
        str(note_id),
    )

    return CreateExtractedIssuesResponse(
        created_issue_ids=created_ids,
        count=len(created_ids),
    )


__all__ = ["router"]
