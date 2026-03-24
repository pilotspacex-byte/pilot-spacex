"""Workspace-scoped Note Annotations API router.

Extracted from workspace_notes.py to keep per-file line count under 700.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Path

from pilot_space.api.v1.dependencies import (
    GetNoteServiceDep,
    ListAnnotationsServiceDep,
    UpdateAnnotationServiceDep,
    WorkspaceRepositoryDep,
)
from pilot_space.api.v1.schemas.annotation import (
    AnnotationResponse,
    AnnotationStatus,
    AnnotationStatusUpdate,
    AnnotationType,
)
from pilot_space.dependencies.auth import CurrentUserId, SessionDep
from pilot_space.domain.exceptions import NotFoundError
from pilot_space.infrastructure.database.models.note_annotation import NoteAnnotation
from pilot_space.infrastructure.logging import get_logger

logger = get_logger(__name__)

annotations_router = APIRouter()

# Shared path aliases (re-declared here to keep this module self-contained)
WorkspaceIdOrSlug = Annotated[str, Path(description="Workspace ID (UUID) or slug")]
NoteIdPath = Annotated[UUID, Path(description="Note ID")]


def _is_valid_uuid(value: str) -> bool:
    """Check if a string is a valid UUID."""
    try:
        UUID(value)
        return True
    except ValueError:
        return False


async def _resolve_workspace_for_annotations(
    workspace_id_or_slug: str,
    workspace_repo: WorkspaceRepositoryDep,
) -> UUID:
    """Resolve workspace ID for annotations sub-router.

    Returns the UUID of the workspace, raising 404 if not found.
    """
    if _is_valid_uuid(workspace_id_or_slug):
        workspace = await workspace_repo.get_by_id(UUID(workspace_id_or_slug))
    else:
        workspace = await workspace_repo.get_by_slug(workspace_id_or_slug)

    if not workspace:
        raise NotFoundError("Workspace not found")
    return workspace.id


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


@annotations_router.get(
    "/{workspace_id}/notes/{note_id}/annotations",
    response_model=list[AnnotationResponse],
    tags=["workspace-notes"],
    summary="Get note annotations",
)
async def get_note_annotations(
    _: SessionDep,
    workspace_id: WorkspaceIdOrSlug,
    note_id: NoteIdPath,
    current_user_id: CurrentUserId,
    list_annotations_service: ListAnnotationsServiceDep,
    get_note_service: GetNoteServiceDep,
    workspace_repo: WorkspaceRepositoryDep,
) -> list[AnnotationResponse]:
    """Get all annotations for a note."""
    from pilot_space.application.services.note import ListAnnotationsPayload

    workspace_uuid = await _resolve_workspace_for_annotations(workspace_id, workspace_repo)

    # Verify note exists and belongs to workspace
    note = await get_note_service.get_by_id(note_id)
    if not note or note.workspace_id != workspace_uuid:
        raise NotFoundError("Note not found")

    # Get annotations via service
    result = await list_annotations_service.execute(ListAnnotationsPayload(note_id=note_id))

    return [_annotation_to_response(a) for a in result.annotations]


@annotations_router.patch(
    "/{workspace_id}/notes/{note_id}/annotations/{annotation_id}",
    response_model=AnnotationResponse,
    tags=["workspace-notes"],
    summary="Update annotation status",
)
async def update_annotation_status(
    _: SessionDep,
    workspace_id: WorkspaceIdOrSlug,
    note_id: NoteIdPath,
    annotation_id: Annotated[UUID, Path(description="Annotation ID")],
    status_update: AnnotationStatusUpdate,
    current_user_id: CurrentUserId,
    update_annotation_service: UpdateAnnotationServiceDep,
    get_note_service: GetNoteServiceDep,
    workspace_repo: WorkspaceRepositoryDep,
) -> AnnotationResponse:
    """Update annotation status (accept/reject/dismiss)."""
    from pilot_space.application.services.note import UpdateAnnotationPayload
    from pilot_space.infrastructure.database.models.note_annotation import (
        AnnotationStatus as DBAnnotationStatus,
    )

    workspace_uuid = await _resolve_workspace_for_annotations(workspace_id, workspace_repo)

    # Verify note exists and belongs to workspace
    note = await get_note_service.get_by_id(note_id)
    if not note or note.workspace_id != workspace_uuid:
        raise NotFoundError("Note not found")

    # Execute service — ownership is validated inside before any DB write
    result = await update_annotation_service.execute(
        UpdateAnnotationPayload(
            annotation_id=annotation_id,
            note_id=note_id,
            status=DBAnnotationStatus(status_update.status.value),
        )
    )

    logger.info(
        "Annotation status updated",
        extra={
            "annotation_id": str(annotation_id),
            "note_id": str(note_id),
            "new_status": status_update.status.value,
        },
    )

    return _annotation_to_response(result.annotation)


__all__ = ["annotations_router"]
