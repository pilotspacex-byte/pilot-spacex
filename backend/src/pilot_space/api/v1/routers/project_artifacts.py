"""Project artifacts router — file upload, list, signed URL, delete.

Endpoints:
  POST   /workspaces/{workspace_id}/projects/{project_id}/artifacts
  GET    /workspaces/{workspace_id}/projects/{project_id}/artifacts
  GET    /workspaces/{workspace_id}/projects/{project_id}/artifacts/{artifact_id}/url
  DELETE /workspaces/{workspace_id}/projects/{project_id}/artifacts/{artifact_id}

Enforces at the router layer:
  - 10 MB size limit (pre-read via file.size; post-read via len(file_data))
  - RFC 7807 error body for 413 and 422

Feature: v1.1 — Artifacts (ARTF-04, ARTF-05, ARTF-06)
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, HTTPException, UploadFile, status

from pilot_space.api.v1.schemas.artifacts import (
    ArtifactListResponse,
    ArtifactResponse,
    ArtifactUrlResponse,
)
from pilot_space.application.services.artifact.artifact_upload_service import (
    ArtifactUploadService,
)
from pilot_space.container._base import InfraContainer
from pilot_space.container.container import Container
from pilot_space.dependencies.auth import CurrentUser, SessionDep, require_workspace_member
from pilot_space.domain.exceptions import NotFoundError
from pilot_space.infrastructure.database.repositories.artifact_repository import (
    ArtifactRepository,
)
from pilot_space.infrastructure.database.rls import set_rls_context
from pilot_space.infrastructure.logging import get_logger
from pilot_space.infrastructure.storage.client import SupabaseStorageClient

logger = get_logger(__name__)

router = APIRouter()

_MAX_BYTES = 10 * 1024 * 1024  # 10 MB flat limit


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ArtifactResponse)
@inject
async def upload_artifact(
    workspace_id: UUID,
    project_id: UUID,
    file: UploadFile,
    session: SessionDep,
    current_user: CurrentUser,
    _member: Annotated[UUID, Depends(require_workspace_member)],
    artifact_service: ArtifactUploadService = Depends(Provide[Container.artifact_upload_service]),
) -> ArtifactResponse:
    """Upload a file as a project artifact.

    Enforces 10 MB limit at the router layer (pre- and post-read) and delegates
    extension / MIME validation to ArtifactUploadService.

    Args:
        workspace_id: Workspace owning the project.
        project_id: Project to associate the artifact with.
        file: Multipart upload file.
        session: Async DB session (required by SessionDep context var).
        current_user: Authenticated user from JWT.
        artifact_service: Injected upload service.

    Returns:
        ArtifactResponse with status=ready on success.

    Raises:
        HTTPException 413: File exceeds 10 MB.
        HTTPException 422: Extension not in allowlist, empty file, or MIME mismatch.
    """
    # Layer 1 size check: use Content-Length hint before buffering (fast path)
    if file.size is not None and file.size > _MAX_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds 10 MB limit ({file.size} bytes declared).",
        )

    file_data = await file.read()

    # Layer 2 size check: after read (handles chunked transfer encoding)
    if len(file_data) > _MAX_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds 10 MB limit ({len(file_data)} bytes received).",
        )

    await set_rls_context(session, current_user.user_id, workspace_id)

    return await artifact_service.upload(
        file_data=file_data,
        filename=file.filename or "upload",
        content_type=file.content_type or "application/octet-stream",
        workspace_id=workspace_id,
        project_id=project_id,
        user_id=current_user.user_id,
    )


@router.get("", response_model=ArtifactListResponse)
@inject
async def list_artifacts(
    workspace_id: UUID,
    project_id: UUID,
    session: SessionDep,
    current_user: CurrentUser,
    _member: Annotated[UUID, Depends(require_workspace_member)],
    artifact_repo: ArtifactRepository = Depends(Provide[InfraContainer.artifact_repository]),
) -> ArtifactListResponse:
    """List ready artifacts for a project, newest first.

    Args:
        workspace_id: Workspace owning the project.
        project_id: Project to list artifacts for.
        session: Async DB session.
        current_user: Authenticated user from JWT.
        artifact_repo: Injected artifact repository.

    Returns:
        ArtifactListResponse with artifacts and total count.
    """
    await set_rls_context(session, current_user.user_id, workspace_id)

    orm_artifacts = await artifact_repo.list_by_project(workspace_id, project_id)
    artifacts = [ArtifactResponse.model_validate(a) for a in orm_artifacts]
    return ArtifactListResponse(artifacts=artifacts, total=len(artifacts))


@router.get("/{artifact_id}/url", response_model=ArtifactUrlResponse)
@inject
async def get_artifact_url(
    workspace_id: UUID,
    project_id: UUID,
    artifact_id: UUID,
    session: SessionDep,
    current_user: CurrentUser,
    _member: Annotated[UUID, Depends(require_workspace_member)],
    artifact_repo: ArtifactRepository = Depends(Provide[InfraContainer.artifact_repository]),
    storage_client: SupabaseStorageClient = Depends(Provide[InfraContainer.storage_client]),
) -> ArtifactUrlResponse:
    """Get a 1-hour signed download URL for an artifact.

    Enforces workspace isolation: artifacts from other workspaces are treated
    as not found (same as DELETE isolation pattern).

    Args:
        workspace_id: Workspace scope from URL path.
        project_id: Project scope from URL path.
        artifact_id: Artifact to generate signed URL for.
        session: Async DB session.
        current_user: Authenticated user from JWT.
        artifact_repo: Injected artifact repository.
        storage_client: Injected Supabase Storage client.

    Returns:
        ArtifactUrlResponse with signed url and expires_in=3600.

    Raises:
        HTTPException 404: Artifact not found or belongs to different workspace.
    """
    await set_rls_context(session, current_user.user_id, workspace_id)

    artifact = await artifact_repo.get_by_id(artifact_id)
    if (
        artifact is None
        or artifact.workspace_id != workspace_id
        or artifact.project_id != project_id
    ):
        raise NotFoundError("Artifact not found")

    signed_url = await storage_client.get_signed_url(
        bucket="note-artifacts",
        key=artifact.storage_key,
        expires_in=3600,
    )
    return ArtifactUrlResponse(url=signed_url, expires_in=3600)


@router.delete("/{artifact_id}", status_code=status.HTTP_204_NO_CONTENT)
@inject
async def delete_artifact(
    workspace_id: UUID,
    project_id: UUID,
    artifact_id: UUID,
    session: SessionDep,
    current_user: CurrentUser,
    _member: Annotated[UUID, Depends(require_workspace_member)],
    artifact_service: ArtifactUploadService = Depends(Provide[Container.artifact_upload_service]),
) -> None:
    """Delete an artifact and its storage object.

    Args:
        workspace_id: Workspace scope for cross-tenant isolation.
        project_id: Project scope from URL path.
        artifact_id: Artifact to delete.
        session: Async DB session.
        current_user: Authenticated user from JWT.
        artifact_service: Injected upload service (handles ownership check).

    Returns:
        None (204 no content).

    Raises:
        HTTPException 403: User does not own the artifact.
        HTTPException 404: Artifact not found or belongs to different workspace.
    """
    await set_rls_context(session, current_user.user_id, workspace_id)

    await artifact_service.delete(
        artifact_id=artifact_id,
        user_id=current_user.user_id,
        workspace_id=workspace_id,
        project_id=project_id,
    )


__all__ = ["router"]
