"""User SQLAlchemy model.

User model synced with Supabase auth.users.
Global entity (not workspace-scoped).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pilot_space.infrastructure.database.base import BaseModel

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
