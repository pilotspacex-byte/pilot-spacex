"""Rollover Cycle service.

T161: Create RolloverCycleService to move incomplete issues to next cycle.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from pilot_space.infrastructure.database.models import (
    Activity,
    ActivityType,
    Cycle,
    CycleStatus,
    Issue,
    StateGroup,
)

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from pilot_space.infrastructure.database.repositories import (
        ActivityRepository,
        CycleRepository,
        IssueRepository,
    )

logger = logging.getLogger(__name__)


@dataclass
class RolloverCyclePayload:
    """Payload for rolling over a cycle.

    Attributes:
        workspace_id: Workspace UUID.
        source_cycle_id: Cycle to rollover from.
        target_cycle_id: Cycle to rollover to.
        actor_id: User performing the rollover.
        issue_ids: Specific issues to rollover (if None, rollover all incomplete).
        include_in_progress: Whether to include in-progress issues.
        complete_source_cycle: Whether to mark source cycle as completed.
    """

    workspace_id: UUID
    source_cycle_id: UUID
    target_cycle_id: UUID
    actor_id: UUID
    issue_ids: list[UUID] | None = None
    include_in_progress: bool = True
    complete_source_cycle: bool = True


@dataclass
class RolloverCycleResult:
    """Result from cycle rollover."""

    source_cycle: Cycle
    target_cycle: Cycle
    rolled_over_issues: list[Issue] = field(default_factory=list)
    skipped_issues: list[Issue] = field(default_factory=list)
    total_rolled_over: int = 0


class RolloverCycleService:
    """Service for rolling over cycles.

    Handles:
    - Moving incomplete issues from source to target cycle
    - Optionally completing source cycle
    - Activity logging for audit trail
    """

    def __init__(
        self,
        session: AsyncSession,
        cycle_repository: CycleRepository,
        issue_repository: IssueRepository,
        activity_repository: ActivityRepository,
    ) -> None:
        """Initialize service.

        Args:
            session: Async database session.
            cycle_repository: Cycle repository.
            issue_repository: Issue repository.
            activity_repository: Activity repository.
        """
        self._session = session
        self._cycle_repo = cycle_repository
        self._issue_repo = issue_repository
        self._activity_repo = activity_repository

    async def execute(self, payload: RolloverCyclePayload) -> RolloverCycleResult:
        """Rollover a cycle to move incomplete issues.

        Args:
            payload: Rollover parameters.

        Returns:
            RolloverCycleResult with rolled over issues.

        Raises:
            ValueError: If cycles not found or validation fails.
        """
        # Validate source cycle
        source_cycle = await self._cycle_repo.get_by_id_with_relations(payload.source_cycle_id)
        if not source_cycle:
            raise ValueError(f"Source cycle not found: {payload.source_cycle_id}")

        # Validate target cycle
        target_cycle = await self._cycle_repo.get_by_id_with_relations(payload.target_cycle_id)
        if not target_cycle:
            raise ValueError(f"Target cycle not found: {payload.target_cycle_id}")

        # Ensure cycles are in the same project
        if source_cycle.project_id != target_cycle.project_id:
            raise ValueError("Source and target cycles must be in the same project")

        # Ensure target cycle is not completed/cancelled
        if target_cycle.status in (CycleStatus.COMPLETED, CycleStatus.CANCELLED):
            raise ValueError(f"Cannot rollover to {target_cycle.status.value} cycle")

        # Get issues to rollover
        if payload.issue_ids:
            # Specific issues
            issues_to_rollover = [
                await self._issue_repo.get_by_id_with_relations(issue_id)
                for issue_id in payload.issue_ids
            ]
            issues_to_rollover = [i for i in issues_to_rollover if i is not None]
        else:
            # All incomplete issues from source cycle
            all_issues = await self._cycle_repo.get_issues_in_cycle(
                payload.source_cycle_id,
                include_completed=True,
            )
            issues_to_rollover = []
            for issue in all_issues:
                # Skip completed/cancelled issues
                if issue.state and issue.state.group in (
                    StateGroup.COMPLETED,
                    StateGroup.CANCELLED,
                ):
                    continue
                # Optionally skip in-progress issues
                if not payload.include_in_progress and issue.state:
                    if issue.state.group == StateGroup.STARTED:
                        continue
                issues_to_rollover.append(issue)

        rolled_over: list[Issue] = []
        skipped: list[Issue] = []

        # Move issues to target cycle
        for issue in issues_to_rollover:
            # Verify issue is in source cycle
            if issue.cycle_id != payload.source_cycle_id:
                skipped.append(issue)
                continue

            # Update issue cycle
            old_cycle_id = issue.cycle_id
            issue.cycle_id = payload.target_cycle_id
            await self._issue_repo.update(issue)

            # Create activity
            activity = Activity(
                workspace_id=payload.workspace_id,
                issue_id=issue.id,
                actor_id=payload.actor_id,
                activity_type=ActivityType.ADDED_TO_CYCLE,
                field="cycle_id",
                old_value=str(old_cycle_id) if old_cycle_id else None,
                new_value=str(payload.target_cycle_id),
                activity_metadata={
                    "rollover": True,
                    "source_cycle_name": source_cycle.name,
                    "target_cycle_name": target_cycle.name,
                },
            )
            await self._activity_repo.create(activity)

            rolled_over.append(issue)

        # Complete source cycle if requested
        if payload.complete_source_cycle and source_cycle.status == CycleStatus.ACTIVE:
            source_cycle.status = CycleStatus.COMPLETED
            await self._cycle_repo.update(source_cycle)

        # Reload cycles
        source_cycle = await self._cycle_repo.get_by_id_with_relations(payload.source_cycle_id)
        target_cycle = await self._cycle_repo.get_by_id_with_relations(payload.target_cycle_id)

        logger.info(
            "Cycle rollover completed",
            extra={
                "source_cycle_id": str(payload.source_cycle_id),
                "target_cycle_id": str(payload.target_cycle_id),
                "rolled_over_count": len(rolled_over),
                "skipped_count": len(skipped),
            },
        )

        return RolloverCycleResult(
            source_cycle=source_cycle,  # type: ignore[arg-type]
            target_cycle=target_cycle,  # type: ignore[arg-type]
            rolled_over_issues=rolled_over,
            skipped_issues=skipped,
            total_rolled_over=len(rolled_over),
        )


__all__ = ["RolloverCyclePayload", "RolloverCycleResult", "RolloverCycleService"]
