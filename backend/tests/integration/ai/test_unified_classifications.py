"""Integration tests for unified ACTION_CLASSIFICATIONS table.

Verifies:
- All CRITICAL actions are properly classified (APPR-03, T-80-01)
- CRITICAL actions cannot be downgraded via workspace overrides (T-80-04)
- Every ActionType enum value has a classification entry (completeness)
- Merged table has expected minimum entry count (53 original + 10 merged)

Reference: docs/DESIGN_DECISIONS.md#DD-003
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from pilot_space.ai.infrastructure.approval import ActionType
from pilot_space.ai.sdk.permission_handler import (
    ActionClassification,
    PermissionHandler,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# All actions that MUST be CRITICAL_REQUIRE_APPROVAL (APPR-03)
CRITICAL_ACTIONS = [
    "delete_workspace",
    "delete_project",
    "delete_issue",
    "delete_note",
    "merge_pr",
    "bulk_delete",
    "unlink_issue_from_note",
    "unlink_issues",
    "close_issue",
    "archive_workspace",
]

# Minimum expected count: 53 original + 10 merged from ActionType enum
MIN_CLASSIFICATION_COUNT = 63


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_handler() -> PermissionHandler:
    """Create a PermissionHandler with a mocked ApprovalService."""
    return PermissionHandler(
        approval_service=AsyncMock(),
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestCriticalActionPreservation:
    """Test 1 (parametrized): Each CRITICAL action maps to CRITICAL_REQUIRE_APPROVAL."""

    @pytest.mark.parametrize("action_name", CRITICAL_ACTIONS)
    def test_critical_action_classified_correctly(self, action_name: str) -> None:
        """Each CRITICAL action MUST be CRITICAL_REQUIRE_APPROVAL in ACTION_CLASSIFICATIONS."""
        classification = PermissionHandler.ACTION_CLASSIFICATIONS.get(action_name)
        assert classification is not None, (
            f"Action '{action_name}' is missing from ACTION_CLASSIFICATIONS"
        )
        assert classification == ActionClassification.CRITICAL_REQUIRE_APPROVAL, (
            f"Action '{action_name}' should be CRITICAL_REQUIRE_APPROVAL "
            f"but is {classification}"
        )


class TestCriticalDowngradeRejection:
    """Test 2: Workspace override attempting to downgrade CRITICAL action is rejected."""

    @pytest.mark.parametrize("action_name", CRITICAL_ACTIONS)
    def test_workspace_override_cannot_downgrade_critical(self, action_name: str) -> None:
        """CRITICAL actions cannot be downgraded to AUTO_EXECUTE by workspace overrides (APPR-03)."""
        handler = _make_handler()
        overrides = {action_name: "auto_execute"}
        result = handler._get_classification(action_name, overrides)
        assert result == ActionClassification.CRITICAL_REQUIRE_APPROVAL, (
            f"CRITICAL action '{action_name}' was downgraded by workspace override"
        )


class TestClassificationCompleteness:
    """Test 3: Every ActionType enum value has a corresponding entry in ACTION_CLASSIFICATIONS."""

    def test_all_action_types_have_classification(self) -> None:
        """Every ActionType enum value MUST have an entry in ACTION_CLASSIFICATIONS."""
        missing = []
        for action_type in ActionType:
            if action_type.value not in PermissionHandler.ACTION_CLASSIFICATIONS:
                missing.append(action_type.value)

        assert missing == [], (
            f"ActionType values missing from ACTION_CLASSIFICATIONS: {missing}"
        )


class TestClassificationCount:
    """Test 4: Total ACTION_CLASSIFICATIONS count is >= 63 (53 original + 10 merged)."""

    def test_minimum_classification_count(self) -> None:
        """ACTION_CLASSIFICATIONS must have at least 63 entries after merge."""
        count = len(PermissionHandler.ACTION_CLASSIFICATIONS)
        assert count >= MIN_CLASSIFICATION_COUNT, (
            f"ACTION_CLASSIFICATIONS has {count} entries, expected >= {MIN_CLASSIFICATION_COUNT}"
        )
