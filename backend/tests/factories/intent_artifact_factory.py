"""Factory for IntentArtifact domain entity.

Provides make_intent_artifact() with sensible defaults for test use.
Follows simple factory function pattern (no factory_boy dependency)
since IntentArtifact is a pure domain dataclass, not an ORM model.

Usage:
    artifact = make_intent_artifact(intent_id=intent.id)
    issue_artifact = make_intent_artifact(artifact_type=ArtifactType.ISSUE)
    note_artifact = make_intent_artifact(
        intent_id=uuid4(),
        artifact_type=ArtifactType.NOTE,
        reference_type="note",
    )
"""

from __future__ import annotations

from uuid import UUID, uuid4

from pilot_space.domain.intent_artifact import ArtifactType, IntentArtifact


def make_intent_artifact(
    *,
    intent_id: UUID | None = None,
    artifact_type: ArtifactType = ArtifactType.NOTE_BLOCK,
    reference_id: UUID | None = None,
    reference_type: str = "note_block",
    id: UUID | None = None,
) -> IntentArtifact:
    """Create an IntentArtifact with valid defaults.

    All parameters are keyword-only to prevent positional argument errors.

    Args:
        intent_id: Parent WorkIntent UUID (generated if not provided).
        artifact_type: Artifact type classification.
        reference_id: UUID of the referenced artifact (generated if not provided).
        reference_type: String type name of the referenced entity (max 50 chars).
        id: Entity UUID (None for unsaved state).

    Returns:
        IntentArtifact instance.
    """
    return IntentArtifact(
        intent_id=intent_id or uuid4(),
        artifact_type=artifact_type,
        reference_id=reference_id or uuid4(),
        reference_type=reference_type,
        id=id,
    )


def make_issue_artifact(intent_id: UUID | None = None, **kwargs: object) -> IntentArtifact:
    """Create an IntentArtifact linked to an Issue.

    Args:
        intent_id: Parent WorkIntent UUID.
        **kwargs: Additional overrides forwarded to make_intent_artifact().

    Returns:
        IntentArtifact with ArtifactType.ISSUE.
    """
    return make_intent_artifact(
        intent_id=intent_id,
        artifact_type=ArtifactType.ISSUE,
        reference_type="issue",
        **kwargs,  # type: ignore[arg-type]
    )


def make_note_artifact(intent_id: UUID | None = None, **kwargs: object) -> IntentArtifact:
    """Create an IntentArtifact linked to a Note.

    Args:
        intent_id: Parent WorkIntent UUID.
        **kwargs: Additional overrides forwarded to make_intent_artifact().

    Returns:
        IntentArtifact with ArtifactType.NOTE.
    """
    return make_intent_artifact(
        intent_id=intent_id,
        artifact_type=ArtifactType.NOTE,
        reference_type="note",
        **kwargs,  # type: ignore[arg-type]
    )


__all__ = [
    "make_intent_artifact",
    "make_issue_artifact",
    "make_note_artifact",
]
