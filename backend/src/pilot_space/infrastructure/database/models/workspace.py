"""Workspace SQLAlchemy model.

Workspace is the top-level container for multi-tenant isolation.
All workspace-scoped entities reference this table.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pilot_space.infrastructure.database.base import BaseModel

if TYPE_CHECKING:
    from pilot_space.infrastructure.database.models.ai_configuration import (
        AIConfiguration,
    )
    from pilot_space.infrastructure.database.models.project import Project
    from pilot_space.infrastructure.database.models.user import User
    from pilot_space.infrastructure.database.models.workspace_member import (
        WorkspaceMember,
    )


class Workspace(BaseModel):
    """Workspace model for multi-tenant isolation.

    Top-level container that scopes all project data.
    RLS policies use workspace_id for data isolation.

    Attributes:
        name: Display name of the workspace.
        slug: URL-friendly unique identifier.
        description: Optional workspace description.
        settings: JSONB for workspace-level configuration.
        owner_id: FK to User who created the workspace.
        members: WorkspaceMember relationships.
        projects: Projects in this workspace.
    """

    __tablename__ = "workspaces"  # type: ignore[assignment]

    # Core fields
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    slug: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Settings (JSONB for flexibility)
    settings: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        default=dict,
    )

    # Owner (creator of workspace)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,  # Allow null if owner is deleted
    )

    # Relationships
    owner: Mapped[User | None] = relationship(
        "User",
        foreign_keys=[owner_id],
        lazy="joined",
    )
    members: Mapped[list[WorkspaceMember]] = relationship(
        "WorkspaceMember",
        back_populates="workspace",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    projects: Mapped[list[Project]] = relationship(
        "Project",
        back_populates="workspace",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    ai_configurations: Mapped[list[AIConfiguration]] = relationship(
        "AIConfiguration",
        back_populates="workspace",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    # Indexes and constraints
    __table_args__ = (
        Index("ix_workspaces_slug", "slug"),
        Index("ix_workspaces_owner_id", "owner_id"),
        Index("ix_workspaces_is_deleted", "is_deleted"),
        UniqueConstraint("slug", name="uq_workspaces_slug"),
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return f"<Workspace(id={self.id}, slug={self.slug})>"
