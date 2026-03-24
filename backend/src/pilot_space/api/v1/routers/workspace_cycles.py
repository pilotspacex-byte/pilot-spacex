"""Workspace-scoped Cycles API router.

Provides nested routes for cycles under workspaces.
POST /workspaces/{workspace_id}/cycles
GET /workspaces/{workspace_id}/cycles
GET /workspaces/{workspace_id}/cycles/{cycle_id}

Supports both UUID and slug for workspace identification.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Path, Query, status

from pilot_space.api.v1.dependencies import (
    CreateCycleServiceDep,
    CycleRepositoryDep,
    WorkspaceRepositoryDep,
)
from pilot_space.api.v1.schemas.cycle import (
    CycleCreateRequest,
    CycleListResponse,
    CycleResponse,
)
from pilot_space.dependencies import DbSession, SyncedUserId
from pilot_space.infrastructure.database.models import CycleStatus
from pilot_space.infrastructure.database.models.workspace import Workspace
from pilot_space.infrastructure.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


# ============================================================================
# Type Aliases
# ============================================================================

WorkspaceIdOrSlug = Annotated[str, Path(description="Workspace ID (UUID) or slug")]


# ============================================================================
# Helpers
# ============================================================================


def _is_valid_uuid(value: str) -> bool:
    """Check if a string is a valid UUID."""
    try:
        UUID(value)
        return True
    except ValueError:
        return False


async def _resolve_workspace(
    workspace_id_or_slug: str,
    workspace_repo: WorkspaceRepositoryDep,
) -> Workspace:
    """Resolve workspace by UUID or slug."""
    if _is_valid_uuid(workspace_id_or_slug):
        workspace = await workspace_repo.get_by_id(UUID(workspace_id_or_slug))
    else:
        workspace = await workspace_repo.get_by_slug(workspace_id_or_slug)

    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )
    return workspace


# ============================================================================
# Endpoints
# ============================================================================


@router.post(
    "/{workspace_id}/cycles",
    response_model=CycleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a cycle in workspace",
    tags=["workspace-cycles"],
)
async def create_workspace_cycle(
    workspace_id: WorkspaceIdOrSlug,
    request: CycleCreateRequest,
    current_user_id: SyncedUserId,
    session: DbSession,
    workspace_repo: WorkspaceRepositoryDep,
    create_service: CreateCycleServiceDep,
) -> CycleResponse:
    """Create a new cycle (sprint) in the workspace."""
    from pilot_space.application.services.cycle import CreateCyclePayload

    workspace = await _resolve_workspace(workspace_id, workspace_repo)

    payload = CreateCyclePayload(
        workspace_id=workspace.id,
        project_id=request.project_id,
        name=request.name,
        description=request.description,
        start_date=request.start_date,
        end_date=request.end_date,
        owned_by_id=request.owned_by_id or current_user_id,
        status=request.status,
    )

    result = await create_service.execute(payload)

    logger.info(
        "Cycle created",
        extra={"cycle_id": str(result.cycle.id), "workspace_id": str(workspace.id)},
    )

    return CycleResponse.from_cycle(result.cycle)


@router.get(
    "/{workspace_id}/cycles",
    response_model=CycleListResponse,
    summary="List cycles in workspace",
)
async def list_workspace_cycles(
    workspace_id: WorkspaceIdOrSlug,
    current_user_id: SyncedUserId,
    workspace_repo: WorkspaceRepositoryDep,
    cycle_repo: CycleRepositoryDep,
    session: DbSession,
    project_id: Annotated[UUID, Query(alias="project_id", description="Project ID")],
    status_filter: Annotated[CycleStatus | None, Query(alias="status")] = None,
    search: str | None = None,
    cursor: str | None = None,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=100)] = 20,
    sort_by: str = "sequence",
    sort_order: Annotated[str, Query(pattern="^(asc|desc)$")] = "desc",
    include_metrics: bool = False,
) -> CycleListResponse:
    """List cycles for a project in a workspace."""
    from pilot_space.application.services.cycle import GetCycleService, ListCyclesPayload

    workspace = await _resolve_workspace(workspace_id, workspace_repo)

    get_service = GetCycleService(cycle_repository=cycle_repo)

    payload = ListCyclesPayload(
        workspace_id=workspace.id,
        project_id=project_id,
        status=status_filter,
        search_term=search,
        cursor=cursor,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
        include_metrics=include_metrics,
    )

    result = await get_service.list_cycles(payload)

    return CycleListResponse(
        items=[
            CycleResponse.from_cycle(
                c,
                metrics=result.metrics.get(str(c.id)),
            )
            for c in result.items
        ],
        total=result.total,
        next_cursor=result.next_cursor,
        prev_cursor=result.prev_cursor,
        has_next=result.has_next,
        has_prev=result.has_prev,
        page_size=result.page_size,
    )


@router.get(
    "/{workspace_id}/cycles/active",
    response_model=CycleResponse | None,
    summary="Get active cycle in workspace",
)
async def get_workspace_active_cycle(
    workspace_id: WorkspaceIdOrSlug,
    current_user_id: SyncedUserId,
    workspace_repo: WorkspaceRepositoryDep,
    cycle_repo: CycleRepositoryDep,
    session: DbSession,
    project_id: Annotated[UUID, Query(description="Project ID")],
    include_metrics: bool = True,
) -> CycleResponse | None:
    """Get the currently active cycle for a project in a workspace."""
    from pilot_space.application.services.cycle import GetCycleService

    await _resolve_workspace(workspace_id, workspace_repo)

    get_service = GetCycleService(cycle_repository=cycle_repo)

    result = await get_service.get_active_cycle(
        project_id,
        include_metrics=include_metrics,
    )

    if not result.found:
        return None

    return CycleResponse.from_cycle(result.cycle, metrics=result.metrics)


@router.get(
    "/{workspace_id}/cycles/{cycle_id}",
    response_model=CycleResponse,
    summary="Get a cycle in workspace",
)
async def get_workspace_cycle(
    workspace_id: WorkspaceIdOrSlug,
    cycle_id: Annotated[UUID, Path(description="Cycle ID")],
    current_user_id: SyncedUserId,
    workspace_repo: WorkspaceRepositoryDep,
    cycle_repo: CycleRepositoryDep,
    session: DbSession,
    include_metrics: bool = True,
) -> CycleResponse:
    """Get a specific cycle by ID in a workspace."""
    from pilot_space.application.services.cycle import GetCyclePayload, GetCycleService

    workspace = await _resolve_workspace(workspace_id, workspace_repo)

    get_service = GetCycleService(cycle_repository=cycle_repo)

    payload = GetCyclePayload(
        cycle_id=cycle_id,
        include_metrics=include_metrics,
    )

    result = await get_service.execute(payload)

    if not result.found or not result.cycle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cycle not found: {cycle_id}",
        )

    cycle = result.cycle
    if cycle.workspace_id != workspace.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cycle not found: {cycle_id}",
        )

    return CycleResponse.from_cycle(cycle, metrics=result.metrics)


__all__ = ["router"]
