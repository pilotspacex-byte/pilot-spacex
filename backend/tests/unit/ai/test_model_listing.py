"""Tests for ModelListingService (Phase 13-01 Task 3).

Covers:
- Empty workspace (no active configs) → empty list
- Multiple active providers → aggregated results
- Per-provider exception isolation → is_selectable=False for failed provider

All tests use xfail(strict=False) per project TDD convention (STATE.md).
Imports use lazy pattern inside test bodies to allow collection without ImportError.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

pytestmark = pytest.mark.asyncio

WORKSPACE_ID = uuid4()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_config(
    provider: str = "anthropic",
    base_url: str | None = None,
    is_active: bool = True,
) -> MagicMock:
    """Build a minimal mock AIConfiguration ORM object."""
    config = MagicMock()
    config.id = uuid4()
    config.provider = provider
    config.api_key_encrypted = "encrypted_key_value"  # pragma: allowlist secret
    config.is_active = is_active
    config.base_url = base_url
    return config


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.xfail(strict=False, reason="TDD: ModelListingService not yet implemented")
async def test_list_models_empty_workspace() -> None:
    """Workspace with no active configs returns empty list."""
    from pilot_space.ai.providers.model_listing import ModelListingService

    service = ModelListingService()
    mock_db = AsyncMock()

    with patch("pilot_space.ai.providers.model_listing.AIConfigurationRepository") as MockRepo:
        mock_repo_instance = AsyncMock()
        mock_repo_instance.get_by_workspace.return_value = []
        MockRepo.return_value = mock_repo_instance

        results = await service.list_models_for_workspace(WORKSPACE_ID, mock_db)

    assert results == []
    mock_repo_instance.get_by_workspace.assert_called_once_with(
        WORKSPACE_ID, include_inactive=False
    )


@pytest.mark.xfail(strict=False, reason="TDD: ModelListingService not yet implemented")
async def test_list_models_aggregates_providers() -> None:
    """Two active providers → items from both in result."""
    from pilot_space.ai.providers.model_listing import ModelListingService, ProviderModel

    service = ModelListingService()
    mock_db = AsyncMock()

    anthropic_config = _make_config(provider="anthropic")
    openai_config = _make_config(provider="openai")

    with (
        patch("pilot_space.ai.providers.model_listing.AIConfigurationRepository") as MockRepo,
        patch(
            "pilot_space.ai.providers.model_listing.decrypt_api_key",
            return_value="fake-api-key",
        ),
        patch.object(
            service,
            "_fetch_models",
            side_effect=[
                [("claude-3-5-haiku-20241022", "Claude 3.5 Haiku")],
                [("gpt-4o", "GPT-4o"), ("gpt-4o-mini", "GPT-4o mini")],
            ],
        ),
    ):
        mock_repo_instance = AsyncMock()
        mock_repo_instance.get_by_workspace.return_value = [
            anthropic_config,
            openai_config,
        ]
        MockRepo.return_value = mock_repo_instance

        results = await service.list_models_for_workspace(WORKSPACE_ID, mock_db)

    assert len(results) == 3  # 1 anthropic + 2 openai

    providers_in_result = {r.provider for r in results}
    assert "anthropic" in providers_in_result
    assert "openai" in providers_in_result

    # All models should be selectable
    assert all(isinstance(r, ProviderModel) for r in results)
    assert all(r.is_selectable for r in results)


@pytest.mark.xfail(strict=False, reason="TDD: ModelListingService not yet implemented")
async def test_list_models_provider_exception_isolated() -> None:
    """One provider raising → that provider gets is_selectable=False, others unaffected."""
    from pilot_space.ai.providers.model_listing import ModelListingService

    service = ModelListingService()
    mock_db = AsyncMock()

    anthropic_config = _make_config(provider="anthropic")
    google_config = _make_config(provider="google")

    with (
        patch("pilot_space.ai.providers.model_listing.AIConfigurationRepository") as MockRepo,
        patch(
            "pilot_space.ai.providers.model_listing.decrypt_api_key",
            return_value="fake-api-key",
        ),
        patch.object(
            service,
            "_fetch_models",
            side_effect=[
                [("claude-3-5-haiku-20241022", "Claude 3.5 Haiku")],  # anthropic OK
                RuntimeError("Google API unreachable"),  # google fails
            ],
        ),
    ):
        mock_repo_instance = AsyncMock()
        mock_repo_instance.get_by_workspace.return_value = [
            anthropic_config,
            google_config,
        ]
        MockRepo.return_value = mock_repo_instance

        results = await service.list_models_for_workspace(WORKSPACE_ID, mock_db)

    # anthropic succeeded → selectable
    anthropic_results = [r for r in results if r.provider == "anthropic"]
    assert len(anthropic_results) >= 1
    assert all(r.is_selectable for r in anthropic_results)

    # google failed → fallback models returned with is_selectable=False
    google_results = [r for r in results if r.provider == "google"]
    assert len(google_results) >= 1, "Fallback models should appear for failed provider"
    assert all(not r.is_selectable for r in google_results)


@pytest.mark.xfail(strict=False, reason="TDD: ModelListingService not yet implemented")
async def test_provider_model_dataclass_fields() -> None:
    """ProviderModel dataclass has required fields."""
    from pilot_space.ai.providers.model_listing import ProviderModel

    model = ProviderModel(
        provider_config_id="abc-123",
        provider="anthropic",
        model_id="claude-3-5-haiku-20241022",
        display_name="Claude 3.5 Haiku",
        is_selectable=True,
    )
    assert model.provider_config_id == "abc-123"
    assert model.provider == "anthropic"
    assert model.model_id == "claude-3-5-haiku-20241022"
    assert model.display_name == "Claude 3.5 Haiku"
    assert model.is_selectable is True


@pytest.mark.xfail(strict=False, reason="TDD: ModelListingService not yet implemented")
async def test_kimi_uses_default_base_url() -> None:
    """Kimi provider uses moonshot.cn base_url when config.base_url is None."""
    from pilot_space.ai.providers.model_listing import ModelListingService

    service = ModelListingService()
    kimi_base_url = service._default_base_url("kimi")
    assert kimi_base_url is not None
    assert "moonshot" in kimi_base_url


@pytest.mark.xfail(strict=False, reason="TDD: ModelListingService not yet implemented")
async def test_glm_uses_default_base_url() -> None:
    """GLM provider uses bigmodel.cn base_url when config.base_url is None."""
    from pilot_space.ai.providers.model_listing import ModelListingService

    service = ModelListingService()
    glm_base_url = service._default_base_url("glm")
    assert glm_base_url is not None
    assert "bigmodel" in glm_base_url
