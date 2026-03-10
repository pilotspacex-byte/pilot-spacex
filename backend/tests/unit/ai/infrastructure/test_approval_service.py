"""Tests for ApprovalService Phase 4 enhancements.

Phase 4 — AI Governance (AIGOV-01):
ApprovalService.check_approval_required() must accept user_role and
query workspace_ai_policy rows to override hardcoded thresholds.

Implemented in plan 04-02 (ApprovalService enhancements).
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from pilot_space.ai.infrastructure.approval import (
    ActionType,
    ApprovalLevel,
    ApprovalService,
    ProjectSettings,
)
from pilot_space.infrastructure.database.models.workspace_member import WorkspaceRole

pytestmark = pytest.mark.asyncio


def _make_service(policy_row=None, policy_raises=False):
    """Build an ApprovalService with a mock session and mock policy repo."""
    session = MagicMock()

    policy_repo = MagicMock()
    if policy_raises:
        policy_repo.get = AsyncMock(side_effect=RuntimeError("db failure"))
    else:
        policy_repo.get = AsyncMock(return_value=policy_row)

    service = ApprovalService(session)
    service._policy_repo = policy_repo
    return service


def _make_policy_row(requires_approval: bool):
    """Create a minimal fake policy row."""
    row = MagicMock()
    row.requires_approval = requires_approval
    return row


async def test_check_approval_required_uses_db_policy_when_row_exists() -> None:
    """DB policy row for (workspace_id, role, action_type) overrides hardcoded level.

    When workspace_ai_policy has a row for (workspace_id, 'MEMBER', 'extract_issues')
    with requires_approval=False, check_approval_required() must return False
    even if the hardcoded ApprovalLevel would require approval.
    """
    workspace_id = uuid.uuid4()
    # Policy row says False (auto-execute) for this MEMBER+action
    service = _make_service(policy_row=_make_policy_row(requires_approval=False))

    result = await service.check_approval_required(
        action_type=ActionType.EXTRACT_ISSUES,
        workspace_id=workspace_id,
        user_role=WorkspaceRole.MEMBER,
        project_settings=ProjectSettings(level=ApprovalLevel.BALANCED),
    )

    assert result is False
    service._policy_repo.get.assert_awaited_once()


async def test_check_approval_required_owner_always_auto_execute() -> None:
    """Owner role returns False (auto-execute) even for DEFAULT_REQUIRE actions.

    OWNER role has implicit auto-execute for non-ALWAYS_REQUIRE actions,
    regardless of workspace_ai_policy rows.
    """
    workspace_id = uuid.uuid4()
    service = _make_service()  # policy repo should never be consulted

    result = await service.check_approval_required(
        action_type=ActionType.EXTRACT_ISSUES,
        workspace_id=workspace_id,
        user_role=WorkspaceRole.OWNER,
    )

    assert result is False
    # Policy repo should NOT be queried for OWNER role
    service._policy_repo.get.assert_not_awaited()


async def test_check_approval_required_always_require_ignores_policy() -> None:
    """DELETE_* and MERGE_PR always return True regardless of workspace_ai_policy row.

    Even if workspace_ai_policy sets requires_approval=False for
    'delete_issue', the hardcoded ALWAYS_REQUIRE guard must override it.
    """
    workspace_id = uuid.uuid4()
    # Policy says auto-execute, but ALWAYS_REQUIRE must win
    service = _make_service(policy_row=_make_policy_row(requires_approval=False))

    result = await service.check_approval_required(
        action_type=ActionType.DELETE_ISSUE,
        workspace_id=workspace_id,
        user_role=WorkspaceRole.ADMIN,
    )

    assert result is True
    # Policy repo should NOT be queried for ALWAYS_REQUIRE actions
    service._policy_repo.get.assert_not_awaited()


async def test_check_approval_required_falls_back_to_level_when_no_row() -> None:
    """When workspace_ai_policy has no row for (workspace, role, action), use existing level logic.

    Absence of a policy row means fall back to the hardcoded ApprovalLevel
    threshold defaults (DD-003), preserving backward compatibility.
    """
    workspace_id = uuid.uuid4()
    service = _make_service(policy_row=None)  # no DB row

    # BALANCED level + DEFAULT_REQUIRE action → should require approval
    result_balanced = await service.check_approval_required(
        action_type=ActionType.EXTRACT_ISSUES,
        workspace_id=workspace_id,
        user_role=WorkspaceRole.MEMBER,
        project_settings=ProjectSettings(level=ApprovalLevel.BALANCED),
    )
    assert result_balanced is True

    # AUTONOMOUS level + DEFAULT_REQUIRE action → auto-execute
    result_auto = await service.check_approval_required(
        action_type=ActionType.EXTRACT_ISSUES,
        workspace_id=workspace_id,
        user_role=WorkspaceRole.MEMBER,
        project_settings=ProjectSettings(level=ApprovalLevel.AUTONOMOUS),
    )
    assert result_auto is False
