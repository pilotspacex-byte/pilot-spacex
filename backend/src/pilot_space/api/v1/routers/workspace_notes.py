"""Workspace-scoped Notes API router.

Provides nested CRUD routes for notes under workspaces.
Supports both UUID and slug for workspace identification.
"""

from __future__ import annotations

import logging
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status

from pilot_space.api.v1.schemas.annotation import (
    AnnotationResponse,
    AnnotationStatus,
    AnnotationStatusUpdate,
    AnnotationType,
)
from pilot_space.api.v1.schemas.base import DeleteResponse, PaginatedResponse
from pilot_space.api.v1.schemas.note import (
    NoteCreate,
    NoteDetailResponse,
    NoteResponse,
    NoteUpdate,
    TipTapContentSchema,
)
from pilot_space.dependencies import CurrentUserId, DbSession, SyncedUserId
from pilot_space.infrastructure.database.models.note import Note
from pilot_space.infrastructure.database.models.note_annotation import NoteAnnotation
from pilot_space.infrastructure.database.models.workspace import Workspace
from pilot_space.infrastructure.database.repositories.note_annotation_repository import (
    NoteAnnotationRepository,
)
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


def get_annotation_repository(session: DbSession) -> NoteAnnotationRepository:
    """Get annotation repository with session."""
    return NoteAnnotationRepository(session=session)


NoteRepo = Annotated[NoteRepository, Depends(get_note_repository)]
WorkspaceRepo = Annotated[WorkspaceRepository, Depends(get_workspace_repository)]
AnnotationRepo = Annotated[NoteAnnotationRepository, Depends(get_annotation_repository)]

# Accept string to support both UUID and slug
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
) -> Workspace:
    """Resolve workspace by UUID or slug.

    Args:
        workspace_id_or_slug: Either a UUID string or a slug.
        workspace_repo: Workspace repository.

    Returns:
        Workspace model.

    Raises:
        HTTPException: If workspace not found.
    """
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


def _note_to_response(note: Note) -> NoteResponse:
    """Convert Note model to NoteResponse schema."""
    return NoteResponse(
        id=note.id,
        created_at=note.created_at,
        updated_at=note.updated_at,
        project_id=note.project_id,
        title=note.title,
        is_pinned=note.is_pinned,
        word_count=note.word_count,
        last_edited_by_id=note.owner_id,
    )


def _note_to_detail_response(note: Note) -> NoteDetailResponse:
    """Convert Note model to NoteDetailResponse schema."""
    content = None
    if note.content:
        content = TipTapContentSchema(
            type="doc",
            content=note.content.get("content", []),
        )
    return NoteDetailResponse(
        id=note.id,
        created_at=note.created_at,
        updated_at=note.updated_at,
        project_id=note.project_id,
        title=note.title,
        is_pinned=note.is_pinned,
        word_count=note.word_count,
        last_edited_by_id=note.owner_id,
        content=content,
        annotation_count=len(note.annotations) if note.annotations else 0,
        discussion_count=len(note.discussions) if note.discussions else 0,
    )


@router.get(
    "/{workspace_id}/notes",
    response_model=PaginatedResponse[NoteResponse],
    tags=["workspace-notes"],
    summary="List notes in workspace",
)
async def list_workspace_notes(
    workspace_id: WorkspaceIdOrSlug,
    current_user_id: CurrentUserId,
    note_repo: NoteRepo,
    workspace_repo: WorkspaceRepo,
    project_id: Annotated[UUID | None, Query(description="Filter by project")] = None,
    is_pinned: Annotated[bool | None, Query(description="Filter by pin status")] = None,
    search: Annotated[str | None, Query(description="Search query")] = None,
    cursor: Annotated[str | None, Query(description="Pagination cursor")] = None,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PaginatedResponse[NoteResponse]:
    """List all notes in a workspace.

    Args:
        workspace_id: The workspace ID (UUID) or slug.
        current_user_id: Current user ID.
        note_repo: Note repository.
        workspace_repo: Workspace repository.
        project_id: Optional project filter.
        is_pinned: Optional pin status filter.
        search: Optional search query.
        cursor: Pagination cursor.
        page_size: Page size.

    Returns:
        Paginated list of notes.
    """
    workspace = await _resolve_workspace(workspace_id, workspace_repo)

    # Get notes
    offset = int(cursor) if cursor and cursor.isdigit() else 0

    if search:
        notes = await note_repo.search_by_title(
            workspace.id,
            search,
            project_id=project_id,
            limit=page_size,
        )
    elif project_id:
        notes = await note_repo.get_by_project(project_id, limit=page_size)
    elif is_pinned:
        notes = await note_repo.get_pinned_notes(workspace.id, limit=page_size)
    else:
        notes = await note_repo.get_by_workspace(
            workspace.id,
            limit=page_size,
            offset=offset,
        )

    items = [_note_to_response(note) for note in notes]
    total = len(items)
    has_next = len(items) == page_size
    next_cursor = str(offset + page_size) if has_next else None

    return PaginatedResponse(
        items=items,
        total=total,
        next_cursor=next_cursor,
        prev_cursor=str(max(0, offset - page_size)) if offset > 0 else None,
        has_next=has_next,
        has_prev=offset > 0,
        page_size=page_size,
    )


@router.get(
    "/{workspace_id}/notes/{note_id}",
    response_model=NoteDetailResponse,
    tags=["workspace-notes"],
    summary="Get note by ID",
)
async def get_workspace_note(
    workspace_id: WorkspaceIdOrSlug,
    note_id: NoteIdPath,
    current_user_id: CurrentUserId,
    note_repo: NoteRepo,
    workspace_repo: WorkspaceRepo,
) -> NoteDetailResponse:
    """Get a specific note by ID.

    Args:
        workspace_id: The workspace ID (UUID) or slug.
        note_id: The note ID.
        current_user_id: Current user ID.
        note_repo: Note repository.
        workspace_repo: Workspace repository.

    Returns:
        Note details.

    Raises:
        HTTPException: If note not found.
    """
    workspace = await _resolve_workspace(workspace_id, workspace_repo)

    # Get note with all relations
    note = await note_repo.get_with_all_relations(note_id)
    if not note or note.workspace_id != workspace.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Note not found",
        )

    return _note_to_detail_response(note)


@router.post(
    "/{workspace_id}/notes",
    response_model=NoteResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["workspace-notes"],
    summary="Create a new note",
)
async def create_workspace_note(
    workspace_id: WorkspaceIdOrSlug,
    note_data: NoteCreate,
    current_user_id: SyncedUserId,
    session: DbSession,
    note_repo: NoteRepo,
    workspace_repo: WorkspaceRepo,
) -> NoteResponse:
    """Create a new note in the workspace.

    Args:
        workspace_id: The workspace ID (UUID) or slug.
        note_data: Note creation data.
        current_user_id: Current user ID.
        session: Database session.
        note_repo: Note repository.
        workspace_repo: Workspace repository.

    Returns:
        Created note.
    """
    workspace = await _resolve_workspace(workspace_id, workspace_repo)

    # Create note
    content: dict[str, Any] = {}
    if note_data.content:
        content = {"type": note_data.content.type, "content": note_data.content.content}

    note = Note(
        workspace_id=workspace.id,
        project_id=note_data.project_id,
        title=note_data.title,
        content=content,
        is_pinned=note_data.is_pinned,
        owner_id=current_user_id,
        word_count=0,
    )
    note = await note_repo.create(note)
    await session.commit()

    logger.info(
        "Note created",
        extra={"note_id": str(note.id), "workspace_id": str(workspace.id)},
    )

    return _note_to_response(note)


@router.patch(
    "/{workspace_id}/notes/{note_id}",
    response_model=NoteResponse,
    tags=["workspace-notes"],
    summary="Update a note",
)
async def update_workspace_note(
    workspace_id: WorkspaceIdOrSlug,
    note_id: NoteIdPath,
    note_data: NoteUpdate,
    current_user_id: CurrentUserId,
    session: DbSession,
    note_repo: NoteRepo,
    workspace_repo: WorkspaceRepo,
) -> NoteResponse:
    """Update an existing note.

    Args:
        workspace_id: The workspace ID (UUID) or slug.
        note_id: The note ID.
        note_data: Note update data.
        current_user_id: Current user ID.
        session: Database session.
        note_repo: Note repository.
        workspace_repo: Workspace repository.

    Returns:
        Updated note.
    """
    workspace = await _resolve_workspace(workspace_id, workspace_repo)

    # Get note
    note = await note_repo.get_by_id(note_id)
    if not note or note.workspace_id != workspace.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Note not found",
        )

    # Update fields
    update_data = note_data.model_dump(exclude_unset=True)
    if update_data.get("content"):
        content = update_data["content"]
        # Content is already a dict after model_dump
        update_data["content"] = {
            "type": content.get("type", "doc"),
            "content": content.get("content", []),
        }
    for key, value in update_data.items():
        setattr(note, key, value)

    note = await note_repo.update(note)
    await session.commit()

    logger.info(
        "Note updated",
        extra={"note_id": str(note_id), "workspace_id": str(workspace.id)},
    )

    return _note_to_response(note)


@router.delete(
    "/{workspace_id}/notes/{note_id}",
    response_model=DeleteResponse,
    tags=["workspace-notes"],
    summary="Delete a note",
)
async def delete_workspace_note(
    workspace_id: WorkspaceIdOrSlug,
    note_id: NoteIdPath,
    current_user_id: CurrentUserId,
    session: DbSession,
    note_repo: NoteRepo,
    workspace_repo: WorkspaceRepo,
) -> DeleteResponse:
    """Soft delete a note.

    Args:
        workspace_id: The workspace ID (UUID) or slug.
        note_id: The note ID.
        current_user_id: Current user ID.
        session: Database session.
        note_repo: Note repository.
        workspace_repo: Workspace repository.

    Returns:
        Delete confirmation.
    """
    workspace = await _resolve_workspace(workspace_id, workspace_repo)

    # Get note
    note = await note_repo.get_by_id(note_id)
    if not note or note.workspace_id != workspace.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Note not found",
        )

    # Soft delete
    await note_repo.delete(note)
    await session.commit()

    logger.info(
        "Note deleted",
        extra={"note_id": str(note_id), "workspace_id": str(workspace.id)},
    )

    return DeleteResponse(id=note_id, message="Note deleted successfully")


@router.post(
    "/{workspace_id}/notes/{note_id}/pin",
    response_model=NoteResponse,
    tags=["workspace-notes"],
    summary="Pin a note",
)
async def pin_workspace_note(
    workspace_id: WorkspaceIdOrSlug,
    note_id: NoteIdPath,
    current_user_id: CurrentUserId,
    session: DbSession,
    note_repo: NoteRepo,
    workspace_repo: WorkspaceRepo,
) -> NoteResponse:
    """Pin a note for quick access.

    Args:
        workspace_id: The workspace ID (UUID) or slug.
        note_id: The note ID.
        current_user_id: Current user ID.
        session: Database session.
        note_repo: Note repository.
        workspace_repo: Workspace repository.

    Returns:
        Updated note.
    """
    workspace = await _resolve_workspace(workspace_id, workspace_repo)

    # Get note
    note = await note_repo.get_by_id(note_id)
    if not note or note.workspace_id != workspace.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Note not found",
        )

    # Pin
    note.is_pinned = True
    note = await note_repo.update(note)
    await session.commit()

    return _note_to_response(note)


@router.delete(
    "/{workspace_id}/notes/{note_id}/pin",
    response_model=NoteResponse,
    tags=["workspace-notes"],
    summary="Unpin a note",
)
async def unpin_workspace_note(
    workspace_id: WorkspaceIdOrSlug,
    note_id: NoteIdPath,
    current_user_id: CurrentUserId,
    session: DbSession,
    note_repo: NoteRepo,
    workspace_repo: WorkspaceRepo,
) -> NoteResponse:
    """Unpin a note.

    Args:
        workspace_id: The workspace ID (UUID) or slug.
        note_id: The note ID.
        current_user_id: Current user ID.
        session: Database session.
        note_repo: Note repository.
        workspace_repo: Workspace repository.

    Returns:
        Updated note.
    """
    workspace = await _resolve_workspace(workspace_id, workspace_repo)

    # Get note
    note = await note_repo.get_by_id(note_id)
    if not note or note.workspace_id != workspace.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Note not found",
        )

    # Unpin
    note.is_pinned = False
    note = await note_repo.update(note)
    await session.commit()

    return _note_to_response(note)


# =============================================================================
# Annotation Endpoints
# =============================================================================


def _annotation_to_response(annotation: NoteAnnotation) -> AnnotationResponse:
    """Convert NoteAnnotation model to AnnotationResponse schema."""
    return AnnotationResponse(
        id=annotation.id,
        created_at=annotation.created_at,
        updated_at=annotation.updated_at,
        note_id=annotation.note_id,
        block_id=annotation.block_id,
        type=AnnotationType(annotation.type.value),
        content=annotation.content,
        confidence=annotation.confidence,
        status=AnnotationStatus(annotation.status.value),
        highlight_start=None,
        highlight_end=None,
        is_ai_generated=True,  # All annotations from DB are AI-generated
        created_by_id=None,
        converted_issue_id=None,
    )


@router.get(
    "/{workspace_id}/notes/{note_id}/annotations",
    response_model=list[AnnotationResponse],
    tags=["workspace-notes"],
    summary="Get note annotations",
)
async def get_note_annotations(
    workspace_id: WorkspaceIdOrSlug,
    note_id: NoteIdPath,
    current_user_id: CurrentUserId,
    note_repo: NoteRepo,
    annotation_repo: AnnotationRepo,
    workspace_repo: WorkspaceRepo,
) -> list[AnnotationResponse]:
    """Get all annotations for a note.

    Args:
        workspace_id: The workspace ID (UUID) or slug.
        note_id: The note ID.
        current_user_id: Current user ID.
        note_repo: Note repository.
        annotation_repo: Annotation repository.
        workspace_repo: Workspace repository.

    Returns:
        List of annotations.
    """
    workspace = await _resolve_workspace(workspace_id, workspace_repo)

    # Verify note exists and belongs to workspace
    note = await note_repo.get_by_id(note_id)
    if not note or note.workspace_id != workspace.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Note not found",
        )

    annotations = await annotation_repo.get_by_note(note_id)
    return [_annotation_to_response(a) for a in annotations]


@router.patch(
    "/{workspace_id}/notes/{note_id}/annotations/{annotation_id}",
    response_model=AnnotationResponse,
    tags=["workspace-notes"],
    summary="Update annotation status",
)
async def update_annotation_status(
    workspace_id: WorkspaceIdOrSlug,
    note_id: NoteIdPath,
    annotation_id: Annotated[UUID, Path(description="Annotation ID")],
    status_update: AnnotationStatusUpdate,
    current_user_id: CurrentUserId,
    session: DbSession,
    note_repo: NoteRepo,
    annotation_repo: AnnotationRepo,
    workspace_repo: WorkspaceRepo,
) -> AnnotationResponse:
    """Update annotation status (accept/reject/dismiss).

    Args:
        workspace_id: The workspace ID (UUID) or slug.
        note_id: The note ID.
        annotation_id: The annotation ID.
        status_update: New status data.
        current_user_id: Current user ID.
        session: Database session.
        note_repo: Note repository.
        annotation_repo: Annotation repository.
        workspace_repo: Workspace repository.

    Returns:
        Updated annotation.
    """
    from pilot_space.infrastructure.database.models.note_annotation import (
        AnnotationStatus as DBAnnotationStatus,
    )

    workspace = await _resolve_workspace(workspace_id, workspace_repo)

    # Verify note exists and belongs to workspace
    note = await note_repo.get_by_id(note_id)
    if not note or note.workspace_id != workspace.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Note not found",
        )

    # Get annotation
    annotation = await annotation_repo.get_by_id(annotation_id)
    if not annotation or annotation.note_id != note_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Annotation not found",
        )

    # Update status
    annotation.status = DBAnnotationStatus(status_update.status.value)
    await annotation_repo.update(annotation)
    await session.commit()

    logger.info(
        "Annotation status updated",
        extra={
            "annotation_id": str(annotation_id),
            "note_id": str(note_id),
            "new_status": status_update.status.value,
        },
    )

    return _annotation_to_response(annotation)


@router.get(
    "/{workspace_id}/notes/{note_id}/versions",
    response_model=list[Any],
    tags=["workspace-notes"],
    summary="Get note version history",
)
async def get_note_versions(
    workspace_id: WorkspaceIdOrSlug,
    note_id: NoteIdPath,
    current_user_id: CurrentUserId,
    note_repo: NoteRepo,
    workspace_repo: WorkspaceRepo,
) -> list[Any]:
    """Get version history for a note.

    Note: Version history feature is not yet fully implemented.
    Returns an empty list for now.

    Args:
        workspace_id: The workspace ID (UUID) or slug.
        note_id: The note ID.
        current_user_id: Current user ID.
        note_repo: Note repository.
        workspace_repo: Workspace repository.

    Returns:
        List of note versions (empty until feature is implemented).
    """
    workspace = await _resolve_workspace(workspace_id, workspace_repo)

    # Verify note exists and belongs to workspace
    note = await note_repo.get_by_id(note_id)
    if not note or note.workspace_id != workspace.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Note not found",
        )

    # TODO: Implement version history with NoteVersion model
    return []


__all__ = ["router"]
