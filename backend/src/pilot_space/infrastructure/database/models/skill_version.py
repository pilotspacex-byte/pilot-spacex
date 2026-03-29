"""SkillVersion SQLAlchemy model.

Workspace-scoped version record for marketplace listings. Each version
represents an immutable snapshot of a skill's content at a point in time.

Source: Phase 50, P50-02
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from pilot_space.infrastructure.database.base import WorkspaceScopedModel
from pilot_space.infrastructure.database.types import JSONBCompat


class SkillVersion(WorkspaceScopedModel):
    """Immutable version record for a marketplace listing.

    Each version captures the skill content and graph data at publish time.
    Versions are never updated -- new versions are created instead.

    Attributes:
        listing_id: FK to the parent marketplace listing.
        version: Semver version string (e.g., '1.0.0').
        skill_content: SKILL.md-format markdown content at this version.
        graph_data: Optional graph structure snapshot.
        changelog: Human-readable description of changes in this version.
    """

    __tablename__ = "skill_versions"  # type: ignore[assignment]

    listing_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("skill_marketplace_listings.id", ondelete="CASCADE"),
        nullable=False,
    )
    version: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    skill_content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    graph_data: Mapped[dict[str, Any] | None] = mapped_column(
        JSONBCompat,
        nullable=True,
    )
    changelog: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    __table_args__ = (
        Index(
            "uq_skill_versions_listing_version",
            "listing_id",
            "version",
            unique=True,
            postgresql_where=text("is_deleted = false"),
        ),
        Index(
            "ix_skill_versions_listing_id",
            "listing_id",
        ),
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return f"<SkillVersion(listing_id={self.listing_id}, v{self.version})>"


__all__ = ["SkillVersion"]
