"""SkillActionButton SQLAlchemy model.

Workspace-scoped action buttons bound to skills or MCP tools.
Displayed on the issue detail page for one-click AI actions.

Source: Phase 17, SKBTN-01..04
"""

from __future__ import annotations

import enum
import uuid

from sqlalchemy import Boolean, Enum, Index, Integer, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from pilot_space.infrastructure.database.base import WorkspaceScopedModel
from pilot_space.infrastructure.database.types import JSONBCompat


class BindingType(enum.StrEnum):
    """Type of action button binding."""

    SKILL = "skill"
    MCP_TOOL = "mcp_tool"


class SkillActionButton(WorkspaceScopedModel):
    """Workspace action button bound to a skill or MCP tool.

    Each row represents a configurable action button displayed on the
    issue detail page. Buttons are bound to either a built-in skill or
    an MCP tool via binding_type + binding_id + binding_metadata.

    The partial unique index on (workspace_id, name) WHERE is_deleted = false
    prevents duplicate button names within a workspace while allowing
    re-create after soft-delete.

    Attributes:
        name: Display name of the button (1-100 chars).
        icon: Optional icon identifier (e.g., lucide icon name).
        binding_type: Whether bound to SKILL or MCP_TOOL.
        binding_id: Optional UUID of the bound skill/tool.
        binding_metadata: JSONB metadata (e.g., plugin_id, server_id).
        sort_order: Display order (lower = first).
        is_active: Whether this button is visible to users.
    """

    __tablename__ = "skill_action_buttons"  # type: ignore[assignment]

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    icon: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    binding_type: Mapped[BindingType] = mapped_column(
        Enum(
            BindingType,
            name="binding_type",
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
    )
    binding_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )
    binding_metadata: Mapped[dict] = mapped_column(  # type: ignore[type-arg]
        JSONBCompat,
        nullable=False,
        default=dict,
    )
    sort_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )

    __table_args__ = (
        # Partial unique index: one button name per workspace (non-deleted).
        Index(
            "uq_skill_action_buttons_workspace_name",
            "workspace_id",
            "name",
            unique=True,
            postgresql_where=text("is_deleted = false"),
        ),
        # Hot-path index: get active buttons for a workspace.
        Index(
            "ix_skill_action_buttons_workspace_active",
            "workspace_id",
            "is_active",
        ),
    )

    def __repr__(self) -> str:
        """Return string representation."""
        status = "[ACTIVE]" if self.is_active else "[INACTIVE]"
        return (
            f"<SkillActionButton(workspace_id={self.workspace_id}, "
            f"name={self.name!r}, binding={self.binding_type.value} {status})>"
        )


__all__ = ["BindingType", "SkillActionButton"]
