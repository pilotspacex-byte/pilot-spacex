"""Cycles API router.

T163: Create Cycles CRUD and management endpoints.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from pilot_space.api.v1.schemas.cycle import (
    AddIssueToCycleRequest,
    BulkAddIssuesToCycleRequest,
    CycleCreateRequest,
    CycleListResponse,
    CycleResponse,
    CycleUpdateRequest,
    RolloverCycleRequest,
    RolloverCycleResponse,
)
from pilot_space.api.v1.schemas.issue import IssueBriefResponse
from pilot_space.dependencies import (
    get_current_user,
    get_current_workspace_id,
    get_session,
)
from pilot_space.infrastructure.database.models import CycleStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cycles", tags=["cycles"])


# ============================================================================
# Dependency Injection
# ============================================================================


async def get_create_cycle_service(
    session: Annotated[..., Depends(get_session)],
) -> CreateCycleService:
    """Get CreateCycleService instance."""
    from pilot_space.application.services.cycle import CreateCycleService
    from pilot_space.infrastructure.database.repositories import CycleRepository

    return CreateCycleService(
        session=session,
        cycle_repository=CycleRepository(session),
    )


async def get_get_cycle_service(
    session: Annotated[..., Depends(get_session)],
) -> GetCycleService:
    """Get GetCycleService instance."""
    from pilot_space.application.services.cycle import GetCycleService
    from pilot_space.infrastructure.database.repositories import CycleRepository

    return GetCycleService(
        cycle_repository=CycleRepository(session),
    )


async def get_update_cycle_service(
    session: Annotated[..., Depends(get_session)],
) -> UpdateCycleService:
    """Get UpdateCycleService instance."""
    from pilot_space.application.services.cycle import UpdateCycleService
    from pilot_space.infrastructure.database.repositories import CycleRepository

    return UpdateCycleService(
        session=session,
        cycle_repository=CycleRepository(session),
    )


async def get_add_issue_service(
    session: Annotated[..., Depends(get_session)],
) -> AddIssueToCycleService:
    """Get AddIssueToCycleService instance."""
    from pilot_space.application.services.cycle import AddIssueToCycleService
    from pilot_space.infrastructure.database.repositories import (
        ActivityRepository,
        CycleRepository,
        IssueRepository,
    )

    return AddIssueToCycleService(
        session=session,
        cycle_repository=CycleRepository(session),
        issue_repository=IssueRepository(session),
        activity_repository=ActivityRepository(session),
    )


async def get_rollover_service(
    session: Annotated[..., Depends(get_session)],
) -> RolloverCycleService:
    """Get RolloverCycleService instance."""
    from pilot_space.application.services.cycle import RolloverCycleService
    from pilot_space.infrastructure.database.repositories import (
        ActivityRepository,
        CycleRepository,
        IssueRepository,
    )

    return RolloverCycleService(
        session=session,
        cycle_repository=CycleRepository(session),
        issue_repository=IssueRepository(session),
        activity_repository=ActivityRepository(session),
    )


# Type imports
if TYPE_CHECKING:
    from pilot_space.application.services.cycle import (
        AddIssueToCycleService,
        CreateCycleService,
        GetCycleService,
        RolloverCycleService,
        UpdateCycleService,
    )


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
    workspace_id: Annotated[UUID, Depends(get_current_workspace_id)],
    user_id: Annotated[UUID, Depends(get_current_user)],
    create_service: Annotated[..., Depends(get_create_cycle_service)],
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
    workspace_id: Annotated[UUID, Depends(get_current_workspace_id)],
    get_service: Annotated[..., Depends(get_get_cycle_service)],
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
    workspace_id: Annotated[UUID, Depends(get_current_workspace_id)],
    get_service: Annotated[..., Depends(get_get_cycle_service)],
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
    "/{cycle_id}",
    response_model=CycleResponse,
    summary="Get a cycle",
)
async def get_cycle(
    cycle_id: UUID,
    get_service: Annotated[..., Depends(get_get_cycle_service)],
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
    user_id: Annotated[UUID, Depends(get_current_user)],
    update_service: Annotated[..., Depends(get_update_cycle_service)],
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
    session: Annotated[..., Depends(get_session)],
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
    workspace_id: Annotated[UUID, Depends(get_current_workspace_id)],
    user_id: Annotated[UUID, Depends(get_current_user)],
    add_service: Annotated[..., Depends(get_add_issue_service)],
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
    workspace_id: Annotated[UUID, Depends(get_current_workspace_id)],
    user_id: Annotated[UUID, Depends(get_current_user)],
    add_service: Annotated[..., Depends(get_add_issue_service)],
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
    workspace_id: Annotated[UUID, Depends(get_current_workspace_id)],
    user_id: Annotated[UUID, Depends(get_current_user)],
    add_service: Annotated[..., Depends(get_add_issue_service)],
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
    workspace_id: Annotated[UUID, Depends(get_current_workspace_id)],
    user_id: Annotated[UUID, Depends(get_current_user)],
    rollover_service: Annotated[..., Depends(get_rollover_service)],
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
                state=i.state,
                assignee=i.assignee,
            )
            for i in result.rolled_over_issues
        ],
        skipped_count=len(result.skipped_issues),
        total_rolled_over=result.total_rolled_over,
    )


__all__ = ["router"]
