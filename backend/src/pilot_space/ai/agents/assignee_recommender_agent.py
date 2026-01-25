"""Assignee Recommender Agent for suggesting issue assignees.

T132: Create AssigneeRecommenderAgent based on workload and expertise.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from pilot_space.ai.agents.base import (
    AgentContext,
    AgentResult,
    BaseAgent,
    TaskType,
)
from pilot_space.ai.telemetry import AIOperation

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


@dataclass
class TeamMember:
    """Team member information for recommendation.

    Attributes:
        user_id: User UUID.
        name: Display name.
        email: Email address.
        current_workload: Number of active issues assigned.
        expertise_labels: Labels they've worked on frequently.
        recent_issue_count: Issues completed in last 30 days.
    """

    user_id: UUID
    name: str
    email: str
    current_workload: int = 0
    expertise_labels: list[str] = field(default_factory=list)
    recent_issue_count: int = 0


@dataclass
class AssigneeRecommendationInput:
    """Input for assignee recommendation.

    Attributes:
        issue_title: Issue title for context.
        issue_description: Issue description.
        issue_labels: Labels assigned to the issue.
        project_id: Project UUID.
        workspace_id: Workspace UUID.
        team_members: Available team members.
    """

    issue_title: str
    workspace_id: UUID
    project_id: UUID
    issue_description: str | None = None
    issue_labels: list[str] | None = None
    team_members: list[TeamMember] | None = None


@dataclass
class AssigneeRecommendation:
    """A recommended assignee.

    Attributes:
        user_id: Recommended user UUID.
        name: User name.
        confidence: Confidence score (0-1).
        reason: Explanation for recommendation.
    """

    user_id: UUID
    name: str
    confidence: float
    reason: str


@dataclass
class AssigneeRecommendationOutput:
    """Output from assignee recommendation.

    Attributes:
        recommendations: Ranked list of recommendations.
        has_strong_match: Whether any recommendation has high confidence.
    """

    recommendations: list[AssigneeRecommendation] = field(default_factory=list)
    has_strong_match: bool = False


class AssigneeRecommenderAgent(
    BaseAgent[AssigneeRecommendationInput, AssigneeRecommendationOutput]
):
    """Agent for recommending issue assignees.

    Uses heuristics and optionally AI to suggest assignees based on:
    - Label expertise (previous work on similar issues)
    - Current workload balance
    - Recent activity in the project

    Can work without AI for simple heuristic matching.
    """

    task_type = TaskType.LATENCY_SENSITIVE
    operation = AIOperation.CONTEXT_GENERATION

    def __init__(
        self,
        session: AsyncSession,
        model: str | None = None,
    ) -> None:
        """Initialize agent.

        Args:
            session: Database session.
            model: Override model.
        """
        super().__init__(model)
        self._session = session

    async def _execute_impl(
        self,
        input_data: AssigneeRecommendationInput,
        context: AgentContext,  # noqa: ARG002
    ) -> AgentResult[AssigneeRecommendationOutput]:
        """Execute assignee recommendation.

        Args:
            input_data: Issue and team context.
            _context: Agent execution context (unused in rule-based implementation).

        Returns:
            AgentResult with recommendations.
        """
        # Get team members if not provided
        team_members = input_data.team_members
        if not team_members:
            team_members = await self._load_team_members(
                input_data.workspace_id,
                input_data.project_id,
            )

        if not team_members:
            return AgentResult(
                output=AssigneeRecommendationOutput(),
                input_tokens=0,
                output_tokens=0,
                model=self.model,
                provider=self.provider,
            )

        # Score each team member
        scored_members = await self._score_members(
            team_members=team_members,
            issue_labels=input_data.issue_labels or [],
            _issue_title=input_data.issue_title,
        )

        # Sort by score and build recommendations
        scored_members.sort(key=lambda x: x[1], reverse=True)

        recommendations: list[AssigneeRecommendation] = []
        for member, score, reason in scored_members[:5]:  # Top 5
            recommendations.append(
                AssigneeRecommendation(
                    user_id=member.user_id,
                    name=member.name,
                    confidence=min(score, 1.0),
                    reason=reason,
                )
            )

        has_strong_match = any(r.confidence >= 0.7 for r in recommendations)

        return AgentResult(
            output=AssigneeRecommendationOutput(
                recommendations=recommendations,
                has_strong_match=has_strong_match,
            ),
            input_tokens=0,
            output_tokens=0,
            model=self.model,
            provider=self.provider,
        )

    async def _load_team_members(
        self,
        workspace_id: UUID,
        project_id: UUID,
    ) -> list[TeamMember]:
        """Load team members from database.

        Args:
            workspace_id: Workspace UUID.
            project_id: Project UUID.

        Returns:
            List of team members with workload info.
        """
        from sqlalchemy import and_, func, select

        from pilot_space.infrastructure.database.models import (
            Issue,
            User,
            WorkspaceMember,
        )

        # Get workspace members
        members_query = (
            select(User)
            .join(WorkspaceMember, User.id == WorkspaceMember.user_id)
            .where(
                and_(
                    WorkspaceMember.workspace_id == workspace_id,
                    WorkspaceMember.is_deleted == False,  # noqa: E712
                )
            )
        )
        result = await self._session.execute(members_query)
        users = result.scalars().all()

        team_members: list[TeamMember] = []
        for user in users:
            # Get current workload (active issues)
            workload_query = (
                select(func.count())
                .select_from(Issue)
                .join(Issue.state)
                .where(
                    and_(
                        Issue.assignee_id == user.id,
                        Issue.project_id == project_id,
                        Issue.is_deleted == False,  # noqa: E712
                        # Active states
                    )
                )
            )
            workload_result = await self._session.execute(workload_query)
            current_workload = workload_result.scalar() or 0

            # Get expertise labels (labels they've worked on)
            expertise_labels: list[str] = []  # TODO: Query from completed issues

            team_members.append(
                TeamMember(
                    user_id=user.id,
                    name=user.full_name or user.email,
                    email=user.email,
                    current_workload=current_workload,
                    expertise_labels=expertise_labels,
                )
            )

        return team_members

    async def _score_members(
        self,
        team_members: list[TeamMember],
        issue_labels: list[str],
        _issue_title: str,
    ) -> list[tuple[TeamMember, float, str]]:
        """Score team members for assignment.

        Args:
            team_members: Available members.
            issue_labels: Issue labels.
            _issue_title: Issue title (reserved for future NLP matching).

        Returns:
            List of (member, score, reason) tuples.
        """
        scored: list[tuple[TeamMember, float, str]] = []

        for member in team_members:
            score = 0.5  # Base score
            reasons: list[str] = []

            # Label expertise matching
            if issue_labels and member.expertise_labels:
                matching_labels = set(issue_labels) & set(member.expertise_labels)
                if matching_labels:
                    label_score = len(matching_labels) / len(issue_labels) * 0.3
                    score += label_score
                    reasons.append(f"Expert in: {', '.join(matching_labels)}")

            # Workload balancing (lower is better)
            if member.current_workload == 0:
                score += 0.2
                reasons.append("Available (no active issues)")
            elif member.current_workload <= 3:
                score += 0.1
                reasons.append(f"Light workload ({member.current_workload} issues)")
            elif member.current_workload >= 7:
                score -= 0.15
                reasons.append(f"Heavy workload ({member.current_workload} issues)")

            # Recent activity bonus
            if member.recent_issue_count > 0:
                activity_score = min(member.recent_issue_count / 10, 0.1)
                score += activity_score
                reasons.append(f"Active contributor ({member.recent_issue_count} recent)")

            reason = " | ".join(reasons) if reasons else "Available team member"
            scored.append((member, score, reason))

        return scored

    def validate_input(self, input_data: AssigneeRecommendationInput) -> None:
        """Validate input data.

        Args:
            input_data: Input to validate.

        Raises:
            ValueError: If input is invalid.
        """
        if not input_data.issue_title:
            raise ValueError("Issue title is required for assignee recommendation")


__all__ = [
    "AssigneeRecommendation",
    "AssigneeRecommendationInput",
    "AssigneeRecommendationOutput",
    "AssigneeRecommenderAgent",
    "TeamMember",
]
