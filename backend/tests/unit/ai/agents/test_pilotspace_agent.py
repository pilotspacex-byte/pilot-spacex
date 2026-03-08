"""xfail test stubs for PilotSpaceAgent BYOK enforcement.

Phase 4 — AI Governance (AIGOV-05):
PilotSpaceAgent must enforce BYOK — workspace_id must have a WorkspaceAPIKey
row to use AI features. Env fallback to ANTHROPIC_API_KEY must be removed.

Implemented in plan 04-07 (AIGOV-05 BYOK enforcement).
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.asyncio


@pytest.mark.xfail(
    strict=False,
    reason="Phase 4 AIGOV-05: no WorkspaceAPIKey raises AINotConfiguredError — implemented in 04-07",
)
async def test_get_api_key_raises_when_no_workspace_key() -> None:
    """When no WorkspaceAPIKey row exists, PilotSpaceAgent raises AINotConfiguredError.

    BYOK enforcement: if workspace has no API key configured,
    the agent must raise AINotConfiguredError (not fall back to env ANTHROPIC_API_KEY).
    This prevents billing model violations.
    """


@pytest.mark.xfail(
    strict=False,
    reason="Phase 4 AIGOV-05: WorkspaceAPIKey present returns key string — implemented in 04-07",
)
async def test_get_api_key_succeeds_when_key_exists() -> None:
    """When WorkspaceAPIKey row is present, agent returns the decrypted key string.

    PilotSpaceAgent._get_api_key(workspace_id) queries WorkspaceAPIKey,
    decrypts the key, and returns the plaintext string for provider calls.
    """


@pytest.mark.xfail(
    strict=False,
    reason="Phase 4 AIGOV-05: workspace_id=None uses env key (system agent) — implemented in 04-07",
)
async def test_system_only_uses_env_key_when_no_workspace_id() -> None:
    """workspace_id=None uses env ANTHROPIC_API_KEY (system/background agent, no error).

    Background agents (kg_populate, indexing) run without a workspace context.
    When workspace_id=None, agent may use ANTHROPIC_API_KEY env var.
    This is the ONLY permitted env fallback — workspace-scoped requests must never fallback.
    """
