"""Workspace-scoped artifact annotation CRUD router.

Endpoints (mounted under /api/v1/workspaces/{workspace_id}/projects/{project_id}/artifacts/{artifact_id}/annotations):
  GET    ""                          → list (optionally filtered by slide_index)
  POST   ""                          → create
  PUT    "/{annotation_id}"          → update content
  DELETE "/{annotation_id}"          → hard delete (204)

Gotchas applied:
  - session: SessionDep is declared on every handler (Gotcha #1)
  - Root collection routes use "" not "/" (project memory)
  - RFC 7807 error bodies via HTTPException detail dict (Gotcha #8)
  - @inject + Provide[Container.x] wiring (Gotcha #2) — module registered in container.py
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, HTTPException, Query, status

from pilot_space.api.v1.schemas.artifact_annotation import (
    ArtifactAnnotationCreate,
    ArtifactAnnotationListResponse,
    ArtifactAnnotationResponse,
    ArtifactAnnotationUpdate,
)
from pilot_space.application.services.artifact_annotation import (
    CreateArtifactAnnotationPayload,
    CreateArtifactAnnotationService,
    DeleteArtifactAnnotationService,
    ListArtifactAnnotationsPayload,
    ListArtifactAnnotationsService,
    UpdateArtifactAnnotationPayload,
    UpdateArtifactAnnotationService,
)
from pilot_space.container.container import Container
from pilot_space.dependencies.auth import CurrentUser, SessionDep, require_workspace_member
from pilot_space.infrastructure.database.rls import set_rls_context
from pilot_space.infrastructure.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


def _not_found_exc(detail: str = "Annotation not found") -> HTTPException:
    """Build a RFC 7807 404 HTTPException."""
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={
            "type": "about:blank",
            "title": "Not Found",
            "status": 404,
            "detail": detail,
        },
    )


def _annotation_to_response(annotation: object) -> ArtifactAnnotationResponse:
    """Convert ORM model to response schema.

    Uses model_validate (from_attributes=True) to map SQLAlchemy columns,
    then serializes timestamps to ISO-8601 strings manually because the
    schema uses str fields to avoid camelCase alias issues.
    """
    from pilot_space.domain.artifact_annotation import ArtifactAnnotation

    a: ArtifactAnnotation = annotation  # type: ignore[assignment]
    return ArtifactAnnotationResponse(
        id=a.id,
        artifact_id=a.artifact_id,
        slide_index=a.slide_index,
        content=a.content,
        user_id=a.user_id,
        created_at=a.created_at.isoformat(),
        updated_at=a.updated_at.isoformat(),
    )


@router.get(
    "",
    response_model=ArtifactAnnotationListResponse,
    summary="List artifact annotations",
    tags=["artifact-annotations"],
)
@inject
async def list_annotations(
    workspace_id: UUID,
    project_id: UUID,
    artifact_id: UUID,
    session: SessionDep,
    current_user: CurrentUser,
    _member: Annotated[UUID, Depends(require_workspace_member)],
    slide_index: int | None = Query(default=None, ge=0, description="Filter by slide index"),
    list_service: ListArtifactAnnotationsService = Depends(
        Provide[Container.list_artifact_annotations_service]
    ),
) -> ArtifactAnnotationListResponse:
    """List annotations for an artifact, optionally filtered by slide index.

    Args:
        workspace_id: Workspace UUID from URL path.
        project_id: Project UUID from URL path.
        artifact_id: Artifact UUID from URL path.
        session: DB session (required by ContextVar — Gotcha #1).
        current_user: Authenticated user payload.
        slide_index: Optional slide/page filter.
        list_service: Injected list service.

    Returns:
        ArtifactAnnotationListResponse with annotations and total.
    """
    await set_rls_context(session, current_user.user_id, workspace_id)

    result = await list_service.execute(
        ListArtifactAnnotationsPayload(
            workspace_id=workspace_id,
            artifact_id=artifact_id,
            slide_index=slide_index,
        )
    )
    return ArtifactAnnotationListResponse(
        annotations=[_annotation_to_response(a) for a in result.annotations],
        total=result.total,
    )


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=ArtifactAnnotationResponse,
    summary="Create artifact annotation",
    tags=["artifact-annotations"],
)
@inject
async def create_annotation(
    workspace_id: UUID,
    project_id: UUID,
    artifact_id: UUID,
    body: ArtifactAnnotationCreate,
    session: SessionDep,
    current_user: CurrentUser,
    _member: Annotated[UUID, Depends(require_workspace_member)],
    create_service: CreateArtifactAnnotationService = Depends(
        Provide[Container.create_artifact_annotation_service]
    ),
) -> ArtifactAnnotationResponse:
    """Create a new annotation on a specific slide of an artifact.

    Args:
        workspace_id: Workspace UUID from URL path.
        project_id: Project UUID from URL path.
        artifact_id: Artifact UUID from URL path.
        body: Validated request body (slide_index, content).
        session: DB session (required by ContextVar — Gotcha #1).
        current_user: Authenticated user payload.
        create_service: Injected create service.

    Returns:
        Created ArtifactAnnotationResponse (201).

    Raises:
        HTTPException 404: Artifact not found or belongs to different workspace/project.
    """
    await set_rls_context(session, current_user.user_id, workspace_id)

    try:
        annotation = await create_service.execute(
            CreateArtifactAnnotationPayload(
                workspace_id=workspace_id,
                artifact_id=artifact_id,
                project_id=project_id,
                user_id=current_user.user_id,
                slide_index=body.slide_index,
                content=body.content,
            )
        )
    except ValueError as exc:
        raise _not_found_exc(str(exc)) from exc

    logger.info(
        "artifact_annotation_created",
        extra={
            "annotation_id": str(annotation.id),
            "artifact_id": str(artifact_id),
            "workspace_id": str(workspace_id),
        },
    )
    return _annotation_to_response(annotation)


@router.put(
    "/{annotation_id}",
    response_model=ArtifactAnnotationResponse,
    summary="Update artifact annotation",
    tags=["artifact-annotations"],
)
@inject
async def update_annotation(
    workspace_id: UUID,
    project_id: UUID,
    artifact_id: UUID,
    annotation_id: UUID,
    body: ArtifactAnnotationUpdate,
    session: SessionDep,
    current_user: CurrentUser,
    _member: Annotated[UUID, Depends(require_workspace_member)],
    update_service: UpdateArtifactAnnotationService = Depends(
        Provide[Container.update_artifact_annotation_service]
    ),
) -> ArtifactAnnotationResponse:
    """Update the content of an existing annotation.

    Args:
        workspace_id: Workspace UUID from URL path.
        project_id: Project UUID (unused in update but kept for path symmetry).
        artifact_id: Artifact UUID from URL path.
        annotation_id: Annotation to update.
        body: Validated request body (content).
        session: DB session (required by ContextVar — Gotcha #1).
        current_user: Authenticated user payload.
        update_service: Injected update service.

    Returns:
        Updated ArtifactAnnotationResponse.

    Raises:
        HTTPException 404: Annotation not found.
    """
    await set_rls_context(session, current_user.user_id, workspace_id)

    try:
        annotation = await update_service.execute(
            UpdateArtifactAnnotationPayload(
                workspace_id=workspace_id,
                artifact_id=artifact_id,
                annotation_id=annotation_id,
                content=body.content,
            )
        )
    except ValueError as exc:
        raise _not_found_exc(str(exc)) from exc

    return _annotation_to_response(annotation)


@router.delete(
    "/{annotation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete artifact annotation",
    tags=["artifact-annotations"],
)
@inject
async def delete_annotation(
    workspace_id: UUID,
    project_id: UUID,
    artifact_id: UUID,
    annotation_id: UUID,
    session: SessionDep,
    current_user: CurrentUser,
    _member: Annotated[UUID, Depends(require_workspace_member)],
    delete_service: DeleteArtifactAnnotationService = Depends(
        Provide[Container.delete_artifact_annotation_service]
    ),
) -> None:
    """Hard-delete an annotation (204 no content).

    Args:
        workspace_id: Workspace UUID from URL path.
        project_id: Project UUID (path symmetry only).
        artifact_id: Artifact UUID from URL path.
        annotation_id: Annotation to delete.
        session: DB session (required by ContextVar — Gotcha #1).
        current_user: Authenticated user payload.
        delete_service: Injected delete service.

    Raises:
        HTTPException 404: Annotation not found.
    """
    await set_rls_context(session, current_user.user_id, workspace_id)

    try:
        await delete_service.execute(
            workspace_id=workspace_id,
            artifact_id=artifact_id,
            annotation_id=annotation_id,
        )
    except ValueError as exc:
        raise _not_found_exc(str(exc)) from exc

    logger.info(
        "artifact_annotation_deleted",
        extra={
            "annotation_id": str(annotation_id),
            "artifact_id": str(artifact_id),
            "workspace_id": str(workspace_id),
        },
    )


__all__ = ["router"]
