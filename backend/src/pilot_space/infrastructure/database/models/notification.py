"""Notification SQLAlchemy model.

Stores in-app notifications for workspace users.
T-029: Create Notification Model.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import (
    DateTime,
    Enum as SQLEnum,
    Index,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from pilot_space.infrastructure.database.base import WorkspaceScopedModel


class NotificationType(str, Enum):
    """Notification event type.

    Determines the icon and grouping in the notification feed.
    """

    PR_REVIEW = "pr_review"
    ASSIGNMENT = "assignment"
    SPRINT_DEADLINE = "sprint_deadline"
    MENTION = "mention"
    GENERAL = "general"


class NotificationPriority(str, Enum):
    """Notification urgency level.

    Controls ordering and visual emphasis in the notification feed.
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class Notification(WorkspaceScopedModel):
    """In-app notification delivered to a specific workspace member.

    Notifications are user-scoped (user_id = recipient) and workspace-scoped
    for multi-tenant RLS isolation.  A null ``read_at`` means the notification
    is unread.

    Attributes:
        workspace_id: FK to workspaces (inherited from WorkspaceScopedModel).
        user_id: UUID of the notification recipient.
        type: Notification event type (pr_review, assignment, etc.).
        title: Short notification title shown in the bell feed (max 255 chars).
        body: Full notification body text.
        entity_type: Optional entity kind ("issue", "pr", "note").
        entity_id: Optional UUID of the referenced entity.
        priority: Urgency level controlling ordering/styling.
        read_at: UTC timestamp when user read the notification; null = unread.
        created_at: UTC timestamp of notification creation (from TimestampMixin).
    """

    __tablename__ = "notifications"  # type: ignore[assignment]

    # Recipient
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )

    # Notification content
    type: Mapped[NotificationType] = mapped_column(
        SQLEnum(
            NotificationType,
            name="notification_type",
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    body: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
    )

    # Optional entity reference
    entity_type: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )
    entity_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )

    # Priority
    priority: Mapped[NotificationPriority] = mapped_column(
        SQLEnum(
            NotificationPriority,
            name="notification_priority",
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        default=NotificationPriority.MEDIUM,
    )

    # Read tracking
    read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    __table_args__ = (
        # Primary query: list notifications for a user in a workspace newest-first
        Index(
            "ix_notifications_workspace_user_created",
            "workspace_id",
            "user_id",
            "created_at",
        ),
        # Unread filter: efficiently count / list unread notifications
        Index(
            "ix_notifications_workspace_user_read_at",
            "workspace_id",
            "user_id",
            "read_at",
        ),
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"<Notification(id={self.id}, user_id={self.user_id}, "
            f"type={self.type}, read={self.read_at is not None})>"
        )

    @property
    def is_read(self) -> bool:
        """Return True if the notification has been read."""
        return self.read_at is not None
