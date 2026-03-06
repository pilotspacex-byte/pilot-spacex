"""Notification repository for in-app notification CRUD."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import desc, func, select, update

from pilot_space.infrastructure.database.models.notification import Notification
from pilot_space.infrastructure.database.repositories.base import BaseRepository

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sqlalchemy.ext.asyncio import AsyncSession


class NotificationRepository(BaseRepository[Notification]):
    """Repository for notification CRUD operations."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session=session, model_class=Notification)

    async def list_for_user(
        self,
        workspace_id: UUID,
        user_id: UUID,
        *,
        page: int = 1,
        page_size: int = 20,
        unread_only: bool = False,
    ) -> tuple[Sequence[Notification], int]:
        """List notifications for a user with pagination.

        Args:
            workspace_id: Workspace UUID for scoping.
            user_id: Recipient user UUID.
            page: 1-based page number.
            page_size: Number of items per page.
            unread_only: When True, return only notifications where read_at IS NULL.

        Returns:
            Tuple of (notifications, total_count).
        """
        base_query = select(Notification).where(
            Notification.workspace_id == workspace_id,
            Notification.user_id == user_id,
            Notification.is_deleted == False,  # noqa: E712
        )
        if unread_only:
            base_query = base_query.where(Notification.read_at.is_(None))

        count_query = select(func.count()).select_from(base_query.subquery())
        total_result = await self.session.execute(count_query)
        total = total_result.scalar_one()

        offset = (page - 1) * page_size
        items_query = (
            base_query.order_by(desc(Notification.created_at)).offset(offset).limit(page_size)
        )
        result = await self.session.execute(items_query)
        return result.scalars().all(), total

    async def count_unread(
        self,
        workspace_id: UUID,
        user_id: UUID,
    ) -> int:
        """Count unread notifications for a user in a workspace.

        Args:
            workspace_id: Workspace UUID.
            user_id: Recipient user UUID.

        Returns:
            Number of unread notifications.
        """
        query = select(func.count()).where(
            Notification.workspace_id == workspace_id,
            Notification.user_id == user_id,
            Notification.read_at.is_(None),
            Notification.is_deleted == False,  # noqa: E712
        )
        result = await self.session.execute(query)
        return result.scalar_one()

    async def mark_read(
        self,
        notification_id: UUID,
        user_id: UUID,
    ) -> Notification | None:
        """Mark a single notification as read.

        Only marks if the notification belongs to user_id (ownership check).

        Args:
            notification_id: Notification UUID.
            user_id: Requesting user UUID.

        Returns:
            Updated notification, or None if not found / not owned.
        """
        now = datetime.now(tz=UTC)
        await self.session.execute(
            update(Notification)
            .where(
                Notification.id == notification_id,
                Notification.user_id == user_id,
                Notification.is_deleted == False,  # noqa: E712
            )
            .values(read_at=now, updated_at=now)
        )
        await self.session.flush()
        return await self.get_by_id(notification_id)

    async def mark_all_read(
        self,
        workspace_id: UUID,
        user_id: UUID,
    ) -> int:
        """Mark all unread notifications as read for a user in a workspace.

        Args:
            workspace_id: Workspace UUID.
            user_id: Recipient user UUID.

        Returns:
            Number of notifications updated.
        """
        now = datetime.now(tz=UTC)
        result = await self.session.execute(
            update(Notification)
            .where(
                Notification.workspace_id == workspace_id,
                Notification.user_id == user_id,
                Notification.read_at.is_(None),
                Notification.is_deleted == False,  # noqa: E712
            )
            .values(read_at=now, updated_at=now)
        )
        await self.session.flush()
        return result.rowcount  # type: ignore[return-value]
