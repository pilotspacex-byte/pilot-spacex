"""Tests for AI Governance router endpoints.

Phase 4 — AI Governance (AIGOV-01/02/04/05):
- GET /workspaces/{slug}/settings/ai-policy — returns per-role matrix
- PUT /workspaces/{slug}/settings/ai-policy/{role}/{action_type} — upserts policy row
- GET /workspaces/{slug}/settings/ai-status — BYOK configuration status
- POST /workspaces/{slug}/audit/{id}/rollback — rollback eligible AI actions
- GET /workspaces/{slug}/approvals — verify endpoint exists in ai_approvals.py (not reimplemented)

Implemented in plan 04-04 (AIGOV-01/02/04/05).
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from pilot_space.domain.exceptions import ValidationError
from pilot_space.infrastructure.auth.supabase_auth import TokenPayload
from pilot_space.schemas.ai_governance import AIStatus, GovernanceAction, RollbackResult

pytestmark = pytest.mark.asyncio

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

WORKSPACE_SLUG = "test-workspace"
WORKSPACE_ID = uuid4()
USER_ID = uuid4()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_token_payload() -> TokenPayload:
    """Build a minimal TokenPayload for auth override."""
    now = datetime.now(tz=UTC)
    return TokenPayload(
        sub=str(USER_ID),
        email="test@example.com",
        role="authenticated",
        aud="authenticated",
        exp=int(now.timestamp()) + 3600,
        iat=int(now.timestamp()),
        app_metadata={},
        user_metadata={},
    )


def _make_governance_action(
    role: str = "MEMBER", action_type: str = "extract_issues"
) -> GovernanceAction:
    """Create a minimal GovernanceAction domain object."""
    return GovernanceAction(
        role=role,
        action_type=action_type,
        requires_approval=True,
    )


def _make_mock_service() -> MagicMock:
    """Create a fully-mocked GovernanceRollbackService."""
    svc = MagicMock()
    svc.list_policies = AsyncMock(return_value=[])
    svc.upsert_policy = AsyncMock()
    svc.delete_policy = AsyncMock()
    svc.get_ai_status = AsyncMock(return_value=AIStatus(byok_configured=False, providers=()))
    svc.execute_rollback = AsyncMock()
    return svc


@pytest.fixture
async def gov_client() -> AsyncGenerator[tuple[AsyncClient, MagicMock], None]:
    """HTTP client with auth and service mocked via DI overrides.

    Yields (client, mock_service) so tests can configure mock_service per-test.
    """
    from pilot_space.api.v1.dependencies import _get_governance_rollback_service
    from pilot_space.dependencies.auth import get_current_user
    from pilot_space.main import app

    token_payload = _make_token_payload()
    mock_service = _make_mock_service()

    app.dependency_overrides[get_current_user] = lambda: token_payload
    app.dependency_overrides[_get_governance_rollback_service] = lambda: mock_service

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"Authorization": "Bearer test-token"},
    ) as client:
        yield client, mock_service

    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(_get_governance_rollback_service, None)


# ---------------------------------------------------------------------------
# Policy CRUD tests
# ---------------------------------------------------------------------------


async def test_get_ai_policy_returns_matrix(
    gov_client: tuple[AsyncClient, MagicMock],
) -> None:
    """GET /workspaces/{slug}/settings/ai-policy returns list of policy rows."""
    client, svc = gov_client
    svc.list_policies = AsyncMock(
        return_value=[
            _make_governance_action("MEMBER", "extract_issues"),
            _make_governance_action("ADMIN", "create_issues"),
        ]
    )

    response = await client.get(f"/api/v1/workspaces/{WORKSPACE_SLUG}/settings/ai-policy")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2
    assert data[0]["role"] == "MEMBER"
    assert data[0]["action_type"] == "extract_issues"
    assert data[0]["requires_approval"] is True


async def test_put_ai_policy_creates_row(
    gov_client: tuple[AsyncClient, MagicMock],
) -> None:
    """PUT /workspaces/{slug}/settings/ai-policy/{role}/{action_type} upserts a row."""
    client, svc = gov_client
    svc.upsert_policy = AsyncMock(return_value=_make_governance_action("MEMBER", "extract_issues"))

    response = await client.put(
        f"/api/v1/workspaces/{WORKSPACE_SLUG}/settings/ai-policy/MEMBER/extract_issues",
        json={"requires_approval": True},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["role"] == "MEMBER"
    assert data["action_type"] == "extract_issues"
    assert data["requires_approval"] is True
    svc.upsert_policy.assert_called_once()


async def test_put_ai_policy_owner_role_rejected(
    gov_client: tuple[AsyncClient, MagicMock],
) -> None:
    """PUT /workspaces/{slug}/settings/ai-policy/OWNER/... returns 422."""
    client, svc = gov_client
    svc.upsert_policy = AsyncMock(
        side_effect=ValidationError("Owner role policy is not configurable.")
    )

    response = await client.put(
        f"/api/v1/workspaces/{WORKSPACE_SLUG}/settings/ai-policy/OWNER/extract_issues",
        json={"requires_approval": True},
    )

    assert response.status_code == 422
    assert "not configurable" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# AI status tests
# ---------------------------------------------------------------------------


async def test_ai_status_byok_configured(
    gov_client: tuple[AsyncClient, MagicMock],
) -> None:
    """GET /workspaces/{slug}/settings/ai-status returns byok_configured=true when keys exist."""
    client, svc = gov_client
    svc.get_ai_status = AsyncMock(
        return_value=AIStatus(byok_configured=True, providers=("anthropic",))
    )

    response = await client.get(f"/api/v1/workspaces/{WORKSPACE_SLUG}/settings/ai-status")

    assert response.status_code == 200
    data = response.json()
    assert data["byok_configured"] is True
    assert "anthropic" in data["providers"]


async def test_ai_status_byok_not_configured(
    gov_client: tuple[AsyncClient, MagicMock],
) -> None:
    """GET /workspaces/{slug}/settings/ai-status returns byok_configured=false when no keys."""
    client, svc = gov_client
    svc.get_ai_status = AsyncMock(return_value=AIStatus(byok_configured=False, providers=()))

    response = await client.get(f"/api/v1/workspaces/{WORKSPACE_SLUG}/settings/ai-status")

    assert response.status_code == 200
    data = response.json()
    assert data["byok_configured"] is False
    assert data["providers"] == []


# ---------------------------------------------------------------------------
# Rollback tests
# ---------------------------------------------------------------------------


async def test_rollback_eligible_entry(
    gov_client: tuple[AsyncClient, MagicMock],
) -> None:
    """POST /audit/{id}/rollback on AI create entry returns 200."""
    client, svc = gov_client
    entry_id = uuid4()
    svc.execute_rollback = AsyncMock(
        return_value=RollbackResult(status="rolled_back", entry_id=entry_id)
    )

    response = await client.post(f"/api/v1/workspaces/{WORKSPACE_SLUG}/audit/{entry_id}/rollback")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "rolled_back"
    assert data["entry_id"] == str(entry_id)


async def test_rollback_ineligible_entry_rejected(
    gov_client: tuple[AsyncClient, MagicMock],
) -> None:
    """POST /audit/{id}/rollback on non-eligible entry returns 422."""
    client, svc = gov_client
    entry_id = uuid4()
    svc.execute_rollback = AsyncMock(
        side_effect=ValidationError(
            "Entry is not rollback-eligible. "
            "Rollback applies only to AI create/update actions on supported resource types."
        )
    )

    response = await client.post(f"/api/v1/workspaces/{WORKSPACE_SLUG}/audit/{entry_id}/rollback")

    assert response.status_code == 422
    assert "rollback" in response.json()["detail"].lower()


async def test_rollback_calls_service_with_correct_args(
    gov_client: tuple[AsyncClient, MagicMock],
) -> None:
    """Successful rollback delegates to service.execute_rollback with correct arguments."""
    client, svc = gov_client
    entry_id = uuid4()
    svc.execute_rollback = AsyncMock(
        return_value=RollbackResult(status="rolled_back", entry_id=entry_id)
    )

    response = await client.post(f"/api/v1/workspaces/{WORKSPACE_SLUG}/audit/{entry_id}/rollback")

    assert response.status_code == 200
    svc.execute_rollback.assert_called_once_with(WORKSPACE_SLUG, entry_id, USER_ID)


async def test_approval_list_returns_pending(
    gov_client: tuple[AsyncClient, MagicMock],
) -> None:
    """GET /workspaces/{slug}/approvals — endpoint exists in ai_approvals.py (verify, not reimplemented)."""
    # Verify the ai_approvals router is mounted and accessible with a GET list route
    from pilot_space.api.v1.routers.ai_approvals import router as approvals_router

    routes = [r.path for r in approvals_router.routes]  # type: ignore[attr-defined]
    # The approvals router has a GET /approvals route (prefix is set at include_router time)
    assert any("/approvals" in r for r in routes), (
        f"Expected '/approvals' route in ai_approvals router, got: {routes}"
    )
