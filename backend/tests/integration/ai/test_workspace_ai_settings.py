"""Integration tests for workspace AI settings endpoints (T066).

Tests GET and PUT endpoints for AI settings configuration.
These tests verify the full HTTP request/response cycle with database integration.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi import status

if TYPE_CHECKING:
    from httpx import AsyncClient
    from sqlalchemy.ext.asyncio import AsyncSession

    from pilot_space.infrastructure.database.models import Workspace


@pytest.fixture
async def test_workspace_with_admin(db_session: AsyncSession, test_user_id: UUID) -> Workspace:
    """Create test workspace with admin member for AI settings tests."""
    from pilot_space.infrastructure.database.models import (
        Workspace,
        WorkspaceMember,
        WorkspaceRole,
    )

    workspace = Workspace(
        name="Test AI Workspace",
        slug=f"test-ai-{uuid4().hex[:8]}",
        description="Workspace for AI settings testing",
        owner_id=test_user_id,
    )
    db_session.add(workspace)
    await db_session.flush()

    # Add the test user as admin
    member = WorkspaceMember(
        workspace_id=workspace.id,
        user_id=test_user_id,
        role=WorkspaceRole.ADMIN,
    )
    db_session.add(member)
    await db_session.commit()
    await db_session.refresh(workspace)

    return workspace


@pytest.mark.asyncio
async def test_get_settings_returns_provider_status(
    authenticated_client: AsyncClient,
    test_workspace_with_admin: Workspace,
    db_session: AsyncSession,
) -> None:
    """Verify GET endpoint returns provider statuses."""
    response = await authenticated_client.get(
        f"/api/v1/workspaces/{test_workspace_with_admin.id}/ai/settings",
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    # Verify structure
    assert "workspace_id" in data
    assert "providers" in data
    assert "features" in data
    assert "default_provider" in data

    # Verify providers
    assert len(data["providers"]) == 3
    provider_names = {p["provider"] for p in data["providers"]}
    assert provider_names == {"anthropic", "openai", "google"}

    # All should be unconfigured initially
    for provider in data["providers"]:
        assert provider["is_configured"] is False
        assert provider["is_valid"] is None
        assert provider["last_validated_at"] is None


@pytest.mark.asyncio
async def test_get_settings_workspace_not_found(
    authenticated_client: AsyncClient,
) -> None:
    """Verify 404 when workspace doesn't exist."""
    fake_workspace_id = uuid4()

    response = await authenticated_client.get(
        f"/api/v1/workspaces/{fake_workspace_id}/ai/settings",
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
@patch("pilot_space.ai.infrastructure.key_storage.AsyncAnthropic")
async def test_update_settings_validates_key_success(
    mock_anthropic: AsyncMock,
    authenticated_client: AsyncClient,
    test_workspace_with_admin: Workspace,
    db_session: AsyncSession,
) -> None:
    """Verify PUT endpoint validates and stores valid API key."""
    # Mock successful validation
    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock()
    mock_anthropic.return_value = mock_client

    response = await authenticated_client.put(
        f"/api/v1/workspaces/{test_workspace_with_admin.id}/ai/settings",
        json={"api_keys": [{"provider": "anthropic", "api_key": "sk-ant-test-valid-key"}]},
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert data["success"] is True
    assert len(data["validation_results"]) == 1
    assert data["validation_results"][0]["provider"] == "anthropic"
    assert data["validation_results"][0]["is_valid"] is True
    assert data["validation_results"][0]["error_message"] is None
    assert "anthropic" in data["updated_providers"]


@pytest.mark.asyncio
@patch("pilot_space.ai.infrastructure.key_storage.AsyncAnthropic")
async def test_update_settings_validates_key_failure(
    mock_anthropic: AsyncMock,
    authenticated_client: AsyncClient,
    test_workspace_with_admin: Workspace,
    db_session: AsyncSession,
) -> None:
    """Verify PUT endpoint rejects invalid API key."""
    # Mock failed validation
    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(side_effect=Exception("Invalid API key"))
    mock_anthropic.return_value = mock_client

    response = await authenticated_client.put(
        f"/api/v1/workspaces/{test_workspace_with_admin.id}/ai/settings",
        json={"api_keys": [{"provider": "anthropic", "api_key": "sk-ant-invalid-key"}]},
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert data["success"] is False
    assert len(data["validation_results"]) == 1
    assert data["validation_results"][0]["provider"] == "anthropic"
    assert data["validation_results"][0]["is_valid"] is False
    assert data["validation_results"][0]["error_message"] is not None
    assert data["updated_providers"] == []


@pytest.mark.asyncio
async def test_update_settings_removes_key(
    authenticated_client: AsyncClient,
    test_workspace_with_admin: Workspace,
    db_session: AsyncSession,
) -> None:
    """Verify PUT endpoint removes key when api_key is None."""
    response = await authenticated_client.put(
        f"/api/v1/workspaces/{test_workspace_with_admin.id}/ai/settings",
        json={"api_keys": [{"provider": "anthropic", "api_key": None}]},
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert data["success"] is True
    assert "anthropic" in data["updated_providers"]


@pytest.mark.asyncio
async def test_update_features_toggles(
    authenticated_client: AsyncClient,
    test_workspace_with_admin: Workspace,
    db_session: AsyncSession,
) -> None:
    """Verify PUT endpoint updates feature toggles."""
    response = await authenticated_client.put(
        f"/api/v1/workspaces/{test_workspace_with_admin.id}/ai/settings",
        json={
            "features": {
                "ghost_text_enabled": False,
                "pr_review_enabled": True,
                "ai_context_enabled": True,
                "issue_extraction_enabled": False,
                "margin_annotations_enabled": True,
                "auto_approve_non_destructive": False,
            }
        },
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert data["updated_features"] is True

    # Verify features were persisted
    get_response = await authenticated_client.get(
        f"/api/v1/workspaces/{test_workspace_with_admin.id}/ai/settings",
    )

    assert get_response.status_code == status.HTTP_200_OK
    features = get_response.json()["features"]
    assert features["ghost_text_enabled"] is False
    assert features["pr_review_enabled"] is True
    assert features["issue_extraction_enabled"] is False


@pytest.mark.asyncio
async def test_update_cost_limit(
    authenticated_client: AsyncClient,
    test_workspace_with_admin: Workspace,
    db_session: AsyncSession,
) -> None:
    """Verify PUT endpoint updates cost limit."""
    response = await authenticated_client.put(
        f"/api/v1/workspaces/{test_workspace_with_admin.id}/ai/settings",
        json={"cost_limit_usd": 100.0},
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert data["updated_features"] is True

    # Verify cost limit was persisted
    get_response = await authenticated_client.get(
        f"/api/v1/workspaces/{test_workspace_with_admin.id}/ai/settings",
    )

    assert get_response.status_code == status.HTTP_200_OK
    assert get_response.json()["cost_limit_usd"] == 100.0


@pytest.mark.asyncio
async def test_update_settings_invalid_provider(
    authenticated_client: AsyncClient,
    test_workspace_with_admin: Workspace,
    db_session: AsyncSession,
) -> None:
    """Verify validation error for invalid provider name."""
    response = await authenticated_client.put(
        f"/api/v1/workspaces/{test_workspace_with_admin.id}/ai/settings",
        json={"api_keys": [{"provider": "invalid-provider", "api_key": "test"}]},
    )

    # Pydantic validation should reject this before reaching handler
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_update_settings_negative_cost_limit(
    authenticated_client: AsyncClient,
    test_workspace_with_admin: Workspace,
    db_session: AsyncSession,
) -> None:
    """Verify validation error for negative cost limit."""
    response = await authenticated_client.put(
        f"/api/v1/workspaces/{test_workspace_with_admin.id}/ai/settings",
        json={"cost_limit_usd": -10.0},
    )

    # Pydantic validation should reject this
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
