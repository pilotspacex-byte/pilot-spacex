"""PM Block API — Insight CRUD and sub-router aggregation.

T-249: PMBlockInsight CRUD (list / dismiss / batch-dismiss)
T-252: Refresh insights

Sub-routers included here:
- pm_sprint_board  (T-231, T-233)
- pm_dependency_graph (T-237)
- pm_capacity (T-242)
- pm_release_notes (T-244)

Feature 017: Note Versioning / PM Block Engine — Phase 2b-2e
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from pydantic import BaseModel, ConfigDict, Field

from pilot_space.api.v1.dependencies import WorkspaceRepositoryDep
from pilot_space.api.v1.routers.pm_capacity import router as pm_capacity_router
from pilot_space.api.v1.routers.pm_dependency_graph import router as pm_dependency_graph_router
from pilot_space.api.v1.routers.pm_release_notes import router as pm_release_notes_router
from pilot_space.api.v1.routers.pm_sprint_board import router as pm_sprint_board_router
from pilot_space.dependencies.auth import CurrentUserId, SessionDep, require_workspace_member
from pilot_space.domain.exceptions import ValidationError
from pilot_space.domain.pm_block_insight import InsightSeverity, PMBlockType
from pilot_space.infrastructure.database.models.pm_block_insight import (
    PMBlockInsight as PMBlockInsightModel,
)
from pilot_space.infrastructure.database.repositories.pm_block_insight_repository import (
    PMBlockInsightRepository,
)
from pilot_space.infrastructure.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/pm-blocks", tags=["pm-blocks"])

# Include sub-routers so main.py only needs to register `pm_blocks_router`
router.include_router(pm_sprint_board_router)
router.include_router(pm_dependency_graph_router)
router.include_router(pm_capacity_router)
router.include_router(pm_release_notes_router)


# ── Response Schemas ──────────────────────────────────────────────────────────


class PMBlockInsightResponse(BaseModel):
    """Response schema for a single PMBlockInsight."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    block_id: str
    block_type: PMBlockType
    insight_type: str
    severity: InsightSeverity
    title: str
    analysis: str
    references: list[str]
    suggested_actions: list[str]
    confidence: float
    dismissed: bool


class RefreshInsightsRequest(BaseModel):
    block_type: str = Field(..., description="PM block type enum value")
    data: dict[str, object] = Field(default_factory=dict)


# ── Helpers ───────────────────────────────────────────────────────────────────


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


# ── PM Block Insights Endpoints (T-249) ──────────────────────────────────────


@router.get(
    "/workspaces/{workspace_id}/pm-block-insights",
    response_model=list[PMBlockInsightResponse],
    summary="List AI insights for a PM block",
)
async def list_pm_block_insights(
    workspace_id: Annotated[UUID, Path()],
    session: SessionDep,
    workspace_repo: WorkspaceRepositoryDep,
    block_id: Annotated[str, Query(description="TipTap block ID")],
    current_user_id: CurrentUserId,
    _: Annotated[UUID, Depends(require_workspace_member)],
    include_dismissed: Annotated[bool, Query()] = False,
) -> list[PMBlockInsightResponse]:
    """Return AI-generated insights for a PM block (FR-056)."""
    repo = PMBlockInsightRepository(session)
    insights = await repo.list_by_block(
        block_id=block_id,
        workspace_id=workspace_id,
        include_dismissed=include_dismissed,
    )
    return [
        PMBlockInsightResponse(
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
        for i in insights
    ]


@router.post(
    "/workspaces/{workspace_id}/pm-block-insights/{insight_id}/dismiss",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Dismiss a PM block insight",
)
async def dismiss_pm_block_insight(
    workspace_id: Annotated[UUID, Path()],
    insight_id: Annotated[UUID, Path()],
    session: SessionDep,
    current_user_id: CurrentUserId,
    _: Annotated[UUID, Depends(require_workspace_member)],
) -> None:
    """Dismiss a single insight (FR-059)."""
    repo = PMBlockInsightRepository(session)
    insight = await repo.get_by_id(insight_id)
    if not insight or insight.workspace_id != workspace_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Insight not found")
    insight.dismissed = True
    await session.flush()
    await session.commit()


@router.post(
    "/workspaces/{workspace_id}/pm-block-insights/dismiss-all",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Dismiss all insights for a block",
)
async def dismiss_all_pm_block_insights(
    workspace_id: Annotated[UUID, Path()],
    session: SessionDep,
    block_id: Annotated[str, Query(description="TipTap block ID")],
    current_user_id: CurrentUserId,
    _: Annotated[UUID, Depends(require_workspace_member)],
) -> None:
    """Batch-dismiss all active insights for a block (FR-059)."""
    repo = PMBlockInsightRepository(session)
    await repo.batch_dismiss(block_id=block_id, workspace_id=workspace_id)
    await session.commit()


# ── Refresh Insights Endpoint (T-252) ────────────────────────────────────────


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
    workspace_repo: WorkspaceRepositoryDep,
    current_user_id: CurrentUserId,
    _: Annotated[UUID, Depends(require_workspace_member)],
) -> list[PMBlockInsightResponse]:
    """Generate fresh AI insights for a PM block (T-252).

    Debounces: returns cached insights if newest was created within 30s.
    """
    from pilot_space.application.services.pm_block_insight_service import PMBlockInsightService

    workspace = await workspace_repo.get_by_id(workspace_id)
    if not workspace:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")

    repo = PMBlockInsightRepository(session)
    existing = await repo.list_by_block(
        block_id=block_id, workspace_id=workspace_id, include_dismissed=True
    )
    if existing:
        newest = max(i.created_at for i in existing)
        if newest.tzinfo is None:
            newest = newest.replace(tzinfo=UTC)
        if datetime.now(UTC) - newest < timedelta(seconds=30):
            return [_to_insight_response(i) for i in existing]

    try:
        block_type_enum = PMBlockType(body.block_type)
    except ValueError as exc:
        raise ValidationError(f"Invalid block_type: {body.block_type}") from exc

    service = PMBlockInsightService(session=session, repository=repo)
    insights = await service.refresh_insights(
        block_id=block_id,
        block_type=block_type_enum,
        workspace_id=str(workspace_id),
        data=body.data,
    )
    return [_to_insight_response(i) for i in insights]
