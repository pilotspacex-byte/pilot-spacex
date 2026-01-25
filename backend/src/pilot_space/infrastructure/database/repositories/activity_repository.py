"""Activity repository for issue audit trail.

T123: Create ActivityRepository for issue history tracking.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import and_, select
from sqlalchemy.orm import joinedload

from pilot_space.infrastructure.database.models import Activity, ActivityType
from pilot_space.infrastructure.database.repositories.base import BaseRepository

if TYPE_CHECKING:
    from collections.abc import Sequence
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession


class ActivityRepository(BaseRepository[Activity]):
    """Repository for Activity entities.

    Provides:
    - Issue timeline queries
    - Activity type filtering
    - Actor lookups
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository.

        Args:
            session: Async database session.
        """
        super().__init__(session, Activity)

    async def get_issue_timeline(
        self,
        issue_id: UUID,
        *,
        limit: int = 50,
        offset: int = 0,
        include_comments: bool = True,
    ) -> Sequence[Activity]:
        """Get activity timeline for an issue.

        Activities are ordered by created_at descending (newest first).

        Args:
            issue_id: Issue UUID.
            limit: Max activities to return.
            offset: Skip first N activities.
            include_comments: Whether to include comment activities.

        Returns:
            List of activities.
        """
        query = (
            select(Activity)
            .options(joinedload(Activity.actor))
            .where(
                and_(
                    Activity.issue_id == issue_id,
                    Activity.is_deleted == False,  # noqa: E712
                )
            )
        )

        if not include_comments:
            comment_types = [
                ActivityType.COMMENT_ADDED,
                ActivityType.COMMENT_UPDATED,
                ActivityType.COMMENT_DELETED,
            ]
            query = query.where(Activity.activity_type.notin_(comment_types))

        query = query.order_by(Activity.created_at.desc()).offset(offset).limit(limit)

        result = await self.session.execute(query)
        return result.unique().scalars().all()

    async def get_issue_comments(
        self,
        issue_id: UUID,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[Activity]:
        """Get comments for an issue.

        Args:
            issue_id: Issue UUID.
            limit: Max comments to return.
            offset: Skip first N comments.

        Returns:
            List of comment activities.
        """
        query = (
            select(Activity)
            .options(joinedload(Activity.actor))
            .where(
                and_(
                    Activity.issue_id == issue_id,
                    Activity.activity_type == ActivityType.COMMENT_ADDED,
                    Activity.is_deleted == False,  # noqa: E712
                )
            )
            .order_by(Activity.created_at.asc())  # Oldest first for comments
            .offset(offset)
            .limit(limit)
        )

        result = await self.session.execute(query)
        return result.unique().scalars().all()

    async def get_by_type(
        self,
        issue_id: UUID,
        activity_types: list[ActivityType],
        *,
        limit: int = 20,
    ) -> Sequence[Activity]:
        """Get activities of specific types.

        Args:
            issue_id: Issue UUID.
            activity_types: Types to filter by.
            limit: Max activities.

        Returns:
            Matching activities.
        """
        query = (
            select(Activity)
            .options(joinedload(Activity.actor))
            .where(
                and_(
                    Activity.issue_id == issue_id,
                    Activity.activity_type.in_(activity_types),
                    Activity.is_deleted == False,  # noqa: E712
                )
            )
            .order_by(Activity.created_at.desc())
            .limit(limit)
        )

        result = await self.session.execute(query)
        return result.unique().scalars().all()

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
        ai_types = [
            ActivityType.AI_ENHANCED,
            ActivityType.AI_SUGGESTION_ACCEPTED,
            ActivityType.AI_SUGGESTION_REJECTED,
            ActivityType.DUPLICATE_DETECTED,
            ActivityType.DUPLICATE_MARKED,
        ]
        return await self.get_by_type(issue_id, ai_types, limit=limit)

    async def get_state_changes(
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
        return await self.get_by_type(
            issue_id,
            [ActivityType.STATE_CHANGED],
            limit=limit,
        )

    async def get_user_activities(
        self,
        actor_id: UUID,
        workspace_id: UUID,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[Activity]:
        """Get activities by a specific user.

        Args:
            actor_id: User UUID.
            workspace_id: Workspace UUID.
            limit: Max activities.
            offset: Skip first N.

        Returns:
            User's activities.
        """
        query = (
            select(Activity)
            .options(
                joinedload(Activity.issue),
                joinedload(Activity.actor),
            )
            .where(
                and_(
                    Activity.workspace_id == workspace_id,
                    Activity.actor_id == actor_id,
                    Activity.is_deleted == False,  # noqa: E712
                )
            )
            .order_by(Activity.created_at.desc())
            .offset(offset)
            .limit(limit)
        )

        result = await self.session.execute(query)
        return result.unique().scalars().all()

    async def count_issue_activities(
        self,
        issue_id: UUID,
        *,
        include_comments: bool = True,
    ) -> int:
        """Count activities for an issue.

        Args:
            issue_id: Issue UUID.
            include_comments: Whether to count comments.

        Returns:
            Activity count.
        """
        return await self.count(
            filters={"issue_id": issue_id} if include_comments else {"issue_id": issue_id},
        )

    async def create_batch(self, activities: list[Activity]) -> list[Activity]:
        """Create multiple activities in a batch.

        Args:
            activities: List of activities to create.

        Returns:
            Created activities.
        """
        for activity in activities:
            self.session.add(activity)
        await self.session.flush()
        for activity in activities:
            await self.session.refresh(activity)
        return activities


__all__ = ["ActivityRepository"]
