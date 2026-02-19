"""Unit tests for PMBlockInsight domain entity (T-229).

Covers:
- UT-017-001: Creation with valid fields
- UT-017-002: Validation — empty/invalid inputs rejected
- UT-017-003: Confidence boundary validation
- UT-017-004: dismiss / undismiss lifecycle
- UT-017-005: soft_delete lifecycle
- UT-017-006: Enum membership

No external dependencies — pure domain logic tests.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from pilot_space.domain.pm_block_insight import (
    InsightSeverity,
    PMBlockInsight,
    PMBlockType,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_insight(**overrides: object) -> PMBlockInsight:
    """Create a valid PMBlockInsight with sensible defaults."""
    defaults: dict[str, object] = {
        "workspace_id": uuid4(),
        "block_id": "block-abc-123",
        "block_type": PMBlockType.SPRINT_BOARD,
        "insight_type": "velocity_risk",
        "severity": InsightSeverity.YELLOW,
        "title": "Sprint velocity declining",
        "analysis": "Team velocity has dropped 30% over 3 sprints.",
        "confidence": 0.85,
    }
    defaults.update(overrides)
    return PMBlockInsight(**defaults)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# UT-017-001: Creation with valid fields
# ---------------------------------------------------------------------------


class TestPMBlockInsightCreation:
    """UT-017-001: PMBlockInsight creation with valid required fields."""

    def test_creates_with_required_fields(self) -> None:
        ws = uuid4()
        insight = PMBlockInsight(
            workspace_id=ws,
            block_id="block-1",
            block_type=PMBlockType.CAPACITY_PLAN,
            insight_type="overallocation",
            severity=InsightSeverity.RED,
            title="Team over-capacity",
            analysis="Available hours exceed capacity by 20%.",
            confidence=0.9,
        )
        assert insight.workspace_id == ws
        assert insight.block_id == "block-1"
        assert insight.block_type == PMBlockType.CAPACITY_PLAN
        assert insight.insight_type == "overallocation"
        assert insight.severity == InsightSeverity.RED
        assert insight.title == "Team over-capacity"
        assert insight.confidence == 0.9

    def test_id_is_none_for_unsaved(self) -> None:
        insight = _make_insight()
        assert insight.id is None

    def test_defaults_dismissed_false(self) -> None:
        insight = _make_insight()
        assert insight.dismissed is False

    def test_defaults_is_deleted_false(self) -> None:
        insight = _make_insight()
        assert insight.is_deleted is False

    def test_defaults_deleted_at_none(self) -> None:
        insight = _make_insight()
        assert insight.deleted_at is None

    def test_timestamps_auto_set(self) -> None:
        insight = _make_insight()
        assert insight.created_at is not None
        assert insight.updated_at is not None

    def test_empty_references_list_by_default(self) -> None:
        insight = _make_insight()
        assert insight.references == []

    def test_empty_suggested_actions_by_default(self) -> None:
        insight = _make_insight()
        assert insight.suggested_actions == []

    def test_custom_references_and_actions(self) -> None:
        refs = ["issue-uuid-1", "https://docs.example.com"]
        actions = ["Reduce scope", "Add capacity"]
        insight = _make_insight(references=refs, suggested_actions=actions)
        assert insight.references == refs
        assert insight.suggested_actions == actions

    def test_all_pm_block_types_accepted(self) -> None:
        for bt in PMBlockType:
            insight = _make_insight(block_type=bt)
            assert insight.block_type == bt

    def test_all_severity_levels_accepted(self) -> None:
        for sev in InsightSeverity:
            insight = _make_insight(severity=sev)
            assert insight.severity == sev


# ---------------------------------------------------------------------------
# UT-017-002: Validation — empty / invalid inputs rejected
# ---------------------------------------------------------------------------


class TestPMBlockInsightValidation:
    """UT-017-002: Invalid field values raise ValueError on construction."""

    def test_empty_block_id_rejected(self) -> None:
        with pytest.raises(ValueError, match="block_id cannot be empty"):
            _make_insight(block_id="   ")

    def test_empty_insight_type_rejected(self) -> None:
        with pytest.raises(ValueError, match="insight_type cannot be empty"):
            _make_insight(insight_type="  ")

    def test_empty_title_rejected(self) -> None:
        with pytest.raises(ValueError, match="title must be 1-255 chars"):
            _make_insight(title="")

    def test_title_too_long_rejected(self) -> None:
        with pytest.raises(ValueError, match="title must be 1-255 chars"):
            _make_insight(title="x" * 256)

    def test_title_at_max_length_accepted(self) -> None:
        insight = _make_insight(title="x" * 255)
        assert len(insight.title) == 255

    def test_empty_analysis_rejected(self) -> None:
        with pytest.raises(ValueError, match="analysis cannot be empty"):
            _make_insight(analysis="  ")


# ---------------------------------------------------------------------------
# UT-017-003: Confidence boundary validation
# ---------------------------------------------------------------------------


class TestPMBlockInsightConfidence:
    """UT-017-003: Confidence must be in [0.0, 1.0]."""

    def test_zero_confidence_accepted(self) -> None:
        insight = _make_insight(confidence=0.0)
        assert insight.confidence == 0.0

    def test_one_confidence_accepted(self) -> None:
        insight = _make_insight(confidence=1.0)
        assert insight.confidence == 1.0

    def test_midpoint_accepted(self) -> None:
        insight = _make_insight(confidence=0.5)
        assert insight.confidence == 0.5

    def test_negative_confidence_rejected(self) -> None:
        with pytest.raises(ValueError, match=r"\[0\.0, 1\.0\]"):
            _make_insight(confidence=-0.01)

    def test_above_one_rejected(self) -> None:
        with pytest.raises(ValueError, match=r"\[0\.0, 1\.0\]"):
            _make_insight(confidence=1.01)


# ---------------------------------------------------------------------------
# UT-017-004: dismiss / undismiss lifecycle
# ---------------------------------------------------------------------------


class TestPMBlockInsightDismiss:
    """UT-017-004: Dismiss and undismiss toggle the dismissed flag."""

    def test_dismiss_sets_flag(self) -> None:
        insight = _make_insight()
        assert insight.dismissed is False
        insight.dismiss()
        assert insight.dismissed is True

    def test_undismiss_clears_flag(self) -> None:
        insight = _make_insight()
        insight.dismiss()
        insight.undismiss()
        assert insight.dismissed is False

    def test_dismiss_updates_updated_at(self) -> None:
        import time

        insight = _make_insight()
        before = insight.updated_at
        time.sleep(0.001)
        insight.dismiss()
        assert insight.updated_at >= before

    def test_undismiss_updates_updated_at(self) -> None:
        import time

        insight = _make_insight()
        insight.dismiss()
        before = insight.updated_at
        time.sleep(0.001)
        insight.undismiss()
        assert insight.updated_at >= before

    def test_double_dismiss_idempotent(self) -> None:
        insight = _make_insight()
        insight.dismiss()
        insight.dismiss()
        assert insight.dismissed is True

    def test_double_undismiss_idempotent(self) -> None:
        insight = _make_insight()
        insight.undismiss()
        assert insight.dismissed is False


# ---------------------------------------------------------------------------
# UT-017-005: soft_delete lifecycle
# ---------------------------------------------------------------------------


class TestPMBlockInsightSoftDelete:
    """UT-017-005: soft_delete marks the insight as deleted."""

    def test_soft_delete_sets_flag(self) -> None:
        insight = _make_insight()
        insight.soft_delete()
        assert insight.is_deleted is True

    def test_soft_delete_sets_deleted_at(self) -> None:
        insight = _make_insight()
        insight.soft_delete()
        assert insight.deleted_at is not None

    def test_soft_delete_updates_updated_at(self) -> None:
        import time

        insight = _make_insight()
        before = insight.updated_at
        time.sleep(0.001)
        insight.soft_delete()
        assert insight.updated_at >= before

    def test_deleted_at_is_none_before_delete(self) -> None:
        insight = _make_insight()
        assert insight.deleted_at is None


# ---------------------------------------------------------------------------
# UT-017-006: Enum membership
# ---------------------------------------------------------------------------


class TestPMBlockEnums:
    """UT-017-006: Enum values match spec."""

    def test_insight_severity_members(self) -> None:
        values = {s.value for s in InsightSeverity}
        assert values == {"green", "yellow", "red"}

    def test_pm_block_type_members(self) -> None:
        values = {t.value for t in PMBlockType}
        assert values == {"sprint_board", "dependency_map", "capacity_plan", "release_notes"}

    def test_severity_is_str_enum(self) -> None:
        assert isinstance(InsightSeverity.RED, str)
        assert InsightSeverity.RED == "red"

    def test_pm_block_type_is_str_enum(self) -> None:
        assert isinstance(PMBlockType.SPRINT_BOARD, str)
        assert PMBlockType.SPRINT_BOARD == "sprint_board"
