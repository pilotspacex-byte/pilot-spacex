"""Tests for PermissionHandler integration with PermissionService (Phase 69-05).

Covers Task 69-05-01 acceptance criteria:
- DD-003 invariant holds even when the DB-backed PermissionService reports AUTO
  for a CRITICAL tool (defense-in-depth).
- DENY mode from PermissionService raises PermissionDeniedError.
- Fall-through to in-memory ACTION_CLASSIFICATIONS when no service / no row.
- filter_denied_tools helper excludes DENY-mode tools from allowed_tools list.
- PermissionAwareHookExecutor's permission callback converts PermissionDeniedError
  into an SSE `tool_denied_by_policy` event and returns the SDK deny dict.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from pilot_space.ai.sdk.hooks import PermissionAwareHookExecutor
from pilot_space.ai.sdk.permission_handler import (
    ActionClassification,
    PermissionHandler,
    filter_denied_tools,
)
from pilot_space.application.services.permissions.exceptions import (
    PermissionDeniedError,
)
from pilot_space.domain.permissions.tool_permission_mode import ToolPermissionMode


def _make_handler(
    permission_service=None,
    workspace_settings: dict | None = None,
) -> PermissionHandler:
    mock_approval = AsyncMock()
    mock_approval.create_approval_request = AsyncMock(return_value=uuid4())
    return PermissionHandler(
        approval_service=mock_approval,
        workspace_settings=workspace_settings,
        permission_service=permission_service,
    )


class TestDD003Invariant:
    """DD-003 defense-in-depth: CRITICAL tools can never be auto-executed,
    regardless of what the (potentially-compromised) DB row says."""

    async def test_dd003_invariant_holds_even_with_malicious_db_row(self) -> None:
        """Service says AUTO for a CRITICAL tool — handler must override to REQUIRE_APPROVAL."""
        workspace_id = uuid4()
        user_id = uuid4()

        # Fake service claims delete_issue is AUTO — impossible in production
        # (InvalidPolicyError would block the set()), but we test defense-in-depth.
        fake_service = AsyncMock()
        fake_service.resolve = AsyncMock(return_value=ToolPermissionMode.AUTO)

        handler = _make_handler(permission_service=fake_service)

        result = await handler.check_permission(
            workspace_id=workspace_id,
            user_id=user_id,
            agent_name="test-agent",
            action_name="delete_issue",
            description="Test",
            proposed_changes={},
        )

        assert result.requires_approval is True
        assert result.classification == ActionClassification.CRITICAL_REQUIRE_APPROVAL


class TestDenyMode:
    async def test_deny_mode_raises_permission_denied_error(self) -> None:
        fake_service = AsyncMock()
        fake_service.resolve = AsyncMock(return_value=ToolPermissionMode.DENY)

        handler = _make_handler(permission_service=fake_service)

        with pytest.raises(PermissionDeniedError):
            await handler.check_permission(
                workspace_id=uuid4(),
                user_id=uuid4(),
                agent_name="test-agent",
                action_name="update_note",
                description="Test",
                proposed_changes={},
            )


class TestFallthrough:
    async def test_falls_through_to_classifications_when_no_service(self) -> None:
        """No permission_service: behaves identically to legacy handler."""
        handler = _make_handler(permission_service=None)
        result = await handler.check_permission(
            workspace_id=uuid4(),
            user_id=uuid4(),
            agent_name="test-agent",
            action_name="ghost_text",
            description="Test",
            proposed_changes={},
        )
        assert result.allowed is True
        assert result.classification == ActionClassification.AUTO_EXECUTE

    async def test_service_auto_for_non_critical_tool_auto_executes(self) -> None:
        fake_service = AsyncMock()
        fake_service.resolve = AsyncMock(return_value=ToolPermissionMode.AUTO)

        handler = _make_handler(permission_service=fake_service)
        result = await handler.check_permission(
            workspace_id=uuid4(),
            user_id=uuid4(),
            agent_name="test-agent",
            action_name="update_note",  # non-critical
            description="Test",
            proposed_changes={},
        )
        assert result.allowed is True
        assert result.classification == ActionClassification.AUTO_EXECUTE


class TestFilterDeniedTools:
    def test_allowed_tools_filter_excludes_deny_mode(self) -> None:
        all_tools = [f"tool_{i}" for i in range(39)]
        denied = {"tool_5"}
        result = filter_denied_tools(all_tools, denied)
        assert len(result) == 38
        assert "tool_5" not in result
        assert "tool_0" in result

    def test_empty_denied_returns_all(self) -> None:
        all_tools = ["a", "b", "c"]
        assert filter_denied_tools(all_tools, set()) == all_tools


class TestHookCallbackEmitsDeniedEvent:
    async def test_hook_callback_converts_permission_denied_to_sse_event(self) -> None:
        """When permission_hook raises PermissionDeniedError, the SDK callback must
        enqueue a `tool_denied_by_policy` event and return an SDK deny dict."""
        workspace_id = uuid4()
        user_id = uuid4()

        # Fake service that DENIES the tool → handler raises PermissionDeniedError
        fake_service = AsyncMock()
        fake_service.resolve = AsyncMock(return_value=ToolPermissionMode.DENY)

        handler = _make_handler(permission_service=fake_service)

        event_queue: asyncio.Queue = asyncio.Queue()
        executor = PermissionAwareHookExecutor(
            permission_handler=handler,
            workspace_id=workspace_id,
            user_id=user_id,
            event_queue=event_queue,
        )
        callback = executor._create_permission_callback()

        result = await callback(
            {
                "tool_name": "mcp__pilot-notes__update_note",
                "tool_input": {"note_id": "x"},
                "hook_event_name": "PreToolUse",
            },
            "tool-use-id",
            None,
        )

        # SDK deny dict
        assert result["hookSpecificOutput"]["permissionDecision"] == "deny"

        # Event emitted
        assert not event_queue.empty()
        event = await event_queue.get()
        assert event["type"] == "tool_denied_by_policy"
        assert event["tool_name"] == "update_note"
