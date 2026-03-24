"""Update Issue service with activity tracking.

T126: Create UpdateIssueService with field-level change detection.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from pilot_space.domain.exceptions import NotFoundError, ValidationError
from pilot_space.infrastructure.database.models import (
    Activity,
    ActivityType,
    Issue,
    IssuePriority,
)
from pilot_space.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from datetime import date
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from pilot_space.infrastructure.database.repositories import (
        ActivityRepository,
        IssueRepository,
        LabelRepository,
    )
    from pilot_space.infrastructure.database.repositories.audit_log_repository import (
        AuditLogRepository,
    )
    from pilot_space.infrastructure.queue.supabase_queue import SupabaseQueueClient

logger = get_logger(__name__)


# Sentinel for unchanged values
class _Unchanged:
    """Sentinel class for unchanged fields."""


UNCHANGED = _Unchanged()


@dataclass
class UpdateIssuePayload:
    """Payload for updating an issue.

    Uses sentinel value UNCHANGED for fields that should not be modified.
    None means explicitly set to null.
    """

    # Required
    issue_id: UUID
    actor_id: UUID

    # Optional fields (UNCHANGED = no change, None = set to null)
    name: str | _Unchanged = UNCHANGED
    description: str | None | _Unchanged = UNCHANGED
    description_html: str | None | _Unchanged = UNCHANGED
    priority: IssuePriority | _Unchanged = UNCHANGED
    state_id: UUID | _Unchanged = UNCHANGED
    assignee_id: UUID | None | _Unchanged = UNCHANGED
    cycle_id: UUID | None | _Unchanged = UNCHANGED
    module_id: UUID | None | _Unchanged = UNCHANGED
    parent_id: UUID | None | _Unchanged = UNCHANGED
    estimate_points: int | None | _Unchanged = UNCHANGED
    # T-245: Time estimate in hours (0.5 increments)
    estimate_hours: float | None | _Unchanged = UNCHANGED
    start_date: date | None | _Unchanged = UNCHANGED
    target_date: date | None | _Unchanged = UNCHANGED
    sort_order: int | _Unchanged = UNCHANGED
    label_ids: list[UUID] | _Unchanged = UNCHANGED

    # Acceptance criteria (list of structured dicts matching JSONB model)
    acceptance_criteria: list[dict[str, Any]] | None | _Unchanged = UNCHANGED

    # AI metadata update
    ai_metadata: dict[str, Any] | None | _Unchanged = UNCHANGED


@dataclass
class UpdateIssueResult:
    """Result from issue update."""

    issue: Issue
    activities: list[Activity]
    changed_fields: list[str]


class UpdateIssueService:
    """Service for updating issues with activity tracking.

    Handles:
    - Field-level change detection
    - State transition logging
    - Assignment changes
    - Label updates
    - Activity creation for each change
    """

    def __init__(
        self,
        session: AsyncSession,
        issue_repository: IssueRepository,
        activity_repository: ActivityRepository,
        label_repository: LabelRepository,
        queue: SupabaseQueueClient | None = None,
        audit_log_repository: AuditLogRepository | None = None,
    ) -> None:
        """Initialize service.

        Args:
            session: Async database session.
            issue_repository: Issue repository.
            activity_repository: Activity repository.
            label_repository: Label repository.
            queue: Optional queue client for KG population.
            audit_log_repository: Optional audit log repository for compliance writes.
        """
        self._session = session
        self._issue_repo = issue_repository
        self._activity_repo = activity_repository
        self._label_repo = label_repository
        self._queue = queue
        self._audit_repo = audit_log_repository

    async def execute(self, payload: UpdateIssuePayload) -> UpdateIssueResult:
        """Update an issue.

        Args:
            payload: Update parameters.

        Returns:
            UpdateIssueResult with updated issue and activities.

        Raises:
            ValueError: If issue not found or invalid data.
        """
        logger.info(
            "Updating issue",
            extra={
                "issue_id": str(payload.issue_id),
                "actor_id": str(payload.actor_id),
            },
        )

        # Get existing issue
        issue = await self._issue_repo.get_by_id_with_relations(payload.issue_id)
        if not issue:
            raise NotFoundError(f"Issue not found: {payload.issue_id}")

        activities: list[Activity] = []
        changed_fields: list[str] = []

        # Track changes and create activities
        if not isinstance(payload.name, _Unchanged):
            if not payload.name or not payload.name.strip():
                raise ValidationError("Issue name is required")
            if len(payload.name) > 255:
                raise ValidationError("Issue name must be 255 characters or less")
            if payload.name != issue.name:
                old_value = issue.name
                issue.name = payload.name.strip()
                changed_fields.append("name")
                activities.append(
                    Activity.create_for_field_update(
                        workspace_id=issue.workspace_id,
                        issue_id=issue.id,
                        actor_id=payload.actor_id,
                        field="name",
                        old_value=old_value,
                        new_value=issue.name,
                    )
                )

        if not isinstance(payload.description, _Unchanged):
            if payload.description != issue.description:
                old_value = issue.description
                issue.description = payload.description
                changed_fields.append("description")
                activities.append(
                    Activity.create_for_field_update(
                        workspace_id=issue.workspace_id,
                        issue_id=issue.id,
                        actor_id=payload.actor_id,
                        field="description",
                        old_value=old_value[:100] if old_value else None,
                        new_value=payload.description[:100] if payload.description else None,
                    )
                )

        if not isinstance(payload.description_html, _Unchanged):
            if payload.description_html != issue.description_html:
                issue.description_html = payload.description_html
                changed_fields.append("description_html")

        if not isinstance(payload.priority, _Unchanged):
            if payload.priority != issue.priority:
                old_value = issue.priority.value
                issue.priority = payload.priority
                changed_fields.append("priority")
                activities.append(
                    Activity(
                        workspace_id=issue.workspace_id,
                        issue_id=issue.id,
                        actor_id=payload.actor_id,
                        activity_type=ActivityType.PRIORITY_CHANGED,
                        field="priority",
                        old_value=old_value,
                        new_value=payload.priority.value,
                    )
                )

        if not isinstance(payload.state_id, _Unchanged):
            if payload.state_id != issue.state_id:
                old_state = issue.state
                old_state_id = issue.state_id
                issue.state_id = payload.state_id
                changed_fields.append("state_id")

                # Get new state name for activity
                from sqlalchemy import select

                from pilot_space.infrastructure.database.models import State

                state_query = select(State).where(State.id == payload.state_id)
                state_result = await self._session.execute(state_query)
                new_state = state_result.scalar_one_or_none()

                activities.append(
                    Activity.create_for_state_change(
                        workspace_id=issue.workspace_id,
                        issue_id=issue.id,
                        actor_id=payload.actor_id,
                        old_state_id=old_state_id,
                        old_state_name=old_state.name if old_state else "Unknown",
                        new_state_id=payload.state_id,
                        new_state_name=new_state.name if new_state else "Unknown",
                    )
                )

        if not isinstance(payload.assignee_id, _Unchanged):
            if payload.assignee_id != issue.assignee_id:
                old_assignee_id = issue.assignee_id
                issue.assignee_id = payload.assignee_id
                changed_fields.append("assignee_id")

                if payload.assignee_id is None:
                    activity_type = ActivityType.UNASSIGNED
                    metadata = {
                        "previous_assignee_id": str(old_assignee_id) if old_assignee_id else None
                    }
                else:
                    activity_type = ActivityType.ASSIGNED
                    metadata = {
                        "previous_assignee_id": str(old_assignee_id) if old_assignee_id else None,
                        "new_assignee_id": str(payload.assignee_id),
                    }

                activities.append(
                    Activity(
                        workspace_id=issue.workspace_id,
                        issue_id=issue.id,
                        actor_id=payload.actor_id,
                        activity_type=activity_type,
                        activity_metadata=metadata,
                    )
                )

        if not isinstance(payload.cycle_id, _Unchanged):
            if payload.cycle_id != issue.cycle_id:
                old_cycle_id = issue.cycle_id
                issue.cycle_id = payload.cycle_id
                changed_fields.append("cycle_id")

                if payload.cycle_id is None:
                    activity_type = ActivityType.REMOVED_FROM_CYCLE
                else:
                    activity_type = ActivityType.ADDED_TO_CYCLE

                activities.append(
                    Activity(
                        workspace_id=issue.workspace_id,
                        issue_id=issue.id,
                        actor_id=payload.actor_id,
                        activity_type=activity_type,
                        activity_metadata={
                            "old_cycle_id": str(old_cycle_id) if old_cycle_id else None,
                            "new_cycle_id": str(payload.cycle_id) if payload.cycle_id else None,
                        },
                    )
                )

        if not isinstance(payload.module_id, _Unchanged):
            if payload.module_id != issue.module_id:
                old_module_id = issue.module_id
                issue.module_id = payload.module_id
                changed_fields.append("module_id")

                if payload.module_id is None:
                    activity_type = ActivityType.REMOVED_FROM_MODULE
                else:
                    activity_type = ActivityType.ADDED_TO_MODULE

                activities.append(
                    Activity(
                        workspace_id=issue.workspace_id,
                        issue_id=issue.id,
                        actor_id=payload.actor_id,
                        activity_type=activity_type,
                        activity_metadata={
                            "old_module_id": str(old_module_id) if old_module_id else None,
                            "new_module_id": str(payload.module_id) if payload.module_id else None,
                        },
                    )
                )

        if not isinstance(payload.parent_id, _Unchanged):
            if payload.parent_id != issue.parent_id:
                old_parent_id = issue.parent_id
                issue.parent_id = payload.parent_id
                changed_fields.append("parent_id")

                if payload.parent_id is None:
                    activity_type = ActivityType.PARENT_REMOVED
                else:
                    activity_type = ActivityType.PARENT_SET

                activities.append(
                    Activity(
                        workspace_id=issue.workspace_id,
                        issue_id=issue.id,
                        actor_id=payload.actor_id,
                        activity_type=activity_type,
                        activity_metadata={
                            "old_parent_id": str(old_parent_id) if old_parent_id else None,
                            "new_parent_id": str(payload.parent_id) if payload.parent_id else None,
                        },
                    )
                )

        if not isinstance(payload.estimate_points, _Unchanged):
            if payload.estimate_points != issue.estimate_points:
                old_value = str(issue.estimate_points) if issue.estimate_points else None
                issue.estimate_points = payload.estimate_points
                changed_fields.append("estimate_points")
                activities.append(
                    Activity(
                        workspace_id=issue.workspace_id,
                        issue_id=issue.id,
                        actor_id=payload.actor_id,
                        activity_type=ActivityType.ESTIMATE_SET,
                        field="estimate_points",
                        old_value=old_value,
                        new_value=str(payload.estimate_points) if payload.estimate_points else None,
                    )
                )

        if not isinstance(payload.estimate_hours, _Unchanged):
            current_eh = float(issue.estimate_hours) if issue.estimate_hours is not None else None
            if payload.estimate_hours != current_eh:
                old_value = str(current_eh) if current_eh is not None else None
                issue.estimate_hours = payload.estimate_hours
                changed_fields.append("estimate_hours")
                activities.append(
                    Activity(
                        workspace_id=issue.workspace_id,
                        issue_id=issue.id,
                        actor_id=payload.actor_id,
                        activity_type=ActivityType.ESTIMATE_SET,
                        field="estimate_hours",
                        old_value=old_value,
                        new_value=str(payload.estimate_hours)
                        if payload.estimate_hours is not None
                        else None,
                    )
                )

        if not isinstance(payload.start_date, _Unchanged):
            if payload.start_date != issue.start_date:
                old_value = issue.start_date.isoformat() if issue.start_date else None
                issue.start_date = payload.start_date
                changed_fields.append("start_date")
                activities.append(
                    Activity(
                        workspace_id=issue.workspace_id,
                        issue_id=issue.id,
                        actor_id=payload.actor_id,
                        activity_type=ActivityType.START_DATE_SET,
                        field="start_date",
                        old_value=old_value,
                        new_value=payload.start_date.isoformat() if payload.start_date else None,
                    )
                )

        if not isinstance(payload.target_date, _Unchanged):
            if payload.target_date != issue.target_date:
                old_value = issue.target_date.isoformat() if issue.target_date else None
                issue.target_date = payload.target_date
                changed_fields.append("target_date")
                activities.append(
                    Activity(
                        workspace_id=issue.workspace_id,
                        issue_id=issue.id,
                        actor_id=payload.actor_id,
                        activity_type=ActivityType.TARGET_DATE_SET,
                        field="target_date",
                        old_value=old_value,
                        new_value=payload.target_date.isoformat() if payload.target_date else None,
                    )
                )

        if not isinstance(payload.sort_order, _Unchanged):
            if payload.sort_order != issue.sort_order:
                issue.sort_order = payload.sort_order
                changed_fields.append("sort_order")

        if not isinstance(payload.ai_metadata, _Unchanged):
            if payload.ai_metadata != issue.ai_metadata:
                issue.ai_metadata = payload.ai_metadata
                changed_fields.append("ai_metadata")

        if not isinstance(payload.acceptance_criteria, _Unchanged):
            if payload.acceptance_criteria != issue.acceptance_criteria:
                issue.acceptance_criteria = payload.acceptance_criteria
                changed_fields.append("acceptance_criteria")

        # Handle label updates
        if not isinstance(payload.label_ids, _Unchanged):
            current_label_ids = {label.id for label in issue.labels}
            new_label_ids = set(payload.label_ids)

            if current_label_ids != new_label_ids:
                await self._issue_repo.bulk_update_labels(issue.id, payload.label_ids)
                changed_fields.append("labels")

                # Create activities for added/removed labels
                added_labels = new_label_ids - current_label_ids
                removed_labels = current_label_ids - new_label_ids

                for label_id in added_labels:
                    activities.append(
                        Activity(
                            workspace_id=issue.workspace_id,
                            issue_id=issue.id,
                            actor_id=payload.actor_id,
                            activity_type=ActivityType.LABEL_ADDED,
                            activity_metadata={"label_id": str(label_id)},
                        )
                    )

                for label_id in removed_labels:
                    activities.append(
                        Activity(
                            workspace_id=issue.workspace_id,
                            issue_id=issue.id,
                            actor_id=payload.actor_id,
                            activity_type=ActivityType.LABEL_REMOVED,
                            activity_metadata={"label_id": str(label_id)},
                        )
                    )

        # Save issue changes
        if changed_fields:
            issue = await self._issue_repo.update(issue)

        # Save activities
        saved_activities = []
        for activity in activities:
            saved_activities.append(await self._activity_repo.create(activity))

        # Reload with relationships
        issue = await self._issue_repo.get_by_id_with_relations(issue.id)

        logger.info(
            "Issue updated",
            extra={
                "issue_id": str(payload.issue_id),
                "changed_fields": changed_fields,
            },
        )

        # Enqueue KG populate on content-relevant changes (non-fatal)
        kg_relevant_fields = {"name", "description"}
        if (
            self._queue is not None
            and issue is not None
            and kg_relevant_fields & set(changed_fields)
        ):
            try:
                from pilot_space.infrastructure.queue.models import QueueName

                await self._queue.enqueue(
                    QueueName.AI_NORMAL,
                    {
                        "task_type": "kg_populate",
                        "entity_type": "issue",
                        "entity_id": str(issue.id),
                        "workspace_id": str(issue.workspace_id),
                        "project_id": str(issue.project_id),
                    },
                )
            except Exception as exc:
                logger.warning("UpdateIssueService: failed to enqueue kg_populate: %s", exc)

        # Write audit log entry for update (non-fatal)
        if self._audit_repo is not None and issue is not None and changed_fields:
            try:
                from pilot_space.infrastructure.database.models.audit_log import ActorType

                await self._audit_repo.create(
                    workspace_id=issue.workspace_id,
                    actor_id=payload.actor_id,
                    actor_type=ActorType.USER,
                    action="issue.update",
                    resource_type="issue",
                    resource_id=issue.id,
                    payload={"changed_fields": changed_fields},
                    ip_address=None,
                )
            except Exception as exc:
                logger.warning("UpdateIssueService: failed to write audit log: %s", exc)

        return UpdateIssueResult(
            issue=issue,  # type: ignore[arg-type]
            activities=saved_activities,
            changed_fields=changed_fields,
        )


__all__ = ["UNCHANGED", "UpdateIssuePayload", "UpdateIssueResult", "UpdateIssueService"]
