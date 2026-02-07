"""WorkspaceDigest SQLAlchemy model.

Stores hourly AI-generated workspace insights with actionable suggestions.
Each digest contains a JSONB array of categorised suggestions
(stale_issues, unlinked_notes, review_needed, etc.).

References:
- specs/012-homepage-note, plan.md Phase 0
- Migration: 028_add_workspace_digests
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pilot_space.infrastructure.database.base import WorkspaceScopedModel
from pilot_space.infrastructure.database.types import JSONBCompat

if TYPE_CHECKING:
    from pilot_space.infrastructure.database.models.workspace import Workspace


class WorkspaceDigest(WorkspaceScopedModel):
    """AI-generated workspace digest with actionable suggestions.

    Generated hourly by background job or on-demand via API.
    Suggestions are categorised JSONB items that the frontend renders
    as dismissible cards in the Digest Panel.

    Attributes:
        generated_at: When this digest was generated.
        generated_by: Origin — 'scheduled' (cron) or 'manual' (user-triggered).
        suggestions: JSONB array of suggestion objects.
        model_used: LLM model identifier (e.g. 'claude-sonnet-4-5-20250929').
        token_usage: Token consumption breakdown (prompt, completion, cached).
    """

    __tablename__ = "workspace_digests"  # type: ignore[assignment]

    __table_args__ = (
        Index(
            "ix_workspace_digests_workspace_generated",
            "workspace_id",
            "generated_at",
        ),
    )

    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    generated_by: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="scheduled",
    )

    suggestions: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONBCompat,
        nullable=False,
        default=list,
    )

    model_used: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    token_usage: Mapped[dict[str, Any] | None] = mapped_column(
        JSONBCompat,
        nullable=True,
    )

    # Relationships
    workspace: Mapped[Workspace] = relationship(
        "Workspace",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"<WorkspaceDigest(id={self.id}, workspace_id={self.workspace_id}, "
            f"generated_at={self.generated_at}, by={self.generated_by})>"
        )
