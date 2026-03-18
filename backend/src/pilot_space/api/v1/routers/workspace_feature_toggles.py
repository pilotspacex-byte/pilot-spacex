"""Workspace feature toggles router for Pilot Space API.

Provides endpoints for managing workspace sidebar feature visibility.
Routes are mounted under /workspaces/{workspace_id}/feature-toggles.

Admin/owner can update toggles; any workspace member can read them.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy.orm.attributes import flag_modified

from pilot_space.api.v1.schemas.workspace import (
    WorkspaceFeatureToggles,
    WorkspaceFeatureTogglesUpdate,
)
from pilot_space.dependencies import (
    CurrentUser,
    DbSession,
)
from pilot_space.infrastructure.database.models.workspace import Workspace
from pilot_space.infrastructure.database.repositories.workspace_repository import (
    WorkspaceRepository,
)
from pilot_space.infrastructure.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()

SETTINGS_KEY = "feature_toggles"


def _get_feature_toggles(workspace: Workspace) -> WorkspaceFeatureToggles:
    """Extract feature toggles from workspace settings, falling back to defaults."""
    if not workspace.settings or SETTINGS_KEY not in workspace.settings:
        return WorkspaceFeatureToggles()

    toggles_data = workspace.settings[SETTINGS_KEY]
    return WorkspaceFeatureToggles(**toggles_data)


async def _get_member_workspace(
    workspace_id: UUID,
    current_user: CurrentUser,
    session: DbSession,
) -> Workspace:
    """Resolve workspace and verify the user is a member (any role)."""
    workspace_repo = WorkspaceRepository(session=session)
    workspace = await workspace_repo.get_with_members(workspace_id)
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )

    member = next(
        (m for m in (workspace.members or []) if m.user_id == current_user.user_id),
        None,
    )
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this workspace",
        )

    return workspace


async def _get_admin_workspace(
    workspace_id: UUID,
    current_user: CurrentUser,
    session: DbSession,
) -> Workspace:
    """Resolve workspace and verify admin/owner access."""
    workspace_repo = WorkspaceRepository(session=session)
    workspace = await workspace_repo.get_with_members(workspace_id)
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )

    member = next(
        (m for m in (workspace.members or []) if m.user_id == current_user.user_id),
        None,
    )
    if not member or not member.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )

    return workspace


@router.get(
    "/{workspace_id}/feature-toggles",
    response_model=WorkspaceFeatureToggles,
    tags=["workspaces", "settings"],
)
async def get_feature_toggles(
    workspace_id: UUID,
    current_user: CurrentUser,
    session: DbSession,
) -> WorkspaceFeatureToggles:
    """Get workspace feature toggles.

    Returns the current enabled/disabled state for all sidebar modules.
    Accessible to any authenticated workspace member.
    """
    workspace = await _get_member_workspace(workspace_id, current_user, session)
    return _get_feature_toggles(workspace)


@router.patch(
    "/{workspace_id}/feature-toggles",
    response_model=WorkspaceFeatureToggles,
    tags=["workspaces", "settings"],
)
async def update_feature_toggles(
    workspace_id: UUID,
    body: WorkspaceFeatureTogglesUpdate,
    current_user: CurrentUser,
    session: DbSession,
) -> WorkspaceFeatureToggles:
    """Update workspace feature toggles.

    Partially update feature toggles — only provided fields are changed.
    Restricted to workspace owner or admin.
    """
    workspace = await _get_admin_workspace(workspace_id, current_user, session)
    workspace_repo = WorkspaceRepository(session=session)

    workspace_settings = workspace.settings or {}
    existing_toggles = workspace_settings.get(SETTINGS_KEY, {})

    # Merge only provided (non-None) fields
    updates = body.model_dump(exclude_none=True)
    existing_toggles.update(updates)
    workspace_settings[SETTINGS_KEY] = existing_toggles

    workspace.settings = workspace_settings
    flag_modified(workspace, "settings")
    await workspace_repo.update(workspace)
    await session.commit()

    logger.info(
        "Feature toggles updated for workspace %s by user %s: %s",
        workspace_id,
        current_user.user_id,
        updates,
    )

    return _get_feature_toggles(workspace)
