"""Create Issue service with AI enhancement support.

T125: Create CreateIssueService with payload pattern.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from pilot_space.infrastructure.database.models import (
    Activity,
    ActivityType,
    Issue,
    IssuePriority,
)

if TYPE_CHECKING:
    from datetime import date
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from pilot_space.infrastructure.database.repositories import (
        ActivityRepository,
        IssueRepository,
        LabelRepository,
    )

logger = logging.getLogger(__name__)


@dataclass
class CreateIssuePayload:
    """Payload for creating a new issue.

    All fields except name have sensible defaults.
    AI enhancement fields are populated by IssueEnhancerAgent.
    """

    # Required
    workspace_id: UUID
    project_id: UUID
    reporter_id: UUID
    name: str

    # Optional
    description: str | None = None
    description_html: str | None = None
    priority: IssuePriority = IssuePriority.NONE
    state_id: UUID | None = None  # Will use project default if None
    assignee_id: UUID | None = None
    cycle_id: UUID | None = None
    module_id: UUID | None = None
    parent_id: UUID | None = None
    estimate_points: int | None = None
    start_date: date | None = None
    target_date: date | None = None
    label_ids: list[UUID] = field(default_factory=list)

    # AI enhancement metadata
    ai_metadata: dict[str, Any] | None = None
    ai_enhanced: bool = False


@dataclass
class CreateIssueResult:
    """Result from issue creation."""

    issue: Issue
    activities: list[Activity]
    ai_enhanced: bool = False


class CreateIssueService:
    """Service for creating issues with AI enhancement support.

    Handles:
    - Issue creation with sequence ID generation
    - Default state assignment
    - Label attachment
    - Activity logging
    - AI metadata storage
    """

    def __init__(
        self,
        session: AsyncSession,
        issue_repository: IssueRepository,
        activity_repository: ActivityRepository,
        label_repository: LabelRepository,
    ) -> None:
        """Initialize service.

        Args:
            session: Async database session.
            issue_repository: Issue repository.
            activity_repository: Activity repository.
            label_repository: Label repository.
        """
        self._session = session
        self._issue_repo = issue_repository
        self._activity_repo = activity_repository
        self._label_repo = label_repository

    async def execute(self, payload: CreateIssuePayload) -> CreateIssueResult:
        """Create a new issue.

        Args:
            payload: Issue creation parameters.

        Returns:
            CreateIssueResult with created issue and activities.

        Raises:
            ValueError: If required fields are missing or invalid.
        """
        logger.info(
            "Creating issue",
            extra={
                "workspace_id": str(payload.workspace_id),
                "project_id": str(payload.project_id),
                "reporter_id": str(payload.reporter_id),
                "ai_enhanced": payload.ai_enhanced,
            },
        )

        # Validate name
        if not payload.name or not payload.name.strip():
            raise ValueError("Issue name is required")
        if len(payload.name) > 255:
            raise ValueError("Issue name must be 255 characters or less")

        # Get next sequence ID for project
        sequence_id = await self._issue_repo.get_next_sequence_id(payload.project_id)

        # Get default state if not provided
        state_id = payload.state_id
        if not state_id:
            state_id = await self._get_default_state_id(payload.project_id)

        # Create issue
        issue = Issue(
            workspace_id=payload.workspace_id,
            project_id=payload.project_id,
            sequence_id=sequence_id,
            name=payload.name.strip(),
            description=payload.description,
            description_html=payload.description_html,
            priority=payload.priority,
            state_id=state_id,
            assignee_id=payload.assignee_id,
            reporter_id=payload.reporter_id,
            cycle_id=payload.cycle_id,
            module_id=payload.module_id,
            parent_id=payload.parent_id,
            estimate_points=payload.estimate_points,
            start_date=payload.start_date,
            target_date=payload.target_date,
            ai_metadata=payload.ai_metadata,
        )

        # Save issue
        issue = await self._issue_repo.create(issue)

        # Attach labels if provided
        if payload.label_ids:
            await self._issue_repo.bulk_update_labels(issue.id, payload.label_ids)

        # Create activity record
        activities: list[Activity] = []
        create_activity = Activity.create_for_issue_creation(
            workspace_id=payload.workspace_id,
            issue_id=issue.id,
            actor_id=payload.reporter_id,
            ai_enhanced=payload.ai_enhanced,
        )
        activities.append(await self._activity_repo.create(create_activity))

        # If AI enhanced, create additional activity
        if payload.ai_enhanced and payload.ai_metadata:
            ai_activity = Activity(
                workspace_id=payload.workspace_id,
                issue_id=issue.id,
                actor_id=None,  # AI action
                activity_type=ActivityType.AI_ENHANCED,
                activity_metadata=payload.ai_metadata,
            )
            activities.append(await self._activity_repo.create(ai_activity))

        # Reload with relationships
        issue = await self._issue_repo.get_by_id_with_relations(issue.id)

        logger.info(
            "Issue created",
            extra={
                "issue_id": str(issue.id) if issue else None,
                "identifier": issue.identifier if issue else None,
            },
        )

        return CreateIssueResult(
            issue=issue,  # type: ignore[arg-type]
            activities=activities,
            ai_enhanced=payload.ai_enhanced,
        )

    async def _get_default_state_id(self, project_id: UUID) -> UUID:
        """Get the default state for a project (first unstarted state).

        Args:
            project_id: Project UUID.

        Returns:
            Default state UUID.

        Raises:
            ValueError: If no default state found.
        """
        from sqlalchemy import and_, select

        from pilot_space.infrastructure.database.models import Project, State, StateGroup

        # Get workspace from project
        proj_query = select(Project.workspace_id).where(Project.id == project_id)
        proj_result = await self._session.execute(proj_query)
        workspace_id = proj_result.scalar_one_or_none()

        if not workspace_id:
            raise ValueError(f"Project not found: {project_id}")

        # Get first unstarted state for the project (or workspace default)
        state_query = (
            select(State)
            .where(
                and_(
                    State.workspace_id == workspace_id,
                    State.group == StateGroup.UNSTARTED,
                    State.is_deleted == False,  # noqa: E712
                )
            )
            .order_by(State.sequence)
            .limit(1)
        )
        state_result = await self._session.execute(state_query)
        state = state_result.scalar_one_or_none()

        if not state:
            raise ValueError(f"No default state found for project: {project_id}")

        return state.id


__all__ = ["CreateIssuePayload", "CreateIssueResult", "CreateIssueService"]
