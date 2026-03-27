"""SprintBoardService — sprint board data and AI transition proposals.

Extracted from pm_sprint_board router (T-231, T-233).
Handles lane grouping and AI-proposed state transitions.
"""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING
from uuid import UUID

from pilot_space.domain.exceptions import NotFoundError
from pilot_space.infrastructure.logging import get_logger
from pilot_space.schemas.sprint_board import (
    SprintBoardCard,
    SprintBoardLane,
    SprintBoardResponse,
    TransitionProposal,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from pilot_space.infrastructure.database.repositories.pm_block_queries_repository import (
        PMBlockQueriesRepository,
    )

logger = get_logger(__name__)

STATE_GROUP_ORDER = ["backlog", "todo", "in_progress", "in_review", "done", "cancelled"]


class SprintBoardService:
    """Sprint board business logic.

    Provides lane grouping for cycle issues and AI transition proposals.
    """

    def __init__(
        self,
        session: AsyncSession,
        pm_block_queries_repository: PMBlockQueriesRepository,
    ) -> None:
        self._session = session
        self._repo = pm_block_queries_repository

    async def get_board(
        self,
        workspace_id: UUID,
        cycle_id: str,
    ) -> SprintBoardResponse:
        """Build sprint board data for a cycle grouped into state lanes.

        Args:
            workspace_id: Workspace UUID.
            cycle_id: Cycle UUID string.

        Returns:
            Dict with cycle_id, cycle_name, lanes, total_issues, is_read_only.

        Raises:
            NotFoundError: If cycle not found.
        """
        cycle_uuid = UUID(cycle_id)
        repo = self._repo

        cycle = await repo.get_cycle(cycle_uuid, workspace_id)
        if not cycle:
            raise NotFoundError("Cycle not found")

        issues = await repo.get_cycle_issues_with_state_and_assignee(cycle_uuid, workspace_id)

        lanes_map: dict[str, list[SprintBoardCard]] = defaultdict(list)
        for issue in issues:
            state = issue.state
            lane_key = state.name.lower().replace(" ", "_") if state else "backlog"
            card = SprintBoardCard(
                id=str(issue.id),
                identifier=issue.identifier,
                name=issue.name,
                priority=(
                    issue.priority.value
                    if hasattr(issue.priority, "value")
                    else str(issue.priority)
                ),
                state_name=state.name if state else "Backlog",
                state_id=str(state.id) if state else "",
                assignee_id=str(issue.assignee_id) if issue.assignee_id else None,
                assignee_name=(
                    getattr(issue.assignee, "full_name", None)
                    or getattr(issue.assignee, "email", None)
                    if issue.assignee
                    else None
                ),
                labels=[],
                estimate_hours=float(getattr(issue, "estimate_points", None) or 0) or None,
            )
            lanes_map[lane_key].append(card)

        lanes = [
            SprintBoardLane(
                state_id=grp,
                state_name=grp.replace("_", " ").title(),
                state_group=grp,
                count=len(lanes_map.get(grp, [])),
                issues=lanes_map.get(grp, []),
            )
            for grp in STATE_GROUP_ORDER
        ]

        is_read_only = str(getattr(cycle, "status", "")).lower() in ("completed", "cancelled")

        return SprintBoardResponse(
            cycle_id=cycle_id,
            cycle_name=cycle.name,
            lanes=lanes,
            total_issues=len(issues),
            is_read_only=is_read_only,
        )

    async def propose_transition(
        self,
        workspace_id: UUID,
        user_id: UUID,
        issue_id: str,
        proposed_state: str,
        reason: str | None,
    ) -> TransitionProposal:
        """Create an approval request for an AI-proposed state transition.

        Args:
            workspace_id: Workspace UUID.
            user_id: Current user UUID.
            issue_id: Issue UUID string.
            proposed_state: Target state group key.
            reason: AI rationale for the proposal.

        Returns:
            Approval ID string.
        """
        from pilot_space.ai.infrastructure.approval import ActionType, ApprovalService

        approval_service = ApprovalService(session=self._session)
        approval_id = await approval_service.create_approval_request(
            workspace_id=workspace_id,
            user_id=user_id,
            action_type=ActionType.TRANSITION_ISSUE_STATE,
            action_data={
                "issue_id": issue_id,
                "proposed_state": proposed_state,
                "reason": reason,
            },
            requested_by_agent="sprint-board-ai",
            context={"workspace_id": str(workspace_id), "issue_id": issue_id},
        )
        return TransitionProposal(approval_id=str(approval_id))


__all__ = ["SprintBoardService"]
