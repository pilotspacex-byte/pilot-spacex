"""IntentArtifact domain entity.

Represents an artifact (note block, issue, note) produced or linked
to a WorkIntent during execution.

Feature 015: AI Workforce Platform
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID


class ArtifactType(StrEnum):
    """Type of artifact linked to a work intent."""

    NOTE_BLOCK = "note_block"
    ISSUE = "issue"
    NOTE = "note"


@dataclass
class IntentArtifact:
    """Domain entity linking a WorkIntent to a produced artifact.

    Artifacts are created when an intent produces or references
    a concrete object (note block, issue, note).

    Attributes:
        intent_id: Parent WorkIntent ID.
        artifact_type: Type classification of the artifact.
        reference_id: UUID of the referenced artifact.
        reference_type: String type name of the referenced entity.
        id: Unique identifier (None for unsaved entities).
        created_at: Creation timestamp.
    """

    intent_id: UUID
    artifact_type: ArtifactType
    reference_id: UUID
    reference_type: str
    id: UUID | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))

    def __post_init__(self) -> None:
        """Validate initial state."""
        if not self.reference_type.strip():
            msg = "reference_type cannot be empty"
            raise ValueError(msg)
        if len(self.reference_type) > 50:
            msg = f"reference_type must be <= 50 chars, got {len(self.reference_type)}"
            raise ValueError(msg)


__all__ = ["ArtifactType", "IntentArtifact"]
