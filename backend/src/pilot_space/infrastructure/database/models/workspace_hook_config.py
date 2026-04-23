"""WorkspaceHookConfig SQLAlchemy model.

Phase 83 -- declarative workspace hook rules (HOOK-02). Each row stores
a named rule that maps a tool pattern to an action (allow/deny/require_approval)
for a specific hook event type (PreToolUse/PostToolUse/Stop).

Rules are evaluated in priority order (lower = higher priority), first match
wins. The evaluator (Plan 02) enforces the DD-003 guard: CRITICAL tools
cannot be allowed by hook rules at runtime.

Writes are admin-only at the DB layer via RLS (see migration 110).
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pilot_space.infrastructure.database.base import (
    Base,
    TimestampMixin,
    WorkspaceScopedMixin,
)

if TYPE_CHECKING:
    from pilot_space.infrastructure.database.models.user import User
    from pilot_space.infrastructure.database.models.workspace import Workspace


class WorkspaceHookConfig(Base, TimestampMixin, WorkspaceScopedMixin):
    """Admin-created hook rule for a workspace.

    Attributes:
        id: Primary key.
        workspace_id: Owning workspace (from WorkspaceScopedMixin).
        name: Human-readable rule name, unique per workspace.
        description: Optional description of the rule's purpose.
        tool_pattern: Glob, regex, or exact match pattern for tool names.
        action: One of ``allow`` | ``deny`` | ``require_approval``.
        event_type: Hook event type: ``PreToolUse`` | ``PostToolUse`` | ``Stop``.
        priority: Evaluation order (lower = higher priority, default 100).
        is_enabled: Whether the rule is active.
        created_by: User who created the rule.
        updated_by: User who last modified the rule.
        workspace: Back-reference to the owning workspace.
        created_by_user: Back-reference to the creating user.
        updated_by_user: Back-reference to the updating user.
    """

    __tablename__ = "workspace_hook_configs"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "name",
            name="uq_workspace_hook_configs_workspace_name",
        ),
        CheckConstraint(
            "action IN ('allow', 'deny', 'require_approval')",
            name="ck_workspace_hook_configs_action",
        ),
        CheckConstraint(
            "event_type IN ('PreToolUse', 'PostToolUse', 'Stop')",
            name="ck_workspace_hook_configs_event_type",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        server_default="gen_random_uuid()",
    )

    name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        doc="Human-readable rule name, unique per workspace",
    )

    description: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
        doc="Optional description of the rule's purpose",
    )

    tool_pattern: Mapped[str] = mapped_column(
        String(256),
        nullable=False,
        doc="Glob, regex, or exact match pattern for tool names",
    )

    action: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        doc="Action: allow | deny | require_approval",
    )

    event_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default="PreToolUse",
        doc="Hook event type: PreToolUse | PostToolUse | Stop",
    )

    priority: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="100",
        doc="Evaluation order (lower = higher priority)",
    )

    is_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="true",
        doc="Whether this rule is active",
    )

    created_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        doc="User who created this rule",
    )

    updated_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        doc="User who last modified this rule",
    )

    # Relationships
    workspace: Mapped[Workspace] = relationship(
        "Workspace",
        lazy="select",
    )
    created_by_user: Mapped[User] = relationship(
        "User",
        lazy="select",
        foreign_keys=[created_by],
    )
    updated_by_user: Mapped[User] = relationship(
        "User",
        lazy="select",
        foreign_keys=[updated_by],
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"<WorkspaceHookConfig(workspace_id={self.workspace_id}, "
            f"name={self.name!r}, action={self.action!r}, "
            f"priority={self.priority})>"
        )
