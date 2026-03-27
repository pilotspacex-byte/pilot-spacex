"""Workspace AI settings router for Pilot Space API.

Provides endpoints for managing workspace AI provider configuration,
API key validation, and feature toggles (T062-T066).
Routes are mounted under /workspaces/{workspace_id}/ai/settings.

Service-based architecture: 2 service slots (embedding + llm).
Supported providers: google (embedding), anthropic (llm), ollama (both).

Thin router shell -- all business logic delegated to WorkspaceAISettingsService.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter

from pilot_space.api.v1.dependencies import WorkspaceAISettingsServiceDep
from pilot_space.api.v1.routers._workspace_admin import get_admin_workspace
from pilot_space.api.v1.schemas.workspace import (
    WorkspaceAISettingsResponse,
    WorkspaceAISettingsUpdate,
    WorkspaceAISettingsUpdateResponse,
)
from pilot_space.dependencies import (
    CurrentUser,
    DbSession,
)

router = APIRouter()


@router.get(
    "/{workspace_id}/ai/settings",
    response_model=WorkspaceAISettingsResponse,
    tags=["workspaces", "ai"],
)
async def get_ai_settings(
    workspace_id: UUID,
    current_user: CurrentUser,
    session: DbSession,
    service: WorkspaceAISettingsServiceDep,
) -> WorkspaceAISettingsResponse:
    """Get workspace AI settings.

    Returns provider statuses grouped by service type and feature toggles.
    Requires workspace admin permission.
    """
    workspace = await get_admin_workspace(workspace_id, current_user, session)
    return await service.get_ai_settings(workspace, workspace_id)


@router.patch(
    "/{workspace_id}/ai/settings",
    response_model=WorkspaceAISettingsUpdateResponse,
    tags=["workspaces", "ai"],
)
async def update_ai_settings(
    workspace_id: UUID,
    body: WorkspaceAISettingsUpdate,
    current_user: CurrentUser,
    session: DbSession,
    service: WorkspaceAISettingsServiceDep,
) -> WorkspaceAISettingsUpdateResponse:
    """Update workspace AI settings.

    Stores API keys (encrypted with Fernet) and feature toggles.
    Requires workspace admin permission.
    """
    workspace = await get_admin_workspace(workspace_id, current_user, session)
    return await service.update_ai_settings(workspace, workspace_id, body)


__all__ = ["router"]
