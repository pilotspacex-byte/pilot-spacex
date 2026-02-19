"""Unit tests for WorkIntent domain entity (T-007).

Covers UT-015-001 through UT-015-010:
- Creation with valid fields
- Full status transition lifecycle (happy path + rejection)
- Invalid transition rejection
- Confidence range validation
- Dedup hash stability and uniqueness
- Immutability of what/why after confirm
- IntentArtifact creation and FK linkage

No external dependencies — pure domain logic tests.
"""

from __future__ import annotations

import hashlib
from uuid import uuid4

import pytest

from pilot_space.domain.intent_artifact import ArtifactType, IntentArtifact
from pilot_space.domain.work_intent import DedupStatus, IntentStatus, WorkIntent
from tests.factories import make_intent_artifact, make_work_intent
from tests.factories.work_intent_factory import (
    make_confirmed_work_intent,
    make_executing_work_intent,
)

# ---------------------------------------------------------------------------
# UT-015-001: Creation with valid fields
# ---------------------------------------------------------------------------


class TestWorkIntentCreation:
    """UT-015-001: WorkIntent creation with valid fields."""

    def test_creates_with_required_fields(self) -> None:
        workspace_id = uuid4()
        intent = WorkIntent(workspace_id=workspace_id, what="Implement OAuth", confidence=0.9)
        assert intent.workspace_id == workspace_id
        assert intent.what == "Implement OAuth"
        assert intent.confidence == 0.9
        assert intent.status == IntentStatus.DETECTED
        assert intent.id is None  # unsaved

    def test_creates_with_optional_fields(self) -> None:
        why = "Users need single sign-on"
        constraints = [{"type": "tech", "value": "OAuth2"}]
        acceptance = {"criteria": "Login via Google works"}
        intent = make_work_intent(why=why, constraints=constraints, acceptance=acceptance)
        assert intent.why == why
        assert intent.constraints == constraints
        assert intent.acceptance == acceptance

    def test_dedup_hash_auto_computed_on_init(self) -> None:
        intent = make_work_intent(what="Build login page")
        expected = WorkIntent.compute_dedup_hash("Build login page")
        assert intent.dedup_hash == expected

    def test_default_dedup_status_is_pending(self) -> None:
        intent = make_work_intent()
        assert intent.dedup_status == DedupStatus.PENDING

    def test_timestamps_set_on_creation(self) -> None:
        intent = make_work_intent()
        assert intent.created_at is not None
        assert intent.updated_at is not None

    def test_factory_default_values(self) -> None:
        intent = make_work_intent()
        assert 0.0 <= intent.confidence <= 1.0
        assert intent.status == IntentStatus.DETECTED


# ---------------------------------------------------------------------------
# UT-015-002: Full status lifecycle (detected -> accepted)
# ---------------------------------------------------------------------------


class TestWorkIntentTransitionToAccepted:
    """UT-015-002: detected -> confirmed -> executing -> review -> accepted."""

    def test_full_happy_path_lifecycle(self) -> None:
        intent = make_work_intent()
        assert intent.status == IntentStatus.DETECTED

        intent.confirm()
        assert intent.status == IntentStatus.CONFIRMED

        intent.start_executing()
        assert intent.status == IntentStatus.EXECUTING

        intent.mark_review()
        assert intent.status == IntentStatus.REVIEW

        intent.accept()
        assert intent.status == IntentStatus.ACCEPTED

    def test_accepted_is_terminal(self) -> None:
        intent = make_work_intent()
        intent.confirm()
        intent.start_executing()
        intent.mark_review()
        intent.accept()
        assert intent.is_terminal is True

    def test_updated_at_changes_on_each_transition(self) -> None:
        import time

        intent = make_work_intent()
        before = intent.updated_at
        time.sleep(0.001)
        intent.confirm()
        assert intent.updated_at >= before


# ---------------------------------------------------------------------------
# UT-015-003: Full status lifecycle ending with rejection
# ---------------------------------------------------------------------------


class TestWorkIntentTransitionToRejected:
    """UT-015-003: detected -> confirmed -> executing -> review -> rejected."""

    def test_reject_from_review(self) -> None:
        intent = make_work_intent()
        intent.confirm()
        intent.start_executing()
        intent.mark_review()
        intent.reject()
        assert intent.status == IntentStatus.REJECTED
        assert intent.is_terminal is True

    def test_reject_from_confirmed(self) -> None:
        intent = make_work_intent()
        intent.confirm()
        intent.reject()
        assert intent.status == IntentStatus.REJECTED

    def test_reject_from_detected(self) -> None:
        intent = make_work_intent()
        intent.reject()
        assert intent.status == IntentStatus.REJECTED

    def test_reject_from_executing(self) -> None:
        intent = make_work_intent()
        intent.confirm()
        intent.start_executing()
        intent.reject()
        assert intent.status == IntentStatus.REJECTED


# ---------------------------------------------------------------------------
# UT-015-004: Invalid transitions are rejected
# ---------------------------------------------------------------------------


class TestWorkIntentInvalidTransitions:
    """UT-015-004: Invalid transitions raise ValueError."""

    def test_detected_cannot_skip_to_executing(self) -> None:
        intent = make_work_intent()
        with pytest.raises(ValueError, match="Cannot transition"):
            intent.start_executing()

    def test_detected_cannot_go_to_accepted(self) -> None:
        intent = make_work_intent()
        with pytest.raises(ValueError, match="Cannot transition"):
            intent.accept()

    def test_detected_cannot_go_to_review(self) -> None:
        intent = make_work_intent()
        with pytest.raises(ValueError, match="Cannot transition"):
            intent.mark_review()

    def test_confirmed_cannot_go_to_accepted(self) -> None:
        intent = make_confirmed_work_intent()
        with pytest.raises(ValueError, match="Cannot transition"):
            intent.accept()

    def test_executing_cannot_go_to_confirmed(self) -> None:
        intent = make_executing_work_intent()
        with pytest.raises(ValueError, match="Cannot transition"):
            intent.confirm()

    def test_accepted_has_no_transitions(self) -> None:
        intent = make_work_intent()
        intent.confirm()
        intent.start_executing()
        intent.mark_review()
        intent.accept()
        with pytest.raises(ValueError, match="Cannot transition"):
            intent.reject()

    def test_rejected_has_no_transitions(self) -> None:
        intent = make_work_intent()
        intent.reject()
        with pytest.raises(ValueError, match="Cannot transition"):
            intent.confirm()

    def test_error_message_includes_allowed_targets(self) -> None:
        intent = make_work_intent()
        with pytest.raises(ValueError, match="Allowed:"):
            intent.start_executing()


# ---------------------------------------------------------------------------
# UT-015-005: Confidence range validation — boundaries accepted
# ---------------------------------------------------------------------------


class TestWorkIntentConfidenceBoundaries:
    """UT-015-005: 0.0 and 1.0 are valid confidence values."""

    def test_confidence_zero_accepted(self) -> None:
        intent = make_work_intent(confidence=0.0)
        assert intent.confidence == 0.0

    def test_confidence_one_accepted(self) -> None:
        intent = make_work_intent(confidence=1.0)
        assert intent.confidence == 1.0

    def test_confidence_midpoint_accepted(self) -> None:
        intent = make_work_intent(confidence=0.75)
        assert intent.confidence == 0.75


# ---------------------------------------------------------------------------
# UT-015-006: Confidence out of range rejected
# ---------------------------------------------------------------------------


class TestWorkIntentConfidenceValidation:
    """UT-015-006: Confidence outside [0.0, 1.0] raises ValueError."""

    def test_negative_confidence_rejected(self) -> None:
        with pytest.raises(ValueError, match="Confidence"):
            make_work_intent(confidence=-0.1)

    def test_confidence_above_one_rejected(self) -> None:
        with pytest.raises(ValueError, match="Confidence"):
            make_work_intent(confidence=1.01)

    def test_set_confidence_out_of_range_rejected(self) -> None:
        intent = make_work_intent(confidence=0.8)
        with pytest.raises(ValueError, match="Confidence"):
            intent.set_confidence(1.5)

    def test_set_confidence_in_range_accepted(self) -> None:
        intent = make_work_intent(confidence=0.8)
        intent.set_confidence(0.5)
        assert intent.confidence == 0.5


# ---------------------------------------------------------------------------
# UT-015-007: Dedup hash is stable for same input
# ---------------------------------------------------------------------------


class TestWorkIntentDedupHashStability:
    """UT-015-007: Same what produces same hash; normalizes whitespace and case."""

    def test_same_what_produces_same_hash(self) -> None:
        h1 = WorkIntent.compute_dedup_hash("Implement OAuth login")
        h2 = WorkIntent.compute_dedup_hash("Implement OAuth login")
        assert h1 == h2

    def test_hash_is_64_char_hex(self) -> None:
        h = WorkIntent.compute_dedup_hash("Build feature")
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_normalizes_extra_whitespace(self) -> None:
        h1 = WorkIntent.compute_dedup_hash("Build  the  feature")
        h2 = WorkIntent.compute_dedup_hash("Build the feature")
        assert h1 == h2

    def test_normalizes_case(self) -> None:
        h1 = WorkIntent.compute_dedup_hash("Build Feature")
        h2 = WorkIntent.compute_dedup_hash("build feature")
        assert h1 == h2

    def test_compute_dedup_hash_matches_sha256(self) -> None:
        text = "implement login"
        normalized = " ".join(text.lower().split())
        expected = hashlib.sha256(normalized.encode()).hexdigest()
        assert WorkIntent.compute_dedup_hash(text) == expected


# ---------------------------------------------------------------------------
# UT-015-008: Dedup hash differs for different inputs
# ---------------------------------------------------------------------------


class TestWorkIntentDedupHashUniqueness:
    """UT-015-008: Different what values produce different hashes."""

    def test_different_what_produces_different_hash(self) -> None:
        h1 = WorkIntent.compute_dedup_hash("Implement OAuth")
        h2 = WorkIntent.compute_dedup_hash("Implement SAML")
        assert h1 != h2

    def test_update_what_recomputes_hash(self) -> None:
        intent = make_work_intent(what="Original task")
        original_hash = intent.dedup_hash
        intent.update_what("Updated task")
        assert intent.dedup_hash != original_hash
        assert intent.dedup_hash == WorkIntent.compute_dedup_hash("Updated task")


# ---------------------------------------------------------------------------
# UT-015-009: what/why immutable after confirmed
# ---------------------------------------------------------------------------


class TestWorkIntentImmutabilityAfterConfirm:
    """UT-015-009: update_what/update_why rejected after confirm."""

    def test_update_what_blocked_after_confirm(self) -> None:
        intent = make_confirmed_work_intent(what="Original task")
        with pytest.raises(ValueError, match="Cannot update 'what'"):
            intent.update_what("Modified task")

    def test_update_why_blocked_after_confirm(self) -> None:
        intent = make_confirmed_work_intent()
        with pytest.raises(ValueError, match="Cannot update 'why'"):
            intent.update_why("Changed motivation")

    def test_update_what_allowed_before_confirm(self) -> None:
        intent = make_work_intent(what="Draft task")
        intent.update_what("Revised task")
        assert intent.what == "Revised task"

    def test_update_why_allowed_before_confirm(self) -> None:
        intent = make_work_intent(why="Original reason")
        intent.update_why("Better reason")
        assert intent.why == "Better reason"

    def test_what_unchanged_on_failed_update(self) -> None:
        intent = make_confirmed_work_intent(what="Final task")
        with pytest.raises(ValueError, match="Cannot update 'what' after status"):
            intent.update_what("Blocked update")
        assert intent.what == "Final task"


# ---------------------------------------------------------------------------
# UT-015-010: IntentArtifact creation with FK to WorkIntent
# ---------------------------------------------------------------------------


class TestIntentArtifactCreation:
    """UT-015-010: IntentArtifact creation with valid FK to WorkIntent."""

    def test_creates_with_intent_id(self) -> None:
        intent = make_work_intent()
        intent.id = uuid4()  # simulate saved state
        artifact = make_intent_artifact(intent_id=intent.id)
        assert artifact.intent_id == intent.id

    def test_note_block_artifact(self) -> None:
        artifact = make_intent_artifact(artifact_type=ArtifactType.NOTE_BLOCK)
        assert artifact.artifact_type == ArtifactType.NOTE_BLOCK
        assert isinstance(artifact.reference_id, type(uuid4()))

    def test_issue_artifact(self) -> None:
        artifact = IntentArtifact(
            intent_id=uuid4(),
            artifact_type=ArtifactType.ISSUE,
            reference_id=uuid4(),
            reference_type="issue",
        )
        assert artifact.artifact_type == ArtifactType.ISSUE
        assert artifact.reference_type == "issue"

    def test_note_artifact(self) -> None:
        artifact = IntentArtifact(
            intent_id=uuid4(),
            artifact_type=ArtifactType.NOTE,
            reference_id=uuid4(),
            reference_type="note",
        )
        assert artifact.artifact_type == ArtifactType.NOTE

    def test_empty_reference_type_rejected(self) -> None:
        with pytest.raises(ValueError, match="reference_type cannot be empty"):
            IntentArtifact(
                intent_id=uuid4(),
                artifact_type=ArtifactType.NOTE_BLOCK,
                reference_id=uuid4(),
                reference_type="   ",
            )

    def test_reference_type_too_long_rejected(self) -> None:
        with pytest.raises(ValueError, match="<= 50 chars"):
            IntentArtifact(
                intent_id=uuid4(),
                artifact_type=ArtifactType.NOTE_BLOCK,
                reference_id=uuid4(),
                reference_type="x" * 51,
            )

    def test_timestamp_auto_set(self) -> None:
        artifact = make_intent_artifact()
        assert artifact.created_at is not None

    def test_id_is_none_for_unsaved(self) -> None:
        artifact = make_intent_artifact()
        assert artifact.id is None

    def test_all_artifact_types_valid(self) -> None:
        for artifact_type in ArtifactType:
            artifact = make_intent_artifact(
                artifact_type=artifact_type,
                reference_type=artifact_type.value,
            )
            assert artifact.artifact_type == artifact_type
