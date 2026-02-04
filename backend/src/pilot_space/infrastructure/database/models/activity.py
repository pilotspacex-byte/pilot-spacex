"""Activity SQLAlchemy model.

Activity tracks all changes and actions on issues for audit trail.

T120: Create Activity model for issue history.
"""

from __future__ import annotations

import uuid
from enum import Enum
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Enum as SQLEnum,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pilot_space.infrastructure.database.base import WorkspaceScopedModel
from pilot_space.infrastructure.database.types import JSONBCompat

if TYPE_CHECKING:
    from pilot_space.infrastructure.database.models.issue import Issue
    from pilot_space.infrastructure.database.models.user import User


class ActivityType(str, Enum):
    """Types of activities tracked on issues.

    Covers all major issue lifecycle events per US-02 spec.
    """

    # Issue lifecycle
    CREATED = "created"
    UPDATED = "updated"
    DELETED = "deleted"
    RESTORED = "restored"

    # State changes
    STATE_CHANGED = "state_changed"
    PRIORITY_CHANGED = "priority_changed"

    # Assignment
    ASSIGNED = "assigned"
    UNASSIGNED = "unassigned"

    # Grouping
    ADDED_TO_CYCLE = "added_to_cycle"
    REMOVED_FROM_CYCLE = "removed_from_cycle"
    ADDED_TO_MODULE = "added_to_module"
    REMOVED_FROM_MODULE = "removed_from_module"

    # Labels
    LABEL_ADDED = "label_added"
    LABEL_REMOVED = "label_removed"

    # Relationships
    PARENT_SET = "parent_set"
    PARENT_REMOVED = "parent_removed"
    SUB_ISSUE_ADDED = "sub_issue_added"
    SUB_ISSUE_REMOVED = "sub_issue_removed"

    # Dates
    START_DATE_SET = "start_date_set"
    TARGET_DATE_SET = "target_date_set"
    ESTIMATE_SET = "estimate_set"

    # Notes
    LINKED_TO_NOTE = "linked_to_note"
    UNLINKED_FROM_NOTE = "unlinked_from_note"

    # Comments
    COMMENT_ADDED = "comment_added"
    COMMENT_UPDATED = "comment_updated"
    COMMENT_DELETED = "comment_deleted"

    # AI actions
    AI_ENHANCED = "ai_enhanced"
    AI_SUGGESTION_ACCEPTED = "ai_suggestion_accepted"
    AI_SUGGESTION_REJECTED = "ai_suggestion_rejected"
    DUPLICATE_DETECTED = "duplicate_detected"
    DUPLICATE_MARKED = "duplicate_marked"


class Activity(WorkspaceScopedModel):
    """Activity model for issue audit trail.

    Tracks all changes and actions on issues for:
    - Activity timeline in issue detail view
    - Audit logging
    - Analytics

    Attributes:
        issue_id: FK to the issue this activity is for.
        actor_id: FK to user who performed the action.
        activity_type: Type of activity from ActivityType enum.
        field: Field name that was changed (for updates).
        old_value: Previous value as string.
        new_value: New value as string.
        comment: Optional comment text for comment activities.
        metadata: JSONB for additional context.
    """

    __tablename__ = "activities"  # type: ignore[assignment]

    # Issue this activity belongs to
    issue_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("issues.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Who performed the action
    actor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,  # NULL for system/AI actions
    )

    # Type of activity
    activity_type: Mapped[ActivityType] = mapped_column(
        SQLEnum(ActivityType, name="activity_type", create_type=False),
        nullable=False,
    )

    # For field changes
    field: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    old_value: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    new_value: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # For comments
    comment: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Additional metadata (renamed to avoid conflict with SQLAlchemy's metadata)
    activity_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata",  # Column name in DB
        JSONBCompat,
        nullable=True,
        default=dict,
    )
    # metadata structure examples:
    # For state changes:
    # {
    #   "old_state_id": "uuid",
    #   "old_state_name": "Backlog",
    #   "new_state_id": "uuid",
    #   "new_state_name": "In Progress"
    # }
    # For AI enhancements:
    # {
    #   "model": "claude-sonnet-4-20250514",
    #   "fields_enhanced": ["title", "description"],
    #   "confidence": 0.85
    # }

    # Relationships
    issue: Mapped[Issue] = relationship(
        "Issue",
        back_populates="activities",
        lazy="joined",
    )
    actor: Mapped[User | None] = relationship(
        "User",
        lazy="joined",
    )

    # Indexes
    __table_args__ = (
        Index("ix_activities_issue_id", "issue_id"),
        Index("ix_activities_actor_id", "actor_id"),
        Index("ix_activities_activity_type", "activity_type"),
        Index("ix_activities_is_deleted", "is_deleted"),
        Index("ix_activities_created_at", "created_at"),
        # Composite for timeline queries
        Index("ix_activities_issue_created", "issue_id", "created_at"),
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return f"<Activity(id={self.id}, type={self.activity_type.value})>"

    @property
    def is_comment(self) -> bool:
        """Check if this is a comment activity."""
        return self.activity_type in (
            ActivityType.COMMENT_ADDED,
            ActivityType.COMMENT_UPDATED,
            ActivityType.COMMENT_DELETED,
        )

    @property
    def is_ai_activity(self) -> bool:
        """Check if this is an AI-related activity."""
        return self.activity_type in (
            ActivityType.AI_ENHANCED,
            ActivityType.AI_SUGGESTION_ACCEPTED,
            ActivityType.AI_SUGGESTION_REJECTED,
            ActivityType.DUPLICATE_DETECTED,
            ActivityType.DUPLICATE_MARKED,
        )

    @property
    def is_state_change(self) -> bool:
        """Check if this is a state change activity."""
        return self.activity_type == ActivityType.STATE_CHANGED

    @classmethod
    def create_for_issue_creation(
        cls,
        *,
        workspace_id: uuid.UUID,
        issue_id: uuid.UUID,
        actor_id: uuid.UUID,
        ai_enhanced: bool = False,
    ) -> Activity:
        """Factory method for issue creation activity.

        Args:
            workspace_id: Workspace UUID.
            issue_id: Issue UUID.
            actor_id: User who created the issue.
            ai_enhanced: Whether AI helped create the issue.

        Returns:
            New Activity instance.
        """
        metadata = {"ai_enhanced": ai_enhanced} if ai_enhanced else None
        return cls(
            workspace_id=workspace_id,
            issue_id=issue_id,
            actor_id=actor_id,
            activity_type=ActivityType.CREATED,
            activity_metadata=metadata,
        )

    @classmethod
    def create_for_state_change(
        cls,
        *,
        workspace_id: uuid.UUID,
        issue_id: uuid.UUID,
        actor_id: uuid.UUID,
        old_state_id: uuid.UUID,
        old_state_name: str,
        new_state_id: uuid.UUID,
        new_state_name: str,
    ) -> Activity:
        """Factory method for state change activity.

        Args:
            workspace_id: Workspace UUID.
            issue_id: Issue UUID.
            actor_id: User who changed the state.
            old_state_id: Previous state UUID.
            old_state_name: Previous state name.
            new_state_id: New state UUID.
            new_state_name: New state name.

        Returns:
            New Activity instance.
        """
        return cls(
            workspace_id=workspace_id,
            issue_id=issue_id,
            actor_id=actor_id,
            activity_type=ActivityType.STATE_CHANGED,
            field="state",
            old_value=old_state_name,
            new_value=new_state_name,
            activity_metadata={
                "old_state_id": str(old_state_id),
                "new_state_id": str(new_state_id),
            },
        )

    @classmethod
    def create_for_field_update(
        cls,
        *,
        workspace_id: uuid.UUID,
        issue_id: uuid.UUID,
        actor_id: uuid.UUID,
        field: str,
        old_value: str | None,
        new_value: str | None,
    ) -> Activity:
        """Factory method for generic field update.

        Args:
            workspace_id: Workspace UUID.
            issue_id: Issue UUID.
            actor_id: User who updated the field.
            field: Name of the field that changed.
            old_value: Previous value as string.
            new_value: New value as string.

        Returns:
            New Activity instance.
        """
        return cls(
            workspace_id=workspace_id,
            issue_id=issue_id,
            actor_id=actor_id,
            activity_type=ActivityType.UPDATED,
            field=field,
            old_value=old_value,
            new_value=new_value,
        )
