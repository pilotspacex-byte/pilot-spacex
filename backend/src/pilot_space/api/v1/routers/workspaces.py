"""Workspace router for Pilot Space API.

Provides endpoints for workspace CRUD operations and label management.
Member management: see workspace_members.py
Invitations: see workspace_invitations.py
AI settings: see workspace_ai_settings.py
"""

from __future__ import annotations

import asyncio
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Path, Query, status

from pilot_space.api.v1.dependencies import WorkspaceServiceDep
from pilot_space.api.v1.schemas.base import DeleteResponse, PaginatedResponse
from pilot_space.api.v1.schemas.issue import LabelBriefSchema
from pilot_space.api.v1.schemas.workspace import (
    WorkspaceCreate,
    WorkspaceDetailResponse,
    WorkspaceResponse,
    WorkspaceUpdate,
)
from pilot_space.application.services.workspace import (
    CreateWorkspacePayload,
    DeleteWorkspacePayload,
    GetWorkspacePayload,
    ListLabelsPayload,
    ListWorkspacesPayload,
    UpdateWorkspacePayload,
)
from pilot_space.dependencies import SyncedUserId
from pilot_space.dependencies.auth import SessionDep
from pilot_space.infrastructure.database import get_db_session
from pilot_space.infrastructure.database.rls import set_rls_context
from pilot_space.infrastructure.logging import get_logger

logger = get_logger(__name__)

# Strong references to fire-and-forget tasks to prevent GC from collecting them
_background_tasks: set[asyncio.Task[None]] = set()

router = APIRouter(prefix="/workspaces", tags=["workspaces"])

# Type alias for endpoints that accept both UUID and slug
WorkspaceIdOrSlug = Annotated[str, Path(description="Workspace ID (UUID) or slug")]


@router.get("", response_model=PaginatedResponse[WorkspaceResponse], tags=["workspaces"])
async def list_workspaces(
    current_user_id: SyncedUserId,
    session: SessionDep,
    service: WorkspaceServiceDep,
    cursor: str | None = Query(default=None, description="Pagination cursor"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
) -> PaginatedResponse[WorkspaceResponse]:
    """List workspaces the current user is a member of.

    Args:
        current_user_id: Authenticated user ID.
        session: Database session (triggers ContextVar).
        service: Workspace service.
        cursor: Pagination cursor.
        page_size: Number of items per page.

    Returns:
        Paginated list of workspaces.
    """
    await set_rls_context(session, current_user_id)
    result = await service.list_workspaces(
        ListWorkspacesPayload(
            user_id=current_user_id,
            cursor=cursor,
            page_size=page_size,
        )
    )

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
        for ws in result.workspaces
    ]

    return PaginatedResponse(
        items=items,
        total=result.total,
        next_cursor=result.next_cursor,
        prev_cursor=result.prev_cursor,
        has_next=result.has_next,
        has_prev=result.has_prev,
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
    current_user_id: SyncedUserId,
    session: SessionDep,
    service: WorkspaceServiceDep,
) -> WorkspaceDetailResponse:
    """Create a new workspace.

    Args:
        request: Workspace creation data.
        current_user_id: Authenticated user ID.
        session: Database session (triggers ContextVar).
        service: Workspace service.

    Returns:
        Created workspace.

    Raises:
        HTTPException: If slug already exists.
    """
    await set_rls_context(session, current_user_id)
    try:
        result = await service.create_workspace(
            CreateWorkspacePayload(
                name=request.name,
                slug=request.slug,
                description=request.description,
                owner_id=current_user_id,
            )
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        ) from e

    workspace = result.workspace

    # SKRG-05: Seed default plugins into the new workspace (non-blocking fire-and-forget)
    task = asyncio.create_task(_seed_workspace_background(workspace.id))
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)

    return WorkspaceDetailResponse(
        id=workspace.id,
        created_at=workspace.created_at,
        updated_at=workspace.updated_at,
        name=workspace.name,
        slug=workspace.slug,
        description=workspace.description,
        owner_id=workspace.owner_id,
        member_count=1,  # Just created with owner
        project_count=0,
        settings=workspace.settings,
        current_user_role="owner",
    )


@router.get("/{workspace_id}", response_model=WorkspaceDetailResponse, tags=["workspaces"])
async def get_workspace(
    workspace_id: WorkspaceIdOrSlug,
    current_user_id: SyncedUserId,
    session: SessionDep,
    service: WorkspaceServiceDep,
) -> WorkspaceDetailResponse:
    """Get workspace by ID or slug.

    Args:
        workspace_id: Workspace identifier (UUID or slug).
        current_user_id: Authenticated user ID.
        session: Database session (triggers ContextVar).
        service: Workspace service.

    Returns:
        Workspace details.

    Raises:
        HTTPException: If workspace not found or user not a member.
    """
    await set_rls_context(session, current_user_id)
    try:
        result = await service.get_workspace(
            GetWorkspacePayload(
                workspace_id_or_slug=workspace_id,
                user_id=current_user_id,
            )
        )
    except ValueError as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_msg,
            ) from e
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=error_msg,
        ) from e

    workspace = result.workspace
    return WorkspaceDetailResponse(
        id=workspace.id,
        created_at=workspace.created_at,
        updated_at=workspace.updated_at,
        name=workspace.name,
        slug=workspace.slug,
        description=workspace.description,
        owner_id=workspace.owner_id,
        member_count=result.member_count,
        project_count=result.project_count,
        settings=workspace.settings,
        current_user_role=result.current_user_role,
    )


@router.patch("/{workspace_id}", response_model=WorkspaceDetailResponse, tags=["workspaces"])
async def update_workspace(
    workspace_id: WorkspaceIdOrSlug,
    request: WorkspaceUpdate,
    current_user_id: SyncedUserId,
    session: SessionDep,
    service: WorkspaceServiceDep,
) -> WorkspaceDetailResponse:
    """Update workspace.

    Requires admin role.

    Args:
        workspace_id: Workspace identifier (UUID or slug).
        request: Update data.
        current_user_id: Authenticated user ID.
        session: Database session (triggers ContextVar).
        service: Workspace service.

    Returns:
        Updated workspace.

    Raises:
        HTTPException: If workspace not found or user not admin.
    """
    await set_rls_context(session, current_user_id)
    update_data = request.model_dump(exclude_unset=True)

    try:
        result = await service.update_workspace(
            UpdateWorkspacePayload(
                workspace_id_or_slug=workspace_id,
                user_id=current_user_id,
                name=update_data.get("name"),
                slug=update_data.get("slug"),
                description=update_data.get("description"),
                settings=update_data.get("settings"),
            )
        )
    except ValueError as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_msg,
            ) from e
        if "already taken" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=error_msg,
            ) from e
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=error_msg,
        ) from e

    workspace = result.workspace
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
        current_user_role="admin",  # Already verified in service
    )


@router.delete("/{workspace_id}", response_model=DeleteResponse, tags=["workspaces"])
async def delete_workspace(
    workspace_id: WorkspaceIdOrSlug,
    current_user_id: SyncedUserId,
    session: SessionDep,
    service: WorkspaceServiceDep,
) -> DeleteResponse:
    """Soft delete workspace.

    Requires owner role.

    Args:
        workspace_id: Workspace identifier (UUID or slug).
        current_user_id: Authenticated user ID.
        session: Database session (triggers ContextVar).
        service: Workspace service.

    Returns:
        Delete confirmation.

    Raises:
        HTTPException: If workspace not found or user not owner.
    """
    await set_rls_context(session, current_user_id)
    try:
        result = await service.delete_workspace(
            DeleteWorkspacePayload(
                workspace_id_or_slug=workspace_id,
                user_id=current_user_id,
            )
        )
    except ValueError as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_msg,
            ) from e
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=error_msg,
        ) from e

    return DeleteResponse(
        id=result.workspace_id,
        message="Workspace deleted successfully",
    )


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
    current_user_id: SyncedUserId,
    session: SessionDep,
    service: WorkspaceServiceDep,
    project_id: Annotated[UUID | None, Query(description="Filter by project ID")] = None,
) -> list[LabelBriefSchema]:
    """List labels available in a workspace.

    Returns workspace-wide labels and optionally project-specific labels.
    Requires workspace membership.

    Args:
        workspace_id: Workspace identifier (UUID or slug).
        current_user_id: Authenticated user ID.
        session: Database session (triggers ContextVar).
        service: Workspace service.
        project_id: Optional project filter.

    Returns:
        List of labels.

    Raises:
        HTTPException: If workspace not found or user not a member.
    """
    await set_rls_context(session, current_user_id)
    try:
        result = await service.list_labels(
            ListLabelsPayload(
                workspace_id_or_slug=workspace_id,
                user_id=current_user_id,
                project_id=project_id,
            )
        )
    except ValueError as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_msg,
            ) from e
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=error_msg,
        ) from e

    return [LabelBriefSchema.model_validate(label) for label in result.labels]


async def _seed_workspace_background(workspace_id: UUID) -> None:
    """Seed default plugins in a background task with its own DB session.

    Uses get_db_session() for an independent session lifecycle so the
    request-scoped session is not shared across tasks (SKRG-05).
    All exceptions are caught and logged -- seeding failures are non-fatal.

    Args:
        workspace_id: Workspace to seed plugins into.
    """
    try:
        async with get_db_session() as bg_session:
            from pilot_space.application.services.workspace_plugin.seed_plugins_service import (
                SeedPluginsService,
            )

            await SeedPluginsService(db_session=bg_session).seed_workspace(
                workspace_id=workspace_id,
            )
    except Exception:
        logger.exception(
            "seed_workspace_background_failed",
            workspace_id=str(workspace_id),
        )


__all__ = ["router"]
