"""IssueSuggestionDismissal — persists per-user AI suggestion dismissals for issues.

Tracks which AI-suggested related issues a user has dismissed, so dismissed
suggestions are excluded from future responses for that user/issue pair.

References:
- specs/015-related-issues, Phase 0 scaffolding
- Migration: 072_add_issue_suggestion
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from pilot_space.infrastructure.database.base import WorkspaceScopedModel


class IssueSuggestionDismissal(WorkspaceScopedModel):
    """Record of a user dismissing an AI-suggested related issue.

    Each row represents one user choosing to hide one suggestion identified
    by (user_id, source_issue_id, target_issue_id). The UNIQUE constraint
    serves as the idempotency guard — duplicate dismissals are silently
    ignored via ON CONFLICT in the service layer.

    Attributes:
        user_id: User who dismissed the suggestion.
        source_issue_id: Issue for which the suggestion was shown.
        target_issue_id: Suggested issue that was dismissed.
        dismissed_at: Server timestamp when the dismissal was recorded.
    """

    __tablename__ = "issue_suggestion_dismissals"  # type: ignore[assignment]

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    source_issue_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("issues.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    target_issue_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("issues.id", ondelete="CASCADE"),
        nullable=False,
    )

    dismissed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "source_issue_id",
            "target_issue_id",
            name="uq_issue_suggestion_dismissals_user_source_target",
        ),
        Index(
            "ix_issue_suggestion_dismissals_workspace_source",
            "workspace_id",
            "source_issue_id",
        ),
        Index(
            "ix_issue_suggestion_dismissals_workspace_user",
            "workspace_id",
            "user_id",
        ),
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"<IssueSuggestionDismissal(id={self.id}, user_id={self.user_id}, "
            f"source={self.source_issue_id}, target={self.target_issue_id})>"
        )
