"""API v1 router aggregator.

Aggregates all v1 API routers into a single router for mounting on the main app.
"""

from fastapi import APIRouter, Depends

from pilot_space.api.v1.dependencies import require_project_membership
from pilot_space.api.v1.routers.ai_configuration import (
    router as ai_configuration_router,
)
from pilot_space.api.v1.routers.artifact_annotations import (
    router as artifact_annotations_router,
)
from pilot_space.api.v1.routers.auth import router as auth_router
from pilot_space.api.v1.routers.git_proxy import router as git_proxy_router
from pilot_space.api.v1.routers.memory import router as memory_router
from pilot_space.api.v1.routers.my_projects import router as my_projects_router
from pilot_space.api.v1.routers.project_artifacts import (
    router as project_artifacts_router,
)
from pilot_space.api.v1.routers.project_members import router as project_members_router
from pilot_space.api.v1.routers.projects import router as projects_router
from pilot_space.api.v1.routers.proposals import router as proposals_router
from pilot_space.api.v1.routers.workspace_artifacts import (
    router as workspace_artifacts_router,
)
from pilot_space.api.v1.routers.workspaces import router as workspaces_router

api_router = APIRouter(prefix="/api/v1")


# Health check endpoint at API level
@api_router.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    """API health check endpoint."""
    return {"status": "healthy", "api_version": "v1"}


# Register routers
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(workspaces_router, prefix="/workspaces", tags=["workspaces"])
api_router.include_router(projects_router, prefix="/projects", tags=["projects"])
api_router.include_router(
    project_artifacts_router,
    prefix="/workspaces/{workspace_id}/projects/{project_id}/artifacts",
    tags=["artifacts"],
    dependencies=[Depends(require_project_membership)],
)
api_router.include_router(
    ai_configuration_router,
    prefix="/workspaces/{workspace_id}/ai-configurations",
    tags=["ai-configuration"],
)

# Phase 87.1 Plan 04 — workspace-scoped signed URL for AI-generated artifacts
# (project_id IS NULL). Sibling of /projects/{pid}/artifacts/{aid}/url for the
# project-less case. Workspace isolation enforced by require_workspace_member +
# RLS + artifact.workspace_id check.
api_router.include_router(
    workspace_artifacts_router,
    prefix="/workspaces/{workspace_id}/artifacts",
    tags=["artifacts"],
)

api_router.include_router(memory_router, prefix="", tags=["memory"])
api_router.include_router(
    git_proxy_router,
    prefix="/workspaces/{workspace_id}/git",
    tags=["git"],
)
api_router.include_router(
    artifact_annotations_router,
    prefix="/workspaces/{workspace_id}/projects/{project_id}/artifacts/{artifact_id}/annotations",
    tags=["artifact-annotations"],
    dependencies=[Depends(require_project_membership)],
)
api_router.include_router(
    project_members_router,
    prefix="/workspaces",
    tags=["project-members"],
)
api_router.include_router(
    my_projects_router,
    prefix="/workspaces",
    tags=["my-projects"],
)

# Phase 89 Plan 02 — Edit Proposal pipeline REST surface.
# Flat prefix (``/proposals``) — workspace scope comes from ``X-Workspace-Id``
# header via ``HeaderWorkspaceMemberId`` dependency, not path param.
api_router.include_router(proposals_router)

# Debug router and mock generators removed (were development-only features)


__all__ = ["api_router"]
