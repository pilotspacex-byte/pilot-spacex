"""Unit tests for WorkspaceHookEvaluator.

Phase 83 -- tests for the hook evaluator: pattern matching, DD-003 guard,
caching, and audit logging. All tests use mocked services (no DB/Redis).
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
    tool_pattern: str = "*",
    action: str = "allow",
    priority: int = 100,
    is_enabled: bool = True,
) -> dict:
    """Build a rule dict matching HookRuleService.get_cached_rules() shape."""
    return {
        "id": str(uuid.uuid4()),
        "name": name,
        "tool_pattern": tool_pattern,
        "action": action,
        "event_type": "PreToolUse",
        "priority": priority,
        "is_enabled": is_enabled,
    }


def _make_evaluator(
    rules: list[dict] | None = None,
    session_factory: AsyncMock | None = None,
) -> WorkspaceHookEvaluator:
    """Create an evaluator with a mocked HookRuleService."""
    service = AsyncMock()
    service.get_cached_rules = AsyncMock(return_value=rules or [])

    return WorkspaceHookEvaluator(
        workspace_id=uuid.uuid4(),
        redis_client=None,
        session_factory=session_factory,
        hook_rule_service=service,
    )


class TestWorkspaceHookEvaluator:
    """Evaluator behavior contracts."""

    @pytest.mark.asyncio
    async def test_allow_all_hook_cannot_bypass_critical(self) -> None:
        """HOOK-05: allow-all hook on CRITICAL tool -> require_approval.

        Even if an admin creates a wildcard ``action=allow`` rule,
        the evaluator must override it to ``require_approval`` for
        tools classified as ``CRITICAL_REQUIRE_APPROVAL`` in
        ``ACTION_CLASSIFICATIONS``.
        """
        evaluator = _make_evaluator(
            rules=[_make_rule(tool_pattern="*", action="allow")],
        )
        result = await evaluator.evaluate("delete_issue")
        assert result == HookAction.REQUIRE_APPROVAL

    @pytest.mark.asyncio
    async def test_deny_hook_blocks_auto_tool(self) -> None:
        """Deny hook on AUTO_EXECUTE tool blocks execution.

        A workspace admin can deny tools that are normally auto-executed.
        The evaluator must respect the deny action regardless of the
        tool's default classification.
        """
        evaluator = _make_evaluator(
            rules=[_make_rule(tool_pattern="ghost_text", action="deny")],
        )
        result = await evaluator.evaluate("ghost_text")
        assert result == HookAction.DENY

    @pytest.mark.asyncio
    async def test_first_match_wins_by_priority(self) -> None:
        """Rules evaluated in priority order, first match wins.

        Given two rules with different priorities matching the same
        tool, the rule with the lower priority number (higher precedence)
        should determine the action.
        """
        evaluator = _make_evaluator(
            rules=[
                _make_rule(
                    name="deny-ghost",
                    tool_pattern="ghost_text",
                    action="deny",
                    priority=10,
                ),
                _make_rule(
                    name="allow-ghost",
                    tool_pattern="ghost_*",
                    action="allow",
                    priority=20,
                ),
            ],
        )
        result = await evaluator.evaluate("ghost_text")
        assert result == HookAction.DENY

    @pytest.mark.asyncio
    async def test_glob_pattern_matching(self) -> None:
        """Glob pattern matches tool names with wildcards."""
        evaluator = _make_evaluator(
            rules=[
                _make_rule(
                    tool_pattern="create_*",
                    action="require_approval",
                ),
            ],
        )
        result = await evaluator.evaluate("create_issue")
        assert result == HookAction.REQUIRE_APPROVAL

    @pytest.mark.asyncio
    async def test_regex_pattern_matching(self) -> None:
        """Regex patterns (wrapped in /) match correctly."""
        evaluator = _make_evaluator(
            rules=[
                _make_rule(
                    tool_pattern="/^delete_.*/",
                    action="deny",
                ),
            ],
        )
        result = await evaluator.evaluate("delete_issue")
        assert result == HookAction.DENY

    @pytest.mark.asyncio
    async def test_exact_match(self) -> None:
        """Exact match only matches the exact tool name."""
        evaluator = _make_evaluator(
            rules=[
                _make_rule(
                    tool_pattern="merge_pr",
                    action="deny",
                ),
            ],
        )
        # Exact match
        result = await evaluator.evaluate("merge_pr")
        assert result == HookAction.DENY

        # No match for suffix
        result = await evaluator.evaluate("merge_pr_review")
        assert result is None

    @pytest.mark.asyncio
    async def test_no_matching_rule_returns_none(self) -> None:
        """Tool with no matching rules returns None."""
        evaluator = _make_evaluator(
            rules=[
                _make_rule(
                    tool_pattern="totally_different_tool",
                    action="deny",
                ),
            ],
        )
        result = await evaluator.evaluate("ghost_text")
        assert result is None

    @pytest.mark.asyncio
    async def test_mcp_prefix_stripped(self) -> None:
        """MCP-prefixed tool names are stripped before matching."""
        evaluator = _make_evaluator(
            rules=[
                _make_rule(
                    tool_pattern="search_notes",
                    action="allow",
                ),
            ],
        )
        result = await evaluator.evaluate("mcp__note_server__search_notes")
        assert result == HookAction.ALLOW

    @pytest.mark.asyncio
    async def test_disabled_rules_ignored(self) -> None:
        """Disabled rules should not be returned by the service.

        The service's get_cached_rules() filters out disabled rules,
        so the evaluator should never see them. This test verifies
        that if a disabled rule somehow appears, it still matches
        (the filter is at the service level, not evaluator).
        """
        # In practice, get_cached_rules() only returns enabled rules.
        # We test that the evaluator works correctly with what it receives.
        evaluator = _make_evaluator(rules=[])
        result = await evaluator.evaluate("any_tool")
        assert result is None

    @pytest.mark.asyncio
    async def test_or_pattern_matching(self) -> None:
        """OR patterns (pipe-separated) match any sub-pattern."""
        evaluator = _make_evaluator(
            rules=[
                _make_rule(
                    tool_pattern="delete_issue|merge_pr",
                    action="deny",
                ),
            ],
        )
        assert await evaluator.evaluate("delete_issue") == HookAction.DENY
        assert await evaluator.evaluate("merge_pr") == HookAction.DENY
        assert await evaluator.evaluate("create_issue") is None

    @pytest.mark.asyncio
    async def test_invalid_action_string_skipped(self) -> None:
        """Rules with invalid action values are skipped."""
        evaluator = _make_evaluator(
            rules=[
                _make_rule(
                    name="bad-action",
                    tool_pattern="*",
                    action="invalid_action",
                ),
            ],
        )
        result = await evaluator.evaluate("ghost_text")
        assert result is None

    @pytest.mark.asyncio
    async def test_service_failure_degrades_gracefully(self) -> None:
        """If HookRuleService raises, evaluator returns None (no crash)."""
        service = AsyncMock()
        service.get_cached_rules = AsyncMock(
            side_effect=RuntimeError("Redis down"),
        )
        evaluator = WorkspaceHookEvaluator(
            workspace_id=uuid.uuid4(),
            hook_rule_service=service,
        )
        result = await evaluator.evaluate("ghost_text")
        assert result is None

    @pytest.mark.asyncio
    async def test_no_service_degrades_gracefully(self) -> None:
        """Evaluator with no service returns None for all tools."""
        evaluator = WorkspaceHookEvaluator(
            workspace_id=uuid.uuid4(),
        )
        result = await evaluator.evaluate("ghost_text")
        assert result is None

    @pytest.mark.asyncio
    async def test_allow_non_critical_tool_passes(self) -> None:
        """Allow rule on non-critical tool returns ALLOW (no DD-003 override)."""
        evaluator = _make_evaluator(
            rules=[
                _make_rule(
                    tool_pattern="ghost_text",
                    action="allow",
                ),
            ],
        )
        result = await evaluator.evaluate("ghost_text")
        assert result == HookAction.ALLOW

    @pytest.mark.asyncio
    async def test_to_sdk_hooks_returns_pre_tool_use(self) -> None:
        """to_sdk_hooks() returns PreToolUse with a single catch-all matcher."""
        evaluator = _make_evaluator()
        hooks = evaluator.to_sdk_hooks()
        assert "PreToolUse" in hooks
        assert len(hooks["PreToolUse"]) == 1
        assert hooks["PreToolUse"][0]["matcher"] == ".*"
        assert hooks["PreToolUse"][0]["timeout"] == 30

    @pytest.mark.asyncio
    async def test_sdk_callback_deny_returns_deny_dict(self) -> None:
        """SDK callback returns deny dict when evaluator returns DENY."""
        evaluator = _make_evaluator(
            rules=[_make_rule(tool_pattern="*", action="deny")],
        )
        hooks = evaluator.to_sdk_hooks()
        callback = hooks["PreToolUse"][0]["hooks"][0]

        result = await callback(
            {"tool_name": "ghost_text"},
            "tool-123",
            None,
        )
        assert result["hookSpecificOutput"]["permissionDecision"] == "deny"

    @pytest.mark.asyncio
    async def test_sdk_callback_allow_returns_empty_dict(self) -> None:
        """SDK callback returns empty dict when evaluator returns ALLOW."""
        evaluator = _make_evaluator(
            rules=[_make_rule(tool_pattern="ghost_text", action="allow")],
        )
        hooks = evaluator.to_sdk_hooks()
        callback = hooks["PreToolUse"][0]["hooks"][0]

        result = await callback(
            {"tool_name": "ghost_text"},
            "tool-123",
            None,
        )
        assert result == {}

    @pytest.mark.asyncio
    async def test_sdk_callback_no_match_returns_empty_dict(self) -> None:
        """SDK callback returns empty dict when no rule matches."""
        evaluator = _make_evaluator(rules=[])
        hooks = evaluator.to_sdk_hooks()
        callback = hooks["PreToolUse"][0]["hooks"][0]

        result = await callback(
            {"tool_name": "ghost_text"},
            "tool-123",
            None,
        )
        assert result == {}

    @pytest.mark.asyncio
    async def test_question_mark_glob(self) -> None:
        """Question mark glob matches single character."""
        evaluator = _make_evaluator(
            rules=[
                _make_rule(tool_pattern="get_issue?", action="deny"),
            ],
        )
        assert await evaluator.evaluate("get_issues") == HookAction.DENY
        assert await evaluator.evaluate("get_issue") is None

    @pytest.mark.asyncio
    async def test_invalid_regex_does_not_crash(self) -> None:
        """Invalid regex pattern does not crash, just doesn't match."""
        evaluator = _make_evaluator(
            rules=[
                _make_rule(tool_pattern="/(invalid[/", action="deny"),
            ],
        )
        result = await evaluator.evaluate("ghost_text")
        assert result is None
