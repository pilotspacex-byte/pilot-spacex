"""Tests for per-session model override routing (AIPR-04).

Tests resolve_model_override() and PilotSpaceAgent._get_api_key() integration
with resolved model credentials.

All tests use lazy imports to avoid ImportError during collection when
ai_chat_model_routing.py does not yet exist (TDD RED phase).

Note on patch targets: resolve_model_override() uses local imports inside the
function body. Patching must target the source module paths, not the routing
module's namespace.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest

WORKSPACE_ID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
CONFIG_ID = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
DECRYPTED_KEY = "sk-ant-test-key-12345"  # pragma: allowlist secret
ENCRYPTED_KEY = "encrypted-key-blob"

_REPO_PATH = (
    "pilot_space.infrastructure.database.repositories"
    ".ai_configuration_repository.AIConfigurationRepository"
)
_DECRYPT_PATH = "pilot_space.infrastructure.encryption.decrypt_api_key"


@pytest.mark.xfail(strict=False, reason="ai_chat_model_routing.py not yet created")
@pytest.mark.asyncio
async def test_resolve_model_override_valid():
    """Given a valid config_id, resolve_model_override returns ResolvedModelConfig."""
    from pilot_space.api.v1.routers.ai_chat_model_routing import (
        ModelOverride,
        ResolvedModelConfig,
        resolve_model_override,
    )

    model_override = ModelOverride(
        provider="anthropic",
        model="claude-sonnet-4",
        config_id=str(CONFIG_ID),
    )

    # Mock AIConfiguration object returned by repo
    mock_config = MagicMock()
    mock_config.is_active = True
    mock_config.api_key_encrypted = ENCRYPTED_KEY
    mock_config.settings = {"base_url": "https://api.anthropic.com"}

    mock_repo_instance = AsyncMock()
    mock_repo_instance.get_by_workspace_and_id.return_value = mock_config

    mock_db = MagicMock()

    with (
        patch(_REPO_PATH, return_value=mock_repo_instance),
        patch(_DECRYPT_PATH, return_value=DECRYPTED_KEY),
    ):
        result = await resolve_model_override(model_override, WORKSPACE_ID, mock_db)

    assert result is not None
    assert isinstance(result, ResolvedModelConfig)
    assert result.api_key == DECRYPTED_KEY
    assert result.model == "claude-sonnet-4"
    assert result.provider == "anthropic"
    mock_repo_instance.get_by_workspace_and_id.assert_called_once_with(WORKSPACE_ID, CONFIG_ID)


@pytest.mark.xfail(strict=False, reason="ai_chat_model_routing.py not yet created")
@pytest.mark.asyncio
async def test_resolve_model_override_invalid_config():
    """Config not found → returns None (fallback to workspace default)."""
    from pilot_space.api.v1.routers.ai_chat_model_routing import (
        ModelOverride,
        resolve_model_override,
    )

    model_override = ModelOverride(
        provider="anthropic",
        model="claude-sonnet-4",
        config_id=str(CONFIG_ID),
    )

    mock_repo_instance = AsyncMock()
    mock_repo_instance.get_by_workspace_and_id.return_value = None  # not found

    mock_db = MagicMock()

    with patch(_REPO_PATH, return_value=mock_repo_instance):
        result = await resolve_model_override(model_override, WORKSPACE_ID, mock_db)

    assert result is None


@pytest.mark.xfail(strict=False, reason="ai_chat_model_routing.py not yet created")
@pytest.mark.asyncio
async def test_resolve_model_override_none():
    """Invalid config_id UUID → returns None immediately without DB query."""
    from pilot_space.api.v1.routers.ai_chat_model_routing import (
        ModelOverride,
        resolve_model_override,
    )

    mock_db = MagicMock()
    mock_repo_instance = AsyncMock()

    override_with_bad_id = ModelOverride(
        provider="anthropic",
        model="claude-sonnet-4",
        config_id="not-a-valid-uuid",
    )

    with patch(_REPO_PATH, return_value=mock_repo_instance):
        result = await resolve_model_override(override_with_bad_id, WORKSPACE_ID, mock_db)

    assert result is None
    mock_repo_instance.get_by_workspace_and_id.assert_not_called()


@pytest.mark.xfail(strict=False, reason="ChatInput.resolved_model field not yet added")
@pytest.mark.asyncio
async def test_agent_uses_resolved_model_key():
    """When ChatInput.resolved_model is set, _get_api_key returns resolved_model.api_key."""
    from pilot_space.ai.agents.pilotspace_agent import ChatInput, PilotSpaceAgent
    from pilot_space.api.v1.routers.ai_chat_model_routing import (
        ResolvedModelConfig,
    )

    resolved = ResolvedModelConfig(
        api_key="sk-user-chosen-key",  # pragma: allowlist secret
        model="claude-opus-4",
        provider="anthropic",
        base_url=None,
    )

    # ChatInput with resolved_model (verifies field exists; _get_api_key is tested below)
    _ = ChatInput(
        message="hello",
        workspace_id=WORKSPACE_ID,
        resolved_model=resolved,
    )

    # Build a minimal agent with enough mocks to call _get_api_key
    mock_key_storage = AsyncMock()
    mock_key_storage.get_api_key.return_value = (
        "sk-workspace-default-key"  # pragma: allowlist secret
    )

    agent = PilotSpaceAgent.__new__(PilotSpaceAgent)
    agent._key_storage = mock_key_storage
    agent._resolved_model = resolved  # set by stream() before calling _get_api_key

    key = await agent._get_api_key(WORKSPACE_ID)

    assert key == "sk-user-chosen-key"  # pragma: allowlist secret
    # Workspace key storage must NOT be queried when resolved_model is set
    mock_key_storage.get_api_key.assert_not_called()
