"""Workspace feature toggles router for Pilot Space API.

Thin HTTP layer — delegates business logic to FeatureToggleService.
Service exceptions (FeatureToggleError hierarchy) are caught by the global
RFC 7807 exception handler registered in error_handler.py.

Routes are mounted under /workspaces/{workspace_id}/feature-toggles.

Admin/owner can update toggles; any workspace member can read them.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter

from pilot_space.api.v1.schemas.workspace import (
    WorkspaceFeatureToggles,
    WorkspaceFeatureTogglesUpdate,
)
from pilot_space.application.services.feature_toggle import FeatureToggleService
from pilot_space.dependencies import (
    CurrentUser,
    DbSession,
)
from pilot_space.infrastructure.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


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

    Service exceptions propagate to the global feature_toggle_error_handler
    which returns RFC 7807 application/problem+json responses.
    """
    service = FeatureToggleService(session)
    return await service.get_toggles(workspace_id, current_user.user_id)


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

    Service exceptions propagate to the global feature_toggle_error_handler
    which returns RFC 7807 application/problem+json responses.
    """
    service = FeatureToggleService(session)
    return await service.update_toggles(workspace_id, current_user.user_id, body)
