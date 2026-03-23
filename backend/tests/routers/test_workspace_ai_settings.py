"""Tests for workspace AI settings router.

Tests the PATCH /workspaces/{id}/ai/settings endpoint,
specifically the Ollama metadata-only save fix (no API key required).
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import status

pytestmark = pytest.mark.asyncio

_OWNER_USER_ID = uuid4()
_WORKSPACE_ID = uuid4()

_ADMIN_WORKSPACE_PATH = "pilot_space.api.v1.routers.workspace_ai_settings.get_admin_workspace"
_KEY_STORAGE_PATH = "pilot_space.ai.infrastructure.key_storage.SecureKeyStorage"
_GET_SETTINGS_PATH = "pilot_space.config.get_settings"


@pytest.fixture
async def ai_settings_client(request: Any) -> AsyncGenerator[Any, None]:
    """Authenticated client with overrides for AI settings router tests."""
    from httpx import ASGITransport, AsyncClient

    from pilot_space.dependencies.auth import get_current_user, get_session
    from pilot_space.infrastructure.auth import TokenPayload
    from pilot_space.main import app

    mock_session = AsyncMock()

    async def mock_session_gen() -> AsyncGenerator[Any, None]:
        yield mock_session

    mock_user = TokenPayload(
        sub=str(_OWNER_USER_ID),
        email="admin@test.com",
        role="authenticated",
        aud="authenticated",
        exp=9999999999,
        iat=1000000000,
    )

    app.dependency_overrides[get_session] = mock_session_gen
    app.dependency_overrides[get_current_user] = lambda: mock_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


def _mock_workspace() -> MagicMock:
    ws = MagicMock()
    ws.id = _WORKSPACE_ID
    ws.settings = {"ai_features": {}}
    member = MagicMock()
    member.user_id = _OWNER_USER_ID
    member.is_admin = True
    ws.members = [member]
    return ws


class TestOllamaMetadataOnlySave:
    """Ollama can be saved with just base_url + model_name, no API key."""

    async def test_ollama_metadata_only_creates_record(self, ai_settings_client: Any) -> None:
        """Ollama save with base_url + model_name (no API key) should succeed."""
        mock_storage = AsyncMock()
        mock_storage.get_key_info = AsyncMock(return_value=None)
        mock_storage.store_api_key = AsyncMock()
        mock_storage.validate_api_key = AsyncMock(return_value=(True, None))

        with (
            patch(_ADMIN_WORKSPACE_PATH, return_value=_mock_workspace()),
            patch(_KEY_STORAGE_PATH, return_value=mock_storage) as mock_cls,
            patch(_GET_SETTINGS_PATH) as mock_settings,
        ):
            mock_settings.return_value = MagicMock(
                encryption_key=MagicMock(get_secret_value=lambda: "test-secret")
            )
            mock_cls.return_value = mock_storage

            resp = await ai_settings_client.patch(
                f"/api/v1/workspaces/{_WORKSPACE_ID}/ai/settings",
                json={
                    "api_keys": [
                        {
                            "provider": "ollama",
                            "service_type": "llm",
                            "base_url": "http://localhost:11434",
                            "model_name": "kimi-k2.5:cloud",
                        }
                    ]
                },
            )

        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert len(data["updatedProviders"]) == 1
        assert "ollama:llm" in data["updatedProviders"]

        # Verify store_api_key called with api_key=None
        mock_storage.store_api_key.assert_called_once_with(
            workspace_id=_WORKSPACE_ID,
            provider="ollama",
            service_type="llm",
            api_key=None,
            base_url="http://localhost:11434",
            model_name="kimi-k2.5:cloud",
        )

    async def test_non_ollama_metadata_only_requires_key(self, ai_settings_client: Any) -> None:
        """Non-Ollama providers still require API key for first-time setup."""
        mock_storage = AsyncMock()
        mock_storage.get_key_info = AsyncMock(return_value=None)

        with (
            patch(_ADMIN_WORKSPACE_PATH, return_value=_mock_workspace()),
            patch(_KEY_STORAGE_PATH, return_value=mock_storage) as mock_cls,
            patch(_GET_SETTINGS_PATH) as mock_settings,
        ):
            mock_settings.return_value = MagicMock(
                encryption_key=MagicMock(get_secret_value=lambda: "test-secret")
            )
            mock_cls.return_value = mock_storage

            resp = await ai_settings_client.patch(
                f"/api/v1/workspaces/{_WORKSPACE_ID}/ai/settings",
                json={
                    "api_keys": [
                        {
                            "provider": "google",
                            "service_type": "embedding",
                            "base_url": "https://custom.google.com",
                        }
                    ]
                },
            )

        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data["success"] is False
        failed = [r for r in data["validationResults"] if not r["isValid"]]
        assert len(failed) == 1
        assert "API key required" in failed[0]["errorMessage"]
        # Rejected path must NOT persist a record
        mock_storage.store_api_key.assert_not_called()

    async def test_ollama_metadata_only_validation_failure(self, ai_settings_client: Any) -> None:
        """Ollama saved but validation fails (e.g. not running) — still saves."""
        mock_storage = AsyncMock()
        mock_storage.get_key_info = AsyncMock(return_value=None)
        mock_storage.store_api_key = AsyncMock()
        mock_storage.validate_api_key = AsyncMock(return_value=(False, "Connection refused"))

        with (
            patch(_ADMIN_WORKSPACE_PATH, return_value=_mock_workspace()),
            patch(_KEY_STORAGE_PATH, return_value=mock_storage) as mock_cls,
            patch(_GET_SETTINGS_PATH) as mock_settings,
        ):
            mock_settings.return_value = MagicMock(
                encryption_key=MagicMock(get_secret_value=lambda: "test-secret")
            )
            mock_cls.return_value = mock_storage

            resp = await ai_settings_client.patch(
                f"/api/v1/workspaces/{_WORKSPACE_ID}/ai/settings",
                json={
                    "api_keys": [
                        {
                            "provider": "ollama",
                            "service_type": "embedding",
                            "base_url": "http://localhost:11434",
                            "model_name": "nomic-embed-text-v2-moe",
                        }
                    ]
                },
            )

        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        # Provider was saved despite validation failure
        assert "ollama:embedding" in data["updatedProviders"]
        # But success is False because validation failed
        assert data["success"] is False
        assert data["validationResults"][0]["isValid"] is False
        assert "Connection refused" in data["validationResults"][0]["errorMessage"]


class TestDefaultProviderSelection:
    """Per-service-type default provider selection."""

    async def test_set_default_llm_provider(self, ai_settings_client: Any) -> None:
        """Setting default_llm_provider persists to workspace settings."""
        mock_workspace = _mock_workspace()
        mock_repo = AsyncMock()

        with (
            patch(_ADMIN_WORKSPACE_PATH, return_value=mock_workspace),
            patch(
                "pilot_space.api.v1.routers.workspace_ai_settings.WorkspaceRepository",
                return_value=mock_repo,
            ),
            patch(_GET_SETTINGS_PATH) as mock_settings,
        ):
            mock_settings.return_value = MagicMock(
                encryption_key=MagicMock(get_secret_value=lambda: "test-secret")
            )

            resp = await ai_settings_client.patch(
                f"/api/v1/workspaces/{_WORKSPACE_ID}/ai/settings",
                json={"defaultLlmProvider": "ollama"},
            )

        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data["updatedFeatures"] is True
        # Verify workspace settings were updated with the new default
        assert mock_workspace.settings["default_llm_provider"] == "ollama"
        # Verify the repo was asked to persist the workspace
        mock_repo.update.assert_called_once()

    async def test_set_default_embedding_provider(self, ai_settings_client: Any) -> None:
        """Setting default_embedding_provider persists to workspace settings."""
        mock_workspace = _mock_workspace()
        mock_repo = AsyncMock()

        with (
            patch(_ADMIN_WORKSPACE_PATH, return_value=mock_workspace),
            patch(
                "pilot_space.api.v1.routers.workspace_ai_settings.WorkspaceRepository",
                return_value=mock_repo,
            ),
            patch(_GET_SETTINGS_PATH) as mock_settings,
        ):
            mock_settings.return_value = MagicMock(
                encryption_key=MagicMock(get_secret_value=lambda: "test-secret")
            )

            resp = await ai_settings_client.patch(
                f"/api/v1/workspaces/{_WORKSPACE_ID}/ai/settings",
                json={"defaultEmbeddingProvider": "ollama"},
            )

        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data["updatedFeatures"] is True
        assert mock_workspace.settings["default_embedding_provider"] == "ollama"

    async def test_invalid_provider_rejected(self, ai_settings_client: Any) -> None:
        """Invalid provider name for default_llm_provider is rejected by schema."""
        mock_workspace = _mock_workspace()

        with patch(_ADMIN_WORKSPACE_PATH, return_value=mock_workspace):
            resp = await ai_settings_client.patch(
                f"/api/v1/workspaces/{_WORKSPACE_ID}/ai/settings",
                json={"defaultLlmProvider": "invalid_provider"},
            )

        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert resp.headers.get("content-type", "").startswith("application/problem+json")
