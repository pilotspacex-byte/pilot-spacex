"""PMBlockInsight SQLAlchemy model.

Persistent storage for AI-generated insights attached to PM blocks.
Feature 017: Note Versioning / PM Block Engine — Phase 2a (T-223)
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Enum as SQLEnum,
    Float,
    Index,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from pilot_space.domain.pm_block_insight import InsightSeverity, PMBlockType
from pilot_space.infrastructure.database.base import WorkspaceScopedModel
from pilot_space.infrastructure.database.types import JSONBCompat


class PMBlockInsight(WorkspaceScopedModel):
    """SQLAlchemy model for AI-generated PM block insights.

    workspace_id is inherited from WorkspaceScopedModel and enforces
    RLS via workspace_members join.
    """

    __tablename__ = "pm_block_insights"  # type: ignore[assignment]

    # Override workspace_id index=False — composite indexes below cover queries.
    workspace_id: Mapped[uuid.UUID] = mapped_column(  # type: ignore[assignment]
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )

    block_id: Mapped[str] = mapped_column(String(), nullable=False)

    block_type: Mapped[PMBlockType] = mapped_column(
        SQLEnum(
            PMBlockType,
            name="pm_block_type_enum",
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
    )

    insight_type: Mapped[str] = mapped_column(String(), nullable=False)

    severity: Mapped[InsightSeverity] = mapped_column(
        SQLEnum(
            InsightSeverity,
            name="insight_severity_enum",
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    analysis: Mapped[str] = mapped_column(Text, nullable=False)

    references: Mapped[list[Any]] = mapped_column(
        JSONBCompat,
        nullable=False,
        server_default="[]",
    )
    suggested_actions: Mapped[list[Any]] = mapped_column(
        JSONBCompat,
        nullable=False,
        server_default="[]",
    )

    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    dismissed: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")

    __table_args__ = (
        CheckConstraint("confidence >= 0.0 AND confidence <= 1.0", name="ck_pbi_confidence_range"),
        Index("idx_pbi_block_dismissed", "block_id", "dismissed"),
        Index("idx_pbi_severity", "severity"),
        Index("idx_pbi_is_deleted", "is_deleted"),
    )

    def __repr__(self) -> str:
        return (
            f"<PMBlockInsight(id={self.id}, block_id={self.block_id!r}, "
            f"severity={self.severity}, dismissed={self.dismissed})>"
        )
