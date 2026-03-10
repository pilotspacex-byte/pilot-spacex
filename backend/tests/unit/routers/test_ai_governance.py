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
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from pilot_space.infrastructure.auth.supabase_auth import TokenPayload
from pilot_space.infrastructure.database.models.audit_log import ActorType, AuditLog
from pilot_space.infrastructure.database.models.workspace_ai_policy import WorkspaceAIPolicy

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


def _make_policy_row(role: str = "MEMBER", action_type: str = "extract_issues") -> MagicMock:
    """Create a minimal WorkspaceAIPolicy-like mock."""
    row = MagicMock(spec=WorkspaceAIPolicy)
    row.id = uuid4()
    row.workspace_id = WORKSPACE_ID
    row.role = role
    row.action_type = action_type
    row.requires_approval = True
    return row


def _make_audit_entry(
    actor_type: ActorType = ActorType.AI,
    action: str = "issue.create",
    resource_type: str = "issue",
) -> MagicMock:
    """Create a minimal AuditLog-like mock."""
    entry = MagicMock(spec=AuditLog)
    entry.id = uuid4()
    entry.workspace_id = WORKSPACE_ID
    entry.actor_id = uuid4()
    entry.actor_type = actor_type
    entry.action = action
    entry.resource_type = resource_type
    entry.resource_id = uuid4()
    entry.payload = {"before": {"title": "Old Title"}, "after": {"title": "New Title"}}
    entry.created_at = datetime.now(UTC)
    return entry


@pytest.fixture
async def gov_client() -> AsyncGenerator[AsyncClient, None]:
    """HTTP client with auth and workspace resolution mocked via overrides."""
    from pilot_space.dependencies.auth import get_current_user
    from pilot_space.main import app

    token_payload = _make_token_payload()
    app.dependency_overrides[get_current_user] = lambda: token_payload

    with (
        patch(
            "pilot_space.api.v1.routers.ai_governance._resolve_workspace",
            new=AsyncMock(return_value=WORKSPACE_ID),
        ),
        patch(
            "pilot_space.api.v1.routers.ai_governance._require_admin_or_owner",
            new=AsyncMock(),
        ),
        patch(
            "pilot_space.api.v1.routers.ai_governance._require_owner",
            new=AsyncMock(),
        ),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport,
            base_url="http://test",
            headers={"Authorization": "Bearer test-token"},
        ) as client:
            yield client

    app.dependency_overrides.pop(get_current_user, None)


# ---------------------------------------------------------------------------
# Policy CRUD tests
# ---------------------------------------------------------------------------


async def test_get_ai_policy_returns_matrix(gov_client: AsyncClient) -> None:
    """GET /workspaces/{slug}/settings/ai-policy returns list of policy rows."""
    rows = [
        _make_policy_row("MEMBER", "extract_issues"),
        _make_policy_row("ADMIN", "create_issues"),
    ]

    with patch("pilot_space.api.v1.routers.ai_governance.WorkspaceAIPolicyRepository") as MockRepo:
        instance = MockRepo.return_value
        instance.list_for_workspace = AsyncMock(return_value=rows)

        response = await gov_client.get(f"/api/v1/workspaces/{WORKSPACE_SLUG}/settings/ai-policy")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2
    assert data[0]["role"] == "MEMBER"
    assert data[0]["action_type"] == "extract_issues"
    assert data[0]["requires_approval"] is True


async def test_put_ai_policy_creates_row(gov_client: AsyncClient) -> None:
    """PUT /workspaces/{slug}/settings/ai-policy/{role}/{action_type} upserts a row."""
    policy_row = _make_policy_row("MEMBER", "extract_issues")
    policy_row.requires_approval = True

    with patch("pilot_space.api.v1.routers.ai_governance.WorkspaceAIPolicyRepository") as MockRepo:
        instance = MockRepo.return_value
        instance.upsert = AsyncMock(return_value=policy_row)

        response = await gov_client.put(
            f"/api/v1/workspaces/{WORKSPACE_SLUG}/settings/ai-policy/MEMBER/extract_issues",
            json={"requires_approval": True},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["role"] == "MEMBER"
    assert data["action_type"] == "extract_issues"
    assert data["requires_approval"] is True
    instance.upsert.assert_called_once_with(WORKSPACE_ID, "MEMBER", "extract_issues", True)


async def test_put_ai_policy_owner_role_rejected(gov_client: AsyncClient) -> None:
    """PUT /workspaces/{slug}/settings/ai-policy/OWNER/... returns 400."""
    response = await gov_client.put(
        f"/api/v1/workspaces/{WORKSPACE_SLUG}/settings/ai-policy/OWNER/extract_issues",
        json={"requires_approval": True},
    )

    assert response.status_code == 400
    assert "not configurable" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# AI status tests
# ---------------------------------------------------------------------------


async def test_ai_status_byok_configured(gov_client: AsyncClient) -> None:
    """GET /workspaces/{slug}/settings/ai-status returns byok_configured=true when keys exist."""
    with patch("pilot_space.api.v1.routers.ai_governance.SecureKeyStorage") as MockStorage:
        instance = MockStorage.return_value
        # anthropic key configured and valid, others not configured
        mock_key_info = MagicMock()
        mock_key_info.is_valid = True
        mock_key_info.last_validated_at = None

        async def _get_key_info(workspace_id: object, provider: str) -> object:
            if provider == "anthropic":
                return mock_key_info
            return None

        instance.get_key_info = _get_key_info

        with patch("pilot_space.api.v1.routers.ai_governance.get_settings") as mock_settings:
            mock_settings.return_value.encryption_key.get_secret_value.return_value = "fake-key"

            response = await gov_client.get(
                f"/api/v1/workspaces/{WORKSPACE_SLUG}/settings/ai-status"
            )

    assert response.status_code == 200
    data = response.json()
    assert data["byok_configured"] is True
    assert "anthropic" in data["providers"]


async def test_ai_status_byok_not_configured(gov_client: AsyncClient) -> None:
    """GET /workspaces/{slug}/settings/ai-status returns byok_configured=false when no keys."""
    with patch("pilot_space.api.v1.routers.ai_governance.SecureKeyStorage") as MockStorage:
        instance = MockStorage.return_value
        instance.get_key_info = AsyncMock(return_value=None)

        with patch("pilot_space.api.v1.routers.ai_governance.get_settings") as mock_settings:
            mock_settings.return_value.encryption_key.get_secret_value.return_value = "fake-key"

            response = await gov_client.get(
                f"/api/v1/workspaces/{WORKSPACE_SLUG}/settings/ai-status"
            )

    assert response.status_code == 200
    data = response.json()
    assert data["byok_configured"] is False
    assert data["providers"] == []


# ---------------------------------------------------------------------------
# Rollback tests
# ---------------------------------------------------------------------------


async def test_rollback_eligible_entry(gov_client: AsyncClient) -> None:
    """POST /audit/{id}/rollback on AI create entry returns 200."""
    entry = _make_audit_entry(ActorType.AI, "issue.create", "issue")
    entry_id = entry.id

    with (
        patch("pilot_space.api.v1.routers.ai_governance.AuditLogRepository") as MockAuditRepo,
        patch("pilot_space.api.v1.routers.ai_governance._dispatch_rollback", new=AsyncMock()),
    ):
        audit_instance = MockAuditRepo.return_value
        audit_instance.get_by_id = AsyncMock(return_value=entry)
        audit_instance.create = AsyncMock(return_value=MagicMock(id=uuid4()))

        response = await gov_client.post(
            f"/api/v1/workspaces/{WORKSPACE_SLUG}/audit/{entry_id}/rollback"
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "rolled_back"
    assert data["entry_id"] == str(entry_id)


async def test_rollback_ineligible_entry_rejected(gov_client: AsyncClient) -> None:
    """POST /audit/{id}/rollback on USER entry returns 400."""
    entry = _make_audit_entry(ActorType.USER, "issue.create", "issue")
    entry_id = entry.id

    with patch("pilot_space.api.v1.routers.ai_governance.AuditLogRepository") as MockAuditRepo:
        audit_instance = MockAuditRepo.return_value
        audit_instance.get_by_id = AsyncMock(return_value=entry)

        response = await gov_client.post(
            f"/api/v1/workspaces/{WORKSPACE_SLUG}/audit/{entry_id}/rollback"
        )

    assert response.status_code == 400
    assert "rollback" in response.json()["detail"].lower()


async def test_rollback_creates_audit_entry(gov_client: AsyncClient) -> None:
    """Successful rollback writes a new audit log row with actor_type=USER."""
    entry = _make_audit_entry(ActorType.AI, "issue.create", "issue")
    entry_id = entry.id

    with (
        patch("pilot_space.api.v1.routers.ai_governance.AuditLogRepository") as MockAuditRepo,
        patch("pilot_space.api.v1.routers.ai_governance._dispatch_rollback", new=AsyncMock()),
    ):
        audit_instance = MockAuditRepo.return_value
        audit_instance.get_by_id = AsyncMock(return_value=entry)
        created_rollback = MagicMock(id=uuid4())
        audit_instance.create = AsyncMock(return_value=created_rollback)

        response = await gov_client.post(
            f"/api/v1/workspaces/{WORKSPACE_SLUG}/audit/{entry_id}/rollback"
        )

    assert response.status_code == 200
    audit_instance.create.assert_called_once()
    create_kwargs = audit_instance.create.call_args.kwargs
    assert create_kwargs["actor_type"] == ActorType.USER
    assert create_kwargs["action"] == "ai.rollback"


async def test_approval_list_returns_pending(gov_client: AsyncClient) -> None:
    """GET /workspaces/{slug}/approvals — endpoint exists in ai_approvals.py (verify, not reimplemented)."""
    # Verify the ai_approvals router is mounted and accessible with a GET list route
    from pilot_space.api.v1.routers.ai_approvals import router as approvals_router

    routes = [r.path for r in approvals_router.routes]  # type: ignore[attr-defined]
    # The approvals router has a GET /approvals route (prefix is set at include_router time)
    assert any("/approvals" in r for r in routes), (
        f"Expected '/approvals' route in ai_approvals router, got: {routes}"
    )
