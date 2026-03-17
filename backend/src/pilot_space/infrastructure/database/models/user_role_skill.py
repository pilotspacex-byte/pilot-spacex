"""UserRoleSkill and RoleTemplate SQLAlchemy models.

UserRoleSkill stores personalized AI skill descriptions per user-workspace pair.
RoleTemplate stores predefined SDLC role templates with default skill content.

Source: 011-role-based-skills, FR-001, FR-002, FR-004, FR-005, FR-013, FR-015, FR-017
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pilot_space.infrastructure.database.base import BaseModel, WorkspaceScopedModel

if TYPE_CHECKING:
    from pilot_space.infrastructure.database.models.user import User


class RoleTemplate(BaseModel):
    """Predefined SDLC role template with default skill content.

    Seeded via migration. Read-only for application users.
    Templates provide starting points for user role skill generation.

    Attributes:
        role_type: Enum key (e.g., 'developer', 'tester'). Unique.
        display_name: Human-readable name for UI display.
        description: Brief description for role selection UI.
        default_skill_content: Default SKILL.md markdown content.
        icon: Frontend icon identifier (e.g., 'Code', 'TestTube').
        sort_order: Display ordering in selection grid.
        version: Template versioning for update notifications.
    """

    __tablename__ = "role_templates"  # type: ignore[assignment]

    role_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        unique=True,
    )
    display_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    default_skill_content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    icon: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    sort_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default=text("1"),
    )

    __table_args__ = (
        Index("ix_role_templates_role_type", "role_type", unique=True),
        Index("ix_role_templates_sort_order", "sort_order"),
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return f"<RoleTemplate(role_type={self.role_type}, display_name={self.display_name})>"


class UserRoleSkill(WorkspaceScopedModel):
    """Personalized AI skill description per user-workspace pair.

    Each record represents one SDLC role the user holds in a specific
    workspace, along with the SKILL.md-format content that gets injected
    into the PilotSpace Agent via filesystem materialization.

    Attributes:
        user_id: Skill owner (FK to users).
        role_type: Predefined enum key or 'custom'.
        role_name: Display name (e.g., "Senior QA Engineer").
        skill_content: SKILL.md markdown content with YAML frontmatter.
        experience_description: User's natural language input for AI generation.
        is_primary: Primary role flag (one per user-workspace).
        template_version: Tracks which version of RoleTemplate was used.
    """

    __tablename__ = "user_role_skills"  # type: ignore[assignment]

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
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
    is_primary: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )
    template_version: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    # Relationships
    user: Mapped[User] = relationship(
        "User",
        lazy="joined",
    )

    __table_args__ = (
        CheckConstraint(
            "length(skill_content) <= 15000",
            name="ck_user_role_skills_skill_content_length",
        ),
        CheckConstraint(
            "length(role_name) <= 100",
            name="ck_user_role_skills_role_name_length",
        ),
        Index("ix_user_role_skills_user_workspace", "user_id", "workspace_id"),
    )

    def __repr__(self) -> str:
        """Return string representation."""
        primary = " [PRIMARY]" if self.is_primary else ""
        return f"<UserRoleSkill(user_id={self.user_id}, role_type={self.role_type}{primary})>"


__all__ = ["RoleTemplate", "UserRoleSkill"]
