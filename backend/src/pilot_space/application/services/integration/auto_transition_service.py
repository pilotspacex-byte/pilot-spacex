"""Auto-transition service for PR-driven state changes.

T184: Create AutoTransitionService for PR merge auto-transitions.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from sqlalchemy import and_, select

from pilot_space.infrastructure.database.models import (
    Activity,
    ActivityType,
    State,
    StateGroup,
)

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from pilot_space.infrastructure.database.repositories import (
        ActivityRepository,
        IssueRepository,
    )

logger = logging.getLogger(__name__)


class AutoTransitionError(Exception):
    """Raised when auto-transition fails."""


@dataclass
class TransitionRule:
    """Rule for auto-transitioning issues.

    Attributes:
        event: Event that triggers the transition.
        from_groups: Source state groups (None = any).
        to_group: Target state group.
        enabled: Whether rule is enabled.
    """

    event: str  # pr_opened, pr_merged, pr_closed
    from_groups: list[StateGroup] | None
    to_group: StateGroup
    enabled: bool = True


# Default transition rules
DEFAULT_RULES: list[TransitionRule] = [
    # PR opened -> In Progress (from any unstarted state)
    TransitionRule(
        event="pr_opened",
        from_groups=[StateGroup.UNSTARTED],
        to_group=StateGroup.STARTED,
    ),
    # PR merged -> Done (from any non-completed state)
    TransitionRule(
        event="pr_merged",
        from_groups=[StateGroup.UNSTARTED, StateGroup.STARTED],
        to_group=StateGroup.COMPLETED,
    ),
]


@dataclass
class AutoTransitionPayload:
    """Payload for auto-transition.

    Attributes:
        workspace_id: Workspace UUID.
        issue_ids: Issue UUIDs to potentially transition.
        event: Event that triggered the transition.
        pr_number: PR number (for metadata).
        pr_title: PR title (for metadata).
        repository: Repository full name.
        rules: Custom rules (uses defaults if None).
    """

    workspace_id: UUID
    issue_ids: list[UUID]
    event: str
    pr_number: int | None = None
    pr_title: str | None = None
    repository: str | None = None
    rules: list[TransitionRule] | None = None


@dataclass
class TransitionedIssue:
    """Issue that was auto-transitioned."""

    issue_id: UUID
    from_state: str
    to_state: str


@dataclass
class AutoTransitionResult:
    """Result from auto-transition."""

    transitioned: list[TransitionedIssue] = field(default_factory=list)
    skipped: int = 0
    errors: list[str] = field(default_factory=list)


class AutoTransitionService:
    """Service for auto-transitioning issues based on PR events.

    Handles:
    - PR opened -> In Progress
    - PR merged -> Done
    - Configurable rules per workspace
    """

    def __init__(
        self,
        session: AsyncSession,
        issue_repo: IssueRepository,
        activity_repo: ActivityRepository,
    ) -> None:
        """Initialize service.

        Args:
            session: Async database session.
            issue_repo: Issue repository.
            activity_repo: Activity repository.
        """
        self._session = session
        self._issue_repo = issue_repo
        self._activity_repo = activity_repo

    async def execute(self, payload: AutoTransitionPayload) -> AutoTransitionResult:
        """Apply auto-transitions to issues.

        Args:
            payload: Transition parameters.

        Returns:
            AutoTransitionResult with affected issues.
        """
        result = AutoTransitionResult()
        rules = payload.rules or DEFAULT_RULES

        # Find matching rule
        matching_rules = [r for r in rules if r.event == payload.event and r.enabled]
        if not matching_rules:
            logger.debug(f"No matching rules for event: {payload.event}")
            return result

        for issue_id in payload.issue_ids:
            try:
                transitioned = await self._try_transition(
                    workspace_id=payload.workspace_id,
                    issue_id=issue_id,
                    rules=matching_rules,
                    metadata={
                        "event": payload.event,
                        "pr_number": payload.pr_number,
                        "pr_title": payload.pr_title,
                        "repository": payload.repository,
                    },
                )
                if transitioned:
                    result.transitioned.append(transitioned)
                else:
                    result.skipped += 1
            except Exception as e:
                logger.warning(f"Error transitioning issue {issue_id}: {e}")
                result.errors.append(str(e))

        logger.info(
            "Auto-transition completed",
            extra={
                "event": payload.event,
                "transitioned": len(result.transitioned),
                "skipped": result.skipped,
            },
        )

        return result

    async def _try_transition(
        self,
        workspace_id: UUID,
        issue_id: UUID,
        rules: list[TransitionRule],
        metadata: dict[str, Any],
    ) -> TransitionedIssue | None:
        """Try to transition a single issue.

        Args:
            workspace_id: Workspace UUID.
            issue_id: Issue UUID.
            rules: Matching transition rules.
            metadata: Activity metadata.

        Returns:
            TransitionedIssue if transitioned, None otherwise.
        """
        # Get issue with state
        issue = await self._issue_repo.get_by_id_with_relations(issue_id)
        if not issue:
            return None

        current_group = issue.state.group if issue.state else None

        # Find applicable rule
        applicable_rule: TransitionRule | None = None
        for rule in rules:
            if rule.from_groups is None or current_group in rule.from_groups:
                applicable_rule = rule
                break

        if not applicable_rule:
            return None

        # Skip if already in target group
        if current_group == applicable_rule.to_group:
            return None

        # Find target state
        target_state = await self._find_state(
            project_id=issue.project_id,
            group=applicable_rule.to_group,
        )
        if not target_state:
            return None

        # Transition
        old_state_name = issue.state.name if issue.state else None
        issue.state_id = target_state.id
        await self._session.flush()

        # Record activity
        activity = Activity(
            workspace_id=workspace_id,
            issue_id=issue_id,
            actor_id=None,  # System action
            activity_type=ActivityType.STATE_CHANGED,
            field="state",
            old_value=old_state_name,
            new_value=target_state.name,
            activity_metadata={
                "auto_transition": True,
                **metadata,
            },
        )
        await self._activity_repo.create(activity)

        return TransitionedIssue(
            issue_id=issue_id,
            from_state=old_state_name or "",
            to_state=target_state.name,
        )

    async def _find_state(
        self,
        project_id: UUID,
        group: StateGroup,
    ) -> State | None:
        """Find a state by group for a project.

        Args:
            project_id: Project UUID.
            group: Target state group.

        Returns:
            State if found, None otherwise.
        """
        query = (
            select(State)
            .where(
                and_(
                    State.project_id == project_id,
                    State.group == group,
                    State.is_deleted == False,  # noqa: E712
                )
            )
            .order_by(State.sequence)
            .limit(1)
        )
        result = await self._session.execute(query)
        return result.scalar_one_or_none()

    def get_default_rules(self) -> list[TransitionRule]:
        """Get default transition rules.

        Returns:
            List of default TransitionRule objects.
        """
        return DEFAULT_RULES.copy()


__all__ = [
    "AutoTransitionError",
    "AutoTransitionPayload",
    "AutoTransitionResult",
    "AutoTransitionService",
    "TransitionRule",
    "TransitionedIssue",
]
