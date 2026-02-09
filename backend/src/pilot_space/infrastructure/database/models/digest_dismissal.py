"""DigestDismissal SQLAlchemy model.

Tracks per-user dismissals of AI digest suggestions so dismissed items
are excluded from future digest responses for that user.

References:
- specs/012-homepage-note, plan.md Phase 0
- Migration: 029_add_digest_dismissals
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pilot_space.infrastructure.database.base import WorkspaceScopedModel

if TYPE_CHECKING:
    from pilot_space.infrastructure.database.models.user import User
    from pilot_space.infrastructure.database.models.workspace import Workspace


class DigestDismissal(WorkspaceScopedModel):
    """Record of a user dismissing a digest suggestion.

    Each row represents one user dismissing one suggestion, identified
    by (suggestion_category, entity_id, entity_type). The combination
    of (workspace_id, user_id, entity_id) is indexed for fast lookups.

    Attributes:
        user_id: User who dismissed the suggestion.
        suggestion_category: Category of suggestion (e.g. 'stale_issues').
        entity_id: ID of the entity the suggestion refers to.
        entity_type: Type of entity ('issue', 'note', etc.).
        dismissed_at: When the user dismissed this suggestion.
    """

    __tablename__ = "digest_dismissals"  # type: ignore[assignment]

    __table_args__ = (
        Index(
            "ix_digest_dismissals_user_entity",
            "workspace_id",
            "user_id",
            "entity_id",
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    suggestion_category: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    entity_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )

    entity_type: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    dismissed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    user: Mapped[User] = relationship(
        "User",
        lazy="selectin",
    )

    workspace: Mapped[Workspace] = relationship(
        "Workspace",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"<DigestDismissal(id={self.id}, user_id={self.user_id}, "
            f"category={self.suggestion_category}, entity={self.entity_type}:{self.entity_id})>"
        )
