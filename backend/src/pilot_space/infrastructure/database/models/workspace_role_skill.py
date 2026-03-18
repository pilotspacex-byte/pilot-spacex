"""WorkspaceRoleSkill SQLAlchemy model.

Workspace-level role skill configured by admins. Separate from UserRoleSkill
(per user-workspace-role). One per workspace per role_type.

Source: Phase 16, WRSKL-01..04
"""

from __future__ import annotations

import uuid

from sqlalchemy import JSON, Boolean, CheckConstraint, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from pilot_space.infrastructure.database.base import WorkspaceScopedModel


class WorkspaceRoleSkill(WorkspaceScopedModel):
    """Admin-configured role skill for a workspace.

    One skill per (workspace_id, role_type) pair enforced via partial unique
    index (is_deleted = false). Soft-deleted rows do not count toward the
    uniqueness constraint, enabling re-create after delete.

    is_active defaults to False — requires explicit admin activation to prevent
    accidental injection of unreviewed content into PilotSpaceAgent context
    (WRSKL-02 approval gate).

    Attributes:
        role_type: SDLC role identifier (e.g., 'developer', 'tester').
        role_name: Human-readable display name.
        skill_content: SKILL.md-format markdown injected into agent context.
        experience_description: Optional natural language used for AI generation.
        is_active: Whether this skill is active (injected into agent context).
        created_by: Admin user who created this skill.
    """

    __tablename__ = "workspace_role_skills"  # type: ignore[assignment]

    role_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    role_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    skill_content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    experience_description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    tags: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
        server_default=text("'[]'"),
    )
    usage: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    __table_args__ = (
        # Partial unique index: only one active skill per role per workspace.
        # Soft-deleted rows (is_deleted = true) do not participate, allowing
        # re-create after delete without hitting a uniqueness violation.
        Index(
            "uq_workspace_role_skills_workspace_role_active",
            "workspace_id",
            "role_type",
            unique=True,
            postgresql_where=text("is_deleted = false"),
        ),
        # Hot-path index for materializer: get_active_by_workspace query
        Index(
            "ix_workspace_role_skills_workspace_active",
            "workspace_id",
            "is_active",
        ),
        CheckConstraint(
            "length(skill_content) <= 15000",
            name="ck_workspace_role_skills_content_length",
        ),
        CheckConstraint(
            "length(role_name) <= 100",
            name="ck_workspace_role_skills_role_name_length",
        ),
    )

    def __repr__(self) -> str:
        """Return string representation."""
        status = "[ACTIVE]" if self.is_active else "[PENDING]"
        return f"<WorkspaceRoleSkill(workspace_id={self.workspace_id}, role_type={self.role_type} {status})>"


__all__ = ["WorkspaceRoleSkill"]
