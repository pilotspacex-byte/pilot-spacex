"""Batch run REST + SSE endpoints for sprint batch implementation.

Provides HTTP endpoints for the PM-facing batch run lifecycle:
- POST   /workspaces/{workspace_id}/batch-runs                         — Create + enqueue
- GET    /workspaces/{workspace_id}/batch-runs/{batch_run_id}          — Get status
- GET    /workspaces/{workspace_id}/batch-runs/preview/{cycle_id}      — DAG preview
- GET    /workspaces/{workspace_id}/batch-runs/{batch_run_id}/stream   — SSE via Redis pub/sub
- POST   /workspaces/{workspace_id}/batch-runs/{batch_run_id}/cancel   — Cancel batch
- POST   /workspaces/{workspace_id}/batch-runs/{batch_run_id}/issues/{issue_id}/cancel

SSE stream channel: ``batch_runs:{batch_run_id}`` (Redis pub/sub fan-out).

Phase 76 Plan 03 — sprint batch implementation API layer.
Design Decisions: DD-003 (approval/destructive actions), DD-066 (SSE streaming).
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Request, status
from fastapi.responses import StreamingResponse

from pilot_space.api.v1.dependencies import BatchRunServiceDep
from pilot_space.api.v1.schemas.base import BaseSchema
from pilot_space.api.v1.streaming import format_sse_event
from pilot_space.application.services.batch_run_service import CreateBatchRunPayload
from pilot_space.dependencies import DbSession, QueueClientDep, RedisDep
from pilot_space.dependencies.auth import CurrentUserId, require_workspace_member
from pilot_space.infrastructure.logging import get_logger
from pilot_space.infrastructure.queue.models import QueueName

logger = get_logger(__name__)

router = APIRouter(tags=["batch-runs"])

# ---------------------------------------------------------------------------
# Request / Response Schemas
# ---------------------------------------------------------------------------


class CreateBatchRunRequest(BaseSchema):
    """Request body for creating a batch run."""

    cycle_id: UUID


class BatchRunIssueResponse(BaseSchema):
    """Per-issue status within a batch run."""

    id: UUID
    issue_id: UUID
    status: str
    execution_order: int
    current_stage: str | None = None
    pr_url: str | None = None
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


class BatchRunResponse(BaseSchema):
    """Full batch run status response."""

    id: UUID
    cycle_id: UUID
    status: str
    total_issues: int
    completed_issues: int
    failed_issues: int
    started_at: datetime | None = None
    completed_at: datetime | None = None
    items: list[BatchRunIssueResponse]


class DAGIssuePreview(BaseSchema):
    """Single issue entry in a DAG preview."""

    id: str
    title: str


class DAGPreviewResponse(BaseSchema):
    """DAG execution plan preview — returned before creating a batch run."""

    issues: list[DAGIssuePreview]
    execution_order: dict[str, int]
    parallel_tracks: int
    cycle_issues: list[str]


class DashboardIssueStatus(BaseSchema):
    """Per-issue status with cost for dashboard display."""

    id: UUID
    issue_id: UUID
    issue_identifier: str | None = None
    issue_title: str | None = None
    status: str
    execution_order: int
    current_stage: str | None = None
    pr_url: str | None = None
    error_message: str | None = None
    cost_cents: int = 0
    started_at: datetime | None = None
    completed_at: datetime | None = None


class AttentionItemResponse(BaseSchema):
    """Single item requiring PM attention."""

    type: str  # "pr_ready" | "blocked" | "pending_approval"
    issue_id: UUID
    issue_identifier: str | None = None
    issue_title: str | None = None
    pr_url: str | None = None


class DashboardResponse(BaseSchema):
    """Aggregated dashboard data for a batch run."""

    # Progress (DSH-01)
    batch_run_id: UUID
    cycle_id: UUID
    status: str
    total_issues: int
    completed_issues: int
    failed_issues: int
    queued_issues: int
    running_issues: int
    completion_percent: float
    started_at: datetime | None = None
    completed_at: datetime | None = None
    # Per-issue statuses (DSH-02)
    issues: list[DashboardIssueStatus]
    # Attention feed (DSH-03)
    attention_items: list[AttentionItemResponse]
    attention_count: int
    # Cost (DSH-04)
    sprint_cost_cents: int
    monthly_cost_cents: int



# ---------------------------------------------------------------------------
# Type aliases for path parameters
# ---------------------------------------------------------------------------

WorkspaceIdPath = Annotated[UUID, Path(description="Workspace UUID")]
BatchRunIdPath = Annotated[UUID, Path(description="Batch run UUID")]
CycleIdPath = Annotated[UUID, Path(description="Cycle UUID")]
IssueIdPath = Annotated[UUID, Path(description="BatchRunIssue UUID to cancel")]

# Workspace membership guard — FastAPI injects workspace_id from path param
WorkspaceMemberId = Annotated[UUID, Depends(require_workspace_member)]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_batch_run_response(batch_run: object) -> BatchRunResponse:
    """Serialize a BatchRun ORM object to a BatchRunResponse."""
    return BatchRunResponse(
        id=batch_run.id,  # type: ignore[attr-defined]
        cycle_id=batch_run.cycle_id,  # type: ignore[attr-defined]
        status=batch_run.status.value,  # type: ignore[attr-defined]
        total_issues=batch_run.total_issues,  # type: ignore[attr-defined]
        completed_issues=batch_run.completed_issues,  # type: ignore[attr-defined]
        failed_issues=batch_run.failed_issues,  # type: ignore[attr-defined]
        started_at=batch_run.started_at,  # type: ignore[attr-defined]
        completed_at=batch_run.completed_at,  # type: ignore[attr-defined]
        items=[
            BatchRunIssueResponse(
                id=item.id,
                issue_id=item.issue_id,
                status=item.status.value,
                execution_order=item.execution_order,
                current_stage=item.current_stage,
                pr_url=item.pr_url,
                error_message=item.error_message,
                started_at=item.started_at,
                completed_at=item.completed_at,
            )
            for item in (batch_run.items or [])  # type: ignore[attr-defined]
        ],
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/workspaces/{workspace_id}/batch-runs",
    response_model=BatchRunResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a sprint batch run",
)
async def create_batch_run(
    workspace_id: WorkspaceIdPath,
    body: CreateBatchRunRequest,
    session: DbSession,
    service: BatchRunServiceDep,
    queue: QueueClientDep,
    current_user_id: CurrentUserId,
    _member: WorkspaceMemberId,
) -> BatchRunResponse:
    """Create a BatchRun for all issues in a sprint cycle.

    Resolves the issue dependency DAG via Kahn's topological sort, assigns
    execution_order, persists BatchRun + BatchRunIssue rows, then enqueues
    a trigger message on the ``batch_impl`` pgmq queue.
    """
    payload = CreateBatchRunPayload(
        workspace_id=workspace_id,
        cycle_id=body.cycle_id,
        triggered_by_id=current_user_id,
    )

    batch_run = await service.create_batch_run(payload)

    # Enqueue trigger message for BatchImplWorker (non-fatal if queue unavailable)
    if queue is not None:
        try:
            await queue.enqueue(
                QueueName.BATCH_IMPL,
                {
                    "batch_run_id": str(batch_run.id),
                    "workspace_id": str(workspace_id),
                    "actor_user_id": str(current_user_id),
                },
            )
            logger.info(
                "batch_run_enqueued",
                batch_run_id=str(batch_run.id),
                workspace_id=str(workspace_id),
            )
        except Exception:
            logger.exception(
                "batch_run_enqueue_failed",
                batch_run_id=str(batch_run.id),
            )
    else:
        logger.warning(
            "queue_not_configured_batch_run_trigger_skipped",
            batch_run_id=str(batch_run.id),
        )

    return _build_batch_run_response(batch_run)


@router.get(
    "/workspaces/{workspace_id}/batch-runs/{batch_run_id}",
    response_model=BatchRunResponse,
    summary="Get batch run status",
)
async def get_batch_run(
    workspace_id: WorkspaceIdPath,
    batch_run_id: BatchRunIdPath,
    session: DbSession,
    service: BatchRunServiceDep,
    _member: WorkspaceMemberId,
) -> BatchRunResponse:
    """Return current status of a batch run with all per-issue statuses."""
    from pilot_space.domain.exceptions import NotFoundError
    from pilot_space.infrastructure.database.repositories.batch_run_repository import (
        BatchRunRepository,
    )

    repo = BatchRunRepository(session)
    batch_run = await repo.get_by_id_with_items(batch_run_id)
    if batch_run is None:
        raise NotFoundError(f"BatchRun {batch_run_id} not found.")

    return _build_batch_run_response(batch_run)


@router.get(
    "/workspaces/{workspace_id}/batch-runs/preview/{cycle_id}",
    response_model=DAGPreviewResponse,
    summary="Preview DAG execution order without creating a batch run",
)
async def preview_dag(
    workspace_id: WorkspaceIdPath,
    cycle_id: CycleIdPath,
    session: DbSession,
    service: BatchRunServiceDep,
    _member: WorkspaceMemberId,
) -> DAGPreviewResponse:
    """Return the execution DAG for a cycle without creating a BatchRun.

    Used by the PilotSpaceAgent chat card to show the PM a dependency plan
    before they approve the batch dispatch.
    """
    result = await service.get_dag_preview(cycle_id, workspace_id)

    return DAGPreviewResponse(
        issues=[DAGIssuePreview(id=issue["id"], title=issue["title"]) for issue in result.issues],
        execution_order=result.execution_order,
        parallel_tracks=result.parallel_tracks,
        cycle_issues=result.cycle_issues,
    )


@router.get(
    "/workspaces/{workspace_id}/batch-runs/{batch_run_id}/stream",
    summary="Stream batch run status updates via SSE",
)
async def stream_batch_run(
    workspace_id: WorkspaceIdPath,
    batch_run_id: BatchRunIdPath,
    session: DbSession,
    redis: RedisDep,
    request: Request,
    _member: WorkspaceMemberId,
) -> StreamingResponse:
    """Subscribe to real-time SSE updates for a batch run.

    Uses Redis pub/sub on channel ``batch_runs:{batch_run_id}``. The
    BatchImplWorker publishes ``batch_status_update`` events as issues
    progress through queued → running → completed/failed.
    """
    channel = f"batch_runs:{batch_run_id}"

    async def _generator() -> object:
        # RedisClient.subscribe() returns an async pubsub object already subscribed
        pubsub = await redis.subscribe(channel)
        try:
            async for message in pubsub.listen():
                if await request.is_disconnected():
                    break
                if message.get("type") != "message":
                    continue
                try:
                    payload = json.loads(message["data"])
                except (json.JSONDecodeError, TypeError):
                    continue
                yield format_sse_event("batch_status_update", payload)
            yield format_sse_event("done", {"status": "complete"})
        except asyncio.CancelledError:
            raise
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.close()

    return StreamingResponse(
        _generator(),  # type: ignore[arg-type]
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post(
    "/workspaces/{workspace_id}/batch-runs/{batch_run_id}/cancel",
    response_model=BatchRunResponse,
    summary="Cancel an entire batch run",
)
async def cancel_batch_run(
    workspace_id: WorkspaceIdPath,
    batch_run_id: BatchRunIdPath,
    session: DbSession,
    service: BatchRunServiceDep,
    redis: RedisDep,
    _member: WorkspaceMemberId,
) -> BatchRunResponse:
    """Cancel a batch run: fails the parent and cancels all non-terminal issues.

    Publishes a ``batch_cancelled`` event to the Redis channel so connected
    SSE clients update their UI immediately.
    """
    batch_run = await service.cancel_batch_run(batch_run_id)

    # Publish cancel event so SSE subscribers see the update immediately
    channel = f"batch_runs:{batch_run_id}"
    try:
        await redis.publish(
            channel,
            json.dumps({"event": "batch_cancelled", "batch_run_id": str(batch_run_id)}),
        )
    except Exception:
        logger.exception("batch_cancel_publish_failed", batch_run_id=str(batch_run_id))

    return _build_batch_run_response(batch_run)


@router.post(
    "/workspaces/{workspace_id}/batch-runs/{batch_run_id}/issues/{issue_id}/cancel",
    status_code=status.HTTP_200_OK,
    summary="Cancel a single issue within a batch run",
)
async def cancel_batch_run_issue(
    workspace_id: WorkspaceIdPath,
    batch_run_id: BatchRunIdPath,
    issue_id: IssueIdPath,
    session: DbSession,
    service: BatchRunServiceDep,
    redis: RedisDep,
    _member: WorkspaceMemberId,
) -> dict[str, str]:
    """Cancel a single BatchRunIssue.

    Publishes an ``issue_cancelled`` event to the Redis channel so connected
    SSE clients can update the individual issue card in the UI.
    """
    await service.cancel_issue(issue_id)

    # Publish event so SSE stream reflects the cancellation immediately
    channel = f"batch_runs:{batch_run_id}"
    try:
        await redis.publish(
            channel,
            json.dumps(
                {
                    "event": "issue_cancelled",
                    "batch_run_id": str(batch_run_id),
                    "issue_id": str(issue_id),
                }
            ),
        )
    except Exception:
        logger.exception(
            "issue_cancel_publish_failed",
            batch_run_id=str(batch_run_id),
            issue_id=str(issue_id),
        )

    return {"status": "cancelled"}


@router.get(
    "/workspaces/{workspace_id}/batch-runs/{batch_run_id}/dashboard",
    response_model=DashboardResponse,
    summary="Get aggregated dashboard data for a batch run",
)
async def get_batch_run_dashboard(
    workspace_id: WorkspaceIdPath,
    batch_run_id: BatchRunIdPath,
    session: DbSession,
    _member: WorkspaceMemberId,
) -> DashboardResponse:
    """Return aggregated dashboard data for a sprint batch run.

    Returns a single response containing:
    - Progress stats (DSH-01): total, completed, failed, queued, running counts + percent
    - Per-issue statuses with cost (DSH-02): all items with identifier, title, cost_cents
    - Attention feed (DSH-03): PRs ready for review, blocked issues, pending approvals
    - Cost breakdown (DSH-04): per-issue cost_cents and sprint total
    """
    from pilot_space.domain.exceptions import NotFoundError
    from pilot_space.infrastructure.database.repositories.batch_run_repository import (
        BatchRunRepository,
    )

    repo = BatchRunRepository(session)
    batch_run = await repo.get_dashboard_data(batch_run_id)
    if batch_run is None:
        raise NotFoundError(f"BatchRun {batch_run_id} not found.")

    items = batch_run.items or []

    # --- Running status counts ---
    running_statuses = {"cloning", "implementing", "creating_pr", "running"}
    queued_statuses = {"queued", "pending"}

    queued_issues = sum(1 for item in items if item.status.value in queued_statuses)
    running_issues = sum(1 for item in items if item.status.value in running_statuses)

    # --- Completion percent ---
    total = batch_run.total_issues
    completed_count = batch_run.completed_issues
    completion_percent = round((completed_count / total) * 100, 1) if total > 0 else 0.0

    # --- Per-issue statuses with cost and identifiers ---
    issue_statuses = [
        DashboardIssueStatus(
            id=item.id,
            issue_id=item.issue_id,
            issue_identifier=item.issue.identifier if item.issue else None,
            issue_title=item.issue.name if item.issue else None,
            status=item.status.value,
            execution_order=item.execution_order,
            current_stage=item.current_stage,
            pr_url=item.pr_url,
            error_message=item.error_message,
            cost_cents=item.cost_cents,
            started_at=item.started_at,
            completed_at=item.completed_at,
        )
        for item in items
    ]

    # --- Attention feed ---
    attention_items: list[AttentionItemResponse] = []

    for item in items:
        issue_identifier = item.issue.identifier if item.issue else None
        issue_title = item.issue.name if item.issue else None

        # PRs ready for review: completed status with a PR URL
        if item.status.value == "completed" and item.pr_url:
            attention_items.append(
                AttentionItemResponse(
                    type="pr_ready",
                    issue_id=item.issue_id,
                    issue_identifier=issue_identifier,
                    issue_title=issue_title,
                    pr_url=item.pr_url,
                )
            )
        # Blocked: cancelled with dependency/blocked in error message
        elif item.status.value == "cancelled" and item.error_message and (
            "dependency" in item.error_message.lower()
            or "blocked" in item.error_message.lower()
        ):
            attention_items.append(
                AttentionItemResponse(
                    type="blocked",
                    issue_id=item.issue_id,
                    issue_identifier=issue_identifier,
                    issue_title=issue_title,
                    pr_url=None,
                )
            )
        # Pending approval: pending status (stuck waiting)
        elif item.status.value == "pending":
            attention_items.append(
                AttentionItemResponse(
                    type="pending_approval",
                    issue_id=item.issue_id,
                    issue_identifier=issue_identifier,
                    issue_title=issue_title,
                    pr_url=None,
                )
            )

    # --- Cost breakdown ---
    sprint_cost_cents = sum(item.cost_cents for item in items)
    # monthly_cost_cents: single-sprint view for now; future: aggregate across batch_runs in month
    monthly_cost_cents = sprint_cost_cents

    return DashboardResponse(
        batch_run_id=batch_run.id,
        cycle_id=batch_run.cycle_id,
        status=batch_run.status.value,
        total_issues=batch_run.total_issues,
        completed_issues=batch_run.completed_issues,
        failed_issues=batch_run.failed_issues,
        queued_issues=queued_issues,
        running_issues=running_issues,
        completion_percent=completion_percent,
        started_at=batch_run.started_at,
        completed_at=batch_run.completed_at,
        issues=issue_statuses,
        attention_items=attention_items,
        attention_count=len(attention_items),
        sprint_cost_cents=sprint_cost_cents,
        monthly_cost_cents=monthly_cost_cents,
    )


__all__ = ["router"]
