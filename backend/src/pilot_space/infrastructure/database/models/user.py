"""User SQLAlchemy model.

User model synced with Supabase auth.users.
Global entity (not workspace-scoped).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pilot_space.infrastructure.database.base import BaseModel
from pilot_space.infrastructure.database.types import JSONBCompat

if TYPE_CHECKING:
    from pilot_space.infrastructure.database.models.workspace_member import (
        WorkspaceMember,
    )


class User(BaseModel):
    """User model synced with Supabase Auth.

    The id should match Supabase auth.users.id for RLS integration.
    User is a global entity - not workspace-scoped.

    Attributes:
        email: Unique email address (from Supabase Auth).
        full_name: Display name.
        avatar_url: Profile image URL.
        workspace_memberships: Workspaces this user belongs to.
    """

    __tablename__ = "users"  # type: ignore[assignment]

    # Core fields (synced from Supabase Auth)
    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
    )
    full_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    avatar_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Default SDLC role for new workspace joins (FR-011)
    default_sdlc_role: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    # Short bio displayed to teammates (max 200 chars)
    bio: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )

    # Per-user AI provider settings (model overrides, base_url)
    # Expected shape (all fields optional):
    # {
    #   "model_sonnet": "claude-sonnet-4-20250514",
    #   "model_haiku": "claude-haiku-4-5-20251001",
    #   "model_opus": "claude-opus-4-5-20251101",
    #   "base_url": "https://proxy.example.com/v1"
    # }
    ai_settings: Mapped[dict[str, Any] | None] = mapped_column(
        JSONBCompat,
        nullable=True,
        default=None,
    )

    # Relationships
    workspace_memberships: Mapped[list[WorkspaceMember]] = relationship(
        "WorkspaceMember",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    # Indexes
    __table_args__ = (
        Index("ix_users_email", "email"),
        Index("ix_users_is_deleted", "is_deleted"),
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return f"<User(id={self.id}, email={self.email})>"
