"""Shared workspace admin/member verification helpers.

Provides reusable workspace lookup + role-check helpers for routers that
operate on path-parameter workspace IDs (e.g. workspace_ai_settings,
workspace_mcp_servers, workspace_feature_toggles).

These are HTTP-layer concerns (raise HTTPException) and are intentionally
kept in the router package rather than the service layer.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status

from pilot_space.dependencies import CurrentUser, DbSession
from pilot_space.infrastructure.database.models.workspace import Workspace
from pilot_space.infrastructure.database.repositories.workspace_repository import (
    WorkspaceRepository,
)


async def get_admin_workspace(
    workspace_id: UUID,
    current_user: CurrentUser,
    session: DbSession,
) -> Workspace:
    """Resolve workspace and verify admin/owner access.

    Args:
        workspace_id: Workspace identifier.
        current_user: Authenticated user from JWT.
        session: Database session.

    Returns:
        Workspace model.

    Raises:
        HTTPException 404: Workspace not found.
        HTTPException 403: User is not admin/owner.
    """
    from pilot_space.infrastructure.database.models.workspace_member import WorkspaceRole

    workspace_repo = WorkspaceRepository(session=session)
    workspace = await workspace_repo.get_by_id(workspace_id)
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )

    role = await workspace_repo.get_member_role(workspace_id, current_user.user_id)
    if role not in (WorkspaceRole.OWNER, WorkspaceRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )

    return workspace


async def get_member_workspace(
    workspace_id: UUID,
    current_user: CurrentUser,
    session: DbSession,
) -> Workspace:
    """Resolve workspace and verify the user is a member (any role).

    Args:
        workspace_id: Workspace identifier.
        current_user: Authenticated user from JWT.
        session: Database session.

    Returns:
        Workspace model.

    Raises:
        HTTPException 404: Workspace not found.
        HTTPException 403: User is not a member.
    """
    workspace_repo = WorkspaceRepository(session=session)
    workspace = await workspace_repo.get_by_id(workspace_id)
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )

    if not await workspace_repo.is_member(workspace_id, current_user.user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this workspace",
        )

    return workspace
