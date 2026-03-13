"""IssueLink SQLAlchemy model (AD-005).

Issue-to-issue relationships for dependency tracking.
Supports blocks, blocked_by, duplicates, and related link types.
"""

from __future__ import annotations

import uuid
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    Enum as SQLEnum,
    ForeignKey,
    Index,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pilot_space.infrastructure.database.base import WorkspaceScopedModel

if TYPE_CHECKING:
    from pilot_space.infrastructure.database.models.issue import Issue


class IssueLinkType(str, Enum):
    """Type of relationship between two issues.

    Link types represent directional or symmetric relationships:
    - BLOCKS: Source issue blocks target issue.
    - BLOCKED_BY: Source issue is blocked by target issue.
    - DUPLICATES: Source issue duplicates target issue.
    - RELATED: Symmetric relationship between issues.
    """

    BLOCKS = "blocks"
    BLOCKED_BY = "blocked_by"
    DUPLICATES = "duplicates"
    RELATED = "related"


class IssueLink(WorkspaceScopedModel):
    """IssueLink model for issue-to-issue relationships (AD-005).

    Tracks dependency and relationship links between issues within a workspace.
    Enforces no self-links and unique (source, target, type) combinations.

    Attributes:
        source_issue_id: FK to the source issue.
        target_issue_id: FK to the target issue.
        link_type: Type of relationship (blocks/blocked_by/duplicates/related).
    """

    __tablename__ = "issue_links"  # type: ignore[assignment]

    source_issue_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("issues.id", ondelete="CASCADE"),
        nullable=False,
    )
    target_issue_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("issues.id", ondelete="CASCADE"),
        nullable=False,
    )
    link_type: Mapped[IssueLinkType] = mapped_column(
        SQLEnum(
            IssueLinkType,
            name="issue_link_type",
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
    )

    # Relationships — noload by default; use explicit selectinload() in queries that need them.
    # find_all_for_issue adds selectinload(source_issue) + selectinload(target_issue) explicitly.
    # find_dependency_chain only needs UUIDs (scalars), so noload avoids 2xN phantom queries.
    source_issue: Mapped[Issue] = relationship(
        "Issue",
        foreign_keys=[source_issue_id],
        lazy="noload",
    )
    target_issue: Mapped[Issue] = relationship(
        "Issue",
        foreign_keys=[target_issue_id],
        lazy="noload",
    )

    __table_args__ = (
        UniqueConstraint(
            "source_issue_id",
            "target_issue_id",
            "link_type",
            name="uq_issue_links_source_target_type",
        ),
        CheckConstraint(
            "source_issue_id != target_issue_id",
            name="ck_issue_links_no_self",
        ),
        Index("ix_issue_links_source", "source_issue_id"),
        Index("ix_issue_links_target", "target_issue_id"),
        Index("ix_issue_links_workspace_type", "workspace_id", "link_type"),
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"<IssueLink(id={self.id}, source={self.source_issue_id}, "
            f"target={self.target_issue_id}, type={self.link_type})>"
        )
