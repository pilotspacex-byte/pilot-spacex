"""ToolPermissionAuditLog SQLAlchemy model.

Phase 69 — append-only audit trail for per-workspace AI tool permission
changes (PERM-06). Every mode change recorded by
``WorkspaceToolPermission`` writes one row here via the service layer.

Rows are never updated or deleted — RLS allows member read and
OWNER/ADMIN insert only (see migration 105).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pilot_space.infrastructure.database.base import Base, WorkspaceScopedMixin

if TYPE_CHECKING:
    from pilot_space.infrastructure.database.models.user import User
    from pilot_space.infrastructure.database.models.workspace import Workspace


class ToolPermissionAuditLog(Base, WorkspaceScopedMixin):
    """Immutable record of a tool-permission mode change.

    Attributes:
        id: Primary key.
        workspace_id: Owning workspace (from WorkspaceScopedMixin).
        tool_name: Fully qualified MCP tool name.
        old_mode: Previous mode, or NULL if this is the first record.
        new_mode: Mode the permission was changed to.
        actor_user_id: User who performed the change.
        reason: Optional free-text justification.
        created_at: Insert timestamp (server-side ``now()``).
    """

    __tablename__ = "tool_permission_audit_log"
    __table_args__ = (
        CheckConstraint(
            "new_mode IN ('auto', 'ask', 'deny')",
            name="ck_tool_permission_audit_log_new_mode",
        ),
        CheckConstraint(
            "old_mode IS NULL OR old_mode IN ('auto', 'ask', 'deny')",
            name="ck_tool_permission_audit_log_old_mode",
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

    old_mode: Mapped[str | None] = mapped_column(
        String(8),
        nullable=True,
        doc="Previous mode (NULL on first insert)",
    )

    new_mode: Mapped[str] = mapped_column(
        String(8),
        nullable=False,
        doc="Mode the permission was changed to",
    )

    actor_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        doc="User who performed the change",
    )

    reason: Mapped[str | None] = mapped_column(
        String(256),
        nullable=True,
        doc="Optional free-text justification",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    workspace: Mapped[Workspace] = relationship("Workspace", lazy="select")
    actor: Mapped[User] = relationship(
        "User",
        lazy="select",
        foreign_keys=[actor_user_id],
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"<ToolPermissionAuditLog(workspace_id={self.workspace_id}, "
            f"tool_name={self.tool_name!r}, "
            f"old_mode={self.old_mode!r}, new_mode={self.new_mode!r})>"
        )
