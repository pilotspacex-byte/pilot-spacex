"""Unit tests for WorkIntent and IntentArtifact domain entities.

Tests status transitions, confidence validation, dedup hash computation,
and immutability rules post-confirmation.
"""

from __future__ import annotations

import hashlib
import uuid

import pytest

from pilot_space.domain.exceptions import ValidationError
from pilot_space.domain.intent_artifact import ArtifactType, IntentArtifact
from pilot_space.domain.work_intent import DedupStatus, IntentStatus, WorkIntent


def make_intent(**kwargs) -> WorkIntent:
    """Factory helper for WorkIntent with sensible defaults."""
    defaults = {
        "workspace_id": uuid.uuid4(),
        "what": "Build user authentication module",
        "confidence": 0.85,
    }
    defaults.update(kwargs)
    return WorkIntent(**defaults)


class TestWorkIntentCreation:
    """Tests for WorkIntent initialization and validation."""

    def test_create_with_required_fields(self) -> None:
        intent = make_intent()
        assert intent.status == IntentStatus.DETECTED
        assert intent.dedup_status == DedupStatus.PENDING
        assert intent.dedup_hash is not None
        assert len(intent.dedup_hash) == 64

    def test_dedup_hash_auto_computed_on_init(self) -> None:
        intent = make_intent(what="Test intent")
        expected = hashlib.sha256(b"test intent").hexdigest()
        assert intent.dedup_hash == expected

    def test_create_with_explicit_dedup_hash_overrides_auto(self) -> None:
        explicit_hash = "a" * 64
        intent = make_intent(dedup_hash=explicit_hash)
        # __post_init__ only sets dedup_hash if None
        assert intent.dedup_hash == explicit_hash

    def test_create_with_invalid_confidence_raises(self) -> None:
        with pytest.raises(ValidationError, match="Confidence must be between"):
            make_intent(confidence=1.1)

    def test_create_with_negative_confidence_raises(self) -> None:
        with pytest.raises(ValidationError, match="Confidence must be between"):
            make_intent(confidence=-0.01)

    def test_confidence_boundary_values_are_valid(self) -> None:
        make_intent(confidence=0.0)
        make_intent(confidence=1.0)


class TestWorkIntentStatusTransitions:
    """Tests for valid and invalid status transitions."""

    def test_detected_to_confirmed(self) -> None:
        intent = make_intent()
        intent.transition_to(IntentStatus.CONFIRMED)
        assert intent.status == IntentStatus.CONFIRMED

    def test_detected_to_rejected(self) -> None:
        intent = make_intent()
        intent.transition_to(IntentStatus.REJECTED)
        assert intent.status == IntentStatus.REJECTED

    def test_confirmed_to_executing(self) -> None:
        intent = make_intent()
        intent.transition_to(IntentStatus.CONFIRMED)
        intent.transition_to(IntentStatus.EXECUTING)
        assert intent.status == IntentStatus.EXECUTING

    def test_confirmed_to_rejected(self) -> None:
        intent = make_intent()
        intent.transition_to(IntentStatus.CONFIRMED)
        intent.transition_to(IntentStatus.REJECTED)
        assert intent.status == IntentStatus.REJECTED

    def test_executing_to_review(self) -> None:
        intent = make_intent()
        intent.transition_to(IntentStatus.CONFIRMED)
        intent.transition_to(IntentStatus.EXECUTING)
        intent.transition_to(IntentStatus.REVIEW)
        assert intent.status == IntentStatus.REVIEW

    def test_executing_to_rejected(self) -> None:
        intent = make_intent()
        intent.transition_to(IntentStatus.CONFIRMED)
        intent.transition_to(IntentStatus.EXECUTING)
        intent.transition_to(IntentStatus.REJECTED)
        assert intent.status == IntentStatus.REJECTED

    def test_review_to_accepted(self) -> None:
        intent = make_intent()
        intent.transition_to(IntentStatus.CONFIRMED)
        intent.transition_to(IntentStatus.EXECUTING)
        intent.transition_to(IntentStatus.REVIEW)
        intent.transition_to(IntentStatus.ACCEPTED)
        assert intent.status == IntentStatus.ACCEPTED

    def test_review_to_rejected(self) -> None:
        intent = make_intent()
        intent.transition_to(IntentStatus.CONFIRMED)
        intent.transition_to(IntentStatus.EXECUTING)
        intent.transition_to(IntentStatus.REVIEW)
        intent.transition_to(IntentStatus.REJECTED)
        assert intent.status == IntentStatus.REJECTED

    def test_detected_to_executing_is_invalid(self) -> None:
        intent = make_intent()
        with pytest.raises(ValidationError, match="Cannot transition"):
            intent.transition_to(IntentStatus.EXECUTING)

    def test_detected_to_accepted_is_invalid(self) -> None:
        intent = make_intent()
        with pytest.raises(ValidationError, match="Cannot transition"):
            intent.transition_to(IntentStatus.ACCEPTED)

    def test_confirmed_to_accepted_is_invalid(self) -> None:
        intent = make_intent()
        intent.transition_to(IntentStatus.CONFIRMED)
        with pytest.raises(ValidationError, match="Cannot transition"):
            intent.transition_to(IntentStatus.ACCEPTED)

    def test_accepted_is_terminal(self) -> None:
        intent = make_intent()
        intent.transition_to(IntentStatus.CONFIRMED)
        intent.transition_to(IntentStatus.EXECUTING)
        intent.transition_to(IntentStatus.REVIEW)
        intent.transition_to(IntentStatus.ACCEPTED)
        with pytest.raises(ValidationError, match="Cannot transition"):
            intent.transition_to(IntentStatus.REJECTED)

    def test_rejected_is_terminal(self) -> None:
        intent = make_intent()
        intent.transition_to(IntentStatus.REJECTED)
        with pytest.raises(ValidationError, match="Cannot transition"):
            intent.transition_to(IntentStatus.CONFIRMED)

    def test_convenience_confirm_method(self) -> None:
        intent = make_intent()
        intent.confirm()
        assert intent.status == IntentStatus.CONFIRMED

    def test_convenience_reject_method(self) -> None:
        intent = make_intent()
        intent.reject()
        assert intent.status == IntentStatus.REJECTED

    def test_convenience_accept_method(self) -> None:
        intent = make_intent()
        intent.confirm()
        intent.start_executing()
        intent.mark_review()
        intent.accept()
        assert intent.status == IntentStatus.ACCEPTED


class TestWorkIntentImmutability:
    """Tests for field immutability after confirmation."""

    def test_update_what_allowed_in_detected(self) -> None:
        intent = make_intent(what="Original description")
        intent.update_what("Updated description")
        assert intent.what == "Updated description"

    def test_update_what_blocked_after_confirmed(self) -> None:
        intent = make_intent()
        intent.confirm()
        with pytest.raises(ValidationError, match="Cannot update 'what'"):
            intent.update_what("New description")

    def test_update_why_allowed_in_detected(self) -> None:
        intent = make_intent()
        intent.update_why("Business reason")
        assert intent.why == "Business reason"

    def test_update_why_blocked_after_confirmed(self) -> None:
        intent = make_intent()
        intent.confirm()
        with pytest.raises(ValidationError, match="Cannot update 'why'"):
            intent.update_why("Different reason")

    def test_update_what_recomputes_dedup_hash(self) -> None:
        intent = make_intent(what="Original")
        original_hash = intent.dedup_hash
        intent.update_what("Changed")
        assert intent.dedup_hash != original_hash
        assert intent.dedup_hash == WorkIntent.compute_dedup_hash("Changed")


class TestWorkIntentDedupHash:
    """Tests for dedup hash computation."""

    def test_hash_normalizes_to_lowercase(self) -> None:
        h1 = WorkIntent.compute_dedup_hash("Build AUTH Module")
        h2 = WorkIntent.compute_dedup_hash("build auth module")
        assert h1 == h2

    def test_hash_normalizes_whitespace(self) -> None:
        h1 = WorkIntent.compute_dedup_hash("  build  auth  module  ")
        h2 = WorkIntent.compute_dedup_hash("build auth module")
        assert h1 == h2

    def test_hash_is_64_chars(self) -> None:
        h = WorkIntent.compute_dedup_hash("test")
        assert len(h) == 64

    def test_different_texts_produce_different_hashes(self) -> None:
        h1 = WorkIntent.compute_dedup_hash("build auth")
        h2 = WorkIntent.compute_dedup_hash("build search")
        assert h1 != h2

    def test_mark_dedup_complete_updates_status(self) -> None:
        intent = make_intent()
        assert intent.dedup_status == DedupStatus.PENDING
        intent.mark_dedup_complete()
        assert intent.dedup_status == DedupStatus.COMPLETE


class TestWorkIntentProperties:
    """Tests for computed properties."""

    def test_is_terminal_false_for_detected(self) -> None:
        intent = make_intent()
        assert intent.is_terminal is False

    def test_is_terminal_true_for_accepted(self) -> None:
        intent = make_intent()
        intent.confirm()
        intent.start_executing()
        intent.mark_review()
        intent.accept()
        assert intent.is_terminal is True

    def test_is_terminal_true_for_rejected(self) -> None:
        intent = make_intent()
        intent.reject()
        assert intent.is_terminal is True

    def test_is_mutable_true_for_detected(self) -> None:
        intent = make_intent()
        assert intent.is_mutable is True

    def test_is_mutable_false_after_confirmed(self) -> None:
        intent = make_intent()
        intent.confirm()
        assert intent.is_mutable is False

    def test_set_confidence_valid(self) -> None:
        intent = make_intent(confidence=0.5)
        intent.set_confidence(0.95)
        assert intent.confidence == 0.95

    def test_set_confidence_invalid_raises(self) -> None:
        intent = make_intent()
        with pytest.raises(ValidationError, match="Confidence must be between"):
            intent.set_confidence(2.0)


class TestIntentArtifact:
    """Tests for IntentArtifact domain entity."""

    def test_create_valid_artifact(self) -> None:
        artifact = IntentArtifact(
            intent_id=uuid.uuid4(),
            artifact_type=ArtifactType.ISSUE,
            reference_id=uuid.uuid4(),
            reference_type="issue",
        )
        assert artifact.artifact_type == ArtifactType.ISSUE
        assert artifact.reference_type == "issue"

    def test_empty_reference_type_raises(self) -> None:
        with pytest.raises(ValueError, match="reference_type cannot be empty"):
            IntentArtifact(
                intent_id=uuid.uuid4(),
                artifact_type=ArtifactType.NOTE,
                reference_id=uuid.uuid4(),
                reference_type="",
            )

    def test_reference_type_too_long_raises(self) -> None:
        with pytest.raises(ValueError, match="reference_type must be <= 50 chars"):
            IntentArtifact(
                intent_id=uuid.uuid4(),
                artifact_type=ArtifactType.NOTE_BLOCK,
                reference_id=uuid.uuid4(),
                reference_type="x" * 51,
            )

    def test_artifact_type_enum_values(self) -> None:
        assert ArtifactType.NOTE_BLOCK.value == "note_block"
        assert ArtifactType.ISSUE.value == "issue"
        assert ArtifactType.NOTE.value == "note"
