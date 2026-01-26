"""Assignee Recommender Agent using Claude Agent SDK.

T132: Create AssigneeRecommenderAgent based on workload and expertise.
SDK Migration: Migrated from legacy BaseAgent to SDKBaseAgent pattern.

This agent recommends issue assignees based on:
- Label expertise (previous work on similar issues)
- Current workload balance
- Recent activity in the project

Can work without AI for simple heuristic matching.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING
from uuid import UUID

from pilot_space.ai.agents.sdk_base import AgentContext, SDKBaseAgent

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from pilot_space.ai.infrastructure.cost_tracker import CostTracker
    from pilot_space.ai.infrastructure.key_storage import SecureKeyStorage
    from pilot_space.ai.infrastructure.resilience import ResilientExecutor
    from pilot_space.ai.providers.provider_selector import ProviderSelector
    from pilot_space.ai.tools.mcp_server import ToolRegistry

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
        db_session: Database session for loading team data.
    """

    issue_title: str
    workspace_id: UUID
    project_id: UUID
    db_session: AsyncSession
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
    SDKBaseAgent[AssigneeRecommendationInput, AssigneeRecommendationOutput]
):
    """Agent for recommending issue assignees.

    Uses heuristics and optionally AI to suggest assignees based on:
    - Label expertise (previous work on similar issues)
    - Current workload balance
    - Recent activity in the project

    Can work without AI for simple heuristic matching.

    Architecture:
    - Extends SDKBaseAgent for infrastructure integration
    - Uses claude-3-5-haiku for fast recommendations
    - Falls back to rule-based scoring when AI unavailable
    - Tracks token usage and costs

    Usage:
        agent = AssigneeRecommenderAgent(
            tool_registry=tool_registry,
            provider_selector=provider_selector,
            cost_tracker=cost_tracker,
            resilient_executor=resilient_executor,
            key_storage=key_storage,
        )
        result = await agent.run(input_data, context)
    """

    AGENT_NAME = "assignee_recommender"
    DEFAULT_MODEL = "claude-3-5-haiku-20241022"

    def __init__(
        self,
        tool_registry: ToolRegistry,
        provider_selector: ProviderSelector,
        cost_tracker: CostTracker,
        resilient_executor: ResilientExecutor,
        key_storage: SecureKeyStorage,
    ) -> None:
        """Initialize assignee recommender agent.

        Args:
            tool_registry: Registry for MCP tool access
            provider_selector: Provider/model selection service
            cost_tracker: Cost tracking service
            resilient_executor: Retry and circuit breaker service
            key_storage: Secure API key storage
        """
        super().__init__(
            tool_registry=tool_registry,
            provider_selector=provider_selector,
            cost_tracker=cost_tracker,
            resilient_executor=resilient_executor,
        )
        self._key_storage = key_storage

    def get_model(self) -> tuple[str, str]:
        """Get provider and model for assignee recommendation.

        Returns:
            Tuple of ("anthropic", "claude-3-5-haiku-20241022")
        """
        return ("anthropic", self.DEFAULT_MODEL)

    async def execute(
        self,
        input_data: AssigneeRecommendationInput,
        context: AgentContext,
    ) -> AssigneeRecommendationOutput:
        """Execute assignee recommendation.

        Args:
            input_data: Issue and team context.
            context: Agent execution context.

        Returns:
            AssigneeRecommendationOutput with recommendations.
        """
        # Validate input
        self._validate_input(input_data)

        # Get team members if not provided
        team_members = input_data.team_members
        if not team_members:
            team_members = await self._load_team_members(
                input_data.db_session,
                input_data.workspace_id,
                input_data.project_id,
            )

        if not team_members:
            return AssigneeRecommendationOutput()

        # Score each team member using rule-based heuristics
        scored_members = await self._score_members(
            team_members=team_members,
            issue_labels=input_data.issue_labels or [],
            issue_title=input_data.issue_title,
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

        # Track token usage (rule-based, so no tokens used)
        await self.track_usage(
            context=context,
            input_tokens=0,
            output_tokens=0,
        )

        return AssigneeRecommendationOutput(
            recommendations=recommendations,
            has_strong_match=has_strong_match,
        )

    def _validate_input(self, input_data: AssigneeRecommendationInput) -> None:
        """Validate input data.

        Args:
            input_data: Input to validate.

        Raises:
            ValueError: If input is invalid.
        """
        if not input_data.issue_title:
            raise ValueError("Issue title is required for assignee recommendation")

        if not input_data.db_session:
            raise ValueError("Database session is required")

    async def _load_team_members(
        self,
        session: AsyncSession,
        workspace_id: UUID,
        project_id: UUID,
    ) -> list[TeamMember]:
        """Load team members from database.

        Args:
            session: Async database session.
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
        result = await session.execute(members_query)
        users = result.scalars().all()

        team_members: list[TeamMember] = []
        for user in users:
            # Get current workload (active issues)
            workload_query = (
                select(func.count())
                .select_from(Issue)
                .where(
                    and_(
                        Issue.assignee_id == user.id,
                        Issue.project_id == project_id,
                        Issue.is_deleted == False,  # noqa: E712
                        # Active states
                    )
                )
            )
            workload_result = await session.execute(workload_query)
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
        issue_title: str,  # noqa: ARG002
    ) -> list[tuple[TeamMember, float, str]]:
        """Score team members for assignment.

        Args:
            team_members: Available members.
            issue_labels: Issue labels.
            issue_title: Issue title (reserved for future NLP matching).

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


__all__ = [
    "AssigneeRecommendation",
    "AssigneeRecommendationInput",
    "AssigneeRecommendationOutput",
    "AssigneeRecommenderAgent",
    "TeamMember",
]
