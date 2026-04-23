"""Security tests: DD-003 defense-in-depth for workspace hook rules.

Phase 83 -- verify that the HookRuleService enforces:
1. Pattern validation (200-char limit, regex compilation check).
2. 50-rule-per-workspace limit.
3. Allow rules CAN be created for CRITICAL tools (guard is at evaluation,
   not creation -- admins should see what they configured).

And that the WorkspaceHookEvaluator enforces:
4. DD-003 guard: CRITICAL tools cannot be auto-approved even if a
   workspace hook says "allow".
5. Non-critical tools respect allow rules normally.

These are unit-level tests -- no database required. The repository is
mocked to isolate service-layer logic.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pilot_space.ai.sdk.permission_handler import (
    ActionClassification,
    PermissionHandler,
)
from pilot_space.ai.sdk.workspace_hook_evaluator import WorkspaceHookEvaluator
from pilot_space.application.services.hooks.exceptions import (
    HookRuleLimitError,
    InvalidHookPatternError,
)
from pilot_space.application.services.hooks.hook_rule_service import HookRuleService
from pilot_space.domain.hooks.hook_action import HookAction


def _make_service() -> HookRuleService:
    """Create a HookRuleService with mocked Redis (no real connections)."""
    redis_mock = MagicMock()
    redis_mock.is_connected = False  # Disable Redis for unit tests
    return HookRuleService(redis_client=redis_mock)


def _mock_hook_config(
    *,
    workspace_id: uuid.UUID | None = None,
    name: str = "test-rule",
    tool_pattern: str = "delete_*",
    action: str = "deny",
) -> MagicMock:
    """Build a mock WorkspaceHookConfig."""
    mock = MagicMock()
    mock.workspace_id = workspace_id or uuid.uuid4()
    mock.name = name
    mock.tool_pattern = tool_pattern
    mock.action = action
    mock.id = uuid.uuid4()
    mock.event_type = "PreToolUse"
    mock.priority = 100
    mock.is_enabled = True
    return mock


def _make_evaluator(rules: list[dict]) -> WorkspaceHookEvaluator:
    """Create an evaluator with mocked HookRuleService."""
    service = AsyncMock()
    service.get_cached_rules = AsyncMock(return_value=rules)
    return WorkspaceHookEvaluator(
        workspace_id=uuid.uuid4(),
        hook_rule_service=service,
    )


def _make_allow_all_rule() -> dict:
    """Build an allow-all wildcard rule dict."""
    return {
        "id": str(uuid.uuid4()),
        "name": "allow-all",
        "tool_pattern": "*",
        "action": "allow",
        "event_type": "PreToolUse",
        "priority": 1,
    }


class TestHookDD003Guard:
    """DD-003 defense-in-depth: hook rules cannot bypass CRITICAL approval."""

    @pytest.mark.asyncio
    async def test_create_allow_rule_for_critical_tool_succeeds(self) -> None:
        """Admin CAN create an allow rule for a critical tool.

        The DD-003 guard is at evaluation time (Plan 02), not creation
        time. This lets admins see their configuration while maintaining
        the security invariant at runtime.
        """
        service = _make_service()
        workspace_id = uuid.uuid4()
        actor_id = uuid.uuid4()

        mock_repo = AsyncMock()
        mock_repo.count_for_workspace.return_value = 0
        mock_hook = _mock_hook_config(
            workspace_id=workspace_id,
            name="allow-critical",
            tool_pattern="delete_issue",
            action="allow",
        )
        mock_repo.create.return_value = mock_hook

        with patch.object(service, "_repo", return_value=mock_repo):
            result = await service.create(
                workspace_id=workspace_id,
                name="allow-critical",
                tool_pattern="delete_issue",
                action="allow",
                actor_user_id=actor_id,
            )

        assert result.action == "allow"
        assert result.tool_pattern == "delete_issue"
        mock_repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_allow_all_rule_succeeds(self) -> None:
        """Admin CAN create a wildcard allow-all rule.

        Evaluator (Plan 02) overrides to require_approval for CRITICAL tools.
        """
        service = _make_service()
        workspace_id = uuid.uuid4()
        actor_id = uuid.uuid4()

        mock_repo = AsyncMock()
        mock_repo.count_for_workspace.return_value = 0
        mock_hook = _mock_hook_config(
            workspace_id=workspace_id,
            name="allow-all",
            tool_pattern="*",
            action="allow",
        )
        mock_repo.create.return_value = mock_hook

        with patch.object(service, "_repo", return_value=mock_repo):
            result = await service.create(
                workspace_id=workspace_id,
                name="allow-all",
                tool_pattern="*",
                action="allow",
                actor_user_id=actor_id,
            )

        assert result.action == "allow"
        assert result.tool_pattern == "*"


class TestEvaluatorDD003Guard:
    """DD-003 evaluator guard: CRITICAL tools always require approval."""

    @pytest.mark.asyncio
    async def test_evaluator_overrides_allow_for_all_critical_tools(
        self,
    ) -> None:
        """EXHAUSTIVE: every CRITICAL tool must be overridden.

        Iterates ALL tools in ACTION_CLASSIFICATIONS that are
        CRITICAL_REQUIRE_APPROVAL. For each, creates an allow-all
        evaluator and verifies it returns HookAction.REQUIRE_APPROVAL.
        """
        critical_tools = [
            tool_name
            for tool_name, classification in (
                PermissionHandler.ACTION_CLASSIFICATIONS.items()
            )
            if classification == ActionClassification.CRITICAL_REQUIRE_APPROVAL
        ]

        # Verify we actually have critical tools to test
        assert len(critical_tools) > 0, (
            "No CRITICAL_REQUIRE_APPROVAL tools found in "
            "ACTION_CLASSIFICATIONS -- test is vacuous"
        )

        evaluator = _make_evaluator([_make_allow_all_rule()])

        for tool_name in critical_tools:
            result = await evaluator.evaluate(tool_name)
            assert result == HookAction.REQUIRE_APPROVAL, (
                f"DD-003 violation: CRITICAL tool '{tool_name}' was not "
                f"overridden to require_approval (got {result})"
            )

    @pytest.mark.asyncio
    async def test_evaluator_allow_passes_for_auto_execute_tools(
        self,
    ) -> None:
        """Allow rule on AUTO_EXECUTE tool returns ALLOW (no override)."""
        auto_tools = [
            tool_name
            for tool_name, classification in (
                PermissionHandler.ACTION_CLASSIFICATIONS.items()
            )
            if classification == ActionClassification.AUTO_EXECUTE
        ]

        assert len(auto_tools) > 0, (
            "No AUTO_EXECUTE tools found -- test is vacuous"
        )

        evaluator = _make_evaluator([_make_allow_all_rule()])

        # Test a sample of auto-execute tools (first 5)
        for tool_name in auto_tools[:5]:
            result = await evaluator.evaluate(tool_name)
            assert result == HookAction.ALLOW, (
                f"AUTO_EXECUTE tool '{tool_name}' was not allowed "
                f"(got {result})"
            )

    @pytest.mark.asyncio
    async def test_evaluator_deny_overrides_critical_tool(self) -> None:
        """Deny rule on CRITICAL tool returns DENY (deny always wins)."""
        evaluator = _make_evaluator(
            [
                {
                    "id": str(uuid.uuid4()),
                    "name": "deny-critical",
                    "tool_pattern": "delete_issue",
                    "action": "deny",
                    "event_type": "PreToolUse",
                    "priority": 1,
                },
            ],
        )
        result = await evaluator.evaluate("delete_issue")
        assert result == HookAction.DENY

    @pytest.mark.asyncio
    async def test_evaluator_require_approval_on_critical_passes(
        self,
    ) -> None:
        """Require_approval rule on CRITICAL tool returns REQUIRE_APPROVAL."""
        evaluator = _make_evaluator(
            [
                {
                    "id": str(uuid.uuid4()),
                    "name": "approval-critical",
                    "tool_pattern": "delete_issue",
                    "action": "require_approval",
                    "event_type": "PreToolUse",
                    "priority": 1,
                },
            ],
        )
        result = await evaluator.evaluate("delete_issue")
        assert result == HookAction.REQUIRE_APPROVAL


class TestHookPatternValidation:
    """Pattern validation: ReDoS mitigation and regex compilation."""

    @pytest.mark.asyncio
    async def test_service_validates_invalid_regex_pattern(self) -> None:
        """Invalid regex patterns are rejected at creation."""
        service = _make_service()
        workspace_id = uuid.uuid4()
        actor_id = uuid.uuid4()

        mock_repo = AsyncMock()
        mock_repo.count_for_workspace.return_value = 0

        with (
            patch.object(service, "_repo", return_value=mock_repo),
            pytest.raises(InvalidHookPatternError, match="Invalid regex"),
        ):
            await service.create(
                workspace_id=workspace_id,
                name="bad-regex",
                tool_pattern="/(invalid[/",
                action="deny",
                actor_user_id=actor_id,
            )

    @pytest.mark.asyncio
    async def test_service_rejects_pattern_over_200_chars(self) -> None:
        """Patterns longer than 200 chars are rejected (ReDoS mitigation)."""
        service = _make_service()
        workspace_id = uuid.uuid4()
        actor_id = uuid.uuid4()

        long_pattern = "a" * 201

        mock_repo = AsyncMock()
        mock_repo.count_for_workspace.return_value = 0

        with (
            patch.object(service, "_repo", return_value=mock_repo),
            pytest.raises(InvalidHookPatternError, match="200 character limit"),
        ):
            await service.create(
                workspace_id=workspace_id,
                name="long-pattern",
                tool_pattern=long_pattern,
                action="deny",
                actor_user_id=actor_id,
            )

    @pytest.mark.asyncio
    async def test_service_rejects_empty_pattern(self) -> None:
        """Empty patterns are rejected."""
        service = _make_service()
        workspace_id = uuid.uuid4()
        actor_id = uuid.uuid4()

        mock_repo = AsyncMock()
        mock_repo.count_for_workspace.return_value = 0

        with (
            patch.object(service, "_repo", return_value=mock_repo),
            pytest.raises(InvalidHookPatternError, match="must not be empty"),
        ):
            await service.create(
                workspace_id=workspace_id,
                name="empty-pattern",
                tool_pattern="   ",
                action="deny",
                actor_user_id=actor_id,
            )

    @pytest.mark.asyncio
    async def test_valid_glob_pattern_accepted(self) -> None:
        """Standard glob patterns are accepted."""
        service = _make_service()
        workspace_id = uuid.uuid4()
        actor_id = uuid.uuid4()

        mock_repo = AsyncMock()
        mock_repo.count_for_workspace.return_value = 0
        mock_hook = _mock_hook_config(
            workspace_id=workspace_id,
            tool_pattern="delete_*",
        )
        mock_repo.create.return_value = mock_hook

        with patch.object(service, "_repo", return_value=mock_repo):
            result = await service.create(
                workspace_id=workspace_id,
                name="glob-rule",
                tool_pattern="delete_*",
                action="deny",
                actor_user_id=actor_id,
            )

        assert result is not None

    @pytest.mark.asyncio
    async def test_valid_regex_pattern_accepted(self) -> None:
        """Valid regex patterns (wrapped in /) are accepted."""
        service = _make_service()
        workspace_id = uuid.uuid4()
        actor_id = uuid.uuid4()

        mock_repo = AsyncMock()
        mock_repo.count_for_workspace.return_value = 0
        mock_hook = _mock_hook_config(
            workspace_id=workspace_id,
            tool_pattern="/^(delete|remove)_.*/",
        )
        mock_repo.create.return_value = mock_hook

        with patch.object(service, "_repo", return_value=mock_repo):
            result = await service.create(
                workspace_id=workspace_id,
                name="regex-rule",
                tool_pattern="/^(delete|remove)_.*/",
                action="require_approval",
                actor_user_id=actor_id,
            )

        assert result is not None

    @pytest.mark.asyncio
    async def test_pattern_exactly_200_chars_accepted(self) -> None:
        """Pattern at exactly the 200-char boundary is accepted."""
        service = _make_service()
        workspace_id = uuid.uuid4()
        actor_id = uuid.uuid4()

        pattern_200 = "a" * 200

        mock_repo = AsyncMock()
        mock_repo.count_for_workspace.return_value = 0
        mock_hook = _mock_hook_config(
            workspace_id=workspace_id,
            tool_pattern=pattern_200,
        )
        mock_repo.create.return_value = mock_hook

        with patch.object(service, "_repo", return_value=mock_repo):
            result = await service.create(
                workspace_id=workspace_id,
                name="boundary-rule",
                tool_pattern=pattern_200,
                action="deny",
                actor_user_id=actor_id,
            )

        assert result is not None


class TestHookRuleLimits:
    """Rule count limits: max 50 per workspace."""

    @pytest.mark.asyncio
    async def test_service_enforces_max_50_rules(self) -> None:
        """Cannot create more than 50 rules per workspace."""
        service = _make_service()
        workspace_id = uuid.uuid4()
        actor_id = uuid.uuid4()

        mock_repo = AsyncMock()
        mock_repo.count_for_workspace.return_value = 50  # At limit

        with (
            patch.object(service, "_repo", return_value=mock_repo),
            pytest.raises(HookRuleLimitError, match="maximum of 50"),
        ):
            await service.create(
                workspace_id=workspace_id,
                name="one-too-many",
                tool_pattern="some_tool",
                action="deny",
                actor_user_id=actor_id,
            )

    @pytest.mark.asyncio
    async def test_service_allows_at_49_rules(self) -> None:
        """Can create a rule when workspace has 49 (under limit)."""
        service = _make_service()
        workspace_id = uuid.uuid4()
        actor_id = uuid.uuid4()

        mock_repo = AsyncMock()
        mock_repo.count_for_workspace.return_value = 49
        mock_hook = _mock_hook_config(workspace_id=workspace_id)
        mock_repo.create.return_value = mock_hook

        with patch.object(service, "_repo", return_value=mock_repo):
            result = await service.create(
                workspace_id=workspace_id,
                name="rule-49",
                tool_pattern="some_tool",
                action="deny",
                actor_user_id=actor_id,
            )

        assert result is not None
        mock_repo.create.assert_called_once()
