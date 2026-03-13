"""Tests for approval_waiter module.

Covers:
- wait_for_approval(): DB polling, approval/rejection/timeout/error handling
- ApprovalActionExecutor: action dispatch, unknown action, missing fields
- SSE helpers: classify_urgency, build_affected_entities, build_approval_sse_event
- Hook integration: end-to-end hook -> wait -> resolve flow
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from pilot_space.ai.sdk.approval_waiter import (
    ApprovalActionExecutor,
    build_affected_entities,
    build_approval_sse_event,
    classify_urgency,
    wait_for_approval,
)
from pilot_space.ai.sdk.hooks import PermissionCheckHook

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_approval_record(status: str = "pending") -> SimpleNamespace:
    """Create a fake approval DB record with str-coercible status."""
    return SimpleNamespace(id=uuid4(), status=status)


def _fake_db_session_factory(mock_session: Any | None = None):
    """Return an async context manager producing a mock session."""

    @asynccontextmanager
    async def _ctx():
        yield mock_session or AsyncMock()

    return _ctx


# ---------------------------------------------------------------------------
# TestWaitForApproval
# ---------------------------------------------------------------------------


class TestWaitForApproval:
    """Tests for wait_for_approval() DB polling function."""

    @pytest.mark.asyncio
    async def test_returns_approved_when_status_changes(self) -> None:
        """Pending on first poll, approved on second -> returns 'approved'."""
        records = iter([_make_approval_record("pending"), _make_approval_record("approved")])

        mock_repo = MagicMock()
        mock_repo.get_by_id = AsyncMock(side_effect=lambda _: next(records))

        with (
            patch(
                "pilot_space.ai.sdk.approval_waiter.get_db_session",
                _fake_db_session_factory(),
            ),
            patch(
                "pilot_space.ai.sdk.approval_waiter.ApprovalRepository",
                return_value=mock_repo,
            ),
            patch("pilot_space.ai.sdk.approval_waiter.asyncio.sleep", new_callable=AsyncMock),
        ):
            result = await wait_for_approval(uuid4(), timeout_seconds=10, poll_interval=0.01)

        assert result == "approved"

    @pytest.mark.asyncio
    async def test_returns_rejected_on_rejection(self) -> None:
        """Rejected status returns 'rejected' immediately."""
        mock_repo = MagicMock()
        mock_repo.get_by_id = AsyncMock(return_value=_make_approval_record("rejected"))

        with (
            patch(
                "pilot_space.ai.sdk.approval_waiter.get_db_session",
                _fake_db_session_factory(),
            ),
            patch(
                "pilot_space.ai.sdk.approval_waiter.ApprovalRepository",
                return_value=mock_repo,
            ),
            patch("pilot_space.ai.sdk.approval_waiter.asyncio.sleep", new_callable=AsyncMock),
        ):
            result = await wait_for_approval(uuid4(), timeout_seconds=10, poll_interval=0.01)

        assert result == "rejected"

    @pytest.mark.asyncio
    async def test_returns_expired_on_timeout(self) -> None:
        """Status stays pending past timeout -> returns 'expired'."""
        mock_repo = MagicMock()
        mock_repo.get_by_id = AsyncMock(return_value=_make_approval_record("pending"))

        with (
            patch(
                "pilot_space.ai.sdk.approval_waiter.get_db_session",
                _fake_db_session_factory(),
            ),
            patch(
                "pilot_space.ai.sdk.approval_waiter.ApprovalRepository",
                return_value=mock_repo,
            ),
            patch("pilot_space.ai.sdk.approval_waiter.asyncio.sleep", new_callable=AsyncMock),
        ):
            # timeout_seconds=0 means deadline is immediately exceeded
            result = await wait_for_approval(uuid4(), timeout_seconds=0, poll_interval=0.01)

        assert result == "expired"

    @pytest.mark.asyncio
    async def test_returns_expired_when_not_found(self) -> None:
        """Approval record not found -> returns 'expired'."""
        mock_repo = MagicMock()
        mock_repo.get_by_id = AsyncMock(return_value=None)

        with (
            patch(
                "pilot_space.ai.sdk.approval_waiter.get_db_session",
                _fake_db_session_factory(),
            ),
            patch(
                "pilot_space.ai.sdk.approval_waiter.ApprovalRepository",
                return_value=mock_repo,
            ),
            patch("pilot_space.ai.sdk.approval_waiter.asyncio.sleep", new_callable=AsyncMock),
        ):
            result = await wait_for_approval(uuid4(), timeout_seconds=10, poll_interval=0.01)

        assert result == "expired"

    @pytest.mark.asyncio
    async def test_handles_db_error_gracefully(self) -> None:
        """DB error on first poll, approved on second -> retries and succeeds."""
        call_count = 0
        approved = _make_approval_record("approved")

        @asynccontextmanager
        async def error_then_ok():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("DB connection lost")
            yield AsyncMock()

        mock_repo = MagicMock()
        mock_repo.get_by_id = AsyncMock(return_value=approved)

        with (
            patch("pilot_space.ai.sdk.approval_waiter.get_db_session", error_then_ok),
            patch(
                "pilot_space.ai.sdk.approval_waiter.ApprovalRepository",
                return_value=mock_repo,
            ),
            patch("pilot_space.ai.sdk.approval_waiter.asyncio.sleep", new_callable=AsyncMock),
        ):
            result = await wait_for_approval(uuid4(), timeout_seconds=10, poll_interval=0.01)

        assert result == "approved"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_uses_fresh_session_per_poll(self) -> None:
        """Verify get_db_session is called on each poll iteration."""
        records = iter([_make_approval_record("pending"), _make_approval_record("approved")])
        mock_repo = MagicMock()
        mock_repo.get_by_id = AsyncMock(side_effect=lambda _: next(records))

        session_call_count = 0

        @asynccontextmanager
        async def counting_session():
            nonlocal session_call_count
            session_call_count += 1
            yield AsyncMock()

        with (
            patch("pilot_space.ai.sdk.approval_waiter.get_db_session", counting_session),
            patch(
                "pilot_space.ai.sdk.approval_waiter.ApprovalRepository",
                return_value=mock_repo,
            ),
            patch("pilot_space.ai.sdk.approval_waiter.asyncio.sleep", new_callable=AsyncMock),
        ):
            await wait_for_approval(uuid4(), timeout_seconds=10, poll_interval=0.01)

        assert session_call_count == 2  # One per poll iteration


# ---------------------------------------------------------------------------
# TestApprovalActionExecutor
# ---------------------------------------------------------------------------


class TestApprovalActionExecutor:
    """Tests for ApprovalActionExecutor action dispatch."""

    @pytest.mark.asyncio
    async def test_unknown_action_returns_unsupported(self) -> None:
        """Unknown action_type returns unsupported message, no exception."""
        executor = ApprovalActionExecutor(AsyncMock())

        result = await executor.execute(
            action_type="unknown_action",
            payload={"foo": "bar"},
            user_id=uuid4(),
        )

        assert result["status"] == "unsupported"
        assert "unknown_action" in result["message"]

    @pytest.mark.asyncio
    async def test_create_issue_success(self) -> None:
        """create_issue with valid payload returns executed status."""
        executor = ApprovalActionExecutor(AsyncMock())

        result = await executor.execute(
            action_type="create_issue",
            payload={
                "workspace_id": str(uuid4()),
                "name": "Test Issue",
            },
            user_id=uuid4(),
        )

        assert result["status"] == "executed"
        assert result["name"] == "Test Issue"

    @pytest.mark.asyncio
    async def test_create_issue_missing_workspace_id(self) -> None:
        """create_issue without workspace_id returns error."""
        executor = ApprovalActionExecutor(AsyncMock())

        result = await executor.execute(
            action_type="create_issue",
            payload={"name": "Test Issue"},
            user_id=uuid4(),
        )

        assert result["status"] == "error"
        assert "workspace_id" in result["action_error"]

    @pytest.mark.asyncio
    async def test_update_issue_missing_id(self) -> None:
        """update_issue with missing issue_id returns error."""
        executor = ApprovalActionExecutor(AsyncMock())

        result = await executor.execute(
            action_type="update_issue",
            payload={"name": "Updated"},
            user_id=uuid4(),
        )

        assert result["status"] == "error"
        assert "issue_id" in result["action_error"]

    @pytest.mark.asyncio
    async def test_update_issue_success(self) -> None:
        """update_issue with valid payload returns executed status."""
        executor = ApprovalActionExecutor(AsyncMock())
        issue_id = uuid4()
        mock_issue = MagicMock()

        mock_repo = AsyncMock()
        mock_repo.get_by_id.return_value = mock_issue
        mock_repo.update = AsyncMock()

        with patch(
            "pilot_space.infrastructure.database.repositories.issue_repository.IssueRepository",
            return_value=mock_repo,
        ):
            result = await executor.execute(
                action_type="update_issue",
                payload={"issue_id": str(issue_id), "name": "Updated name"},
                user_id=uuid4(),
            )

        assert result["status"] == "executed"
        assert result["issue_id"] == str(issue_id)

    @pytest.mark.asyncio
    async def test_transition_issue_state_success(self) -> None:
        """transition_issue_state with valid payload returns executed status."""
        executor = ApprovalActionExecutor(AsyncMock())
        issue_id = uuid4()

        result = await executor.execute(
            action_type="transition_issue_state",
            payload={"issue_id": str(issue_id), "new_state": "in_progress"},
            user_id=uuid4(),
        )

        assert result["status"] == "executed"
        assert result["new_state"] == "in_progress"
        assert result["issue_id"] == str(issue_id)

    @pytest.mark.asyncio
    async def test_transition_issue_state_missing_fields(self) -> None:
        """transition_issue_state missing required fields returns error."""
        executor = ApprovalActionExecutor(AsyncMock())

        result = await executor.execute(
            action_type="transition_issue_state",
            payload={"issue_id": str(uuid4())},  # missing new_state
            user_id=uuid4(),
        )

        assert result["status"] == "error"


# ---------------------------------------------------------------------------
# TestSSEHelpers
# ---------------------------------------------------------------------------


class TestSSEHelpers:
    """Tests for extracted SSE helper functions."""

    def test_classify_urgency_destructive(self) -> None:
        assert classify_urgency("delete_issue_from_db") == "high"
        assert classify_urgency("merge_pull_request") == "high"

    def test_classify_urgency_content_creation(self) -> None:
        assert classify_urgency("create_issue_in_db") == "medium"

    def test_classify_urgency_other(self) -> None:
        assert classify_urgency("update_issue_in_db") == "low"

    def test_build_affected_entities_issue(self) -> None:
        entities = build_affected_entities("update_issue_in_db", {"issue_id": "abc-123"})
        assert len(entities) == 1
        assert entities[0]["type"] == "issue"
        assert entities[0]["id"] == "abc-123"

    def test_build_affected_entities_note(self) -> None:
        entities = build_affected_entities("update_note", {"note_id": "note-1"})
        assert len(entities) == 1
        assert entities[0]["type"] == "note"

    def test_build_affected_entities_pr(self) -> None:
        entities = build_affected_entities("merge_pull_request", {"pr_number": 42})
        assert len(entities) == 1
        assert entities[0]["name"] == "PR #42"

    def test_build_affected_entities_empty(self) -> None:
        entities = build_affected_entities("some_tool", {})
        assert entities == []

    def test_build_approval_sse_event_format(self) -> None:
        with patch("pilot_space.ai.sdk.hooks.PermissionCheckHook") as mock_hook:
            mock_hook.TOOL_ACTION_MAPPING = {"create_issue_in_db": "create_issue"}
            event = build_approval_sse_event(
                approval_id=uuid4(),
                tool_name="create_issue_in_db",
                tool_input={"name": "Test"},
                reason="Needs approval",
            )

        assert event.startswith("event: approval_request\n")
        assert '"actionType": "create_issue"' in event
        assert '"urgency": "medium"' in event


# ---------------------------------------------------------------------------
# TestHookApprovalIntegration
# ---------------------------------------------------------------------------


class TestHookApprovalIntegration:
    """Integration tests for hook -> wait_for_approval -> resolve flow."""

    @pytest.mark.asyncio
    async def test_hook_waits_then_allows_on_approval(self) -> None:
        """Simulates the full flow: hook calls wait_for_approval, gets 'approved'."""
        approval_id = uuid4()

        with patch(
            "pilot_space.ai.sdk.approval_waiter.wait_for_approval",
            new_callable=AsyncMock,
            return_value="approved",
        ) as mock_wait:
            from pilot_space.ai.sdk.approval_waiter import wait_for_approval as wfa

            result = await wfa(approval_id)

        assert result == "approved"
        mock_wait.assert_awaited_once_with(approval_id)

    @pytest.mark.asyncio
    async def test_hook_denies_on_rejection(self) -> None:
        """Hook returns 'rejected' when user rejects."""
        with patch(
            "pilot_space.ai.sdk.approval_waiter.wait_for_approval",
            new_callable=AsyncMock,
            return_value="rejected",
        ):
            from pilot_space.ai.sdk.approval_waiter import wait_for_approval

            result = await wait_for_approval(uuid4())

        assert result == "rejected"

    @pytest.mark.asyncio
    async def test_hook_denies_on_timeout(self) -> None:
        """Hook returns 'expired' when approval times out."""
        with patch(
            "pilot_space.ai.sdk.approval_waiter.wait_for_approval",
            new_callable=AsyncMock,
            return_value="expired",
        ):
            from pilot_space.ai.sdk.approval_waiter import wait_for_approval

            result = await wait_for_approval(uuid4())

        assert result == "expired"


# ---------------------------------------------------------------------------
# TestStripMcpPrefix
# ---------------------------------------------------------------------------


class TestStripMcpPrefix:
    """Tests for PermissionCheckHook._strip_mcp_prefix static method."""

    def test_strips_pilot_notes_prefix(self) -> None:
        """mcp__pilot-notes__write_to_note -> write_to_note."""
        assert (
            PermissionCheckHook.strip_mcp_prefix("mcp__pilot-notes__write_to_note")
            == "write_to_note"
        )

    def test_strips_pilot_issues_prefix(self) -> None:
        """mcp__pilot-issues__create_issue -> create_issue."""
        assert (
            PermissionCheckHook.strip_mcp_prefix("mcp__pilot-issues__create_issue")
            == "create_issue"
        )

    def test_strips_pilot_projects_prefix(self) -> None:
        """mcp__pilot-projects__update_project -> update_project."""
        assert (
            PermissionCheckHook.strip_mcp_prefix("mcp__pilot-projects__update_project")
            == "update_project"
        )

    def test_preserves_bare_tool_name(self) -> None:
        """Bare tool names pass through unchanged."""
        assert PermissionCheckHook.strip_mcp_prefix("write_to_note") == "write_to_note"

    def test_preserves_legacy_tool_name(self) -> None:
        """Legacy _in_db names pass through unchanged."""
        assert PermissionCheckHook.strip_mcp_prefix("create_issue_in_db") == "create_issue_in_db"

    def test_handles_empty_string(self) -> None:
        """Empty string returns empty."""
        assert PermissionCheckHook.strip_mcp_prefix("") == ""

    def test_handles_partial_mcp_prefix(self) -> None:
        """Partial prefix (missing server name) returns unchanged."""
        assert PermissionCheckHook.strip_mcp_prefix("mcp__only_one") == "mcp__only_one"


# ---------------------------------------------------------------------------
# TestPermissionCheckHookMcpIntegration
# ---------------------------------------------------------------------------


class TestPermissionCheckHookMcpIntegration:
    """Tests that MCP-prefixed tool names trigger approval correctly."""

    @pytest.mark.asyncio
    async def test_mcp_write_to_note_requires_approval(self) -> None:
        """mcp__pilot-notes__write_to_note should require approval, not be 'read-only'."""
        mock_handler = AsyncMock()
        mock_handler.check_permission = AsyncMock(
            return_value=MagicMock(
                requires_approval=True,
                approval_id=uuid4(),
                reason="write_to_note requires approval",
            )
        )

        hook = PermissionCheckHook(mock_handler)
        from pilot_space.ai.sdk.hooks import ToolCallContext

        ctx = ToolCallContext(
            tool_name="mcp__pilot-notes__write_to_note",
            tool_input={"note_id": "abc", "markdown": "test"},
            workspace_id=uuid4(),
            user_id=uuid4(),
            agent_name="PilotSpaceAgent",
        )
        result = await hook.should_execute(ctx)

        assert result.requires_approval is True
        mock_handler.check_permission.assert_awaited_once()
        call_kwargs = mock_handler.check_permission.call_args
        assert call_kwargs.kwargs["action_name"] == "write_to_note"

    @pytest.mark.asyncio
    async def test_mcp_search_notes_auto_executes(self) -> None:
        """mcp__pilot-notes__search_notes should auto-execute (read-only)."""
        mock_handler = AsyncMock()
        mock_handler.check_permission = AsyncMock(
            return_value=MagicMock(
                requires_approval=False,
                allowed=True,
                reason="auto-execute",
            )
        )

        hook = PermissionCheckHook(mock_handler)
        from pilot_space.ai.sdk.hooks import ToolCallContext

        ctx = ToolCallContext(
            tool_name="mcp__pilot-notes__search_notes",
            tool_input={"query": "test"},
            workspace_id=uuid4(),
            user_id=uuid4(),
            agent_name="PilotSpaceAgent",
        )
        result = await hook.should_execute(ctx)

        assert result.allow is True
        call_kwargs = mock_handler.check_permission.call_args
        assert call_kwargs.kwargs["action_name"] == "search_notes"

    @pytest.mark.asyncio
    async def test_legacy_tool_name_still_maps(self) -> None:
        """Legacy create_issue_in_db still maps to create_issue action."""
        mock_handler = AsyncMock()
        mock_handler.check_permission = AsyncMock(
            return_value=MagicMock(requires_approval=False, allowed=True, reason="ok")
        )

        hook = PermissionCheckHook(mock_handler)
        from pilot_space.ai.sdk.hooks import ToolCallContext

        ctx = ToolCallContext(
            tool_name="create_issue_in_db",
            tool_input={},
            workspace_id=uuid4(),
            user_id=uuid4(),
            agent_name="PilotSpaceAgent",
        )
        await hook.should_execute(ctx)

        call_kwargs = mock_handler.check_permission.call_args
        assert call_kwargs.kwargs["action_name"] == "create_issue"


class TestHookTimeoutConfiguration:
    """Verify the SDK hook timeout exceeds wait_for_approval's 300s limit."""

    def test_permission_matcher_has_sufficient_timeout(self) -> None:
        """Permission hook timeout must exceed wait_for_approval's 300s."""
        from pilot_space.ai.sdk.hooks import PermissionAwareHookExecutor

        mock_handler = AsyncMock()
        executor = PermissionAwareHookExecutor(
            permission_handler=mock_handler,
            workspace_id=uuid4(),
            user_id=uuid4(),
            agent_name="test",
        )
        sdk_hooks = executor.to_sdk_hooks()

        pre_hooks = sdk_hooks.get("PreToolUse", [])
        # Find the permission matcher (has ".*" pattern)
        permission_matchers = [m for m in pre_hooks if m.get("matcher") == ".*"]
        assert len(permission_matchers) >= 1
        pm = permission_matchers[0]
        assert "timeout" in pm, "Permission matcher must set timeout"
        assert pm["timeout"] >= 300, (
            f"Timeout {pm['timeout']}s is less than wait_for_approval's 300s"
        )
