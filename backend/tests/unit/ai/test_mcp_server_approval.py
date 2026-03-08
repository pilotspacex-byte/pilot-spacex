"""Unit tests for check_approval_from_db() and ToolContext.user_role.

Tests verify:
1. Fallback to TOOL_APPROVAL_MAP when no tool_context (or no action_type)
2. DB policy requires_approval=True -> REQUIRE_APPROVAL
3. DB policy requires_approval=False -> AUTO_EXECUTE
4. OWNER role -> AUTO_EXECUTE regardless of DB policy
5. ToolContext accepts user_role without breaking existing callers

All external dependencies (ApprovalService, DB) are fully mocked.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pilot_space.ai.tools.mcp_server import (
    ToolApprovalLevel,
    ToolContext,
    check_approval_from_db,
    get_tool_approval_level,
)
from pilot_space.infrastructure.database.models.workspace_member import WorkspaceRole

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_WORKSPACE_ID = str(uuid.uuid4())


def _make_context(role: WorkspaceRole | None = None) -> ToolContext:
    """Build a minimal ToolContext with a fake async session."""
    return ToolContext(
        db_session=AsyncMock(),
        workspace_id=_WORKSPACE_ID,
        user_id=str(uuid.uuid4()),
        user_role=role,
    )


def _make_mock_approval_svc(requires: bool, always_require_set: set | None = None) -> MagicMock:
    """Build a mock ApprovalService instance."""
    mock_svc = MagicMock()
    mock_svc.check_approval_required = AsyncMock(return_value=requires)
    mock_svc.ALWAYS_REQUIRE_ACTIONS = always_require_set or set()
    return mock_svc


# ---------------------------------------------------------------------------
# Test 5: ToolContext.user_role field backward compat
# ---------------------------------------------------------------------------


class TestToolContextUserRoleField:
    """Test 5: ToolContext.user_role field is optional and defaults to None."""

    def test_user_role_defaults_to_none(self) -> None:
        ctx = ToolContext(
            db_session=AsyncMock(),
            workspace_id=_WORKSPACE_ID,
        )
        assert ctx.user_role is None

    def test_user_role_accepts_workspace_role(self) -> None:
        for role in WorkspaceRole:
            ctx = ToolContext(
                db_session=AsyncMock(),
                workspace_id=_WORKSPACE_ID,
                user_role=role,
            )
            assert ctx.user_role == role

    def test_user_id_still_optional(self) -> None:
        ctx = ToolContext(
            db_session=AsyncMock(),
            workspace_id=_WORKSPACE_ID,
        )
        assert ctx.user_id is None

    def test_extra_still_defaults_to_empty_dict(self) -> None:
        ctx = ToolContext(
            db_session=AsyncMock(),
            workspace_id=_WORKSPACE_ID,
        )
        assert ctx.extra == {}


# ---------------------------------------------------------------------------
# Test 1: Fallback when tool_context or action_type is None
# ---------------------------------------------------------------------------


class TestCheckApprovalFromDbFallback:
    """Test 1: Falls back to TOOL_APPROVAL_MAP when tool_context is None."""

    @pytest.mark.asyncio
    async def test_no_tool_context_returns_static_map_value(self) -> None:
        """When tool_context is None, return get_tool_approval_level() result."""
        result = await check_approval_from_db("create_issue", None, None)
        expected = get_tool_approval_level("create_issue")
        assert result == expected

    @pytest.mark.asyncio
    async def test_none_action_type_with_context_returns_static_map_value(self) -> None:
        """When action_type is None, fall back regardless of tool_context."""
        ctx = _make_context()
        result = await check_approval_from_db("create_issue", None, ctx)
        expected = get_tool_approval_level("create_issue")
        assert result == expected

    @pytest.mark.asyncio
    async def test_auto_execute_tool_falls_back_correctly(self) -> None:
        """enhance_text is AUTO_EXECUTE in the static map — fallback should respect that."""
        result = await check_approval_from_db("enhance_text", None, None)
        assert result == ToolApprovalLevel.AUTO_EXECUTE


# ---------------------------------------------------------------------------
# Test 2: DB policy requires_approval=True -> REQUIRE_APPROVAL
# ---------------------------------------------------------------------------


class TestCheckApprovalFromDbPolicyRequiresApproval:
    """Test 2: DB policy requires_approval=True -> REQUIRE_APPROVAL."""

    @pytest.mark.asyncio
    async def test_db_policy_true_returns_require_approval(self) -> None:
        from pilot_space.ai.infrastructure.approval import ActionType

        ctx = _make_context(role=WorkspaceRole.MEMBER)
        mock_svc = _make_mock_approval_svc(requires=True, always_require_set=set())

        with (
            patch(
                "pilot_space.ai.infrastructure.approval.ApprovalService",
                return_value=mock_svc,
            ),
            patch(
                "pilot_space.infrastructure.database.repositories.workspace_ai_policy_repository.WorkspaceAIPolicyRepository"
            ),
        ):
            result = await check_approval_from_db("create_issue", ActionType.CREATE_ISSUE, ctx)

        assert result == ToolApprovalLevel.REQUIRE_APPROVAL


# ---------------------------------------------------------------------------
# Test 3: DB policy requires_approval=False -> AUTO_EXECUTE
# ---------------------------------------------------------------------------


class TestCheckApprovalFromDbPolicyAutoExecute:
    """Test 3: DB policy requires_approval=False -> AUTO_EXECUTE."""

    @pytest.mark.asyncio
    async def test_db_policy_false_returns_auto_execute(self) -> None:
        from pilot_space.ai.infrastructure.approval import ActionType

        ctx = _make_context(role=WorkspaceRole.MEMBER)
        mock_svc = _make_mock_approval_svc(requires=False)

        with (
            patch(
                "pilot_space.ai.infrastructure.approval.ApprovalService",
                return_value=mock_svc,
            ),
            patch(
                "pilot_space.infrastructure.database.repositories.workspace_ai_policy_repository.WorkspaceAIPolicyRepository"
            ),
        ):
            result = await check_approval_from_db("create_issue", ActionType.CREATE_ISSUE, ctx)

        assert result == ToolApprovalLevel.AUTO_EXECUTE


# ---------------------------------------------------------------------------
# Test 4: OWNER role -> AUTO_EXECUTE regardless of DB policy
# ---------------------------------------------------------------------------


class TestCheckApprovalFromDbOwnerRole:
    """Test 4: OWNER role -> AUTO_EXECUTE regardless of DB policy."""

    @pytest.mark.asyncio
    async def test_owner_returns_auto_execute(self) -> None:
        """ApprovalService returns False for OWNER (hardcoded trust root)."""
        from pilot_space.ai.infrastructure.approval import ActionType

        ctx = _make_context(role=WorkspaceRole.OWNER)
        # ApprovalService.check_approval_required returns False for OWNER per its own logic
        mock_svc = _make_mock_approval_svc(requires=False)

        with (
            patch(
                "pilot_space.ai.infrastructure.approval.ApprovalService",
                return_value=mock_svc,
            ),
            patch(
                "pilot_space.infrastructure.database.repositories.workspace_ai_policy_repository.WorkspaceAIPolicyRepository"
            ),
        ):
            result = await check_approval_from_db("create_issue", ActionType.CREATE_ISSUE, ctx)

        assert result == ToolApprovalLevel.AUTO_EXECUTE

    @pytest.mark.asyncio
    async def test_always_require_action_returns_always_require(self) -> None:
        """ALWAYS_REQUIRE actions return ALWAYS_REQUIRE even when requires=True."""
        from pilot_space.ai.infrastructure.approval import ActionType

        ctx = _make_context(role=WorkspaceRole.OWNER)
        mock_svc = _make_mock_approval_svc(
            requires=True,
            always_require_set={ActionType.DELETE_WORKSPACE},
        )

        with (
            patch(
                "pilot_space.ai.infrastructure.approval.ApprovalService",
                return_value=mock_svc,
            ),
            patch(
                "pilot_space.infrastructure.database.repositories.workspace_ai_policy_repository.WorkspaceAIPolicyRepository"
            ),
        ):
            result = await check_approval_from_db(
                "delete_workspace", ActionType.DELETE_WORKSPACE, ctx
            )

        assert result == ToolApprovalLevel.ALWAYS_REQUIRE


# ---------------------------------------------------------------------------
# Exception fallback: any exception -> static map
# ---------------------------------------------------------------------------


class TestCheckApprovalFromDbExceptionFallback:
    """Verifies graceful fallback on any exception during DB lookup."""

    @pytest.mark.asyncio
    async def test_exception_falls_back_to_static_map(self) -> None:
        from pilot_space.ai.infrastructure.approval import ActionType

        ctx = _make_context(role=WorkspaceRole.MEMBER)
        mock_svc = MagicMock()
        mock_svc.check_approval_required = AsyncMock(
            side_effect=RuntimeError("DB connection failed")
        )

        with (
            patch(
                "pilot_space.ai.infrastructure.approval.ApprovalService",
                return_value=mock_svc,
            ),
            patch(
                "pilot_space.infrastructure.database.repositories.workspace_ai_policy_repository.WorkspaceAIPolicyRepository"
            ),
        ):
            result = await check_approval_from_db("create_issue", ActionType.CREATE_ISSUE, ctx)

        # Should fall back to static TOOL_APPROVAL_MAP value
        expected = get_tool_approval_level("create_issue")
        assert result == expected
