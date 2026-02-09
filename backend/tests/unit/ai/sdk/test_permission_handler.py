"""Tests for permission_handler module.

Covers:
- _get_classification(): default lookup, workspace overrides, DD-003 critical guard
- check_permission(): auto-execute vs approval-required flow
"""

from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from pilot_space.ai.sdk.permission_handler import (
    ActionClassification,
    PermissionHandler,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_handler(
    workspace_settings: dict | None = None,
) -> PermissionHandler:
    """Create a PermissionHandler with a mocked ApprovalService."""
    mock_service = AsyncMock()
    mock_service.create_approval_request = AsyncMock(return_value=uuid4())
    return PermissionHandler(
        approval_service=mock_service,
        workspace_settings=workspace_settings,
    )


# ---------------------------------------------------------------------------
# TestGetClassification
# ---------------------------------------------------------------------------


class TestGetClassification:
    """Tests for _get_classification() method."""

    def test_returns_default_for_known_action(self) -> None:
        handler = _make_handler()
        result = handler._get_classification("ghost_text")
        assert result == ActionClassification.AUTO_EXECUTE

    def test_returns_default_require_approval_for_unknown_action(self) -> None:
        handler = _make_handler()
        result = handler._get_classification("unknown_action_xyz")
        assert result == ActionClassification.DEFAULT_REQUIRE_APPROVAL

    def test_workspace_override_applies_to_non_critical_action(self) -> None:
        handler = _make_handler()
        overrides = {"create_issue": "auto_execute"}
        result = handler._get_classification("create_issue", overrides)
        assert result == ActionClassification.AUTO_EXECUTE

    def test_workspace_override_cannot_downgrade_critical_to_auto(self) -> None:
        """DD-003: Destructive actions cannot be downgraded by workspace overrides."""
        handler = _make_handler()
        overrides = {"delete_issue": "auto_execute"}
        result = handler._get_classification("delete_issue", overrides)
        assert result == ActionClassification.CRITICAL_REQUIRE_APPROVAL

    def test_workspace_override_cannot_downgrade_critical_to_default(self) -> None:
        """DD-003: Destructive actions cannot be downgraded to DEFAULT either."""
        handler = _make_handler()
        overrides = {"merge_pr": "default_require"}
        result = handler._get_classification("merge_pr", overrides)
        assert result == ActionClassification.CRITICAL_REQUIRE_APPROVAL

    def test_workspace_override_cannot_downgrade_archive_workspace(self) -> None:
        """DD-003: archive_workspace is critical and cannot be overridden."""
        handler = _make_handler()
        overrides = {"archive_workspace": "auto_execute"}
        result = handler._get_classification("archive_workspace", overrides)
        assert result == ActionClassification.CRITICAL_REQUIRE_APPROVAL

    def test_workspace_override_cannot_downgrade_close_issue(self) -> None:
        """DD-003: close_issue is critical and cannot be overridden."""
        handler = _make_handler()
        overrides = {"close_issue": "auto_execute"}
        result = handler._get_classification("close_issue", overrides)
        assert result == ActionClassification.CRITICAL_REQUIRE_APPROVAL

    def test_all_critical_actions_are_guarded(self) -> None:
        """Verify every CRITICAL action in ACTION_CLASSIFICATIONS is guarded."""
        handler = _make_handler()
        critical_actions = [
            name
            for name, cls in PermissionHandler.ACTION_CLASSIFICATIONS.items()
            if cls == ActionClassification.CRITICAL_REQUIRE_APPROVAL
        ]
        assert len(critical_actions) > 0, "Should have at least one critical action"

        for action in critical_actions:
            overrides = {action: "auto_execute"}
            result = handler._get_classification(action, overrides)
            assert result == ActionClassification.CRITICAL_REQUIRE_APPROVAL, (
                f"Critical action '{action}' was downgraded by workspace override"
            )

    def test_no_override_returns_default(self) -> None:
        handler = _make_handler()
        result = handler._get_classification("create_issue")
        assert result == ActionClassification.DEFAULT_REQUIRE_APPROVAL

    def test_none_overrides_returns_default(self) -> None:
        handler = _make_handler()
        result = handler._get_classification("create_issue", None)
        assert result == ActionClassification.DEFAULT_REQUIRE_APPROVAL


# ---------------------------------------------------------------------------
# TestCheckPermission
# ---------------------------------------------------------------------------


class TestCheckPermission:
    """Tests for check_permission() method."""

    @pytest.mark.asyncio
    async def test_auto_execute_action_returns_auto(self) -> None:
        handler = _make_handler()
        result = await handler.check_permission(
            workspace_id=uuid4(),
            user_id=uuid4(),
            agent_name="test_agent",
            action_name="ghost_text",
            description="Generate ghost text",
            proposed_changes={},
        )
        assert result.requires_approval is False
        assert result.allowed is True

    @pytest.mark.asyncio
    async def test_content_creation_action_requires_approval(self) -> None:
        handler = _make_handler()
        result = await handler.check_permission(
            workspace_id=uuid4(),
            user_id=uuid4(),
            agent_name="test_agent",
            action_name="create_issue",
            description="Create a new issue",
            proposed_changes={"title": "Test"},
        )
        assert result.requires_approval is True
        assert result.approval_id is not None

    @pytest.mark.asyncio
    async def test_critical_action_requires_approval(self) -> None:
        handler = _make_handler()
        result = await handler.check_permission(
            workspace_id=uuid4(),
            user_id=uuid4(),
            agent_name="test_agent",
            action_name="delete_issue",
            description="Delete an issue",
            proposed_changes={"issue_id": str(uuid4())},
        )
        assert result.requires_approval is True
        assert result.approval_id is not None
