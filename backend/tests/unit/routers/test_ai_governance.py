"""xfail test stubs for AI Governance router endpoints.

Phase 4 — AI Governance (AIGOV-01/02/04/05):
- GET /workspaces/{slug}/settings/ai-policy — returns per-role matrix
- PUT /workspaces/{slug}/settings/ai-policy — OWNER creates/updates policy rows
- GET /workspaces/{slug}/approvals — lists pending AI approvals
- POST /workspaces/{slug}/audit/{id}/rollback — rollback eligible AI actions
- GET /workspaces/{slug}/settings/ai-status — BYOK configuration status

Implemented in plans 04-02 (AIGOV-01/02), 04-05 (AIGOV-03/04), 04-07 (AIGOV-05).
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.asyncio


@pytest.mark.xfail(
    strict=False,
    reason="Phase 4 AIGOV-01/02: GET ai-policy endpoint — implemented in 04-02",
)
async def test_get_ai_policy_returns_matrix() -> None:
    """GET /workspaces/{slug}/settings/ai-policy returns per-role matrix.

    Response must include a dict keyed by role ('OWNER', 'ADMIN', 'MEMBER', 'GUEST'),
    each mapping action_type -> requires_approval bool. Rows missing from
    workspace_ai_policy fall back to hardcoded defaults.
    """


@pytest.mark.xfail(
    strict=False,
    reason="Phase 4 AIGOV-02: PUT ai-policy creates policy row — implemented in 04-02",
)
async def test_put_ai_policy_creates_row() -> None:
    """PUT /workspaces/{slug}/settings/ai-policy creates or updates a policy row.

    OWNER-scoped request with {role, action_type, requires_approval} body
    must upsert a workspace_ai_policy row and return 200 with the updated row.
    """


@pytest.mark.xfail(
    strict=False,
    reason="Phase 4 AIGOV-02: Owner role cannot be configured — implemented in 04-02",
)
async def test_put_ai_policy_owner_role_rejected() -> None:
    """Attempting to configure OWNER row returns 422.

    OWNER always auto-executes DEFAULT_REQUIRE actions; the policy row for
    role='OWNER' must not be configurable (API rejects with 422 Unprocessable Entity).
    """


@pytest.mark.xfail(
    strict=False,
    reason="Phase 4 AIGOV-04: GET approvals returns pending list — implemented in 04-05",
)
async def test_approval_list_returns_pending() -> None:
    """GET /workspaces/{slug}/approvals returns paginated pending AI approvals.

    Must include approval id, action_type, actor (agent name), and created_at.
    """


@pytest.mark.xfail(
    strict=False,
    reason="Phase 4 AIGOV-04: rollback eligible AI audit entry — implemented in 04-05",
)
async def test_rollback_eligible_entry() -> None:
    """POST /workspaces/{slug}/audit/{id}/rollback succeeds for AI-created entry.

    AI create actions (actor_type=AI, action=create_*) are rollback-eligible.
    Rollback must succeed and return 200 with the rollback audit entry.
    """


@pytest.mark.xfail(
    strict=False,
    reason="Phase 4 AIGOV-04: non-AI entry rollback rejected — implemented in 04-05",
)
async def test_rollback_ineligible_entry_rejected() -> None:
    """POST /workspaces/{slug}/audit/{id}/rollback returns 400 for non-rollback-eligible entries.

    Entries with actor_type=USER or destructive actions (delete_*) must
    return 400 Bad Request with reason='not_eligible_for_rollback'.
    """


@pytest.mark.xfail(
    strict=False,
    reason="Phase 4 AIGOV-04: rollback creates audit entry — implemented in 04-05",
)
async def test_rollback_creates_audit_entry() -> None:
    """Successful rollback writes a new audit log row with actor_type=USER.

    The rollback itself must be recorded in audit_logs with
    actor_type='USER', action='rollback', and references the original entry id.
    """


@pytest.mark.xfail(
    strict=False,
    reason="Phase 4 AIGOV-05: ai-status with BYOK key present — implemented in 04-07",
)
async def test_ai_status_byok_configured() -> None:
    """GET /workspaces/{slug}/settings/ai-status returns byok_configured=true when key exists.

    When WorkspaceAPIKey row exists for the workspace,
    response must include byok_configured=true and provider name.
    """


@pytest.mark.xfail(
    strict=False,
    reason="Phase 4 AIGOV-05: ai-status with no BYOK key — implemented in 04-07",
)
async def test_ai_status_byok_not_configured() -> None:
    """GET /workspaces/{slug}/settings/ai-status returns byok_configured=false when no key.

    When WorkspaceAPIKey row is absent, response must include
    byok_configured=false. AI features should be disabled client-side.
    """
