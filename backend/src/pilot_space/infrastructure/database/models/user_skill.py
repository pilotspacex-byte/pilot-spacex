"""UserSkill SQLAlchemy model.

Per-user personalized skill derived from a skill template. Replaces
UserRoleSkill with a simpler schema: no role_type, no is_primary.
Users can have multiple active skills simultaneously.

Source: Phase 20, P20-02
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pilot_space.infrastructure.database.base import WorkspaceScopedModel

if TYPE_CHECKING:
    from pilot_space.infrastructure.database.models.skill_template import SkillTemplate
    from pilot_space.infrastructure.database.models.user import User


class UserSkill(WorkspaceScopedModel):
    """Personalized skill per user-workspace pair.

    Each record represents one skill the user has activated, optionally
    linked to a SkillTemplate via template_id. The skill_content is
    AI-personalized based on the user's experience_description.

    template_id is nullable: skills from deleted templates or custom
    skills without a template source retain their content.

    is_active defaults to True — skills are immediately materialized
    into the agent context.

    Attributes:
        user_id: Skill owner (FK to users, CASCADE on delete).
        template_id: Source template (FK to skill_templates, SET NULL on delete).
        skill_content: SKILL.md-format markdown content (max 15000 chars).
        experience_description: User's natural language input for AI generation.
        is_active: Whether skill is materialized into agent context.
    """

    __tablename__ = "user_skills"  # type: ignore[assignment]

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    template_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("skill_templates.id", ondelete="SET NULL"),
        nullable=True,
    )
    skill_content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    experience_description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    skill_name: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )

    # Relationships
    # lazy="raise" forces callers to use explicit eager loading (selectinload/joinedload).
    # UserSkillRepository.get_by_user_workspace uses selectinload(UserSkill.template)
    # for the materializer hot-path.
    user: Mapped[User] = relationship(
        "User",
        lazy="raise",
    )
    template: Mapped[SkillTemplate | None] = relationship(
        "SkillTemplate",
        lazy="raise",
    )

    __table_args__ = (
        # Partial unique index: one skill per template per user per workspace.
        # Soft-deleted rows excluded — allows re-create after delete.
        Index(
            "uq_user_skills_user_workspace_template",
            "user_id",
            "workspace_id",
            "template_id",
            unique=True,
            postgresql_where=text("is_deleted = false"),
        ),
        # Hot-path index: user's skills in a workspace
        Index(
            "ix_user_skills_user_workspace",
            "user_id",
            "workspace_id",
        ),
        # Hot-path index: all skills in a workspace (admin view)
        Index(
            "ix_user_skills_workspace",
            "workspace_id",
        ),
        CheckConstraint(
            "length(skill_content) <= 15000",
            name="ck_user_skills_content_length",
        ),
    )

    def __repr__(self) -> str:
        """Return string representation."""
        status = "[ACTIVE]" if self.is_active else "[INACTIVE]"
        tmpl = f", template_id={self.template_id}" if self.template_id else ""
        return f"<UserSkill(user_id={self.user_id}{tmpl} {status})>"


__all__ = ["UserSkill"]
