"""xfail test stubs for ApprovalService Phase 4 enhancements.

Phase 4 — AI Governance (AIGOV-01):
ApprovalService.check_approval_required() must accept user_role and
query workspace_ai_policy rows to override hardcoded thresholds.

Implemented in plan 04-02 (ApprovalService enhancements).
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.asyncio


@pytest.mark.xfail(
    strict=False,
    reason="Phase 4 AIGOV-01: ApprovalService.check_approval_required() async + user_role — implemented in 04-02",
)
async def test_check_approval_required_uses_db_policy_when_row_exists() -> None:
    """DB policy row for (workspace_id, role, action_type) overrides hardcoded level.

    When workspace_ai_policy has a row for (workspace_id, 'MEMBER', 'create_issues')
    with requires_approval=False, check_approval_required() must return False
    even if the hardcoded ApprovalLevel would require approval.
    """


@pytest.mark.xfail(
    strict=False,
    reason="Phase 4 AIGOV-01: Owner always auto-execute for DEFAULT_REQUIRE — implemented in 04-02",
)
async def test_check_approval_required_owner_always_auto_execute() -> None:
    """Owner role returns False (auto-execute) even for DEFAULT_REQUIRE actions.

    OWNER role has implicit auto-execute for non-ALWAYS_REQUIRE actions,
    regardless of workspace_ai_policy rows.
    """


@pytest.mark.xfail(
    strict=False,
    reason="Phase 4 AIGOV-01: ALWAYS_REQUIRE hardcoded regardless of policy — implemented in 04-02",
)
async def test_check_approval_required_always_require_ignores_policy() -> None:
    """DELETE_* and MERGE_PR always return True regardless of workspace_ai_policy row.

    Even if workspace_ai_policy sets requires_approval=False for
    'delete_issue', the hardcoded ALWAYS_REQUIRE guard must override it.
    """


@pytest.mark.xfail(
    strict=False,
    reason="Phase 4 AIGOV-01: falls back to level when no policy row — implemented in 04-02",
)
async def test_check_approval_required_falls_back_to_level_when_no_row() -> None:
    """When workspace_ai_policy has no row for (workspace, role, action), use existing level logic.

    Absence of a policy row means fall back to the hardcoded ApprovalLevel
    threshold defaults (DD-003), preserving backward compatibility.
    """
