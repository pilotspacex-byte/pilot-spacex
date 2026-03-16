"""PMBlockInsight domain entity.

AI-generated insight attached to a PM block (sprint-board, dependency-map,
capacity-plan, release-notes). Each insight carries a severity level,
confidence score, and suggested corrective actions.

Feature 017: Note Versioning / PM Block Engine — Phase 2a (T-226)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID


class InsightSeverity(StrEnum):
    """Traffic-light severity for a PM block insight."""

    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"


class PMBlockType(StrEnum):
    """PM block types that can carry AI insights (Feature 017)."""

    SPRINT_BOARD = "sprint_board"
    DEPENDENCY_MAP = "dependency_map"
    CAPACITY_PLAN = "capacity_plan"
    RELEASE_NOTES = "release_notes"


@dataclass
class PMBlockInsight:
    """Domain entity for an AI-generated PM block insight.

    Insights are created by the AI layer and attached to specific
    PM block nodes. They are immutable after creation except for
    the ``dismissed`` flag, which users can toggle.

    Attributes:
        workspace_id: Workspace UUID (RLS boundary).
        block_id: TipTap block ID the insight is attached to.
        block_type: Classification of the PM block.
        insight_type: Free-form category string (e.g. "velocity_risk").
        severity: Traffic-light severity level.
        title: Short human-readable title (max 255 chars).
        analysis: Detailed AI analysis text.
        confidence: Score in [0.0, 1.0]. Higher = more reliable.
        references: List of related artifact references (UUIDs or URLs).
        suggested_actions: List of recommended corrective actions.
        dismissed: Whether the user has dismissed this insight.
        is_deleted: Soft-delete flag.
        deleted_at: Soft-delete timestamp.
        id: Unique identifier (None for unsaved entities).
        created_at: Creation timestamp.
        updated_at: Last update timestamp.
    """

    workspace_id: UUID
    block_id: str
    block_type: PMBlockType
    insight_type: str
    severity: InsightSeverity
    title: str
    analysis: str
    confidence: float
    references: list[str] = field(default_factory=list)
    suggested_actions: list[str] = field(default_factory=list)
    dismissed: bool = False
    is_deleted: bool = False
    deleted_at: datetime | None = None
    id: UUID | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))

    def __post_init__(self) -> None:
        """Validate invariants on creation."""
        if not self.block_id.strip():
            msg = "block_id cannot be empty"
            raise ValueError(msg)
        if not self.insight_type.strip():
            msg = "insight_type cannot be empty"
            raise ValueError(msg)
        if not (1 <= len(self.title) <= 255):
            msg = f"title must be 1-255 chars, got {len(self.title)}"
            raise ValueError(msg)
        if not self.analysis.strip():
            msg = "analysis cannot be empty"
            raise ValueError(msg)
        self._validate_confidence(self.confidence)

    @staticmethod
    def _validate_confidence(value: float) -> None:
        if not (0.0 <= value <= 1.0):
            msg = f"confidence must be in [0.0, 1.0], got {value}"
            raise ValueError(msg)

    def dismiss(self) -> None:
        """Mark this insight as dismissed by the user."""
        self.dismissed = True
        self.updated_at = datetime.now(tz=UTC)

    def undismiss(self) -> None:
        """Restore a previously dismissed insight."""
        self.dismissed = False
        self.updated_at = datetime.now(tz=UTC)

    def soft_delete(self) -> None:
        """Soft-delete this insight."""
        self.is_deleted = True
        self.deleted_at = datetime.now(tz=UTC)
        self.updated_at = datetime.now(tz=UTC)


__all__ = ["InsightSeverity", "PMBlockInsight", "PMBlockType"]
