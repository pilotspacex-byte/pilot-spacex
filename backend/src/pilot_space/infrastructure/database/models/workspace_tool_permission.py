"""WorkspaceToolPermission SQLAlchemy model.

Phase 69 — granular per-workspace AI tool permissions (PERM-01).

Each row stores the admin-chosen approval mode (``auto``/``ask``/``deny``)
for a single MCP tool in a single workspace. The row is inserted lazily
the first time an admin overrides the default for that tool, so the
absence of a row means "use the workspace default policy".

Writes are admin-only at the DB layer via RLS (see migration 105).
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pilot_space.infrastructure.database.base import (
    Base,
    TimestampMixin,
    WorkspaceScopedMixin,
)

if TYPE_CHECKING:
    from pilot_space.infrastructure.database.models.user import User
    from pilot_space.infrastructure.database.models.workspace import Workspace


class WorkspaceToolPermission(Base, TimestampMixin, WorkspaceScopedMixin):
    """Admin-set approval mode for a single AI tool in a single workspace.

    Attributes:
        id: Primary key.
        workspace_id: Owning workspace (from WorkspaceScopedMixin).
        tool_name: Fully-qualified MCP tool name (e.g. ``issues.update_issue``).
        mode: One of ``auto`` | ``ask`` | ``deny``.
        updated_by: User who last changed the mode.
        workspace: Back-reference to the owning workspace.
        updated_by_user: Back-reference to the updating user.
    """

    __tablename__ = "workspace_tool_permissions"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "tool_name",
            name="uq_workspace_tool_permissions_workspace_tool",
        ),
        CheckConstraint(
            "mode IN ('auto', 'ask', 'deny')",
            name="ck_workspace_tool_permissions_mode",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        server_default="gen_random_uuid()",
    )

    tool_name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        doc="Fully qualified MCP tool name",
    )

    mode: Mapped[str] = mapped_column(
        String(8),
        nullable=False,
        doc="Approval mode: auto | ask | deny",
    )

    updated_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        doc="User who last changed this permission",
    )

    # Relationships
    workspace: Mapped[Workspace] = relationship(
        "Workspace",
        lazy="select",
    )
    updated_by_user: Mapped[User] = relationship(
        "User",
        lazy="select",
        foreign_keys=[updated_by],
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"<WorkspaceToolPermission(workspace_id={self.workspace_id}, "
            f"tool_name={self.tool_name!r}, mode={self.mode!r})>"
        )
