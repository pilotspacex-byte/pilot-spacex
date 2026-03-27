"""PMBlockInsightService — analyze PM block data and generate insights.

T-249: PMBlockInsight CRUD
T-251: PMBlockInsight analyzers (sprint_board, dependency_map, capacity_plan, release_notes)
T-252: refresh_insights with debounce

Feature 017: Note Versioning / PM Block Engine — Phase 2a
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from pilot_space.domain.pm_block_insight import InsightSeverity, PMBlockInsight, PMBlockType
from pilot_space.infrastructure.database.models.pm_block_insight import (
    PMBlockInsight as PMBlockInsightModel,
)
from pilot_space.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from pilot_space.infrastructure.database.repositories.pm_block_insight_repository import (
        PMBlockInsightRepository,
    )

logger = get_logger(__name__)


class PMBlockInsightService:
    """Analyze PM block data and generate/store AI insights.

    Routes block data to type-specific analyzers. On refresh, old insights
    for the block are soft-deleted before new ones are stored.
    """

    def __init__(
        self,
        session: AsyncSession,
        repository: PMBlockInsightRepository,
    ) -> None:
        self._session = session
        self._repo = repository

    # ── Public API ────────────────────────────────────────────────────────────

    async def list_blocks(
        self,
        block_id: str,
        workspace_id: UUID,
        *,
        include_dismissed: bool = False,
    ) -> list[PMBlockInsightModel]:
        """List AI insights for a PM block.

        Args:
            block_id: TipTap block node ID.
            workspace_id: Workspace UUID (RLS boundary).
            include_dismissed: Whether to include dismissed insights.

        Returns:
            List of PMBlockInsight ORM models.
        """
        return list(
            await self._repo.list_by_block(
                block_id=block_id,
                workspace_id=workspace_id,
                include_dismissed=include_dismissed,
            )
        )

    async def dismiss(
        self,
        insight_id: UUID,
        workspace_id: UUID,
    ) -> None:
        """Dismiss a single insight.

        Args:
            insight_id: Insight UUID.
            workspace_id: Workspace UUID for ownership check.

        Raises:
            NotFoundError: If insight not found or belongs to another workspace.
        """
        from pilot_space.domain.exceptions import NotFoundError

        insight = await self._repo.get_by_id(insight_id)
        if not insight or insight.workspace_id != workspace_id:
            raise NotFoundError("Insight not found")
        insight.dismissed = True
        await self._session.flush()
        await self._session.commit()

    async def batch_dismiss(
        self,
        block_id: str,
        workspace_id: UUID,
    ) -> None:
        """Batch-dismiss all active insights for a block.

        Args:
            block_id: TipTap block node ID.
            workspace_id: Workspace UUID (RLS boundary).
        """
        await self._repo.batch_dismiss(block_id=block_id, workspace_id=workspace_id)
        await self._session.commit()

    async def refresh_insights_debounced(
        self,
        block_id: str,
        block_type_str: str,
        workspace_id: UUID,
        data: dict[str, Any],
    ) -> list[PMBlockInsightModel]:
        """Refresh insights with 30s debounce.

        Returns cached insights if newest was created within 30s.
        Otherwise generates fresh insights.

        Args:
            block_id: TipTap block node ID.
            block_type_str: PM block type enum value string.
            workspace_id: Workspace UUID.
            data: Block payload forwarded to analyze.

        Returns:
            Persisted PMBlockInsight ORM objects.

        Raises:
            ValidationError: If block_type_str is invalid.
        """
        from datetime import UTC, datetime, timedelta

        from pilot_space.domain.exceptions import ValidationError

        existing = await self._repo.list_by_block(
            block_id=block_id, workspace_id=workspace_id, include_dismissed=True
        )
        if existing:
            newest = max(i.created_at for i in existing)
            if newest.tzinfo is None:
                newest = newest.replace(tzinfo=UTC)
            if datetime.now(UTC) - newest < timedelta(seconds=30):
                return list(existing)

        try:
            block_type_enum = PMBlockType(block_type_str)
        except ValueError as exc:
            raise ValidationError(f"Invalid block_type: {block_type_str}") from exc

        return await self.refresh_insights(
            block_id=block_id,
            block_type=block_type_enum,
            workspace_id=str(workspace_id),
            data=data,
        )

    async def analyze_block(
        self,
        block_id: str,
        block_type: PMBlockType,
        workspace_id: str,
        data: dict[str, Any],
    ) -> list[PMBlockInsight]:
        """Analyze PM block data and return unsaved insights.

        Args:
            block_id: TipTap block node ID.
            block_type: Classification of the PM block.
            workspace_id: Workspace UUID string (RLS boundary).
            data: Block payload; schema depends on block_type.

        Returns:
            List of unsaved PMBlockInsight domain entities.
        """
        ws_uuid = UUID(workspace_id)

        # Insufficient-data guard: sprint boards need ≥3 completed cycles
        if block_type == PMBlockType.SPRINT_BOARD:
            completed = data.get("completed_cycles_count", 0)
            if isinstance(completed, int) and completed < 3:
                return [
                    _make_insight(
                        workspace_id=ws_uuid,
                        block_id=block_id,
                        block_type=block_type,
                        insight_type="insufficient_data",
                        severity=InsightSeverity.GREEN,
                        title="Insufficient data",
                        analysis=(
                            "Insights improve with more sprint history. "
                            "Complete at least 3 sprints."
                        ),
                        confidence=1.0,
                    )
                ]

        router = {
            PMBlockType.SPRINT_BOARD: self._analyze_sprint_board,
            PMBlockType.DEPENDENCY_MAP: self._analyze_dependency_map,
            PMBlockType.CAPACITY_PLAN: self._analyze_capacity,
            PMBlockType.RELEASE_NOTES: self._analyze_release_notes,
        }
        analyzer = router[block_type]
        return analyzer(block_id=block_id, workspace_id=ws_uuid, data=data)

    async def refresh_insights(
        self,
        block_id: str,
        block_type: PMBlockType,
        workspace_id: str,
        data: dict[str, Any],
    ) -> list[PMBlockInsightModel]:
        """Soft-delete old insights for block_id, analyze, persist new ones.

        Args:
            block_id: TipTap block node ID.
            block_type: Classification of the PM block.
            workspace_id: Workspace UUID string.
            data: Block payload forwarded to analyze_block.

        Returns:
            Persisted PMBlockInsight ORM objects.
        """
        ws_uuid = UUID(workspace_id)

        # Soft-delete all existing insights for this block
        await self._soft_delete_by_block(block_id=block_id, workspace_id=ws_uuid)

        new_insights = await self.analyze_block(
            block_id=block_id,
            block_type=block_type,
            workspace_id=workspace_id,
            data=data,
        )

        persisted: list[PMBlockInsightModel] = []
        for insight in new_insights:
            model = PMBlockInsightModel(
                workspace_id=insight.workspace_id,
                block_id=insight.block_id,
                block_type=insight.block_type,
                insight_type=insight.insight_type,
                severity=insight.severity,
                title=insight.title,
                analysis=insight.analysis,
                confidence=insight.confidence,
                references=insight.references,
                suggested_actions=insight.suggested_actions,
            )
            saved = await self._repo.create(model)
            persisted.append(saved)

        logger.info(
            "Refreshed PM block insights",
            extra={
                "block_id": block_id,
                "block_type": block_type.value,
                "workspace_id": workspace_id,
                "count": len(persisted),
            },
        )
        return persisted

    # ── Type-specific analyzers ───────────────────────────────────────────────

    def _analyze_sprint_board(
        self, *, block_id: str, workspace_id: UUID, data: dict[str, Any]
    ) -> list[PMBlockInsight]:
        """Sprint board analyzer: stale issues, blocker count, velocity anomaly."""
        insights: list[PMBlockInsight] = []

        stale_count: int = data.get("stale_issues_count", 0)
        if stale_count > 0:
            severity = InsightSeverity.RED if stale_count > 3 else InsightSeverity.YELLOW
            insights.append(
                _make_insight(
                    workspace_id=workspace_id,
                    block_id=block_id,
                    block_type=PMBlockType.SPRINT_BOARD,
                    insight_type="stale_issues",
                    severity=severity,
                    title=f"{stale_count} stale issue(s) in sprint",
                    analysis=(
                        f"{stale_count} issue(s) have not changed state in over 7 days. "
                        "Consider reassigning or breaking them down."
                    ),
                    confidence=0.9,
                    suggested_actions=[
                        "Review stale issues in standup",
                        "Break down issues exceeding 7 days",
                        "Reassign if blocked",
                    ],
                )
            )

        blocker_count: int = data.get("blocker_count", 0)
        if blocker_count > 3:
            insights.append(
                _make_insight(
                    workspace_id=workspace_id,
                    block_id=block_id,
                    block_type=PMBlockType.SPRINT_BOARD,
                    insight_type="high_blocker_count",
                    severity=InsightSeverity.RED,
                    title=f"{blocker_count} active blockers",
                    analysis=(
                        f"{blocker_count} issues are currently blocked. "
                        "High blocker count indicates systemic dependency risk."
                    ),
                    confidence=0.85,
                    suggested_actions=[
                        "Schedule blocker resolution session",
                        "Escalate if external dependencies",
                    ],
                )
            )

        velocity_pct: float = data.get("velocity_deviation_pct", 0.0)
        if abs(velocity_pct) > 20:
            direction = "below" if velocity_pct < 0 else "above"
            severity = InsightSeverity.RED if abs(velocity_pct) > 40 else InsightSeverity.YELLOW
            insights.append(
                _make_insight(
                    workspace_id=workspace_id,
                    block_id=block_id,
                    block_type=PMBlockType.SPRINT_BOARD,
                    insight_type="velocity_anomaly",
                    severity=severity,
                    title=f"Velocity {abs(velocity_pct):.0f}% {direction} average",
                    analysis=(
                        f"Current sprint velocity deviates {abs(velocity_pct):.0f}% "
                        f"{direction} historical average. "
                        "Investigate scope changes or team capacity."
                    ),
                    confidence=0.75,
                    suggested_actions=["Review sprint scope", "Check team availability"],
                )
            )

        return insights

    def _analyze_dependency_map(
        self, *, block_id: str, workspace_id: UUID, data: dict[str, Any]
    ) -> list[PMBlockInsight]:
        """Dependency map analyzer: critical path length, bottleneck nodes."""
        insights: list[PMBlockInsight] = []

        critical_path_length: int = data.get("critical_path_length", 0)
        if critical_path_length > 20:
            insights.append(
                _make_insight(
                    workspace_id=workspace_id,
                    block_id=block_id,
                    block_type=PMBlockType.DEPENDENCY_MAP,
                    insight_type="long_critical_path",
                    severity=InsightSeverity.RED,
                    title=f"Critical path spans {critical_path_length} issues",
                    analysis=(
                        f"The critical path has {critical_path_length} issues — "
                        "high delivery risk. Parallelise work or descope."
                    ),
                    confidence=0.9,
                    suggested_actions=[
                        "Identify parallelisable work",
                        "Consider descoping low-value tail items",
                    ],
                )
            )
        elif critical_path_length > 10:
            insights.append(
                _make_insight(
                    workspace_id=workspace_id,
                    block_id=block_id,
                    block_type=PMBlockType.DEPENDENCY_MAP,
                    insight_type="long_critical_path",
                    severity=InsightSeverity.YELLOW,
                    title=f"Critical path spans {critical_path_length} issues",
                    analysis=(
                        f"The critical path has {critical_path_length} issues. "
                        "Monitor closely for delay propagation."
                    ),
                    confidence=0.85,
                    suggested_actions=["Review critical path in weekly planning"],
                )
            )

        bottleneck_count: int = data.get("bottleneck_node_count", 0)
        if bottleneck_count > 0:
            insights.append(
                _make_insight(
                    workspace_id=workspace_id,
                    block_id=block_id,
                    block_type=PMBlockType.DEPENDENCY_MAP,
                    insight_type="bottleneck_nodes",
                    severity=InsightSeverity.YELLOW,
                    title=f"{bottleneck_count} bottleneck node(s) detected",
                    analysis=(
                        f"{bottleneck_count} issue(s) have >5 incoming dependencies. "
                        "Delays on these will cascade across the graph."
                    ),
                    confidence=0.8,
                    suggested_actions=[
                        "Prioritise bottleneck issues",
                        "Assign senior engineers to bottleneck nodes",
                    ],
                )
            )

        return insights

    def _analyze_capacity(
        self, *, block_id: str, workspace_id: UUID, data: dict[str, Any]
    ) -> list[PMBlockInsight]:
        """Capacity plan analyzer: overallocation and underallocation."""
        insights: list[PMBlockInsight] = []

        members: list[dict[str, Any]] = data.get("members", [])
        overallocated = [m for m in members if m.get("utilization_pct", 0) > 100]
        underallocated = [m for m in members if m.get("utilization_pct", 0) < 30]

        if overallocated:
            names = ", ".join(m.get("display_name", "Unknown") for m in overallocated[:3])
            insights.append(
                _make_insight(
                    workspace_id=workspace_id,
                    block_id=block_id,
                    block_type=PMBlockType.CAPACITY_PLAN,
                    insight_type="overallocation",
                    severity=InsightSeverity.RED,
                    title=f"{len(overallocated)} member(s) over capacity",
                    analysis=(
                        f"{names} are allocated over 100% of available hours. "
                        "Risk of burnout and missed commitments."
                    ),
                    confidence=0.95,
                    suggested_actions=[
                        "Redistribute tasks from overallocated members",
                        "Negotiate scope reduction with stakeholders",
                    ],
                )
            )

        if underallocated:
            names = ", ".join(m.get("display_name", "Unknown") for m in underallocated[:3])
            insights.append(
                _make_insight(
                    workspace_id=workspace_id,
                    block_id=block_id,
                    block_type=PMBlockType.CAPACITY_PLAN,
                    insight_type="underallocation",
                    severity=InsightSeverity.YELLOW,
                    title=f"{len(underallocated)} member(s) under-utilised",
                    analysis=(
                        f"{names} are allocated under 30% of available hours. "
                        "Capacity available to absorb additional scope."
                    ),
                    confidence=0.8,
                    suggested_actions=[
                        "Assign backlog items to under-utilised members",
                        "Pull in next-sprint work if ready",
                    ],
                )
            )

        return insights

    def _analyze_release_notes(
        self, *, block_id: str, workspace_id: UUID, data: dict[str, Any]
    ) -> list[PMBlockInsight]:
        """Release notes analyzer: coverage gaps from uncategorized issues."""
        insights: list[PMBlockInsight] = []

        entries: list[dict[str, Any]] = data.get("entries", [])
        uncategorized = [e for e in entries if e.get("category") == "uncategorized"]

        if uncategorized:
            insights.append(
                _make_insight(
                    workspace_id=workspace_id,
                    block_id=block_id,
                    block_type=PMBlockType.RELEASE_NOTES,
                    insight_type="coverage_gaps",
                    severity=InsightSeverity.YELLOW,
                    title=f"{len(uncategorized)} issue(s) uncategorized",
                    analysis=(
                        f"{len(uncategorized)} completed issue(s) could not be classified "
                        "into a release note category. "
                        "Review and manually assign categories for completeness."
                    ),
                    confidence=0.9,
                    suggested_actions=[
                        "Review uncategorized issues and assign categories",
                        "Add keywords to issue names to improve auto-classification",
                    ],
                )
            )

        return insights

    # ── Internal helpers ──────────────────────────────────────────────────────

    async def _soft_delete_by_block(self, *, block_id: str, workspace_id: UUID) -> None:
        """Soft-delete all non-deleted insights for a block."""
        from sqlalchemy import and_, update

        from pilot_space.infrastructure.database.models.pm_block_insight import (
            PMBlockInsight as PMBlockInsightModel,
        )

        await self._session.execute(
            update(PMBlockInsightModel)
            .where(
                and_(
                    PMBlockInsightModel.block_id == block_id,
                    PMBlockInsightModel.workspace_id == workspace_id,
                    PMBlockInsightModel.is_deleted == False,  # noqa: E712
                )
            )
            .values(is_deleted=True, deleted_at=datetime.now(tz=UTC))
            .execution_options(synchronize_session="fetch")
        )


# ── Factory helper ────────────────────────────────────────────────────────────


def _make_insight(
    *,
    workspace_id: UUID,
    block_id: str,
    block_type: PMBlockType,
    insight_type: str,
    severity: InsightSeverity,
    title: str,
    analysis: str,
    confidence: float,
    references: list[str] | None = None,
    suggested_actions: list[str] | None = None,
) -> PMBlockInsight:
    return PMBlockInsight(
        workspace_id=workspace_id,
        block_id=block_id,
        block_type=block_type,
        insight_type=insight_type,
        severity=severity,
        title=title,
        analysis=analysis,
        confidence=confidence,
        references=references or [],
        suggested_actions=suggested_actions or [],
    )


__all__ = ["PMBlockInsightService"]
