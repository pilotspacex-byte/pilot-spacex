"""Workspace-scoped artifact router — signed URL for project-less (AI-generated) artifacts.

Phase 87.1 Plan 04 (Rule 3 deviation): Wave 1 made `Artifact.project_id` nullable so
AI-generated files have no project context, but the only signed-URL endpoint
(`project_artifacts.get_artifact_url`) requires both `workspace_id` AND `project_id`
in the path AND filters with `artifact.project_id != project_id` — which 404s for
NULL-project rows.

This adds a workspace-scoped variant that mirrors the project-scoped logic but
omits the `project_id` filter. Workspace isolation is preserved via the existing
`workspace_id` filter and `require_workspace_member` membership check.

Endpoints:
  GET /workspaces/{workspace_id}/artifacts/{artifact_id}/url
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends

from pilot_space.api.v1.schemas.artifacts import ArtifactUrlResponse
from pilot_space.container._base import InfraContainer
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


@router.get("/{artifact_id}/url", response_model=ArtifactUrlResponse)
@inject
async def get_workspace_artifact_url(
    workspace_id: UUID,
    artifact_id: UUID,
    session: SessionDep,
    current_user: CurrentUser,
    _member: Annotated[UUID, Depends(require_workspace_member)],
    artifact_repo: ArtifactRepository = Depends(Provide[InfraContainer.artifact_repository]),
    storage_client: SupabaseStorageClient = Depends(Provide[InfraContainer.storage_client]),
) -> ArtifactUrlResponse:
    """Get a 1-hour signed download URL for a workspace-scoped artifact.

    Unlike the project-scoped sibling, this endpoint does NOT require a project_id
    in the path and intentionally does NOT filter by project_id — supporting both
    AI-generated artifacts (project_id IS NULL) and project artifacts uniformly.

    Workspace isolation is enforced via:
      1. `require_workspace_member` membership check (membership-required)
      2. `artifact.workspace_id != workspace_id` rejection (404)
      3. RLS context set before the lookup

    Args:
        workspace_id: Workspace scope from URL path.
        artifact_id: Artifact to generate signed URL for.

    Returns:
        ArtifactUrlResponse with signed url and expires_in=3600.

    Raises:
        NotFoundError: Artifact not found or belongs to a different workspace.
    """
    await set_rls_context(session, current_user.user_id, workspace_id)

    artifact = await artifact_repo.get_by_id(artifact_id)
    if artifact is None or artifact.workspace_id != workspace_id:
        raise NotFoundError("Artifact not found")

    signed_url = await storage_client.get_signed_url(
        bucket="note-artifacts",
        key=artifact.storage_key,
        expires_in=3600,
    )
    return ArtifactUrlResponse(url=signed_url, expires_in=3600)
