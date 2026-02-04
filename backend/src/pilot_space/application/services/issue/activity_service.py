"""Activity service for issue audit trail.

T129: Create ActivityService for issue history management.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from pilot_space.infrastructure.database.models import Activity, ActivityType

if TYPE_CHECKING:
    from collections.abc import Sequence
    from uuid import UUID

    from pilot_space.infrastructure.database.repositories import ActivityRepository

logger = logging.getLogger(__name__)


@dataclass
class CreateActivityPayload:
    """Payload for creating an activity."""

    workspace_id: UUID
    issue_id: UUID
    activity_type: ActivityType
    actor_id: UUID | None = None
    field: str | None = None
    old_value: str | None = None
    new_value: str | None = None
    comment: str | None = None
    metadata: dict[str, Any] | None = None


@dataclass
class ActivityTimelineResult:
    """Result from getting activity timeline."""

    activities: Sequence[Activity]
    total: int


class ActivityService:
    """Service for activity management.

    Handles:
    - Activity creation
    - Timeline retrieval
    - Comment management
    - AI activity tracking
    """

    def __init__(
        self,
        activity_repository: ActivityRepository,
    ) -> None:
        """Initialize service.

        Args:
            activity_repository: Activity repository.
        """
        self._activity_repo = activity_repository

    async def create(self, payload: CreateActivityPayload) -> Activity:
        """Create an activity.

        Args:
            payload: Activity parameters.

        Returns:
            Created activity.
        """
        activity = Activity(
            workspace_id=payload.workspace_id,
            issue_id=payload.issue_id,
            actor_id=payload.actor_id,
            activity_type=payload.activity_type,
            field=payload.field,
            old_value=payload.old_value,
            new_value=payload.new_value,
            comment=payload.comment,
            activity_metadata=payload.metadata,
        )

        return await self._activity_repo.create(activity)

    async def get_timeline(
        self,
        issue_id: UUID,
        *,
        limit: int = 50,
        offset: int = 0,
        include_comments: bool = True,
    ) -> ActivityTimelineResult:
        """Get activity timeline for an issue.

        Args:
            issue_id: Issue UUID.
            limit: Max activities.
            offset: Skip first N.
            include_comments: Whether to include comment activities.

        Returns:
            ActivityTimelineResult with activities.
        """
        activities = await self._activity_repo.get_issue_timeline(
            issue_id,
            limit=limit,
            offset=offset,
            include_comments=include_comments,
        )

        total = await self._activity_repo.count_issue_activities(
            issue_id,
            include_comments=include_comments,
        )

        return ActivityTimelineResult(
            activities=activities,
            total=total,
        )

    async def get_comments(
        self,
        issue_id: UUID,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[Activity]:
        """Get comments for an issue.

        Args:
            issue_id: Issue UUID.
            limit: Max comments.
            offset: Skip first N.

        Returns:
            List of comment activities.
        """
        return await self._activity_repo.get_issue_comments(
            issue_id,
            limit=limit,
            offset=offset,
        )

    async def add_comment(
        self,
        workspace_id: UUID,
        issue_id: UUID,
        actor_id: UUID,
        comment_text: str,
    ) -> Activity:
        """Add a comment to an issue.

        Args:
            workspace_id: Workspace UUID.
            issue_id: Issue UUID.
            actor_id: Commenter UUID.
            comment_text: Comment content.

        Returns:
            Created comment activity.

        Raises:
            ValueError: If comment is empty.
        """
        if not comment_text or not comment_text.strip():
            raise ValueError("Comment text is required")

        return await self.create(
            CreateActivityPayload(
                workspace_id=workspace_id,
                issue_id=issue_id,
                actor_id=actor_id,
                activity_type=ActivityType.COMMENT_ADDED,
                comment=comment_text.strip(),
            )
        )

    async def get_ai_activities(
        self,
        issue_id: UUID,
        *,
        limit: int = 20,
    ) -> Sequence[Activity]:
        """Get AI-related activities for an issue.

        Args:
            issue_id: Issue UUID.
            limit: Max activities.

        Returns:
            AI activities.
        """
        return await self._activity_repo.get_ai_activities(issue_id, limit=limit)

    async def get_state_history(
        self,
        issue_id: UUID,
        *,
        limit: int = 20,
    ) -> Sequence[Activity]:
        """Get state change history for an issue.

        Args:
            issue_id: Issue UUID.
            limit: Max activities.

        Returns:
            State change activities.
        """
        return await self._activity_repo.get_state_changes(issue_id, limit=limit)

    async def log_ai_enhancement(
        self,
        workspace_id: UUID,
        issue_id: UUID,
        enhancement_type: str,
        metadata: dict[str, Any],
    ) -> Activity:
        """Log an AI enhancement activity.

        Args:
            workspace_id: Workspace UUID.
            issue_id: Issue UUID.
            enhancement_type: Type of enhancement.
            metadata: Enhancement details.

        Returns:
            Created activity.
        """
        return await self.create(
            CreateActivityPayload(
                workspace_id=workspace_id,
                issue_id=issue_id,
                actor_id=None,  # AI action
                activity_type=ActivityType.AI_ENHANCED,
                metadata={
                    "enhancement_type": enhancement_type,
                    **metadata,
                },
            )
        )

    async def log_duplicate_detection(
        self,
        workspace_id: UUID,
        issue_id: UUID,
        duplicate_candidates: list[dict[str, Any]],
    ) -> Activity:
        """Log duplicate detection activity.

        Args:
            workspace_id: Workspace UUID.
            issue_id: Issue UUID.
            duplicate_candidates: List of potential duplicates.

        Returns:
            Created activity.
        """
        return await self.create(
            CreateActivityPayload(
                workspace_id=workspace_id,
                issue_id=issue_id,
                actor_id=None,  # AI action
                activity_type=ActivityType.DUPLICATE_DETECTED,
                metadata={
                    "duplicate_candidates": duplicate_candidates,
                    "candidate_count": len(duplicate_candidates),
                },
            )
        )

    async def log_suggestion_decision(
        self,
        workspace_id: UUID,
        issue_id: UUID,
        actor_id: UUID,
        suggestion_type: str,
        accepted: bool,
        suggestion_details: dict[str, Any],
    ) -> Activity:
        """Log user decision on AI suggestion.

        Args:
            workspace_id: Workspace UUID.
            issue_id: Issue UUID.
            actor_id: User who made decision.
            suggestion_type: Type of suggestion.
            accepted: Whether suggestion was accepted.
            suggestion_details: Details of the suggestion.

        Returns:
            Created activity.
        """
        activity_type = (
            ActivityType.AI_SUGGESTION_ACCEPTED if accepted else ActivityType.AI_SUGGESTION_REJECTED
        )

        return await self.create(
            CreateActivityPayload(
                workspace_id=workspace_id,
                issue_id=issue_id,
                actor_id=actor_id,
                activity_type=activity_type,
                metadata={
                    "suggestion_type": suggestion_type,
                    **suggestion_details,
                },
            )
        )


__all__ = ["ActivityService", "ActivityTimelineResult", "CreateActivityPayload"]
