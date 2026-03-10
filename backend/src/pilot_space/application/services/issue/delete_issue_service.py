"""Delete issue service with activity tracking."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from pilot_space.infrastructure.database.repositories.activity_repository import (
        ActivityRepository,
    )
    from pilot_space.infrastructure.database.repositories.audit_log_repository import (
        AuditLogRepository,
    )
    from pilot_space.infrastructure.database.repositories.issue_repository import (
        IssueRepository,
    )


@dataclass(frozen=True, slots=True)
class DeleteIssuePayload:
    """Payload for deleting an issue.

    Attributes:
        issue_id: The issue ID to delete.
        actor_id: The user ID performing the deletion.
    """

    issue_id: UUID
    actor_id: UUID


@dataclass(frozen=True, slots=True)
class DeleteIssueResult:
    """Result from issue deletion.

    Attributes:
        issue_id: ID of the deleted issue.
        success: Whether the deletion was successful.
    """

    issue_id: UUID
    success: bool


class DeleteIssueService:
    """Service for deleting issues (soft delete).

    Handles soft deletion of issues and tracks activity.
    """

    def __init__(
        self,
        session: AsyncSession,
        issue_repository: IssueRepository,
        activity_repository: ActivityRepository,
        audit_log_repository: AuditLogRepository | None = None,
    ) -> None:
        """Initialize DeleteIssueService.

        Args:
            session: The async database session.
            issue_repository: Repository for issue operations.
            activity_repository: Repository for activity tracking.
            audit_log_repository: Optional audit log repository for compliance writes.
        """
        self._session = session
        self._issue_repo = issue_repository
        self._activity_repo = activity_repository
        self._audit_repo = audit_log_repository

    async def execute(self, payload: DeleteIssuePayload) -> DeleteIssueResult:
        """Execute issue deletion.

        Args:
            payload: The deletion payload.

        Returns:
            DeleteIssueResult with deletion status.

        Raises:
            ValueError: If issue not found.
        """
        # Get issue
        issue = await self._issue_repo.get_by_id(payload.issue_id)
        if not issue:
            raise ValueError("Issue not found")

        # Soft delete
        await self._issue_repo.delete(issue)

        # Track deletion activity
        from pilot_space.infrastructure.database.models.activity import Activity, ActivityType

        activity = Activity(
            workspace_id=issue.workspace_id,
            issue_id=issue.id,
            actor_id=payload.actor_id,
            activity_type=ActivityType.DELETED,
            activity_metadata={"name": issue.name, "identifier": issue.identifier},
        )
        await self._activity_repo.create(activity)

        # Write audit log entry (non-fatal)
        if self._audit_repo is not None:
            try:
                from pilot_space.infrastructure.database.models.audit_log import ActorType

                await self._audit_repo.create(
                    workspace_id=issue.workspace_id,
                    actor_id=payload.actor_id,
                    actor_type=ActorType.USER,
                    action="issue.delete",
                    resource_type="issue",
                    resource_id=issue.id,
                    payload={
                        "before": {"name": issue.name, "identifier": issue.identifier},
                        "after": {},
                    },
                    ip_address=None,
                )
            except Exception as exc:
                import logging

                logging.getLogger(__name__).warning(
                    "DeleteIssueService: failed to write audit log: %s", exc
                )

        await self._session.commit()

        return DeleteIssueResult(issue_id=payload.issue_id, success=True)


__all__ = ["DeleteIssuePayload", "DeleteIssueResult", "DeleteIssueService"]
