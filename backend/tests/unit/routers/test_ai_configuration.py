"""Tests for AI Configuration router — provider registry extensions.

Covers:
- Custom/Kimi/GLM provider creation (Phase 13-01)
- base_url + display_name in responses
- GET /ai/configurations/models endpoint
- Partial provider failure isolation
- Provider key testing: _test_openai_compatible_key, _test_provider_api_key dispatcher (Phase 23-01)
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

pytestmark = pytest.mark.asyncio

WORKSPACE_ID = uuid4()
USER_ID = uuid4()
CONFIG_ID = uuid4()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_config(
    provider: str = "anthropic",
    base_url: str | None = None,
    display_name: str | None = None,
    is_active: bool = True,
) -> MagicMock:
    """Build a mock AIConfiguration ORM object."""
    config = MagicMock()
    config.id = CONFIG_ID
    config.workspace_id = WORKSPACE_ID
    config.provider = provider
    config.api_key_encrypted = "encrypted_key_value"  # pragma: allowlist secret
    config.is_active = is_active
    config.has_api_key = True
    config.settings = None
    config.usage_limits = None
    config.base_url = base_url
    config.display_name = display_name
    config.created_at = "2026-01-01T00:00:00Z"
    config.updated_at = "2026-01-01T00:00:00Z"
    return config


def _make_workspace_member(role: str = "admin") -> MagicMock:
    """Build a mock workspace member."""
    member = MagicMock()
    member.user_id = USER_ID
    member.role = MagicMock()
    member.role.__str__ = lambda _: role
    return member


def _make_workspace() -> MagicMock:
    """Build a mock workspace with an admin member."""
    workspace = MagicMock()
    workspace.members = [_make_workspace_member("admin")]
    return workspace


# ---------------------------------------------------------------------------
# Test: custom provider creation
# ---------------------------------------------------------------------------


async def test_create_custom_provider() -> None:
    """POST with provider=custom, base_url, display_name returns 201 with those fields."""
    from pilot_space.api.v1.schemas.ai_configuration import (
        AIConfigurationCreate,
        AIConfigurationResponse,
        LLMProvider,
    )

    # Schema-level check: LLMProvider.CUSTOM must exist
    assert hasattr(LLMProvider, "CUSTOM"), "LLMProvider.CUSTOM not yet defined"

    payload = AIConfigurationCreate(
        provider=LLMProvider.CUSTOM,
        api_key="sk-custom-key-xyz",  # pragma: allowlist secret
        base_url="https://example.com/v1",
        display_name="My Custom LLM",
    )
    assert payload.provider == LLMProvider.CUSTOM
    assert payload.base_url == "https://example.com/v1"
    assert payload.display_name == "My Custom LLM"

    # Response schema must include base_url + display_name
    response = AIConfigurationResponse(
        id=CONFIG_ID,
        workspace_id=WORKSPACE_ID,
        provider=LLMProvider.CUSTOM,
        is_active=True,
        has_api_key=True,
        settings=None,
        usage_limits=None,
        base_url="https://example.com/v1",
        display_name="My Custom LLM",
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )
    assert response.base_url == "https://example.com/v1"
    assert response.display_name == "My Custom LLM"


async def test_create_kimi_provider() -> None:
    """POST with provider=kimi stores successfully — no 422 on unknown enum."""
    from pilot_space.api.v1.schemas.ai_configuration import (
        AIConfigurationCreate,
        LLMProvider,
    )

    assert hasattr(LLMProvider, "KIMI"), "LLMProvider.KIMI not yet defined"

    payload = AIConfigurationCreate(
        provider=LLMProvider.KIMI,
        api_key="kimi-api-key-test-value",  # pragma: allowlist secret
    )
    assert payload.provider == LLMProvider.KIMI


async def test_create_glm_provider() -> None:
    """POST with provider=glm stores successfully."""
    from pilot_space.api.v1.schemas.ai_configuration import (
        AIConfigurationCreate,
        LLMProvider,
    )

    assert hasattr(LLMProvider, "GLM"), "LLMProvider.GLM not yet defined"

    payload = AIConfigurationCreate(
        provider=LLMProvider.GLM,
        api_key="glm-api-key-test-value",  # pragma: allowlist secret
    )
    assert payload.provider == LLMProvider.GLM


async def test_custom_provider_requires_base_url() -> None:
    """Custom provider without base_url raises ValidationError."""
    from pydantic import ValidationError

    from pilot_space.api.v1.schemas.ai_configuration import (
        AIConfigurationCreate,
        LLMProvider,
    )

    with pytest.raises(ValidationError):
        AIConfigurationCreate(
            provider=LLMProvider.CUSTOM,
            api_key="sk-custom-key-xyz",  # pragma: allowlist secret
            # base_url intentionally omitted
        )


async def test_provider_status_has_api_key_in_response() -> None:
    """GET list returns has_api_key=True when key exists."""
    from pilot_space.api.v1.schemas.ai_configuration import (
        AIConfigurationResponse,
        LLMProvider,
    )

    response = AIConfigurationResponse(
        id=CONFIG_ID,
        workspace_id=WORKSPACE_ID,
        provider=LLMProvider.ANTHROPIC,
        is_active=True,
        has_api_key=True,
        settings=None,
        usage_limits=None,
        base_url=None,
        display_name=None,
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )
    assert response.has_api_key is True


# ---------------------------------------------------------------------------
# Test: GET /models endpoint
# ---------------------------------------------------------------------------


async def test_models_endpoint_returns_list() -> None:
    """GET /models returns 200 with items list (may be empty if no active configs)."""
    from pilot_space.api.v1.schemas.ai_configuration import ModelListResponse

    # If schema exists, it should have items and total
    response = ModelListResponse(items=[], total=0)
    assert response.total == 0
    assert response.items == []


async def test_models_endpoint_partial_failure() -> None:
    """If one provider raises, others still appear in result (failure isolation)."""
    from pilot_space.ai.providers.model_listing import ModelListingService

    # Build a service whose _fetch_models raises for "openai" but returns for "anthropic"
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
                RuntimeError("OpenAI unreachable"),
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

    # anthropic models should be selectable
    anthropic_models = [r for r in results if r.provider == "anthropic"]
    assert len(anthropic_models) >= 1
    assert all(m.is_selectable for m in anthropic_models)

    # openai models should be non-selectable (fallback)
    openai_models = [r for r in results if r.provider == "openai"]
    # fallback models should be present and marked is_selectable=False
    assert all(not m.is_selectable for m in openai_models)


# ---------------------------------------------------------------------------
# Test: _test_openai_compatible_key (Phase 23-01)
# ---------------------------------------------------------------------------


async def test_openai_compatible_key_success() -> None:
    """Valid OpenAI-compatible key returns (True, 'API key is valid')."""
    import openai

    from pilot_space.application.services.ai_configuration import AIConfigurationService

    mock_client = AsyncMock()
    mock_client.models.list = AsyncMock(return_value=[])

    with patch.object(openai, "AsyncOpenAI", return_value=mock_client) as mock_ctor:
        success, message = await AIConfigurationService._test_openai_compatible_key(
            "valid-key",
            "https://api.moonshot.cn/v1",  # pragma: allowlist secret
        )

    mock_ctor.assert_called_once_with(
        api_key="valid-key",  # pragma: allowlist secret
        base_url="https://api.moonshot.cn/v1",
    )
    assert success is True
    assert message == "API key is valid"


async def test_openai_compatible_key_auth_error() -> None:
    """Invalid key returns (False, 'Invalid API key')."""
    import openai

    from pilot_space.application.services.ai_configuration import AIConfigurationService

    mock_client = AsyncMock()
    mock_client.models.list = AsyncMock(
        side_effect=openai.AuthenticationError(
            message="Invalid API key",
            response=MagicMock(status_code=401),
            body=None,
        )
    )

    with patch.object(openai, "AsyncOpenAI", return_value=mock_client):
        success, message = await AIConfigurationService._test_openai_compatible_key(
            "bad-key",
            "https://api.example.com/v1",  # pragma: allowlist secret
        )

    assert success is False
    assert message == "Invalid API key"


async def test_openai_compatible_key_rate_limit() -> None:
    """Rate-limited key returns (True, 'API key is valid (rate limited)')."""
    import openai

    from pilot_space.application.services.ai_configuration import AIConfigurationService

    mock_client = AsyncMock()
    mock_client.models.list = AsyncMock(
        side_effect=openai.RateLimitError(
            message="Rate limited",
            response=MagicMock(status_code=429),
            body=None,
        )
    )

    with patch.object(openai, "AsyncOpenAI", return_value=mock_client):
        success, message = await AIConfigurationService._test_openai_compatible_key(
            "valid-key",
            "https://api.example.com/v1",  # pragma: allowlist secret
        )

    assert success is True
    assert "rate limited" in message.lower()


# ---------------------------------------------------------------------------
# Test: _test_provider_api_key dispatcher for kimi/glm/custom (Phase 23-01)
# ---------------------------------------------------------------------------


async def test_provider_api_key_kimi_dispatches_to_compatible() -> None:
    """KIMI provider calls _test_openai_compatible_key with default base_url."""
    from pilot_space.application.services.ai_configuration import AIConfigurationService
    from pilot_space.infrastructure.database.models.ai_configuration import LLMProvider

    with patch.object(
        AIConfigurationService,
        "_test_openai_compatible_key",
        new_callable=AsyncMock,
        return_value=(True, "API key is valid"),
    ) as mock_compat:
        success, message = await AIConfigurationService._test_provider_api_key(
            LLMProvider.KIMI,
            "kimi-key",  # pragma: allowlist secret
        )

    mock_compat.assert_awaited_once_with("kimi-key", "https://api.moonshot.cn/v1")
    assert success is True


async def test_provider_api_key_kimi_custom_base_url() -> None:
    """KIMI provider uses explicit base_url when provided."""
    from pilot_space.application.services.ai_configuration import AIConfigurationService
    from pilot_space.infrastructure.database.models.ai_configuration import LLMProvider

    with patch.object(
        AIConfigurationService,
        "_test_openai_compatible_key",
        new_callable=AsyncMock,
        return_value=(True, "API key is valid"),
    ) as mock_compat:
        success, _ = await AIConfigurationService._test_provider_api_key(
            LLMProvider.KIMI,
            "kimi-key",  # pragma: allowlist secret
            base_url="https://custom.kimi.api/v1",
        )

    mock_compat.assert_awaited_once_with("kimi-key", "https://custom.kimi.api/v1")
    assert success is True


async def test_provider_api_key_glm_dispatches_to_compatible() -> None:
    """GLM provider calls _test_openai_compatible_key with default base_url."""
    from pilot_space.application.services.ai_configuration import AIConfigurationService
    from pilot_space.infrastructure.database.models.ai_configuration import LLMProvider

    with patch.object(
        AIConfigurationService,
        "_test_openai_compatible_key",
        new_callable=AsyncMock,
        return_value=(True, "API key is valid"),
    ) as mock_compat:
        success, _ = await AIConfigurationService._test_provider_api_key(
            LLMProvider.GLM,
            "glm-key",  # pragma: allowlist secret
        )

    mock_compat.assert_awaited_once_with("glm-key", "https://open.bigmodel.cn/api/paas/v4")
    assert success is True


async def test_provider_api_key_custom_dispatches_to_compatible() -> None:
    """CUSTOM provider calls _test_openai_compatible_key with provided base_url."""
    from pilot_space.application.services.ai_configuration import AIConfigurationService
    from pilot_space.infrastructure.database.models.ai_configuration import LLMProvider

    with patch.object(
        AIConfigurationService,
        "_test_openai_compatible_key",
        new_callable=AsyncMock,
        return_value=(True, "API key is valid"),
    ) as mock_compat:
        success, _ = await AIConfigurationService._test_provider_api_key(
            LLMProvider.CUSTOM,
            "custom-key",  # pragma: allowlist secret
            base_url="https://my-llm.example.com/v1",
        )

    mock_compat.assert_awaited_once_with("custom-key", "https://my-llm.example.com/v1")
    assert success is True


async def test_provider_api_key_custom_requires_base_url() -> None:
    """CUSTOM provider without base_url returns error."""
    from pilot_space.application.services.ai_configuration import AIConfigurationService
    from pilot_space.infrastructure.database.models.ai_configuration import LLMProvider

    success, message = await AIConfigurationService._test_provider_api_key(
        LLMProvider.CUSTOM,
        "custom-key",  # pragma: allowlist secret
    )

    assert success is False
    assert "base_url" in message.lower()


async def test_provider_api_key_existing_providers_unchanged() -> None:
    """Existing providers (anthropic, openai, google) still dispatch correctly."""
    from pilot_space.application.services.ai_configuration import AIConfigurationService
    from pilot_space.infrastructure.database.models.ai_configuration import LLMProvider

    with patch.object(
        AIConfigurationService,
        "_test_anthropic_key",
        new_callable=AsyncMock,
        return_value=(True, "API key is valid"),
    ) as mock_anthropic:
        await AIConfigurationService._test_provider_api_key(
            LLMProvider.ANTHROPIC, "key"
        )  # pragma: allowlist secret
    mock_anthropic.assert_awaited_once_with("key")

    with patch.object(
        AIConfigurationService,
        "_test_openai_key",
        new_callable=AsyncMock,
        return_value=(True, "API key is valid"),
    ) as mock_openai:
        await AIConfigurationService._test_provider_api_key(
            LLMProvider.OPENAI, "key"
        )  # pragma: allowlist secret
    mock_openai.assert_awaited_once_with("key")

    with patch.object(
        AIConfigurationService,
        "_test_google_key",
        new_callable=AsyncMock,
        return_value=(True, "API key is valid"),
    ) as mock_google:
        await AIConfigurationService._test_provider_api_key(
            LLMProvider.GOOGLE, "key"
        )  # pragma: allowlist secret
    mock_google.assert_awaited_once_with("key")
