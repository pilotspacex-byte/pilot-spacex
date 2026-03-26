"""PM Block API — Insight CRUD and sub-router aggregation.

T-249: PMBlockInsight CRUD (list / dismiss / batch-dismiss)
T-252: Refresh insights

Sub-routers included here:
- pm_sprint_board  (T-231, T-233)
- pm_dependency_graph (T-237)
- pm_capacity (T-242)
- pm_release_notes (T-244)

Feature 017: Note Versioning / PM Block Engine — Phase 2b-2e

Thin router shell -- all business logic delegated to PMBlockInsightService.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, status

from pilot_space.api.v1.dependencies import PMBlockInsightServiceDep, WorkspaceRepositoryDep
from pilot_space.api.v1.routers.pm_capacity import router as pm_capacity_router
from pilot_space.api.v1.routers.pm_dependency_graph import router as pm_dependency_graph_router
from pilot_space.api.v1.routers.pm_release_notes import router as pm_release_notes_router
from pilot_space.api.v1.routers.pm_sprint_board import router as pm_sprint_board_router
from pilot_space.api.v1.schemas.pm_blocks import PMBlockInsightResponse, RefreshInsightsRequest
from pilot_space.dependencies.auth import CurrentUserId, SessionDep, require_workspace_member
from pilot_space.domain.exceptions import NotFoundError
from pilot_space.infrastructure.database.models.pm_block_insight import (
    PMBlockInsight as PMBlockInsightModel,
)

router = APIRouter(prefix="/pm-blocks", tags=["pm-blocks"])

# Include sub-routers so main.py only needs to register `pm_blocks_router`
router.include_router(pm_sprint_board_router)
router.include_router(pm_dependency_graph_router)
router.include_router(pm_capacity_router)
router.include_router(pm_release_notes_router)


# -- Helpers -------------------------------------------------------------------


def _to_insight_response(i: PMBlockInsightModel) -> PMBlockInsightResponse:
    return PMBlockInsightResponse(
        id=i.id,
        workspace_id=i.workspace_id,
        block_id=i.block_id,
        block_type=i.block_type,
        insight_type=i.insight_type,
        severity=i.severity,
        title=i.title,
        analysis=i.analysis,
        references=i.references or [],
        suggested_actions=i.suggested_actions or [],
        confidence=i.confidence,
        dismissed=i.dismissed,
    )


# -- PM Block Insights Endpoints (T-249) --------------------------------------


@router.get(
    "/workspaces/{workspace_id}/pm-block-insights",
    response_model=list[PMBlockInsightResponse],
    summary="List AI insights for a PM block",
)
async def list_pm_block_insights(
    workspace_id: Annotated[UUID, Path()],
    session: SessionDep,
    service: PMBlockInsightServiceDep,
    block_id: Annotated[str, Query(description="TipTap block ID")],
    current_user_id: CurrentUserId,
    _: Annotated[UUID, Depends(require_workspace_member)],
    include_dismissed: Annotated[bool, Query()] = False,
) -> list[PMBlockInsightResponse]:
    """Return AI-generated insights for a PM block (FR-056)."""
    insights = await service.list_blocks(
        block_id=block_id,
        workspace_id=workspace_id,
        include_dismissed=include_dismissed,
    )
    return [_to_insight_response(i) for i in insights]


@router.post(
    "/workspaces/{workspace_id}/pm-block-insights/{insight_id}/dismiss",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Dismiss a PM block insight",
)
async def dismiss_pm_block_insight(
    workspace_id: Annotated[UUID, Path()],
    insight_id: Annotated[UUID, Path()],
    session: SessionDep,
    service: PMBlockInsightServiceDep,
    current_user_id: CurrentUserId,
    _: Annotated[UUID, Depends(require_workspace_member)],
) -> None:
    """Dismiss a single insight (FR-059)."""
    await service.dismiss(insight_id=insight_id, workspace_id=workspace_id)


@router.post(
    "/workspaces/{workspace_id}/pm-block-insights/dismiss-all",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Dismiss all insights for a block",
)
async def dismiss_all_pm_block_insights(
    workspace_id: Annotated[UUID, Path()],
    session: SessionDep,
    service: PMBlockInsightServiceDep,
    block_id: Annotated[str, Query(description="TipTap block ID")],
    current_user_id: CurrentUserId,
    _: Annotated[UUID, Depends(require_workspace_member)],
) -> None:
    """Batch-dismiss all active insights for a block (FR-059)."""
    await service.batch_dismiss(block_id=block_id, workspace_id=workspace_id)


# -- Refresh Insights Endpoint (T-252) ----------------------------------------


@router.post(
    "/workspaces/{workspace_id}/blocks/{block_id}/refresh-insights",
    response_model=list[PMBlockInsightResponse],
    summary="Refresh AI insights for a PM block",
)
async def refresh_pm_block_insights(
    workspace_id: Annotated[UUID, Path()],
    block_id: Annotated[str, Path()],
    body: RefreshInsightsRequest,
    session: SessionDep,
    service: PMBlockInsightServiceDep,
    workspace_repo: WorkspaceRepositoryDep,
    current_user_id: CurrentUserId,
    _: Annotated[UUID, Depends(require_workspace_member)],
) -> list[PMBlockInsightResponse]:
    """Generate fresh AI insights for a PM block (T-252).

    Debounces: returns cached insights if newest was created within 30s.
    """
    workspace = await workspace_repo.get_by_id(workspace_id)
    if not workspace:
        raise NotFoundError("Workspace not found")

    insights = await service.refresh_insights_debounced(
        block_id=block_id,
        block_type_str=body.block_type,
        workspace_id=workspace_id,
        data=body.data,
    )
    return [_to_insight_response(i) for i in insights]
