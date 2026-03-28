"""SkillMarketplaceListing SQLAlchemy model.

Workspace-scoped marketplace listing for published skills. Listings are
published by a workspace but readable by all authenticated users (public
marketplace). Each listing tracks metadata, version, ratings, and optional
graph data.

Source: Phase 50, P50-02
"""

from __future__ import annotations

import uuid

from sqlalchemy import Float, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from pilot_space.infrastructure.database.base import WorkspaceScopedModel
from pilot_space.infrastructure.database.types import JSONBCompat


class SkillMarketplaceListing(WorkspaceScopedModel):
    """Marketplace listing for a publishable skill.

    Represents a skill available in the marketplace. Published by a workspace,
    but visible to all authenticated users for browsing and installation.

    Attributes:
        name: Listing display name (max 100 chars).
        description: Brief description for marketplace cards.
        long_description: Extended description for detail pages.
        author: Author name or organization (max 100 chars).
        icon: Frontend icon identifier (e.g., 'Wand2', 'Code').
        category: Skill category for filtering (e.g., 'development', 'design').
        tags: JSON array of string tags for search.
        version: Current published version string (semver).
        download_count: Number of installs across all workspaces.
        avg_rating: Computed average from skill_reviews.
        screenshots: JSON array of screenshot URLs.
        graph_data: Optional graph structure for visual preview.
        published_by: User who published this listing.
    """

    __tablename__ = "skill_marketplace_listings"  # type: ignore[assignment]

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    long_description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    author: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    icon: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        server_default=text("'Wand2'"),
    )
    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    tags: Mapped[list] = mapped_column(
        JSONBCompat,
        nullable=False,
        default=list,
        server_default=text("'[]'"),
    )
    version: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    download_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    avg_rating: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    screenshots: Mapped[list | None] = mapped_column(
        JSONBCompat,
        nullable=True,
    )
    graph_data: Mapped[dict | None] = mapped_column(
        JSONBCompat,
        nullable=True,
    )
    published_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    __table_args__ = (
        Index(
            "uq_skill_marketplace_listings_name_author",
            "name",
            "author",
            unique=True,
            postgresql_where=text("is_deleted = false"),
        ),
        Index(
            "ix_skill_marketplace_listings_category",
            "category",
        ),
        Index(
            "ix_skill_marketplace_listings_workspace_id",
            "workspace_id",
        ),
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return f"<SkillMarketplaceListing(name={self.name}, author={self.author}, v{self.version})>"


__all__ = ["SkillMarketplaceListing"]
