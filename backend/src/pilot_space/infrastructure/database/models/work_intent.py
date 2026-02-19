"""WorkIntent and IntentArtifact SQLAlchemy models.

Persistent storage for AI workforce platform intents and their artifacts.
Feature 015: AI Workforce Platform
"""

from __future__ import annotations

import uuid
from typing import Any

from pgvector.sqlalchemy import Vector  # type: ignore[import-untyped]
from sqlalchemy import (
    Enum as SQLEnum,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pilot_space.domain.intent_artifact import ArtifactType
from pilot_space.domain.work_intent import DedupStatus, IntentStatus
from pilot_space.infrastructure.database.base import BaseModel, WorkspaceScopedModel
from pilot_space.infrastructure.database.types import JSONBCompat


class WorkIntent(WorkspaceScopedModel):
    """SQLAlchemy model for work intents.

    Represents a user intent tracked through the AI workforce platform.
    Supports lifecycle management, dedup hashing, and parent-child hierarchy.
    """

    __tablename__ = "work_intents"  # type: ignore[assignment]

    # Override workspace_id to suppress the mixin's standalone index — the
    # composite ix_work_intents_workspace_status(workspace_id, status) covers it.
    workspace_id: Mapped[uuid.UUID] = mapped_column(  # type: ignore[assignment]
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=False,
    )

    # Core intent fields
    what: Mapped[str] = mapped_column(Text, nullable=False)
    why: Mapped[str | None] = mapped_column(Text, nullable=True)
    constraints: Mapped[list[Any] | dict[str, Any] | None] = mapped_column(
        JSONBCompat,
        nullable=True,
        default=None,
    )
    acceptance: Mapped[list[Any] | dict[str, Any] | None] = mapped_column(
        JSONBCompat,
        nullable=True,
        default=None,
    )

    # Lifecycle
    status: Mapped[IntentStatus] = mapped_column(
        SQLEnum(
            IntentStatus,
            name="work_intent_status_enum",
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        default=IntentStatus.DETECTED,
    )

    # Ownership and confidence
    owner: Mapped[str | None] = mapped_column(String(255), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)

    # Hierarchy
    parent_intent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("work_intents.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Source reference (soft ref to TipTap block UUID)
    source_block_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )

    # Embedding for pgvector dedup (768-dim Gemini, nullable until computed)
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(768),
        nullable=True,
        comment="768-dim Gemini embedding for HNSW dedup query",
    )

    # Deduplication
    dedup_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    dedup_status: Mapped[DedupStatus] = mapped_column(
        SQLEnum(
            DedupStatus,
            name="intent_dedup_status_enum",
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        default=DedupStatus.PENDING,
    )

    # Relationships
    artifacts: Mapped[list[IntentArtifact]] = relationship(
        "IntentArtifact",
        back_populates="intent",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    sub_intents: Mapped[list[WorkIntent]] = relationship(
        "WorkIntent",
        back_populates="parent_intent",
        foreign_keys=[parent_intent_id],
        lazy="selectin",
    )
    parent_intent: Mapped[WorkIntent | None] = relationship(
        "WorkIntent",
        back_populates="sub_intents",
        foreign_keys=[parent_intent_id],
        remote_side="WorkIntent.id",
        lazy="joined",
    )

    # Composite indexes
    __table_args__ = (
        Index("ix_work_intents_workspace_status", "workspace_id", "status"),
        Index("ix_work_intents_parent_intent_id", "parent_intent_id"),
        Index("ix_work_intents_source_block_id", "source_block_id"),
        Index("ix_work_intents_dedup_hash", "dedup_hash"),
        Index("ix_work_intents_is_deleted", "is_deleted"),
    )

    def __repr__(self) -> str:
        return f"<WorkIntent(id={self.id}, status={self.status}, what={self.what[:40]!r})>"


class IntentArtifact(BaseModel):
    """SQLAlchemy model for intent artifacts.

    Links a WorkIntent to a concrete artifact produced during execution.
    RLS enforced via join to work_intents.workspace_id.
    """

    __tablename__ = "intent_artifacts"  # type: ignore[assignment]

    # Parent intent (cascade delete)
    intent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("work_intents.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Artifact classification
    artifact_type: Mapped[ArtifactType] = mapped_column(
        SQLEnum(
            ArtifactType,
            name="intent_artifact_type_enum",
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
    )

    # Reference to actual artifact
    reference_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )
    reference_type: Mapped[str] = mapped_column(String(50), nullable=False)

    # Relationship back to intent
    intent: Mapped[WorkIntent] = relationship(
        "WorkIntent",
        back_populates="artifacts",
        lazy="joined",
    )

    # NOTE: IntentArtifact has no soft-delete — it uses CASCADE from work_intents.
    # Override is_deleted and deleted_at to be unused but inherited from BaseModel.
    __table_args__ = (
        Index("ix_intent_artifacts_intent_id", "intent_id"),
        Index("ix_intent_artifacts_reference_id", "reference_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<IntentArtifact(id={self.id}, intent_id={self.intent_id}, type={self.artifact_type})>"
        )
