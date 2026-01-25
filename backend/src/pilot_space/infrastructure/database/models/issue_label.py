"""Issue-Label junction table.

Many-to-many relationship between issues and labels.

T119: Create issue_labels junction table.
"""

from __future__ import annotations

from sqlalchemy import Column, DateTime, ForeignKey, Index, Table, func
from sqlalchemy.dialects.postgresql import UUID

from pilot_space.infrastructure.database.base import Base

# Junction table for many-to-many relationship between Issues and Labels
# Using a Table object (not a Model) for simple many-to-many without extra columns
issue_labels = Table(
    "issue_labels",
    Base.metadata,
    Column(
        "issue_id",
        UUID(as_uuid=True),
        ForeignKey("issues.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "label_id",
        UUID(as_uuid=True),
        ForeignKey("labels.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "created_at",
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    ),
    # Indexes for efficient lookups
    Index("ix_issue_labels_issue_id", "issue_id"),
    Index("ix_issue_labels_label_id", "label_id"),
)

__all__ = ["issue_labels"]
