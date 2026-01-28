"""Template SQLAlchemy model.

Template provides reusable document structures for Notes.
Each workspace can have default and custom templates.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import Boolean, Index, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from pilot_space.infrastructure.database.base import WorkspaceScopedModel
from pilot_space.infrastructure.database.types import JSONBCompat


class Template(WorkspaceScopedModel):
    """Template model for reusable Note structures.

    Templates provide pre-defined content and structure that can be used
    when creating new Notes. Each workspace has its own templates.

    Attributes:
        name: Display name of the template.
        description: Optional template description.
        content: TipTap JSON document structure.
        category: Template category for organization (e.g., 'meeting', 'spec').
        is_default: Whether this is a default template for the workspace.
    """

    __tablename__ = "templates"  # type: ignore[assignment]

    # Core fields
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # TipTap JSON content (ProseMirror document structure)
    content: Mapped[dict[str, Any]] = mapped_column(
        JSONBCompat,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )

    # Organization
    category: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    is_default: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )

    # Indexes and constraints
    __table_args__ = (
        Index("ix_templates_category", "category"),
        Index("ix_templates_is_default", "is_default"),
        Index("ix_templates_is_deleted", "is_deleted"),
        Index("ix_templates_name", "name"),
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return f"<Template(id={self.id}, name={self.name}, category={self.category})>"
