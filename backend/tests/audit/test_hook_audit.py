"""Audit trail tests for workspace hook evaluations.

Phase 83 -- verifies that every hook evaluation writes an audit_log row
with hook_name, tool_name, decision, and latency_ms. Also verifies that
audit failures are non-fatal and that missing session_factory is handled.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pilot_space.ai.sdk.workspace_hook_evaluator import WorkspaceHookEvaluator
from pilot_space.domain.hooks.hook_action import HookAction


def _make_rule(
    *,
    name: str = "test-rule",
    tool_pattern: str = "ghost_text",
    action: str = "allow",
    priority: int = 100,
) -> dict:
    """Build a rule dict matching HookRuleService.get_cached_rules() shape."""
    return {
        "id": str(uuid.uuid4()),
        "name": name,
        "tool_pattern": tool_pattern,
        "action": action,
        "event_type": "PreToolUse",
        "priority": priority,
    }


class _FakeAsyncSession:
    """Fake async session that works with ``async with factory() as session``."""

    def __init__(self) -> None:
        self.commit = AsyncMock()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


def _make_mock_session_factory_and_repo() -> (
    tuple[MagicMock, _FakeAsyncSession, AsyncMock]
):
    """Create a mock session factory and capture AuditLogRepository.create call.

    Returns:
        Tuple of (session_factory, mock_session, mock_repo).
    """
    mock_repo = AsyncMock()
    mock_repo.create = AsyncMock()

    mock_session = _FakeAsyncSession()

    # session_factory() must return an async context manager (not a coroutine)
    session_factory = MagicMock()
    session_factory.return_value = mock_session

    return session_factory, mock_session, mock_repo


class TestHookAudit:
    """Audit trail for hook evaluations."""

    @pytest.mark.asyncio
    async def test_evaluation_creates_audit_entry(self) -> None:
        """Matching rule evaluation writes audit_log row.

        Verifies that repo.create() is called with:
        - action="hook.evaluation"
        - resource_type="ai_hook"
        - payload containing hook_name, tool_name, decision, latency_ms
        """
        session_factory, mock_session, mock_repo = (
            _make_mock_session_factory_and_repo()
        )

        hook_service = AsyncMock()
        hook_service.get_cached_rules = AsyncMock(
            return_value=[
                _make_rule(
                    name="allow-ghost",
                    tool_pattern="ghost_text",
                    action="allow",
                ),
            ],
        )

        evaluator = WorkspaceHookEvaluator(
            workspace_id=uuid.uuid4(),
            session_factory=session_factory,
            hook_rule_service=hook_service,
        )

        # Patch AuditLogRepository at the import target inside _log_evaluation
        with patch(
            "pilot_space.infrastructure.database.repositories"
            ".audit_log_repository.AuditLogRepository",
            return_value=mock_repo,
        ):
            result = await evaluator.evaluate("ghost_text")

        assert result == HookAction.ALLOW

        # Verify audit repo was called
        mock_repo.create.assert_called_once()
        call_kwargs = mock_repo.create.call_args.kwargs

        assert call_kwargs["action"] == "hook.evaluation"
        assert call_kwargs["resource_type"] == "ai_hook"

        payload = call_kwargs["payload"]
        assert payload["hook_name"] == "allow-ghost"
        assert payload["tool_name"] == "ghost_text"
        assert payload["decision"] == "allow"
        assert "latency_ms" in payload
        assert isinstance(payload["latency_ms"], float)

    @pytest.mark.asyncio
    async def test_audit_failure_is_non_fatal(self) -> None:
        """Audit write failure does not crash the evaluator.

        Mock repo.create() to raise Exception. Verify the evaluation
        still returns the correct result and no exception propagates.
        """
        session_factory, mock_session, mock_repo = (
            _make_mock_session_factory_and_repo()
        )
        mock_repo.create = AsyncMock(
            side_effect=RuntimeError("DB connection lost"),
        )

        hook_service = AsyncMock()
        hook_service.get_cached_rules = AsyncMock(
            return_value=[
                _make_rule(
                    name="deny-tool",
                    tool_pattern="ghost_text",
                    action="deny",
                ),
            ],
        )

        evaluator = WorkspaceHookEvaluator(
            workspace_id=uuid.uuid4(),
            session_factory=session_factory,
            hook_rule_service=hook_service,
        )

        with patch(
            "pilot_space.infrastructure.database.repositories"
            ".audit_log_repository.AuditLogRepository",
            return_value=mock_repo,
        ):
            # Should NOT raise despite audit failure
            result = await evaluator.evaluate("ghost_text")

        assert result == HookAction.DENY

    @pytest.mark.asyncio
    async def test_no_audit_when_no_session_factory(self) -> None:
        """Evaluator with session_factory=None skips audit (no crash).

        Creates evaluator without session_factory. Evaluation should
        succeed with no audit row written and no exception.
        """
        hook_service = AsyncMock()
        hook_service.get_cached_rules = AsyncMock(
            return_value=[
                _make_rule(
                    name="allow-tool",
                    tool_pattern="ghost_text",
                    action="allow",
                ),
            ],
        )

        evaluator = WorkspaceHookEvaluator(
            workspace_id=uuid.uuid4(),
            session_factory=None,  # No session factory
            hook_rule_service=hook_service,
        )

        # Should NOT raise
        result = await evaluator.evaluate("ghost_text")
        assert result == HookAction.ALLOW

    @pytest.mark.asyncio
    async def test_audit_captures_dd003_override(self) -> None:
        """DD-003 override is logged with decision=require_approval.

        When the evaluator overrides an allow->require_approval for a
        CRITICAL tool, the audit payload should reflect the final
        decision (require_approval), not the configured action (allow).
        """
        session_factory, mock_session, mock_repo = (
            _make_mock_session_factory_and_repo()
        )

        hook_service = AsyncMock()
        hook_service.get_cached_rules = AsyncMock(
            return_value=[
                _make_rule(
                    name="allow-all",
                    tool_pattern="*",
                    action="allow",
                ),
            ],
        )

        evaluator = WorkspaceHookEvaluator(
            workspace_id=uuid.uuid4(),
            session_factory=session_factory,
            hook_rule_service=hook_service,
        )

        with patch(
            "pilot_space.infrastructure.database.repositories"
            ".audit_log_repository.AuditLogRepository",
            return_value=mock_repo,
        ):
            result = await evaluator.evaluate("delete_issue")

        assert result == HookAction.REQUIRE_APPROVAL

        # Verify the audit captured the overridden decision
        mock_repo.create.assert_called_once()
        payload = mock_repo.create.call_args.kwargs["payload"]
        assert payload["decision"] == "require_approval"
        assert payload["hook_name"] == "allow-all"
        assert payload["tool_name"] == "delete_issue"

    @pytest.mark.asyncio
    async def test_no_audit_when_no_match(self) -> None:
        """No audit row is written when no rule matches."""
        session_factory, mock_session, mock_repo = (
            _make_mock_session_factory_and_repo()
        )

        hook_service = AsyncMock()
        hook_service.get_cached_rules = AsyncMock(
            return_value=[
                _make_rule(
                    name="other-tool",
                    tool_pattern="other_tool",
                    action="deny",
                ),
            ],
        )

        evaluator = WorkspaceHookEvaluator(
            workspace_id=uuid.uuid4(),
            session_factory=session_factory,
            hook_rule_service=hook_service,
        )

        with patch(
            "pilot_space.infrastructure.database.repositories"
            ".audit_log_repository.AuditLogRepository",
            return_value=mock_repo,
        ):
            result = await evaluator.evaluate("ghost_text")

        assert result is None
        mock_repo.create.assert_not_called()
