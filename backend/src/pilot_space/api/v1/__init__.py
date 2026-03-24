"""API v1 router aggregator.

Aggregates all v1 API routers into a single router for mounting on the main app.
"""

from fastapi import APIRouter

from pilot_space.api.v1.routers.ai_configuration import router as ai_configuration_router
from pilot_space.api.v1.routers.artifact_annotations import router as artifact_annotations_router
from pilot_space.api.v1.routers.auth import router as auth_router
from pilot_space.api.v1.routers.memory import router as memory_router
from pilot_space.api.v1.routers.project_artifacts import router as project_artifacts_router
from pilot_space.api.v1.routers.projects import router as projects_router
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
)
api_router.include_router(
    ai_configuration_router,
    prefix="/workspaces/{workspace_id}/ai-configurations",
    tags=["ai-configuration"],
)

api_router.include_router(memory_router, prefix="", tags=["memory"])
api_router.include_router(
    artifact_annotations_router,
    prefix="/workspaces/{workspace_id}/projects/{project_id}/artifacts/{artifact_id}/annotations",
    tags=["artifact-annotations"],
)

# Debug router and mock generators removed (were development-only features)


__all__ = ["api_router"]
