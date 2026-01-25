"""Workspace router for Pilot Space API.

Provides endpoints for workspace CRUD and member management.
"""

from __future__ import annotations

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from pilot_space.api.v1.schemas.base import DeleteResponse, PaginatedResponse
from pilot_space.api.v1.schemas.workspace import (
    WorkspaceCreate,
    WorkspaceDetailResponse,
    WorkspaceMemberCreate,
    WorkspaceMemberResponse,
    WorkspaceMemberUpdate,
    WorkspaceResponse,
    WorkspaceUpdate,
)
from pilot_space.dependencies import CurrentUser, CurrentUserId, DbSession
from pilot_space.infrastructure.database.models.workspace import Workspace
from pilot_space.infrastructure.database.models.workspace_member import WorkspaceRole
from pilot_space.infrastructure.database.repositories.workspace_repository import (
    WorkspaceRepository,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


def get_workspace_repository(session: DbSession) -> WorkspaceRepository:
    """Get workspace repository with session."""
    return WorkspaceRepository(session=session)


WorkspaceRepo = Annotated[WorkspaceRepository, Depends(get_workspace_repository)]


def _workspace_to_response(
    workspace: Workspace,
    current_user_role: str | None = None,
) -> WorkspaceDetailResponse:
    """Convert workspace model to response."""
    return WorkspaceDetailResponse(
        id=workspace.id,
        created_at=workspace.created_at,
        updated_at=workspace.updated_at,
        name=workspace.name,
        slug=workspace.slug,
        description=workspace.description,
        owner_id=workspace.owner_id,
        member_count=len(workspace.members) if workspace.members else 0,
        project_count=len(workspace.projects) if workspace.projects else 0,
        settings=workspace.settings,
        current_user_role=current_user_role,
    )


@router.get("", response_model=PaginatedResponse[WorkspaceResponse], tags=["workspaces"])
async def list_workspaces(
    current_user: CurrentUser,
    workspace_repo: WorkspaceRepo,
    cursor: str | None = Query(default=None, description="Pagination cursor"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
) -> PaginatedResponse[WorkspaceResponse]:
    """List workspaces the current user is a member of.

    Args:
        current_user: Authenticated user.
        workspace_repo: Workspace repository.
        cursor: Pagination cursor.
        page_size: Number of items per page.

    Returns:
        Paginated list of workspaces.
    """
    # Get user's workspaces (not paginated in this simple implementation)
    workspaces = await workspace_repo.get_user_workspaces(user_id=current_user.user_id)

    items = [
        WorkspaceResponse(
            id=ws.id,
            created_at=ws.created_at,
            updated_at=ws.updated_at,
            name=ws.name,
            slug=ws.slug,
            description=ws.description,
            owner_id=ws.owner_id,
            member_count=len(ws.members) if ws.members else 0,
            project_count=len(ws.projects) if ws.projects else 0,
        )
        for ws in workspaces
    ]

    # Apply simple pagination
    total = len(items)
    start_idx = 0
    if cursor:
        # Simple cursor: just use offset
        start_idx = int(cursor) if cursor.isdigit() else 0
    end_idx = start_idx + page_size
    paginated_items = items[start_idx:end_idx]
    has_next = end_idx < total
    has_prev = start_idx > 0

    return PaginatedResponse(
        items=paginated_items,
        total=total,
        next_cursor=str(end_idx) if has_next else None,
        prev_cursor=str(max(0, start_idx - page_size)) if has_prev else None,
        has_next=has_next,
        has_prev=has_prev,
        page_size=page_size,
    )


@router.post(
    "",
    response_model=WorkspaceDetailResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["workspaces"],
)
async def create_workspace(
    request: WorkspaceCreate,
    current_user_id: CurrentUserId,
    workspace_repo: WorkspaceRepo,
) -> WorkspaceDetailResponse:
    """Create a new workspace.

    Args:
        request: Workspace creation data.
        current_user_id: Authenticated user ID.
        workspace_repo: Workspace repository.

    Returns:
        Created workspace.

    Raises:
        HTTPException: If slug already exists.
    """
    # Check slug uniqueness
    existing = await workspace_repo.get_by_slug(request.slug)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Workspace with slug '{request.slug}' already exists",
        )

    # Create workspace entity
    workspace = Workspace(
        name=request.name,
        slug=request.slug,
        description=request.description,
        owner_id=current_user_id,
    )
    workspace = await workspace_repo.create(workspace)

    # Add owner as admin member
    await workspace_repo.add_member(
        workspace_id=workspace.id,
        user_id=current_user_id,
        role=WorkspaceRole.ADMIN,
    )

    logger.info(
        "Workspace created",
        extra={"workspace_id": str(workspace.id), "slug": workspace.slug},
    )

    return _workspace_to_response(workspace, current_user_role="admin")


@router.get("/{workspace_id}", response_model=WorkspaceDetailResponse, tags=["workspaces"])
async def get_workspace(
    workspace_id: UUID,
    current_user: CurrentUser,
    workspace_repo: WorkspaceRepo,
) -> WorkspaceDetailResponse:
    """Get workspace by ID.

    Args:
        workspace_id: Workspace identifier.
        current_user: Authenticated user.
        workspace_repo: Workspace repository.

    Returns:
        Workspace details.

    Raises:
        HTTPException: If workspace not found or user not a member.
    """
    workspace = await workspace_repo.get_by_id(workspace_id)
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )

    # Check membership
    member = next(
        (m for m in (workspace.members or []) if m.user_id == current_user.user_id),
        None,
    )
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this workspace",
        )

    return _workspace_to_response(workspace, current_user_role=member.role.value)


@router.patch("/{workspace_id}", response_model=WorkspaceDetailResponse, tags=["workspaces"])
async def update_workspace(
    workspace_id: UUID,
    request: WorkspaceUpdate,
    current_user: CurrentUser,
    workspace_repo: WorkspaceRepo,
) -> WorkspaceDetailResponse:
    """Update workspace.

    Requires admin role.

    Args:
        workspace_id: Workspace identifier.
        request: Update data.
        current_user: Authenticated user.
        workspace_repo: Workspace repository.

    Returns:
        Updated workspace.

    Raises:
        HTTPException: If workspace not found or user not admin.
    """
    workspace = await workspace_repo.get_by_id(workspace_id)
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )

    # Check admin role
    member = next(
        (m for m in (workspace.members or []) if m.user_id == current_user.user_id),
        None,
    )
    if not member or member.role != WorkspaceRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )

    # Update workspace
    update_data = request.model_dump(exclude_unset=True)
    if update_data:
        for key, value in update_data.items():
            setattr(workspace, key, value)
        workspace = await workspace_repo.update(workspace)

    logger.info(
        "Workspace updated",
        extra={"workspace_id": str(workspace_id)},
    )

    return _workspace_to_response(workspace, current_user_role="admin")


@router.delete("/{workspace_id}", response_model=DeleteResponse, tags=["workspaces"])
async def delete_workspace(
    workspace_id: UUID,
    current_user: CurrentUser,
    workspace_repo: WorkspaceRepo,
) -> DeleteResponse:
    """Soft delete workspace.

    Requires admin role.

    Args:
        workspace_id: Workspace identifier.
        current_user: Authenticated user.
        workspace_repo: Workspace repository.

    Returns:
        Delete confirmation.

    Raises:
        HTTPException: If workspace not found or user not admin.
    """
    workspace = await workspace_repo.get_by_id(workspace_id)
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )

    # Check admin role
    member = next(
        (m for m in (workspace.members or []) if m.user_id == current_user.user_id),
        None,
    )
    if not member or member.role != WorkspaceRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )

    await workspace_repo.delete(workspace)

    logger.info(
        "Workspace deleted",
        extra={"workspace_id": str(workspace_id)},
    )

    return DeleteResponse(id=workspace_id, message="Workspace deleted successfully")


# Member management endpoints
@router.get(
    "/{workspace_id}/members", response_model=list[WorkspaceMemberResponse], tags=["workspaces"]
)
async def list_workspace_members(
    workspace_id: UUID,
    current_user: CurrentUser,
    workspace_repo: WorkspaceRepo,
) -> list[WorkspaceMemberResponse]:
    """List workspace members.

    Args:
        workspace_id: Workspace identifier.
        current_user: Authenticated user.
        workspace_repo: Workspace repository.

    Returns:
        List of workspace members.

    Raises:
        HTTPException: If workspace not found or user not a member.
    """
    workspace = await workspace_repo.get_by_id(workspace_id)
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )

    # Check membership
    is_member = any(m.user_id == current_user.user_id for m in (workspace.members or []))
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


@router.post(
    "/{workspace_id}/members",
    response_model=WorkspaceMemberResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["workspaces"],
)
async def add_workspace_member(
    workspace_id: UUID,
    request: WorkspaceMemberCreate,
    current_user: CurrentUser,
    workspace_repo: WorkspaceRepo,
) -> WorkspaceMemberResponse:
    """Add member to workspace.

    Requires admin role.

    Args:
        workspace_id: Workspace identifier.
        request: Member data.
        current_user: Authenticated user.
        workspace_repo: Workspace repository.

    Returns:
        Added member.

    Raises:
        HTTPException: If workspace not found, user not admin, or member not found.
    """
    workspace = await workspace_repo.get_by_id(workspace_id)
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )

    # Check admin role
    member = next(
        (m for m in (workspace.members or []) if m.user_id == current_user.user_id),
        None,
    )
    if not member or member.role != WorkspaceRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )

    # TODO: Look up user by email and add them
    # For now, return 501 Not Implemented
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Member invitation not yet implemented",
    )


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
    if not current_member or current_member.role != WorkspaceRole.ADMIN:
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
    "/{workspace_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["workspaces"]
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

    # Check authorization (admin or self)
    is_admin = any(
        m.user_id == current_user.user_id and m.role == WorkspaceRole.ADMIN
        for m in (workspace.members or [])
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
