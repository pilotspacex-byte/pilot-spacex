"""BatchRunService — sprint batch implementation orchestration.

Provides Kahn's topological sort for issue dependency DAGs, batch run
creation with execution_order assignment, cancel cascade logic, and
a DAG preview operation for the PM approval workflow.

Phase 76 Plan 01 — sprint batch implementation foundation.
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from pilot_space.domain.exceptions import (
    BatchRunCycleDetectedError,
    BatchRunError,
    BatchRunNotFoundError,
)
from pilot_space.infrastructure.database.models.batch_run import BatchRun, BatchRunStatus
from pilot_space.infrastructure.database.models.batch_run_issue import (
    BatchRunIssue,
    BatchRunIssueStatus,
)
from pilot_space.infrastructure.database.models.issue import Issue
from pilot_space.infrastructure.database.models.issue_link import (
    IssueLink,
    IssueLinkType,
)
from pilot_space.infrastructure.database.repositories.batch_run_repository import (
    BatchRunRepository,
)


# ---------------------------------------------------------------------------
# Pure algorithm: Kahn's topological sort
# ---------------------------------------------------------------------------


def kahn_topological_sort(
    issue_ids: list[UUID],
    blocks_links: list[tuple[UUID, UUID]],
) -> tuple[dict[UUID, int], list[UUID]]:
    """Assign execution_order to issues via Kahn's topological sort.

    Interprets each tuple ``(a, b)`` in *blocks_links* as "issue *a* blocks
    issue *b*", meaning *b* must execute after *a*.

    Args:
        issue_ids: All issue IDs that form the graph vertices.
        blocks_links: Directed edges ``(blocker_id, blocked_id)`` where
            blocker must complete before blocked can start.

    Returns:
        A 2-tuple ``(execution_order_map, cycle_issues)`` where:
        - ``execution_order_map`` maps each issue UUID to its wave number
          (0-indexed; issues in the same wave can execute in parallel).
        - ``cycle_issues`` is a list of issue IDs involved in a cycle.
          Empty when the DAG is acyclic.

    Examples:
        Linear chain A → B → C:
            kahn_topological_sort([A, B, C], [(A, B), (B, C)])
            → ({A: 0, B: 1, C: 2}, [])

        Parallel tracks A → C, B → C:
            kahn_topological_sort([A, B, C], [(A, C), (B, C)])
            → ({A: 0, B: 0, C: 1}, [])

        No dependencies:
            kahn_topological_sort([A, B], [])
            → ({A: 0, B: 0}, [])

        Cycle A → B → A:
            kahn_topological_sort([A, B], [(A, B), (B, A)])
            → ({}, [A, B])
    """
    # Build adjacency structures (only for nodes present in issue_ids)
    issue_set = set(issue_ids)
    in_degree: dict[UUID, int] = {iid: 0 for iid in issue_ids}
    adjacency: dict[UUID, list[UUID]] = defaultdict(list)

    for blocker, blocked in blocks_links:
        # Skip edges where either endpoint is not in our issue set
        if blocker not in issue_set or blocked not in issue_set:
            continue
        adjacency[blocker].append(blocked)
        in_degree[blocked] += 1

    # Initialise queue with all zero-in-degree nodes (wave 0)
    queue: deque[UUID] = deque()
    execution_order: dict[UUID, int] = {}

    for iid in issue_ids:
        if in_degree[iid] == 0:
            queue.append(iid)
            execution_order[iid] = 0

    processed = 0
    while queue:
        current = queue.popleft()
        processed += 1
        current_wave = execution_order[current]

        for neighbor in adjacency.get(current, []):
            in_degree[neighbor] -= 1
            # Neighbor's wave is at least one after the latest blocker
            neighbor_wave = max(
                execution_order.get(neighbor, 0),
                current_wave + 1,
            )
            execution_order[neighbor] = neighbor_wave
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    # If not all nodes were processed, there is a cycle
    if processed < len(issue_ids):
        cycle_issues = [iid for iid in issue_ids if iid not in execution_order]
        return {}, cycle_issues

    return execution_order, []


# ---------------------------------------------------------------------------
# Service payload / result types
# ---------------------------------------------------------------------------


@dataclass
class CreateBatchRunPayload:
    """Input for BatchRunService.create_batch_run.

    Attributes:
        workspace_id: The workspace UUID (used for RLS / model field).
        cycle_id: The sprint cycle to batch-implement.
        triggered_by_id: UUID of the user who approved the batch run.
    """

    workspace_id: UUID
    cycle_id: UUID
    triggered_by_id: UUID


@dataclass
class DAGPreviewResult:
    """Output of BatchRunService.get_dag_preview.

    Attributes:
        issues: List of (issue_id, title) tuples in the cycle.
        execution_order: Map of issue_id → wave number.
        parallel_tracks: Number of distinct wave numbers (parallelism degree).
        cycle_issues: Issue IDs involved in a dependency cycle, if any.
    """

    issues: list[dict[str, str]] = field(default_factory=list)
    execution_order: dict[str, int] = field(default_factory=dict)
    parallel_tracks: int = 0
    cycle_issues: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class BatchRunService:
    """Orchestrates sprint batch run creation, cancellation, and status updates.

    Implements:
    - Kahn's topological sort over issue BLOCKS links
    - Batch run creation with per-issue execution_order assignment
    - Cancel cascade (batch-level and per-issue)
    - DAG preview for the PM approval chat card

    Args:
        session: Request-scoped async DB session.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = BatchRunRepository(session)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def create_batch_run(self, payload: CreateBatchRunPayload) -> BatchRun:
        """Create a BatchRun for all issues in a sprint cycle.

        Loads every non-deleted issue assigned to the cycle, resolves their
        BLOCKS dependency links, runs Kahn's topological sort to determine
        execution_order, then persists the BatchRun + BatchRunIssue rows.

        Issues in wave 0 are set to QUEUED immediately; all others start as
        PENDING (they become QUEUED only when their blockers complete).

        Args:
            payload: Workspace, cycle, and triggering-user context.

        Returns:
            The newly created BatchRun with items loaded.

        Raises:
            BatchRunError: If the cycle contains no issues.
            BatchRunCycleDetectedError: If dependency links form a cycle.
        """
        # 1. Load all issues in the cycle
        issues = await self._load_cycle_issues(payload.cycle_id, payload.workspace_id)
        if not issues:
            raise BatchRunError(
                f"Cycle {payload.cycle_id} has no issues to implement.",
            )

        issue_ids = [issue.id for issue in issues]

        # 2. Load BLOCKS links between those issues
        blocks_links = await self._load_blocks_links(issue_ids, payload.workspace_id)

        # 3. Topological sort
        execution_order_map, cycle_issues = kahn_topological_sort(issue_ids, blocks_links)
        if cycle_issues:
            raise BatchRunCycleDetectedError(
                f"Circular dependency detected among issues: "
                f"{[str(iid) for iid in cycle_issues]}",
                details={"cycle_issues": [str(iid) for iid in cycle_issues]},
            )

        # 4. Create the BatchRun header
        batch_run = BatchRun(
            workspace_id=payload.workspace_id,
            cycle_id=payload.cycle_id,
            triggered_by_id=payload.triggered_by_id,
            status=BatchRunStatus.PENDING,
            total_issues=len(issues),
            completed_issues=0,
            failed_issues=0,
        )
        self._session.add(batch_run)
        await self._session.flush()
        await self._session.refresh(batch_run)

        # 5. Create BatchRunIssue rows
        batch_run_issues: list[BatchRunIssue] = []
        for issue in issues:
            order = execution_order_map[issue.id]
            # First wave is immediately dispatchable
            status = (
                BatchRunIssueStatus.QUEUED
                if order == 0
                else BatchRunIssueStatus.PENDING
            )
            bri = BatchRunIssue(
                workspace_id=payload.workspace_id,
                batch_run_id=batch_run.id,
                issue_id=issue.id,
                status=status,
                execution_order=order,
            )
            self._session.add(bri)
            batch_run_issues.append(bri)

        await self._session.flush()

        # 6. Return with items loaded
        result = await self._repo.get_by_id_with_items(batch_run.id)
        if result is None:
            # Should never happen — we just created it
            raise BatchRunError("Failed to reload created batch run.")
        return result

    async def cancel_batch_run(self, batch_run_id: UUID) -> BatchRun:
        """Cancel a batch run: fail the parent, cancel all non-terminal issues.

        Args:
            batch_run_id: UUID of the BatchRun to cancel.

        Returns:
            The updated BatchRun.

        Raises:
            BatchRunNotFoundError: If the batch run does not exist.
        """
        batch_run = await self._repo.get_by_id_with_items(batch_run_id)
        if batch_run is None:
            raise BatchRunNotFoundError(f"BatchRun {batch_run_id} not found.")

        # Cancel all non-terminal issues
        await self._repo.cancel_pending_issues(batch_run_id)

        # Mark batch run as FAILED (a cancelled run is a failed run)
        await self._repo.update_batch_run_status(
            batch_run_id,
            BatchRunStatus.FAILED,
            completed_at=datetime.now(tz=UTC),
        )

        # Re-fetch to return fresh state
        updated = await self._repo.get_by_id_with_items(batch_run_id)
        if updated is None:
            raise BatchRunNotFoundError(f"BatchRun {batch_run_id} not found after cancel.")
        return updated

    async def cancel_issue(self, batch_run_issue_id: UUID) -> None:
        """Cancel a single BatchRunIssue.

        Args:
            batch_run_issue_id: UUID of the BatchRunIssue to cancel.
        """
        await self._repo.update_issue_status(
            batch_run_issue_id,
            BatchRunIssueStatus.CANCELLED,
        )

    async def get_dag_preview(
        self,
        cycle_id: UUID,
        workspace_id: UUID,
    ) -> DAGPreviewResult:
        """Preview the execution DAG without creating a BatchRun.

        Used by the PilotSpaceAgent chat card to show the PM a dependency
        graph before they approve. Returns execution_order, parallel track
        count, and cycle detection results.

        Args:
            cycle_id: The sprint cycle UUID.
            workspace_id: The workspace UUID.

        Returns:
            DAGPreviewResult with issue list, execution order, and stats.
        """
        issues = await self._load_cycle_issues(cycle_id, workspace_id)
        issue_ids = [issue.id for issue in issues]

        blocks_links = await self._load_blocks_links(issue_ids, workspace_id)
        execution_order_map, cycle_issues = kahn_topological_sort(issue_ids, blocks_links)

        return DAGPreviewResult(
            issues=[
                {"id": str(issue.id), "title": getattr(issue, "title", str(issue.id))}
                for issue in issues
            ],
            execution_order={str(iid): order for iid, order in execution_order_map.items()},
            parallel_tracks=len(set(execution_order_map.values())) if execution_order_map else 0,
            cycle_issues=[str(iid) for iid in cycle_issues],
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _load_cycle_issues(
        self,
        cycle_id: UUID,
        workspace_id: UUID,
    ) -> list[Issue]:
        """Load all non-deleted issues in a cycle.

        Args:
            cycle_id: The sprint cycle UUID.
            workspace_id: The workspace UUID (for safety filter).

        Returns:
            List of Issue objects.
        """
        query = select(Issue).where(
            and_(
                Issue.cycle_id == cycle_id,
                Issue.workspace_id == workspace_id,
                Issue.is_deleted == False,  # noqa: E712
            )
        )
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def _load_blocks_links(
        self,
        issue_ids: list[UUID],
        workspace_id: UUID,
    ) -> list[tuple[UUID, UUID]]:
        """Load all BLOCKS links between a set of issues.

        Queries IssueLink for rows where link_type='blocks' and both
        source and target are in issue_ids.

        Args:
            issue_ids: The issue UUIDs to consider.
            workspace_id: The workspace UUID (for RLS filter).

        Returns:
            List of (blocker_id, blocked_id) tuples.
        """
        if not issue_ids:
            return []

        query = select(IssueLink).where(
            and_(
                IssueLink.workspace_id == workspace_id,
                IssueLink.is_deleted == False,  # noqa: E712
                IssueLink.link_type == IssueLinkType.BLOCKS,
                IssueLink.source_issue_id.in_(issue_ids),
                IssueLink.target_issue_id.in_(issue_ids),
            )
        )
        result = await self._session.execute(query)
        links = result.scalars().all()
        return [(link.source_issue_id, link.target_issue_id) for link in links]


__all__ = [
    "BatchRunService",
    "CreateBatchRunPayload",
    "DAGPreviewResult",
    "kahn_topological_sort",
]
