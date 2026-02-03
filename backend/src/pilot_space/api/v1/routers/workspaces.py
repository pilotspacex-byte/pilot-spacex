"""Workspace router for Pilot Space API.

Provides endpoints for workspace CRUD operations and label management.
Member management: see workspace_members.py
AI settings: see workspace_ai_settings.py
"""

from __future__ import annotations

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status

from pilot_space.api.v1.schemas.base import DeleteResponse, PaginatedResponse
from pilot_space.api.v1.schemas.issue import LabelBriefSchema
from pilot_space.api.v1.schemas.workspace import (
    WorkspaceCreate,
    WorkspaceDetailResponse,
    WorkspaceResponse,
    WorkspaceUpdate,
)
from pilot_space.dependencies import (
    DEMO_WORKSPACE_SLUGS,
    CurrentUser,
    CurrentUserId,
    CurrentUserIdOrDemo,
    DbSession,
)
from pilot_space.infrastructure.database.models.workspace import Workspace
from pilot_space.infrastructure.database.models.workspace_member import WorkspaceRole
from pilot_space.infrastructure.database.repositories.label_repository import (
    LabelRepository,
)
from pilot_space.infrastructure.database.repositories.workspace_repository import (
    WorkspaceRepository,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


def get_workspace_repository(session: DbSession) -> WorkspaceRepository:
    """Get workspace repository with session."""
    return WorkspaceRepository(session=session)


WorkspaceRepo = Annotated[WorkspaceRepository, Depends(get_workspace_repository)]


def get_label_repository(session: DbSession) -> LabelRepository:
    """Get label repository with session."""
    return LabelRepository(session=session)


LabelRepo = Annotated[LabelRepository, Depends(get_label_repository)]

# Type alias for endpoints that accept both UUID and slug
WorkspaceIdOrSlug = Annotated[str, Path(description="Workspace ID (UUID) or slug")]


def _is_demo_workspace(workspace_id_or_slug: str) -> bool:
    """Check if the workspace identifier refers to a demo workspace."""
    from pilot_space.config import get_settings

    settings = get_settings()
    if settings.app_env not in ("development", "test"):
        return False
    return workspace_id_or_slug in DEMO_WORKSPACE_SLUGS


def _is_valid_uuid(value: str) -> bool:
    """Check if a string is a valid UUID."""
    try:
        UUID(value)
        return True
    except ValueError:
        return False


async def _resolve_workspace(
    workspace_id_or_slug: str,
    workspace_repo: WorkspaceRepository,
    *,
    load_members: bool = False,
) -> Workspace:
    """Resolve workspace by UUID or slug.

    Args:
        workspace_id_or_slug: UUID string or slug.
        workspace_repo: Workspace repository.
        load_members: If True, eagerly load members relationship.
    """
    if _is_valid_uuid(workspace_id_or_slug):
        if load_members:
            workspace = await workspace_repo.get_with_members(UUID(workspace_id_or_slug))
        else:
            workspace = await workspace_repo.get_by_id(UUID(workspace_id_or_slug))
    elif load_members:
        workspace = await workspace_repo.get_by_slug_with_members(workspace_id_or_slug)
    else:
        workspace = await workspace_repo.get_by_slug(workspace_id_or_slug)

    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )
    return workspace


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


# ============================================================================
# Label Management Endpoints
# ============================================================================


@router.get(
    "/{workspace_id}/labels",
    response_model=list[LabelBriefSchema],
    tags=["workspaces", "labels"],
)
async def list_workspace_labels(
    workspace_id: WorkspaceIdOrSlug,
    current_user_id: CurrentUserIdOrDemo,
    workspace_repo: WorkspaceRepo,
    label_repo: LabelRepo,
    project_id: Annotated[UUID | None, Query(description="Filter by project ID")] = None,
) -> list[LabelBriefSchema]:
    """List labels available in a workspace.

    Returns workspace-wide labels and optionally project-specific labels.
    Requires workspace membership.

    Args:
        workspace_id: Workspace identifier (UUID or slug).
        current_user_id: Authenticated user ID (falls back to demo user in dev).
        workspace_repo: Workspace repository.
        label_repo: Label repository.
        project_id: Optional project filter.

    Returns:
        List of labels.

    Raises:
        HTTPException: If workspace not found or user not a member.
    """
    workspace = await _resolve_workspace(workspace_id, workspace_repo, load_members=True)

    # Check membership (demo workspaces bypass check in dev/test)
    if not _is_demo_workspace(workspace_id):
        is_member = any(m.user_id == current_user_id for m in (workspace.members or []))
        if not is_member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not a member of this workspace",
            )

    labels = await label_repo.get_workspace_labels(
        workspace.id,
        include_project_labels=True,
        project_id=project_id,
    )

    return [LabelBriefSchema.model_validate(label) for label in labels]


__all__ = ["router"]
