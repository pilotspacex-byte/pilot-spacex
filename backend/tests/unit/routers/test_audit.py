"""Tests for audit router actor_type query parameter.

Phase 4 — AI Governance (AIGOV-03):
The audit router must pass actor_type query parameter to AuditLogRepository
for both list and export endpoints.

Implemented in plan 04-03 (AIGOV-03 audit router actor_type param).
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from pilot_space.infrastructure.auth import TokenPayload
from pilot_space.infrastructure.database.models.audit_log import ActorType, AuditLog
from pilot_space.infrastructure.database.repositories.audit_log_repository import (
    AuditLogPage,
)

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


def _make_audit_row(actor_type: ActorType = ActorType.AI) -> MagicMock:
    """Create a minimal AuditLog-like mock for response serialization."""
    row = MagicMock(spec=AuditLog)
    row.id = uuid4()
    row.workspace_id = WORKSPACE_ID
    row.actor_id = uuid4()
    row.actor_type = actor_type
    row.action = "issue.create"
    row.resource_type = "issue"
    row.resource_id = None
    row.ip_address = None
    row.payload = None
    row.ai_input = None
    row.ai_output = None
    row.ai_model = None
    row.ai_token_cost = None
    row.ai_rationale = None
    row.created_at = datetime.now(UTC)
    row.updated_at = datetime.now(UTC)
    return row


@pytest.fixture
async def audit_client() -> AsyncGenerator[AsyncClient, None]:
    """HTTP client with auth and workspace resolution mocked via overrides."""
    from pilot_space.dependencies.auth import get_current_user
    from pilot_space.main import app

    token_payload = _make_token_payload()

    # Override auth dependency
    app.dependency_overrides[get_current_user] = lambda: token_payload

    with (
        patch(
            "pilot_space.api.v1.routers.audit._resolve_workspace",
            new=AsyncMock(return_value=WORKSPACE_ID),
        ),
        patch(
            "pilot_space.api.v1.routers.audit.set_rls_context",
            new=AsyncMock(),
        ),
        patch(
            "pilot_space.api.v1.routers.audit._require_admin_or_owner",
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

    # Clean up overrides
    app.dependency_overrides.pop(get_current_user, None)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_audit_list_actor_type_param_passed_to_repo(
    audit_client: AsyncClient,
) -> None:
    """GET /workspaces/{slug}/audit?actor_type=AI passes actor_type to list_filtered."""
    ai_row = _make_audit_row(ActorType.AI)
    mock_page = AuditLogPage(items=[ai_row], has_next=False, next_cursor=None)

    with patch("pilot_space.api.v1.routers.audit.AuditLogRepository") as MockRepo:
        instance = MockRepo.return_value
        instance.list_filtered = AsyncMock(return_value=mock_page)

        response = await audit_client.get(
            f"/api/v1/workspaces/{WORKSPACE_SLUG}/audit?actor_type=AI"
        )

    assert response.status_code == 200
    instance.list_filtered.assert_called_once()
    call_kwargs = instance.list_filtered.call_args.kwargs
    assert call_kwargs["actor_type"] == ActorType.AI


async def test_audit_export_actor_type_param_passed_to_repo(
    audit_client: AsyncClient,
) -> None:
    """GET /workspaces/{slug}/audit/export?actor_type=AI passes actor_type to list_for_export."""
    ai_row = _make_audit_row(ActorType.AI)

    with patch("pilot_space.api.v1.routers.audit.AuditLogRepository") as MockRepo:
        instance = MockRepo.return_value
        instance.list_for_export = AsyncMock(return_value=[ai_row])

        response = await audit_client.get(
            f"/api/v1/workspaces/{WORKSPACE_SLUG}/audit/export?actor_type=AI"
        )

    assert response.status_code == 200
    instance.list_for_export.assert_called_once()
    call_kwargs = instance.list_for_export.call_args.kwargs
    assert call_kwargs["actor_type"] == ActorType.AI


async def test_audit_list_invalid_actor_type_returns_422(
    audit_client: AsyncClient,
) -> None:
    """actor_type=INVALID returns 422 — FastAPI validates the enum automatically."""
    response = await audit_client.get(
        f"/api/v1/workspaces/{WORKSPACE_SLUG}/audit?actor_type=INVALID"
    )
    assert response.status_code == 422
