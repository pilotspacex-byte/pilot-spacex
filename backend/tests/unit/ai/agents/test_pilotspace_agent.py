"""Tests for PilotSpaceAgent BYOK enforcement (AIGOV-05).

Phase 4 — AI Governance:
PilotSpaceAgent must enforce BYOK — workspace_id must have a WorkspaceAPIKey
row to use AI features. Env fallback to ANTHROPIC_API_KEY must be removed for
workspace-scoped calls.

Implemented in plan 04-02.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pilot_space.ai.exceptions import AINotConfiguredError

pytestmark = pytest.mark.asyncio


def _make_agent(key_storage=None):
    """Build a minimal PilotSpaceAgent with mocked dependencies for _get_api_key tests."""
    from pilot_space.ai.agents.pilotspace_agent import PilotSpaceAgent

    agent = PilotSpaceAgent.__new__(PilotSpaceAgent)
    agent._key_storage = key_storage
    return agent


async def test_get_api_key_raises_when_no_workspace_key() -> None:
    """When no WorkspaceAPIKey row exists, PilotSpaceAgent raises AINotConfiguredError.

    BYOK enforcement: if workspace has no API key configured,
    the agent must raise AINotConfiguredError (not fall back to env ANTHROPIC_API_KEY).
    This prevents billing model violations.
    """
    workspace_id = uuid.uuid4()

    # Key storage returns None (no key configured)
    key_storage = MagicMock()
    key_storage.get_api_key = AsyncMock(return_value=None)

    agent = _make_agent(key_storage=key_storage)

    with pytest.raises(AINotConfiguredError) as exc_info:
        await agent._get_api_key(workspace_id)

    assert exc_info.value.workspace_id == workspace_id
    # Ensure env ANTHROPIC_API_KEY was NOT used as fallback
    key_storage.get_api_key.assert_awaited_once_with(workspace_id, "anthropic")


async def test_get_api_key_succeeds_when_key_exists() -> None:
    """When WorkspaceAPIKey row is present, agent returns the decrypted key string.

    PilotSpaceAgent._get_api_key(workspace_id) queries WorkspaceAPIKey,
    decrypts the key, and returns the plaintext string for provider calls.
    """
    workspace_id = uuid.uuid4()
    expected_key = "sk-ant-test-key-abc123"

    key_storage = MagicMock()
    key_storage.get_api_key = AsyncMock(return_value=expected_key)

    agent = _make_agent(key_storage=key_storage)

    result = await agent._get_api_key(workspace_id)

    assert result == expected_key
    key_storage.get_api_key.assert_awaited_once_with(workspace_id, "anthropic")


async def test_system_only_uses_env_key_when_no_workspace_id() -> None:
    """workspace_id=None uses env ANTHROPIC_API_KEY (system/background agent, no error).

    Background agents (kg_populate, indexing) run without a workspace context.
    When workspace_id=None, agent may use ANTHROPIC_API_KEY env var.
    This is the ONLY permitted env fallback — workspace-scoped requests must never fallback.
    """
    agent = _make_agent(key_storage=None)

    env_key = "sk-ant-system-only-key"
    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": env_key}):
        result = await agent._get_api_key(None)

    assert result == env_key


async def test_system_only_raises_when_no_env_key() -> None:
    """workspace_id=None with no ANTHROPIC_API_KEY env var also raises AINotConfiguredError.

    Even for system agents, a missing key must fail explicitly rather than silently
    attempting an unauthenticated request.
    """
    agent = _make_agent(key_storage=None)

    with (
        patch.dict("os.environ", {}, clear=True),
        pytest.raises(AINotConfiguredError) as exc_info,
    ):
        await agent._get_api_key(None)

    assert exc_info.value.workspace_id is None
