"""Artifact annotations router — per-slide annotations on PPTX artifacts.

Endpoints:
  POST   /workspaces/{workspace_id}/projects/{project_id}/artifacts/{artifact_id}/annotations
  GET    /workspaces/{workspace_id}/projects/{project_id}/artifacts/{artifact_id}/annotations
  PUT    /workspaces/{workspace_id}/projects/{project_id}/artifacts/{artifact_id}/annotations/{annotation_id}
  DELETE /workspaces/{workspace_id}/projects/{project_id}/artifacts/{artifact_id}/annotations/{annotation_id}

Enforces at the router layer:
  - Author-only updates and deletes (403 if not annotation creator)
  - RLS enforces workspace isolation at the DB layer

Feature: v1.2 — PPTX Annotations
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select

from pilot_space.api.v1.schemas.artifact_annotations import (
    AnnotationListResponse,
    ArtifactAnnotationResponse,
    CreateAnnotationRequest,
    UpdateAnnotationRequest,
)
from pilot_space.container._base import InfraContainer
from pilot_space.dependencies.auth import CurrentUser, SessionDep, require_workspace_member
from pilot_space.infrastructure.database.models.artifact import Artifact
from pilot_space.infrastructure.database.models.artifact_annotation import ArtifactAnnotation
from pilot_space.infrastructure.database.repositories.artifact_annotation_repository import (
    ArtifactAnnotationRepository,
)
from pilot_space.infrastructure.database.rls import set_rls_context

router = APIRouter()


async def _validate_artifact_project(
    session: SessionDep, artifact_id: UUID, project_id: UUID
) -> None:
    """Verify the artifact belongs to the given project. Raises 404 if not."""
    result = await session.execute(
        select(Artifact.id).where(Artifact.id == artifact_id, Artifact.project_id == project_id)
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Artifact not found in this project",
        )


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ArtifactAnnotationResponse)
@inject
async def create_annotation(
    workspace_id: UUID,
    project_id: UUID,
    artifact_id: UUID,
    body: CreateAnnotationRequest,
    session: SessionDep,
    current_user: CurrentUser,
    _member: Annotated[UUID, Depends(require_workspace_member)],
    repo: ArtifactAnnotationRepository = Depends(
        Provide[InfraContainer.artifact_annotation_repository]
    ),
) -> ArtifactAnnotationResponse:
    """Create a new annotation on a specific slide.

    Args:
        workspace_id: Workspace owning the artifact.
        project_id: Project owning the artifact (used for URL scoping).
        artifact_id: Artifact to annotate.
        body: Slide index and annotation content.
        session: Async DB session (required by SessionDep context var).
        current_user: Authenticated user from JWT.
        _member: Workspace membership guard.
        repo: Injected annotation repository.

    Returns:
        ArtifactAnnotationResponse with the created annotation.
    """
    await set_rls_context(session, current_user.user_id, workspace_id)
    await _validate_artifact_project(session, artifact_id, project_id)

    annotation = ArtifactAnnotation(
        artifact_id=artifact_id,
        slide_index=body.slide_index,
        content=body.content,
        user_id=current_user.user_id,
        workspace_id=workspace_id,
    )
    created = await repo.create(annotation)
    return ArtifactAnnotationResponse.model_validate(created)


@router.get("", response_model=AnnotationListResponse)
@inject
async def list_annotations(
    workspace_id: UUID,
    project_id: UUID,
    artifact_id: UUID,
    slide_index: Annotated[
        int, Query(ge=0, description="Zero-based slide index to fetch annotations for")
    ],
    session: SessionDep,
    current_user: CurrentUser,
    _member: Annotated[UUID, Depends(require_workspace_member)],
    repo: ArtifactAnnotationRepository = Depends(
        Provide[InfraContainer.artifact_annotation_repository]
    ),
) -> AnnotationListResponse:
    """List annotations for a specific slide on an artifact.

    Args:
        workspace_id: Workspace owning the artifact.
        project_id: Project owning the artifact (used for URL scoping).
        artifact_id: Artifact to list annotations for.
        slide_index: Zero-based slide index to filter annotations.
        session: Async DB session.
        current_user: Authenticated user from JWT.
        _member: Workspace membership guard.
        repo: Injected annotation repository.

    Returns:
        AnnotationListResponse with annotations and total count.
    """
    await set_rls_context(session, current_user.user_id, workspace_id)
    await _validate_artifact_project(session, artifact_id, project_id)

    orm_annotations = await repo.list_by_slide(artifact_id, slide_index)
    annotations = [ArtifactAnnotationResponse.model_validate(a) for a in orm_annotations]
    return AnnotationListResponse(annotations=annotations, total=len(annotations))


@router.put("/{annotation_id}", response_model=ArtifactAnnotationResponse)
@inject
async def update_annotation(
    workspace_id: UUID,
    project_id: UUID,
    artifact_id: UUID,
    annotation_id: UUID,
    body: UpdateAnnotationRequest,
    session: SessionDep,
    current_user: CurrentUser,
    _member: Annotated[UUID, Depends(require_workspace_member)],
    repo: ArtifactAnnotationRepository = Depends(
        Provide[InfraContainer.artifact_annotation_repository]
    ),
) -> ArtifactAnnotationResponse:
    """Update an annotation's content. Only the annotation author may update.

    Args:
        workspace_id: Workspace owning the artifact.
        project_id: Project owning the artifact (used for URL scoping).
        artifact_id: Artifact the annotation belongs to (used for URL scoping).
        annotation_id: Annotation to update.
        body: New content.
        session: Async DB session.
        current_user: Authenticated user from JWT.
        _member: Workspace membership guard.
        repo: Injected annotation repository.

    Returns:
        ArtifactAnnotationResponse with updated content.

    Raises:
        HTTPException 404: Annotation not found or not in this workspace/artifact.
        HTTPException 403: Current user is not the annotation author.
    """
    await set_rls_context(session, current_user.user_id, workspace_id)
    await _validate_artifact_project(session, artifact_id, project_id)

    annotation = await repo.get_by_id(annotation_id)
    if annotation is None or annotation.artifact_id != artifact_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Annotation not found",
        )
    if annotation.user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: you do not own this annotation.",
        )

    await repo.update_content(annotation_id, body.content)
    # Refresh for updated_at server value
    updated = await repo.get_by_id(annotation_id)
    return ArtifactAnnotationResponse.model_validate(updated)


@router.delete("/{annotation_id}", status_code=status.HTTP_204_NO_CONTENT)
@inject
async def delete_annotation(
    workspace_id: UUID,
    project_id: UUID,
    artifact_id: UUID,
    annotation_id: UUID,
    session: SessionDep,
    current_user: CurrentUser,
    _member: Annotated[UUID, Depends(require_workspace_member)],
    repo: ArtifactAnnotationRepository = Depends(
        Provide[InfraContainer.artifact_annotation_repository]
    ),
) -> None:
    """Delete an annotation. Only the annotation author may delete.

    Args:
        workspace_id: Workspace owning the artifact.
        project_id: Project owning the artifact (used for URL scoping).
        artifact_id: Artifact the annotation belongs to (used for URL scoping).
        annotation_id: Annotation to delete.
        session: Async DB session.
        current_user: Authenticated user from JWT.
        _member: Workspace membership guard.
        repo: Injected annotation repository.

    Returns:
        None (204 no content).

    Raises:
        HTTPException 404: Annotation not found or not in this workspace/artifact.
        HTTPException 403: Current user is not the annotation author.
    """
    await set_rls_context(session, current_user.user_id, workspace_id)
    await _validate_artifact_project(session, artifact_id, project_id)

    annotation = await repo.get_by_id(annotation_id)
    if annotation is None or annotation.artifact_id != artifact_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Annotation not found",
        )
    if annotation.user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: you do not own this annotation.",
        )

    await repo.delete(annotation_id)


__all__ = ["router"]
