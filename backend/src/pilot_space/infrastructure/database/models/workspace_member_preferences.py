"""WorkspaceMemberPreferences SQLAlchemy model.

Stores per-user per-workspace theme and editor customization preferences.
All theme fields are nullable -- the client applies defaults when null.

Source: Phase 46, THEME-04
"""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from pilot_space.infrastructure.database.base import BaseModel


class WorkspaceMemberPreferences(BaseModel):
    """Per-user per-workspace theme and editor preferences.

    All preference fields are nullable. When null, the frontend applies
    its own defaults (e.g. theme_mode='system', font_size=14).

    Attributes:
        workspace_id: FK to workspaces.id.
        user_id: FK to auth.users / local users table.
        theme_mode: 'light' | 'dark' | 'high-contrast' | 'system' | None.
        accent_color: One of 8 preset accent color names, or None.
        editor_theme_id: Custom editor theme identifier, or None.
        font_size: Editor font size in px, or None (client default 14).
        font_family: Editor font family name, or None (client default 'default').
    """

    __tablename__ = "workspace_member_preferences"  # type: ignore[assignment]

    # Foreign keys
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Theme preferences (all nullable -- client applies defaults)
    theme_mode: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )
    accent_color: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    editor_theme_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    font_size: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    font_family: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    # Constraints
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "user_id",
            name="uq_workspace_member_preferences_workspace_user",
        ),
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"<WorkspaceMemberPreferences("
            f"workspace_id={self.workspace_id}, "
            f"user_id={self.user_id}, "
            f"theme_mode={self.theme_mode})>"
        )
