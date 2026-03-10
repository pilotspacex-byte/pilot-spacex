"""Notification service for in-app notification CRUD.

T-029: Notification Service.

Provides create, mark-read, mark-all-read, and paginated list operations.
All writes go through the repository; no RLS context is set here because
the worker inserts use the service_role policy and the API endpoints set
RLS context before delegating to this service.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import UUID

from pilot_space.infrastructure.database.models.notification import (
    Notification,
    NotificationPriority,
    NotificationType,
)
from pilot_space.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from pilot_space.infrastructure.database.repositories.notification_repository import (
        NotificationRepository,
    )

logger = get_logger(__name__)


@dataclass
class NotificationListResult:
    """Paginated notification list result.

    Attributes:
        items: Notifications for the current page.
        total: Total count matching the filter.
        page: Current page (1-based).
        page_size: Items per page.
    """

    items: Sequence[Notification]
    total: int
    page: int
    page_size: int

    @property
    def total_pages(self) -> int:
        """Return total number of pages."""
        if self.page_size <= 0:
            return 0
        return (self.total + self.page_size - 1) // self.page_size


class NotificationNotFoundError(Exception):
    """Raised when a notification is not found or not owned by the user."""


class NotificationService:
    """Service for notification CRUD operations.

    Args:
        session: Async database session.
        notification_repository: Repository for notification DB access.
    """

    def __init__(
        self,
        session: AsyncSession,
        notification_repository: NotificationRepository,
    ) -> None:
        self._session = session
        self._repo = notification_repository

    async def create(
        self,
        workspace_id: UUID,
        user_id: UUID,
        type: NotificationType,
        title: str,
        body: str,
        entity_type: str | None = None,
        entity_id: UUID | None = None,
        priority: NotificationPriority = NotificationPriority.MEDIUM,
    ) -> Notification:
        """Create and persist a new notification.

        Args:
            workspace_id: Target workspace UUID.
            user_id: Recipient user UUID.
            type: Notification event type.
            title: Short title (max 255 chars, truncated if longer).
            body: Full notification body.
            entity_type: Optional entity kind ("issue", "pr", "note").
            entity_id: Optional UUID of the referenced entity.
            priority: Urgency level.

        Returns:
            Persisted Notification instance.
        """
        truncated_title = title[:255] if len(title) > 255 else title
        notification = Notification(
            workspace_id=workspace_id,
            user_id=user_id,
            type=type,
            title=truncated_title,
            body=body,
            entity_type=entity_type,
            entity_id=entity_id,
            priority=priority,
        )
        self._session.add(notification)
        await self._session.flush()
        await self._session.refresh(notification)

        logger.info(
            "notification_created",
            notification_id=str(notification.id),
            user_id=str(user_id),
            type=type.value,
            priority=priority.value,
        )
        return notification

    async def mark_read(
        self,
        notification_id: UUID,
        user_id: UUID,
    ) -> Notification:
        """Mark a single notification as read.

        Args:
            notification_id: Notification UUID.
            user_id: Requesting user UUID (ownership check).

        Returns:
            Updated Notification.

        Raises:
            NotificationNotFoundError: If not found or not owned by user_id.
        """
        notification = await self._repo.mark_read(notification_id, user_id)
        if notification is None:
            raise NotificationNotFoundError(
                f"Notification {notification_id} not found or not owned by user {user_id}"
            )
        logger.debug(
            "notification_marked_read",
            notification_id=str(notification_id),
            user_id=str(user_id),
        )
        return notification

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
        count = await self._repo.mark_all_read(workspace_id, user_id)
        logger.debug(
            "all_notifications_marked_read",
            workspace_id=str(workspace_id),
            user_id=str(user_id),
            count=count,
        )
        return count

    async def list_for_user(
        self,
        workspace_id: UUID,
        user_id: UUID,
        page: int = 1,
        page_size: int = 20,
        unread_only: bool = False,
    ) -> NotificationListResult:
        """List paginated notifications for a user.

        Args:
            workspace_id: Workspace UUID.
            user_id: Recipient user UUID.
            page: 1-based page number.
            page_size: Items per page (1-100).
            unread_only: Return only unread notifications when True.

        Returns:
            NotificationListResult with items and pagination metadata.
        """
        clamped_page_size = max(1, min(page_size, 100))
        clamped_page = max(1, page)

        items, total = await self._repo.list_for_user(
            workspace_id=workspace_id,
            user_id=user_id,
            page=clamped_page,
            page_size=clamped_page_size,
            unread_only=unread_only,
        )
        return NotificationListResult(
            items=items,
            total=total,
            page=clamped_page,
            page_size=clamped_page_size,
        )

    async def count_unread(
        self,
        workspace_id: UUID,
        user_id: UUID,
    ) -> int:
        """Return the count of unread notifications for the bell badge.

        Args:
            workspace_id: Workspace UUID.
            user_id: Recipient user UUID.

        Returns:
            Number of unread notifications.
        """
        return await self._repo.count_unread(workspace_id, user_id)
