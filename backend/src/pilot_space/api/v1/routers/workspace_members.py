"""Workspace member management router for Pilot Space API.

Provides endpoints for listing, adding, updating, and removing workspace members.
Routes are mounted under /workspaces/{workspace_id}/members.
"""

from __future__ import annotations

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, status

from pilot_space.api.v1.schemas.workspace import (
    WorkspaceMemberResponse,
    WorkspaceMemberUpdate,
)
from pilot_space.dependencies import (
    CurrentUser,
    CurrentUserId,
    DbSession,
)
from pilot_space.infrastructure.database.models.workspace import Workspace
from pilot_space.infrastructure.database.models.workspace_member import WorkspaceRole
from pilot_space.infrastructure.database.repositories.workspace_repository import (
    WorkspaceRepository,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# Type alias for endpoints that accept both UUID and slug
WorkspaceIdOrSlug = Annotated[str, Path(description="Workspace ID (UUID) or slug")]


def _get_workspace_repository(session: DbSession) -> WorkspaceRepository:
    """Get workspace repository with session."""
    return WorkspaceRepository(session=session)


WorkspaceRepo = Annotated[WorkspaceRepository, Depends(_get_workspace_repository)]


def _is_valid_uuid(value: str) -> bool:
    """Check if a string is a valid UUID."""
    try:
        UUID(value)
        return True
    except ValueError:
        return False


async def _resolve_workspace_with_members(
    workspace_id_or_slug: str,
    workspace_repo: WorkspaceRepository,
) -> Workspace:
    """Resolve workspace by UUID or slug with members eagerly loaded.

    Args:
        workspace_id_or_slug: UUID string or slug.
        workspace_repo: Workspace repository.

    Returns:
        Workspace with members loaded.

    Raises:
        HTTPException: If workspace not found.
    """
    if _is_valid_uuid(workspace_id_or_slug):
        workspace = await workspace_repo.get_with_members(UUID(workspace_id_or_slug))
    else:
        workspace = await workspace_repo.get_by_slug_with_members(workspace_id_or_slug)

    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )
    return workspace


@router.get(
    "/{workspace_id}/members",
    response_model=list[WorkspaceMemberResponse],
    tags=["workspaces"],
)
async def list_workspace_members(
    workspace_id: WorkspaceIdOrSlug,
    current_user_id: CurrentUserId,
    workspace_repo: WorkspaceRepo,
) -> list[WorkspaceMemberResponse]:
    """List workspace members.

    Args:
        workspace_id: Workspace identifier (UUID or slug).
        current_user_id: Authenticated user ID.
        workspace_repo: Workspace repository.

    Returns:
        List of workspace members.

    Raises:
        HTTPException: If workspace not found or user not a member.
    """
    workspace = await _resolve_workspace_with_members(workspace_id, workspace_repo)

    # Check membership
    is_member = any(m.user_id == current_user_id for m in (workspace.members or []))
    if not is_member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this workspace",
        )

    return [
        WorkspaceMemberResponse(
            user_id=member.user_id,
            email=member.user.email if member.user else "",
            full_name=member.user.full_name if member.user else None,
            avatar_url=member.user.avatar_url if member.user else None,
            role=member.role.value,
            joined_at=member.created_at,
        )
        for member in (workspace.members or [])
    ]


@router.patch(
    "/{workspace_id}/members/{user_id}",
    response_model=WorkspaceMemberResponse,
    tags=["workspaces"],
)
async def update_workspace_member(
    workspace_id: UUID,
    user_id: UUID,
    request: WorkspaceMemberUpdate,
    current_user: CurrentUser,
    workspace_repo: WorkspaceRepo,
) -> WorkspaceMemberResponse:
    """Update member role.

    Requires admin role.

    Args:
        workspace_id: Workspace identifier.
        user_id: Member user ID.
        request: Update data.
        current_user: Authenticated user.
        workspace_repo: Workspace repository.

    Returns:
        Updated member.

    Raises:
        HTTPException: If not found or not admin.
    """
    workspace = await workspace_repo.get_by_id(workspace_id)
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )

    # Check admin role
    current_member = next(
        (m for m in (workspace.members or []) if m.user_id == current_user.user_id),
        None,
    )
    if not current_member or not current_member.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )

    # Find target member
    target_member = next(
        (m for m in (workspace.members or []) if m.user_id == user_id),
        None,
    )
    if not target_member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found",
        )

    # Update role
    role = WorkspaceRole(request.role)

    # Ownership transfer guard (FR-017, T020a)
    if role == WorkspaceRole.OWNER:
        if not current_member.is_owner:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the workspace owner can transfer ownership",
            )
        # Demote current owner to admin
        await workspace_repo.update_member_role(
            workspace_id, current_user.user_id, WorkspaceRole.ADMIN
        )

    updated_member = await workspace_repo.update_member_role(workspace_id, user_id, role)

    if not updated_member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found",
        )

    return WorkspaceMemberResponse(
        user_id=updated_member.user_id,
        email=updated_member.user.email if updated_member.user else "",
        full_name=updated_member.user.full_name if updated_member.user else None,
        avatar_url=updated_member.user.avatar_url if updated_member.user else None,
        role=updated_member.role.value,
        joined_at=updated_member.created_at,
    )


@router.delete(
    "/{workspace_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["workspaces"],
)
async def remove_workspace_member(
    workspace_id: UUID,
    user_id: UUID,
    current_user: CurrentUser,
    workspace_repo: WorkspaceRepo,
) -> None:
    """Remove member from workspace.

    Requires admin role (or self-removal).

    Args:
        workspace_id: Workspace identifier.
        user_id: Member user ID.
        current_user: Authenticated user.
        workspace_repo: Workspace repository.

    Raises:
        HTTPException: If not found or not authorized.
    """
    workspace = await workspace_repo.get_by_id(workspace_id)
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )

    # Check authorization (admin/owner or self)
    is_admin = any(
        m.user_id == current_user.user_id and m.is_admin for m in (workspace.members or [])
    )
    is_self = user_id == current_user.user_id

    if not (is_admin or is_self):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required to remove other members",
        )

    # Prevent removing the only admin
    if is_self and is_admin:
        admin_count = sum(1 for m in (workspace.members or []) if m.role == WorkspaceRole.ADMIN)
        if admin_count == 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot remove the only admin from workspace",
            )

    await workspace_repo.remove_member(workspace_id, user_id)

    logger.info(
        "Workspace member removed",
        extra={"workspace_id": str(workspace_id), "user_id": str(user_id)},
    )


__all__ = ["router"]
