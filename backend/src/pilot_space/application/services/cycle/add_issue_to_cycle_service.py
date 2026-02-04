"""Add/Remove Issue to/from Cycle service.

T160: Create AddIssueToCycleService to add/remove issues from cycle.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from pilot_space.infrastructure.database.models import Activity, ActivityType, Issue

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
class AddIssueToCyclePayload:
    """Payload for adding an issue to a cycle.

    Attributes:
        workspace_id: Workspace UUID.
        cycle_id: Cycle UUID.
        issue_id: Issue UUID.
        actor_id: User performing the action.
    """

    workspace_id: UUID
    cycle_id: UUID
    issue_id: UUID
    actor_id: UUID


@dataclass
class AddIssueToCycleResult:
    """Result from adding issue to cycle."""

    issue: Issue
    added: bool = True


@dataclass
class RemoveIssueFromCyclePayload:
    """Payload for removing an issue from a cycle.

    Attributes:
        workspace_id: Workspace UUID.
        cycle_id: Cycle UUID.
        issue_id: Issue UUID.
        actor_id: User performing the action.
    """

    workspace_id: UUID
    cycle_id: UUID
    issue_id: UUID
    actor_id: UUID


@dataclass
class RemoveIssueFromCycleResult:
    """Result from removing issue from cycle."""

    issue: Issue
    removed: bool = True


class AddIssueToCycleService:
    """Service for adding and removing issues from cycles.

    Handles:
    - Adding issue to cycle
    - Removing issue from cycle
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

    async def add_issue(self, payload: AddIssueToCyclePayload) -> AddIssueToCycleResult:
        """Add an issue to a cycle.

        Args:
            payload: Add issue parameters.

        Returns:
            AddIssueToCycleResult with updated issue.

        Raises:
            ValueError: If cycle or issue not found.
        """
        # Validate cycle exists
        cycle = await self._cycle_repo.get_by_id(payload.cycle_id)
        if not cycle:
            raise ValueError(f"Cycle not found: {payload.cycle_id}")

        # Validate issue exists
        issue = await self._issue_repo.get_by_id_with_relations(payload.issue_id)
        if not issue:
            raise ValueError(f"Issue not found: {payload.issue_id}")

        # Check if issue is already in this cycle
        if issue.cycle_id == payload.cycle_id:
            return AddIssueToCycleResult(issue=issue, added=False)

        # Store old cycle for activity
        old_cycle_id = issue.cycle_id

        # Update issue
        issue.cycle_id = payload.cycle_id
        await self._issue_repo.update(issue)

        # Create activity
        activity = Activity(
            workspace_id=payload.workspace_id,
            issue_id=payload.issue_id,
            actor_id=payload.actor_id,
            activity_type=ActivityType.ADDED_TO_CYCLE,
            field="cycle_id",
            old_value=str(old_cycle_id) if old_cycle_id else None,
            new_value=str(payload.cycle_id),
            activity_metadata={
                "cycle_name": cycle.name,
            },
        )
        await self._activity_repo.create(activity)

        # Reload with relationships
        issue = await self._issue_repo.get_by_id_with_relations(payload.issue_id)

        logger.info(
            "Issue added to cycle",
            extra={
                "issue_id": str(payload.issue_id),
                "cycle_id": str(payload.cycle_id),
            },
        )

        return AddIssueToCycleResult(
            issue=issue,  # type: ignore[arg-type]
            added=True,
        )

    async def remove_issue(
        self, payload: RemoveIssueFromCyclePayload
    ) -> RemoveIssueFromCycleResult:
        """Remove an issue from a cycle.

        Args:
            payload: Remove issue parameters.

        Returns:
            RemoveIssueFromCycleResult with updated issue.

        Raises:
            ValueError: If issue not found or not in the specified cycle.
        """
        # Validate cycle exists
        cycle = await self._cycle_repo.get_by_id(payload.cycle_id)
        if not cycle:
            raise ValueError(f"Cycle not found: {payload.cycle_id}")

        # Validate issue exists
        issue = await self._issue_repo.get_by_id_with_relations(payload.issue_id)
        if not issue:
            raise ValueError(f"Issue not found: {payload.issue_id}")

        # Check if issue is in this cycle
        if issue.cycle_id != payload.cycle_id:
            raise ValueError(f"Issue {payload.issue_id} is not in cycle {payload.cycle_id}")

        # Update issue
        issue.cycle_id = None
        await self._issue_repo.update(issue)

        # Create activity
        activity = Activity(
            workspace_id=payload.workspace_id,
            issue_id=payload.issue_id,
            actor_id=payload.actor_id,
            activity_type=ActivityType.REMOVED_FROM_CYCLE,
            field="cycle_id",
            old_value=str(payload.cycle_id),
            new_value=None,
            activity_metadata={
                "cycle_name": cycle.name,
            },
        )
        await self._activity_repo.create(activity)

        # Reload with relationships
        issue = await self._issue_repo.get_by_id_with_relations(payload.issue_id)

        logger.info(
            "Issue removed from cycle",
            extra={
                "issue_id": str(payload.issue_id),
                "cycle_id": str(payload.cycle_id),
            },
        )

        return RemoveIssueFromCycleResult(
            issue=issue,  # type: ignore[arg-type]
            removed=True,
        )

    async def bulk_add_issues(
        self,
        workspace_id: UUID,
        cycle_id: UUID,
        issue_ids: list[UUID],
        actor_id: UUID,
    ) -> list[AddIssueToCycleResult]:
        """Add multiple issues to a cycle.

        Args:
            workspace_id: Workspace UUID.
            cycle_id: Cycle UUID.
            issue_ids: List of issue UUIDs.
            actor_id: User performing the action.

        Returns:
            List of AddIssueToCycleResult for each issue.
        """
        results: list[AddIssueToCycleResult] = []
        for issue_id in issue_ids:
            try:
                result = await self.add_issue(
                    AddIssueToCyclePayload(
                        workspace_id=workspace_id,
                        cycle_id=cycle_id,
                        issue_id=issue_id,
                        actor_id=actor_id,
                    )
                )
                results.append(result)
            except ValueError as e:
                logger.warning(
                    f"Failed to add issue {issue_id} to cycle: {e}",
                    extra={
                        "issue_id": str(issue_id),
                        "cycle_id": str(cycle_id),
                    },
                )
        return results


__all__ = [
    "AddIssueToCyclePayload",
    "AddIssueToCycleResult",
    "AddIssueToCycleService",
    "RemoveIssueFromCyclePayload",
    "RemoveIssueFromCycleResult",
]
