"""SkillReview SQLAlchemy model.

Workspace-scoped review and rating for marketplace listings. Each user
can submit one review per listing (enforced by partial unique index).

Source: Phase 50, P50-02
"""

from __future__ import annotations

import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from pilot_space.infrastructure.database.base import WorkspaceScopedModel


class SkillReview(WorkspaceScopedModel):
    """User review and rating for a marketplace listing.

    One review per user per listing (enforced by partial unique index
    excluding soft-deleted rows). Rating is constrained to 1-5 range.

    Attributes:
        listing_id: FK to the reviewed marketplace listing.
        user_id: FK to the reviewing user.
        rating: Integer rating from 1 (worst) to 5 (best).
        review_text: Optional text review content.
    """

    __tablename__ = "skill_reviews"  # type: ignore[assignment]

    listing_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("skill_marketplace_listings.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    rating: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    review_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    __table_args__ = (
        Index(
            "uq_skill_reviews_listing_user",
            "listing_id",
            "user_id",
            unique=True,
            postgresql_where=text("is_deleted = false"),
        ),
        CheckConstraint(
            "rating >= 1 AND rating <= 5",
            name="ck_skill_reviews_rating_range",
        ),
        Index(
            "ix_skill_reviews_listing_id",
            "listing_id",
        ),
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return f"<SkillReview(listing_id={self.listing_id}, rating={self.rating})>"


__all__ = ["SkillReview"]
