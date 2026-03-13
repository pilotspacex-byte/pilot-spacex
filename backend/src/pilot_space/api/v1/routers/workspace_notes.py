"""Workspace-scoped Notes API router (CRUD + tree operations).

Annotation endpoints are in workspace_note_annotations.py to keep file size under 700 lines.
"""

from __future__ import annotations

import json
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Path, Query, Response, status

from pilot_space.api.middleware import create_problem_response

from pilot_space.api.v1.dependencies import (
    CreateNoteServiceDep,
    DeleteNoteServiceDep,
    GetNoteServiceDep,
    ListNotesServiceDep,
    NoteRepositoryDep,
    MovePageServiceDep,
    PinNoteServiceDep,
    ProjectRepositoryDep,
    ReorderPageServiceDep,
    UpdateNoteServiceDep,
    WorkspaceRepositoryDep,
)
from pilot_space.api.v1.routers.workspace_quota import (
    _check_storage_quota,  # pyright: ignore[reportPrivateUsage]
    _update_storage_usage,  # pyright: ignore[reportPrivateUsage]
)
from pilot_space.api.v1.schemas.base import DeleteResponse, PaginatedResponse
from pilot_space.api.v1.schemas.issue import IssueBriefResponse
from pilot_space.api.v1.schemas.note import (
    MovePageRequest,
    NoteCreate,
    NoteDetailResponse,
    NoteMove,
    NoteResponse,
    NoteUpdate,
    PageTreeResponse,
    ReorderPageRequest,
    TipTapContentSchema,
)
from pilot_space.dependencies.auth import CurrentUserId, SessionDep, SyncedUserId
from pilot_space.infrastructure.database.models.note import Note
from pilot_space.infrastructure.database.models.workspace import Workspace
from pilot_space.infrastructure.database.rls import set_rls_context
from pilot_space.infrastructure.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()

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
    workspace_repo: WorkspaceRepositoryDep,
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
        workspace_id=note.workspace_id,
        project_id=note.project_id,
        title=note.title,
        is_pinned=note.is_pinned,
        word_count=note.word_count,
        last_edited_by_id=note.owner_id,
        icon_emoji=note.icon_emoji,
    )


def _note_to_detail_response(note: Note) -> NoteDetailResponse:
    """Convert Note model to NoteDetailResponse schema."""
    content = None
    if note.content:
        content = TipTapContentSchema(
            type="doc",
            content=note.content.get("content", []),
        )

    linked_issues = [
        IssueBriefResponse.model_validate(link.issue)
        for link in (note.issue_links or [])
        if link.issue and not link.is_deleted
    ]
    return NoteDetailResponse(
        id=note.id,
        created_at=note.created_at,
        updated_at=note.updated_at,
        workspace_id=note.workspace_id,
        project_id=note.project_id,
        title=note.title,
        is_pinned=note.is_pinned,
        word_count=note.word_count,
        last_edited_by_id=note.owner_id,
        icon_emoji=note.icon_emoji,
        content=content,
        annotation_count=len(note.annotations) if note.annotations else 0,
        discussion_count=len(note.discussions) if note.discussions else 0,
        linked_issues=linked_issues,
    )


def _note_to_tree_response(note: Note) -> PageTreeResponse:
    """Convert Note model to PageTreeResponse schema (includes tree fields)."""
    return PageTreeResponse(
        id=note.id,
        created_at=note.created_at,
        updated_at=note.updated_at,
        workspace_id=note.workspace_id,
        project_id=note.project_id,
        title=note.title,
        is_pinned=note.is_pinned,
        word_count=note.word_count,
        last_edited_by_id=note.owner_id,
        icon_emoji=note.icon_emoji,
        parent_id=note.parent_id,
        depth=note.depth,
        position=note.position,
    )


@router.get(
    "/{workspace_id}/notes",
    response_model=PaginatedResponse[NoteResponse],
    tags=["workspace-notes"],
    summary="List notes in workspace",
)
async def list_workspace_notes(
    _: SessionDep,
    workspace_id: WorkspaceIdOrSlug,
    current_user_id: CurrentUserId,
    list_service: ListNotesServiceDep,
    workspace_repo: WorkspaceRepositoryDep,
    project_ids: list[UUID] = Query(default=[], description="Filter by one or more projects"),
    is_pinned: Annotated[bool | None, Query(description="Filter by pin status")] = None,
    search: Annotated[str | None, Query(description="Search query")] = None,
    cursor: Annotated[str | None, Query(description="Pagination cursor")] = None,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PaginatedResponse[NoteResponse]:
    """List all notes in a workspace."""
    from pilot_space.application.services.note import ListNotesPayload

    workspace = await _resolve_workspace(workspace_id, workspace_repo)

    # Get notes via service
    offset = int(cursor) if cursor and cursor.isdigit() else 0

    result = await list_service.execute(
        ListNotesPayload(
            workspace_id=workspace.id,
            project_ids=project_ids,
            is_pinned=is_pinned,
            search=search,
            limit=page_size,
            offset=offset,
        )
    )

    items = [_note_to_response(note) for note in result.notes]
    next_cursor = str(offset + page_size) if result.has_next else None

    return PaginatedResponse(
        items=items,
        total=result.total,
        next_cursor=next_cursor,
        prev_cursor=str(max(0, offset - page_size)) if offset > 0 else None,
        has_next=result.has_next,
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
    _: SessionDep,
    workspace_id: WorkspaceIdOrSlug,
    note_id: NoteIdPath,
    current_user_id: CurrentUserId,
    get_service: GetNoteServiceDep,
    workspace_repo: WorkspaceRepositoryDep,
) -> NoteDetailResponse:
    """Get a specific note by ID."""
    from pilot_space.application.services.note import GetNoteOptions

    workspace = await _resolve_workspace(workspace_id, workspace_repo)

    # Get note with all relations via service
    note = await get_service.get_by_id(
        note_id,
        options=GetNoteOptions(include_all_relations=True),
    )

    if not note or note.workspace_id != workspace.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Note not found",
        )

    return _note_to_detail_response(note)


@router.post(
    "/{workspace_id}/notes",
    response_model=NoteDetailResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["workspace-notes"],
    summary="Create a new note",
)
async def create_workspace_note(
    workspace_id: WorkspaceIdOrSlug,
    note_data: NoteCreate,
    current_user_id: SyncedUserId,
    session: SessionDep,
    create_service: CreateNoteServiceDep,
    workspace_repo: WorkspaceRepositoryDep,
    response: Response = Response(),
) -> NoteDetailResponse:
    """Create a new note in the workspace.

    Args:
        workspace_id: The workspace ID (UUID) or slug.
        note_data: Note creation data.
        current_user_id: Current user ID.
        session: Database session.
        create_service: Create note service.
        workspace_repo: Workspace repository.
        response: FastAPI response for header injection.

    Returns:
        Created note.
    """
    from pilot_space.application.services.note.create_note_service import CreateNotePayload

    workspace = await _resolve_workspace(workspace_id, workspace_repo)

    # Prepare content
    content_dict: dict[str, Any] | None = None
    if note_data.content:
        content_dict = {"type": note_data.content.type, "content": note_data.content.content}

    delta_bytes = len(json.dumps(content_dict or {}).encode("utf-8"))
    _quota_ok, _warning_pct = await _check_storage_quota(session, workspace.id, delta_bytes)
    if not _quota_ok:
        raise HTTPException(
            status_code=status.HTTP_507_INSUFFICIENT_STORAGE,
            detail="Storage quota exceeded",
        )

    # Execute service
    payload = CreateNotePayload(
        workspace_id=workspace.id,
        owner_id=current_user_id,
        title=note_data.title,
        content=content_dict,
        project_id=note_data.project_id,
        is_pinned=note_data.is_pinned,
    )
    result = await create_service.execute(payload)

    try:
        await _update_storage_usage(session, workspace.id, delta_bytes)
    except Exception:
        logger.warning("storage_usage_update_failed", workspace_id=str(workspace.id))
    if _warning_pct is not None:
        response.headers["X-Storage-Warning"] = str(round(_warning_pct, 4))

    logger.info(
        "Note created",
        extra={"note_id": str(result.note.id), "workspace_id": str(workspace.id)},
    )

    return _note_to_detail_response(result.note)


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
    session: SessionDep,
    update_service: UpdateNoteServiceDep,
    workspace_repo: WorkspaceRepositoryDep,
    response: Response = Response(),
) -> NoteResponse:
    """Update an existing note.

    Args:
        workspace_id: The workspace ID (UUID) or slug.
        note_id: The note ID.
        note_data: Note update data.
        current_user_id: Current user ID.
        session: Database session.
        update_service: Update note service.
        workspace_repo: Workspace repository.
        response: FastAPI response for header injection.

    Returns:
        Updated note.
    """
    from pilot_space.application.services.note.update_note_service import UNSET, UpdateNotePayload

    workspace = await _resolve_workspace(workspace_id, workspace_repo)

    # Prepare update fields
    update_data = note_data.model_dump(exclude_unset=True)
    content_dict: dict[str, Any] | None = None
    if update_data.get("content"):
        content = update_data["content"]
        # Content is already a dict after model_dump
        content_dict = {
            "type": content.get("type", "doc"),
            "content": content.get("content", []),
        }

    delta_bytes = len(json.dumps(content_dict or {}).encode("utf-8"))
    _quota_ok, _warning_pct = await _check_storage_quota(session, workspace.id, delta_bytes)
    if not _quota_ok:
        raise HTTPException(
            status_code=status.HTTP_507_INSUFFICIENT_STORAGE,
            detail="Storage quota exceeded",
        )

    # Execute service — pass UNSET for icon_emoji when omitted to distinguish from explicit null
    payload = UpdateNotePayload(
        note_id=note_id,
        title=update_data.get("title"),
        content=content_dict,
        summary=update_data.get("summary"),
        is_pinned=update_data.get("is_pinned"),
        project_id=update_data.get("project_id"),
        icon_emoji=update_data.get("icon_emoji", UNSET),
    )
    result = await update_service.execute(payload)

    try:
        await _update_storage_usage(session, workspace.id, delta_bytes)
    except Exception:
        logger.warning("storage_usage_update_failed", workspace_id=str(workspace.id))
    if _warning_pct is not None:
        response.headers["X-Storage-Warning"] = str(round(_warning_pct, 4))

    logger.info(
        "Note updated",
        extra={"note_id": str(note_id), "workspace_id": str(workspace.id)},
    )

    return _note_to_response(result.note)


@router.delete(
    "/{workspace_id}/notes/{note_id}",
    response_model=DeleteResponse,
    tags=["workspace-notes"],
    summary="Delete a note",
)
async def delete_workspace_note(
    _: SessionDep,
    workspace_id: WorkspaceIdOrSlug,
    note_id: NoteIdPath,
    current_user_id: CurrentUserId,
    delete_service: DeleteNoteServiceDep,
    workspace_repo: WorkspaceRepositoryDep,
) -> DeleteResponse:
    """Soft delete a note with activity tracking."""
    from pilot_space.application.services.note import DeleteNotePayload

    workspace = await _resolve_workspace(workspace_id, workspace_repo)

    try:
        # Execute service
        result = await delete_service.execute(
            DeleteNotePayload(
                note_id=note_id,
                actor_id=current_user_id,
            )
        )

        logger.info(
            "Note deleted",
            extra={"note_id": str(note_id), "workspace_id": str(workspace.id)},
        )

        return DeleteResponse(id=result.note_id, message="Note deleted successfully")

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


@router.post(
    "/{workspace_id}/notes/{note_id}/move",
    response_model=NoteResponse,
    tags=["workspace-notes"],
    summary="Move a note to a different project or root workspace",
)
async def move_workspace_note(
    workspace_id: WorkspaceIdOrSlug,
    note_id: NoteIdPath,
    move_data: NoteMove,
    current_user_id: CurrentUserId,
    session: SessionDep,
    update_service: UpdateNoteServiceDep,
    workspace_repo: WorkspaceRepositoryDep,
    note_repo: NoteRepositoryDep,
    project_repo: ProjectRepositoryDep,
) -> NoteResponse:
    """Move a note to a different project or root workspace.

    Pass project_id=null to remove project association (move to root workspace).

    Args:
        workspace_id: The workspace ID (UUID) or slug.
        note_id: The note ID.
        move_data: Move data with new project_id (nullable).
        current_user_id: Current user ID.
        session: Database session.
        update_service: Update note service.
        workspace_repo: Workspace repository.
        note_repo: Note repository (used to validate note workspace).
        project_repo: Project repository (used to validate project workspace).

    Returns:
        Updated note with new project association.
    """
    from pilot_space.application.services.note.update_note_service import UpdateNotePayload

    workspace = await _resolve_workspace(workspace_id, workspace_repo)
    await set_rls_context(session, current_user_id, workspace.id)

    note = await note_repo.get_by_id(note_id)
    if note is None or note.workspace_id != workspace.id:
        return create_problem_response(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Note not found in this workspace",
            instance=f"/workspaces/{workspace_id}/notes/{note_id}",
        )

    if move_data.project_id is not None:
        project = await project_repo.get_by_id(move_data.project_id)
        if project is None or project.workspace_id != workspace.id:
            return create_problem_response(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found in this workspace",
                instance=f"/workspaces/{workspace_id}/projects/{move_data.project_id}",
            )

    payload = UpdateNotePayload(
        note_id=note_id,
        actor_id=current_user_id,
        clear_project_id=move_data.project_id is None,
        project_id=move_data.project_id,
    )

    try:
        result = await update_service.execute(payload)
    except ValueError as e:
        return create_problem_response(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    logger.info(
        "Note moved",
        extra={
            "note_id": str(note_id),
            "workspace_id": str(workspace.id),
            "project_id": str(move_data.project_id) if move_data.project_id else None,
        },
    )

    return _note_to_response(result.note)

@router.post(
    "/{workspace_id}/notes/{note_id}/reorder",
    response_model=PageTreeResponse,
    tags=["workspace-notes"],
    summary="Reorder a page among its siblings",
)
async def reorder_page(
    workspace_id: WorkspaceIdOrSlug,
    note_id: NoteIdPath,
    body: ReorderPageRequest,
    current_user_id: CurrentUserId,
    session: SessionDep,  # CRITICAL: populates DI ContextVar
    reorder_service: ReorderPageServiceDep,
    workspace_repo: WorkspaceRepositoryDep,
) -> PageTreeResponse:
    """Reorder a page among its siblings using gap-based position arithmetic.

    Args:
        workspace_id: The workspace ID (UUID) or slug.
        note_id: The note ID to reorder.
        body: Reorder request with sibling anchor ID (None prepends).
        current_user_id: Current user ID.
        session: Database session (required for DI ContextVar).
        reorder_service: Reorder page service.
        workspace_repo: Workspace repository.

    Returns:
        Updated page with tree fields (parent_id, depth, position).

    Raises:
        HTTPException 422: If note not found or personal page attempted.
    """
    from pilot_space.application.services.note.reorder_page_service import ReorderPagePayload

    workspace = await _resolve_workspace(workspace_id, workspace_repo)
    await set_rls_context(session, current_user_id, workspace.id)

    try:
        result = await reorder_service.execute(
            ReorderPagePayload(
                note_id=note_id,
                insert_after_id=body.insert_after_id,
                workspace_id=workspace.id,
                actor_id=current_user_id,
            )
        )
    except ValueError as e:
        msg = str(e)
        status_code = (
            status.HTTP_404_NOT_FOUND
            if "not found" in msg.lower()
            else status.HTTP_422_UNPROCESSABLE_ENTITY
        )
        raise HTTPException(status_code=status_code, detail=msg) from e

    logger.info(
        "Page reordered",
        extra={"note_id": str(note_id), "position": str(result.note.position)},
    )

    return _note_to_tree_response(result.note)

@router.post(
    "/{workspace_id}/notes/{note_id}/pin",
    response_model=NoteResponse,
    tags=["workspace-notes"],
    summary="Pin a note",
)
async def pin_workspace_note(
    _: SessionDep,
    workspace_id: WorkspaceIdOrSlug,
    note_id: NoteIdPath,
    current_user_id: CurrentUserId,
    pin_service: PinNoteServiceDep,
    workspace_repo: WorkspaceRepositoryDep,
) -> NoteResponse:
    """Pin a note for quick access."""
    from pilot_space.application.services.note import PinNotePayload

    workspace = await _resolve_workspace(workspace_id, workspace_repo)

    try:
        # Execute service
        result = await pin_service.execute(
            PinNotePayload(
                note_id=note_id,
                is_pinned=True,
            )
        )

        # Verify workspace ownership
        if result.note.workspace_id != workspace.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Note not found",
            )

        return _note_to_response(result.note)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


@router.delete(
    "/{workspace_id}/notes/{note_id}/pin",
    response_model=NoteResponse,
    tags=["workspace-notes"],
    summary="Unpin a note",
)
async def unpin_workspace_note(
    _: SessionDep,
    workspace_id: WorkspaceIdOrSlug,
    note_id: NoteIdPath,
    current_user_id: CurrentUserId,
    pin_service: PinNoteServiceDep,
    workspace_repo: WorkspaceRepositoryDep,
) -> NoteResponse:
    """Unpin a note."""
    from pilot_space.application.services.note import PinNotePayload

    workspace = await _resolve_workspace(workspace_id, workspace_repo)

    try:
        # Execute service
        result = await pin_service.execute(
            PinNotePayload(
                note_id=note_id,
                is_pinned=False,
            )
        )

        # Verify workspace ownership
        if result.note.workspace_id != workspace.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Note not found",
            )

        return _note_to_response(result.note)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


__all__ = ["router"]
