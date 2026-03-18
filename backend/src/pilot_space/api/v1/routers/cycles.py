"""Cycles API router.

T163: Create Cycles CRUD and management endpoints.
"""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from pilot_space.api.v1.dependencies import (
    AddIssueToCycleServiceDep,
    CreateCycleServiceDep,
    GetCycleServiceDep,
    RolloverCycleServiceDep,
    UpdateCycleServiceDep,
)
from pilot_space.api.v1.schemas.cycle import (
    AddIssueToCycleRequest,
    BulkAddIssuesToCycleRequest,
    CycleCreateRequest,
    CycleListResponse,
    CycleResponse,
    CycleUpdateRequest,
    RolloverCycleRequest,
    RolloverCycleResponse,
    VelocityChartResponse,
    VelocityDataPoint,
)
from pilot_space.api.v1.schemas.issue import (
    IssueBriefResponse,
    StateBriefSchema,
    UserBriefSchema,
)
from pilot_space.dependencies import get_current_user_id, get_current_workspace_id
from pilot_space.dependencies.auth import SessionDep
from pilot_space.infrastructure.database.models import CycleStatus
from pilot_space.infrastructure.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/cycles", tags=["cycles"])


# ============================================================================
# Cycle CRUD Endpoints
# ============================================================================


@router.post(
    "",
    response_model=CycleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a cycle",
)
async def create_cycle(
    request: CycleCreateRequest,
    session: SessionDep,
    workspace_id: Annotated[UUID, Depends(get_current_workspace_id)],
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    create_service: CreateCycleServiceDep,
) -> CycleResponse:
    """Create a new cycle (sprint).

    Args:
        request: Cycle creation request.
        workspace_id: Current workspace.
        user_id: Current user.
        create_service: Cycle creation service.

    Returns:
        Created cycle.
    """
    from pilot_space.application.services.cycle import CreateCyclePayload

    payload = CreateCyclePayload(
        workspace_id=workspace_id,
        project_id=request.project_id,
        name=request.name,
        description=request.description,
        start_date=request.start_date,
        end_date=request.end_date,
        owned_by_id=request.owned_by_id or user_id,
        status=request.status,
    )

    try:
        result = await create_service.execute(payload)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    return CycleResponse.from_cycle(result.cycle)


@router.get(
    "",
    response_model=CycleListResponse,
    summary="List cycles",
)
async def list_cycles(
    session: SessionDep,
    workspace_id: Annotated[UUID, Depends(get_current_workspace_id)],
    get_service: GetCycleServiceDep,
    project_id: UUID,
    status_filter: Annotated[CycleStatus | None, Query(alias="status")] = None,
    search: str | None = None,
    cursor: str | None = None,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    sort_by: str = "sequence",
    sort_order: Annotated[str, Query(pattern="^(asc|desc)$")] = "desc",
    include_metrics: bool = False,
) -> CycleListResponse:
    """List cycles for a project with pagination.

    Args:
        workspace_id: Current workspace.
        get_service: Cycle get service.
        project_id: Project filter (required).
        status_filter: Filter by status.
        search: Search term.
        cursor: Pagination cursor.
        page_size: Items per page.
        sort_by: Sort column.
        sort_order: Sort direction.
        include_metrics: Whether to include metrics.

    Returns:
        Paginated cycle list.
    """
    from pilot_space.application.services.cycle import ListCyclesPayload

    payload = ListCyclesPayload(
        workspace_id=workspace_id,
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
    "/active",
    response_model=CycleResponse | None,
    summary="Get active cycle",
)
async def get_active_cycle(
    session: SessionDep,
    workspace_id: Annotated[UUID, Depends(get_current_workspace_id)],
    get_service: GetCycleServiceDep,
    project_id: UUID,
    include_metrics: bool = True,
) -> CycleResponse | None:
    """Get the currently active cycle for a project.

    Args:
        workspace_id: Current workspace.
        get_service: Cycle get service.
        project_id: Project ID.
        include_metrics: Whether to include metrics.

    Returns:
        Active cycle or None.
    """
    result = await get_service.get_active_cycle(
        project_id,
        include_metrics=include_metrics,
    )

    if not result.found:
        return None

    return CycleResponse.from_cycle(result.cycle, metrics=result.metrics)


@router.get(
    "/velocity",
    response_model=VelocityChartResponse,
    summary="Get velocity chart data",
)
async def get_velocity_chart(
    session: SessionDep,
    workspace_id: Annotated[UUID, Depends(get_current_workspace_id)],
    get_service: GetCycleServiceDep,
    project_id: UUID,
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
) -> VelocityChartResponse:
    """Get velocity chart data for a project.

    Returns velocity data points from completed cycles.

    Args:
        workspace_id: Current workspace.
        get_service: Cycle get service.
        project_id: Project ID.
        limit: Maximum number of cycles to include.

    Returns:
        Velocity chart data with data points and average.
    """
    result = await get_service.get_velocity_chart(
        project_id,
        workspace_id,
        limit=limit,
    )

    return VelocityChartResponse(
        project_id=result.project_id,
        data_points=[
            VelocityDataPoint.model_validate(dp, from_attributes=True) for dp in result.data_points
        ],
        average_velocity=result.average_velocity,
    )


@router.get(
    "/{cycle_id}",
    response_model=CycleResponse,
    summary="Get a cycle",
)
async def get_cycle(
    cycle_id: UUID,
    session: SessionDep,
    get_service: GetCycleServiceDep,
    include_metrics: bool = True,
) -> CycleResponse:
    """Get a cycle by ID.

    Args:
        cycle_id: Cycle UUID.
        get_service: Cycle get service.
        include_metrics: Whether to include metrics.

    Returns:
        Cycle details.

    Raises:
        HTTPException: If cycle not found.
    """
    from pilot_space.application.services.cycle import GetCyclePayload

    payload = GetCyclePayload(
        cycle_id=cycle_id,
        include_metrics=include_metrics,
    )

    result = await get_service.execute(payload)

    if not result.found:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cycle not found: {cycle_id}",
        )

    return CycleResponse.from_cycle(result.cycle, metrics=result.metrics)


@router.patch(
    "/{cycle_id}",
    response_model=CycleResponse,
    summary="Update a cycle",
)
async def update_cycle(
    cycle_id: UUID,
    request: CycleUpdateRequest,
    session: SessionDep,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    update_service: UpdateCycleServiceDep,
) -> CycleResponse:
    """Update a cycle.

    Args:
        cycle_id: Cycle UUID.
        request: Update request.
        user_id: Current user.
        update_service: Cycle update service.

    Returns:
        Updated cycle.

    Raises:
        HTTPException: If cycle not found or validation fails.
    """
    from pilot_space.application.services.cycle.update_cycle_service import (
        UNCHANGED,
        UpdateCyclePayload,
    )

    # Build payload with explicit handling of clear flags
    payload = UpdateCyclePayload(
        cycle_id=cycle_id,
        actor_id=user_id,
        name=request.name if request.name is not None else UNCHANGED,
        description=(
            None
            if request.clear_description
            else (request.description if request.description is not None else UNCHANGED)
        ),
        start_date=(
            None
            if request.clear_start_date
            else (request.start_date if request.start_date is not None else UNCHANGED)
        ),
        end_date=(
            None
            if request.clear_end_date
            else (request.end_date if request.end_date is not None else UNCHANGED)
        ),
        status=request.status if request.status is not None else UNCHANGED,
        owned_by_id=(
            None
            if request.clear_owner
            else (request.owned_by_id if request.owned_by_id is not None else UNCHANGED)
        ),
    )

    try:
        result = await update_service.execute(payload)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    return CycleResponse.from_cycle(result.cycle)


@router.delete(
    "/{cycle_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a cycle",
)
async def delete_cycle(
    cycle_id: UUID,
    session: SessionDep,
) -> None:
    """Soft delete a cycle.

    Args:
        cycle_id: Cycle UUID.
        session: Database session.
    """
    from pilot_space.infrastructure.database.repositories import CycleRepository

    repo = CycleRepository(session)
    cycle = await repo.get_by_id(cycle_id)

    if not cycle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cycle not found: {cycle_id}",
        )

    await repo.delete(cycle)
    await session.commit()


# ============================================================================
# Cycle Issue Management Endpoints
# ============================================================================


@router.post(
    "/{cycle_id}/issues",
    response_model=dict[str, Any],
    status_code=status.HTTP_201_CREATED,
    summary="Add issue to cycle",
)
async def add_issue_to_cycle(
    cycle_id: UUID,
    request: AddIssueToCycleRequest,
    session: SessionDep,
    workspace_id: Annotated[UUID, Depends(get_current_workspace_id)],
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    add_service: AddIssueToCycleServiceDep,
) -> dict[str, Any]:
    """Add an issue to a cycle.

    Args:
        cycle_id: Cycle UUID.
        request: Add issue request.
        workspace_id: Current workspace.
        user_id: Current user.
        add_service: Add issue service.

    Returns:
        Success status.
    """
    from pilot_space.application.services.cycle import AddIssueToCyclePayload

    payload = AddIssueToCyclePayload(
        workspace_id=workspace_id,
        cycle_id=cycle_id,
        issue_id=request.issue_id,
        actor_id=user_id,
    )

    try:
        result = await add_service.add_issue(payload)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    return {"added": result.added, "issue_id": str(request.issue_id)}


@router.post(
    "/{cycle_id}/issues/bulk",
    response_model=dict[str, Any],
    status_code=status.HTTP_201_CREATED,
    summary="Add multiple issues to cycle",
)
async def bulk_add_issues_to_cycle(
    cycle_id: UUID,
    request: BulkAddIssuesToCycleRequest,
    session: SessionDep,
    workspace_id: Annotated[UUID, Depends(get_current_workspace_id)],
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    add_service: AddIssueToCycleServiceDep,
) -> dict[str, Any]:
    """Add multiple issues to a cycle.

    Args:
        cycle_id: Cycle UUID.
        request: Bulk add request.
        workspace_id: Current workspace.
        user_id: Current user.
        add_service: Add issue service.

    Returns:
        Success status with counts.
    """
    results = await add_service.bulk_add_issues(
        workspace_id=workspace_id,
        cycle_id=cycle_id,
        issue_ids=request.issue_ids,
        actor_id=user_id,
    )

    added_count = sum(1 for r in results if r.added)

    return {
        "added_count": added_count,
        "total_requested": len(request.issue_ids),
    }


@router.delete(
    "/{cycle_id}/issues/{issue_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove issue from cycle",
)
async def remove_issue_from_cycle(
    cycle_id: UUID,
    issue_id: UUID,
    session: SessionDep,
    workspace_id: Annotated[UUID, Depends(get_current_workspace_id)],
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    add_service: AddIssueToCycleServiceDep,
) -> None:
    """Remove an issue from a cycle.

    Args:
        cycle_id: Cycle UUID.
        issue_id: Issue UUID.
        workspace_id: Current workspace.
        user_id: Current user.
        add_service: Add issue service.
    """
    from pilot_space.application.services.cycle import RemoveIssueFromCyclePayload

    payload = RemoveIssueFromCyclePayload(
        workspace_id=workspace_id,
        cycle_id=cycle_id,
        issue_id=issue_id,
        actor_id=user_id,
    )

    try:
        await add_service.remove_issue(payload)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


# ============================================================================
# Cycle Rollover Endpoint
# ============================================================================


@router.post(
    "/{cycle_id}/rollover",
    response_model=RolloverCycleResponse,
    summary="Rollover cycle",
)
async def rollover_cycle(
    cycle_id: UUID,
    request: RolloverCycleRequest,
    session: SessionDep,
    workspace_id: Annotated[UUID, Depends(get_current_workspace_id)],
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    rollover_service: RolloverCycleServiceDep,
) -> RolloverCycleResponse:
    """Rollover incomplete issues from one cycle to another.

    Args:
        cycle_id: Source cycle UUID.
        request: Rollover request.
        workspace_id: Current workspace.
        user_id: Current user.
        rollover_service: Rollover service.

    Returns:
        Rollover result with issues moved.
    """
    from pilot_space.application.services.cycle import RolloverCyclePayload

    payload = RolloverCyclePayload(
        workspace_id=workspace_id,
        source_cycle_id=cycle_id,
        target_cycle_id=request.target_cycle_id,
        actor_id=user_id,
        issue_ids=request.issue_ids,
        include_in_progress=request.include_in_progress,
        complete_source_cycle=request.complete_source_cycle,
    )

    try:
        result = await rollover_service.execute(payload)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    return RolloverCycleResponse(
        source_cycle=CycleResponse.from_cycle(result.source_cycle),
        target_cycle=CycleResponse.from_cycle(result.target_cycle),
        rolled_over_issues=[
            IssueBriefResponse(
                id=i.id,
                identifier=i.identifier,
                name=i.name,
                priority=i.priority,
                state=StateBriefSchema.model_validate(i.state),
                assignee=UserBriefSchema.model_validate(i.assignee) if i.assignee else None,
            )
            for i in result.rolled_over_issues
        ],
        skipped_count=len(result.skipped_issues),
        total_rolled_over=result.total_rolled_over,
    )


__all__ = ["router"]
