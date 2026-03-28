"""SkillTemplate SQLAlchemy model.

Workspace-scoped skill template replacing both RoleTemplate (global) and
WorkspaceRoleSkill (workspace-level). Each template has a source indicating
its origin: 'built_in', 'workspace', or 'custom'.

Source: Phase 20, P20-01
"""

from __future__ import annotations

import uuid

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from pilot_space.infrastructure.database.base import WorkspaceScopedModel


class SkillTemplate(WorkspaceScopedModel):
    """Workspace-scoped skill template for the skill catalog.

    Replaces both global RoleTemplate and workspace-scoped WorkspaceRoleSkill
    with a single unified table. Templates are browseable by users when
    selecting skills to personalize.

    Source field indicates origin:
    - 'built_in': Seeded from RoleTemplate on workspace creation
    - 'workspace': Created by workspace admins
    - 'custom': User-created (future)

    is_active defaults to True (unlike WorkspaceRoleSkill which defaults False)
    because templates are immediately available in the catalog.

    Attributes:
        name: Template display name (max 100 chars).
        description: Brief description for catalog UI.
        skill_content: SKILL.md-format markdown content (max 15000 chars).
        icon: Frontend icon identifier (e.g., 'Wand2', 'Code').
        sort_order: Display ordering in catalog grid.
        source: Origin type ('built_in', 'workspace', 'custom').
        role_type: Optional SDLC role lineage (nullable for non-role templates).
        is_active: Whether template is visible in catalog.
        created_by: Admin user who created this template.
    """

    __tablename__ = "skill_templates"  # type: ignore[assignment]

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    skill_content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    icon: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        server_default=text("'Wand2'"),
    )
    sort_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    source: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    role_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    marketplace_listing_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("skill_marketplace_listings.id", ondelete="SET NULL"),
        nullable=True,
    )
    installed_version: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    __table_args__ = (
        # Partial unique index: one template per name per workspace.
        # Soft-deleted rows excluded — allows re-create after delete.
        Index(
            "uq_skill_templates_workspace_name",
            "workspace_id",
            "name",
            unique=True,
            postgresql_where=text("is_deleted = false"),
        ),
        # Hot-path index: filter by source type
        Index(
            "ix_skill_templates_workspace_source",
            "workspace_id",
            "source",
        ),
        # Hot-path index: active templates for catalog
        Index(
            "ix_skill_templates_workspace_active",
            "workspace_id",
            "is_active",
        ),
        CheckConstraint(
            "length(skill_content) <= 15000",
            name="ck_skill_templates_content_length",
        ),
        CheckConstraint(
            "length(name) <= 100",
            name="ck_skill_templates_name_length",
        ),
        Index(
            "ix_skill_templates_marketplace_listing_id",
            "marketplace_listing_id",
        ),
    )

    def __repr__(self) -> str:
        """Return string representation."""
        status = "[ACTIVE]" if self.is_active else "[INACTIVE]"
        return f"<SkillTemplate(name={self.name}, source={self.source} {status})>"


__all__ = ["SkillTemplate"]
