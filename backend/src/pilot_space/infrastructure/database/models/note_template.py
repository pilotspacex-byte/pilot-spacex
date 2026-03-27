"""NoteTemplate SQLAlchemy model.

T-141: Reusable note templates per workspace.
System templates (is_system=True) have workspace_id=NULL and are available
to all workspaces. Custom workspace templates are workspace-scoped.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import Boolean, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from pilot_space.infrastructure.database.base import BaseModel
from pilot_space.infrastructure.database.types import JSONBCompat


class NoteTemplate(BaseModel):
    """Reusable note template.

    System templates (is_system=True) have workspace_id=NULL and are globally
    available. Workspace custom templates are scoped to a single workspace.

    Attributes:
        workspace_id: Owning workspace UUID, NULL for system templates.
        name: Template display name (max 255 chars).
        description: Optional description text.
        content: TipTap-compatible JSON content blob.
        is_system: True for built-in read-only system templates.
        created_by: UUID of the user who created this template (NULL for system).
    """

    __tablename__ = "note_templates"  # type: ignore[assignment]

    workspace_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    content: Mapped[dict[str, Any]] = mapped_column(
        JSONBCompat,
        nullable=False,
    )
    is_system: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="false",
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )

    __table_args__ = (Index("ix_note_templates_is_deleted", "is_deleted"),)


__all__ = ["NoteTemplate"]
