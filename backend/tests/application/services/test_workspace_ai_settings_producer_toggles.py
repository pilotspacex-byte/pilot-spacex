"""Phase 70-06 Task 3 — workspace memory producer toggles wiring tests.

Decision B2: import path matches the existing module name
``workspace_ai_settings`` (no ``_service`` suffix). Decision B3: mock
at the repo boundary — no real DB needed for unit tests.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from pilot_space.application.services.workspace_ai_settings import (
    WorkspaceAISettingsService,
)
from pilot_space.application.services.workspace_ai_settings_toggles import (
    ProducerToggles,
    get_producer_toggles,
    set_producer_toggle,
)

# SQLAlchemy's flag_modified requires _sa_instance_state; our fake
# workspace SimpleNamespace doesn't have it. Patch it for all set tests.
_FM_PATCH = "pilot_space.application.services.workspace_ai_settings_toggles.flag_modified"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _workspace_row(settings: dict | None = None) -> SimpleNamespace:
    """Simulate a Workspace ORM model row."""
    return SimpleNamespace(
        id=uuid4(),
        settings=settings,
    )


class _FakeSession:
    """Minimal async session stand-in for unit tests."""

    def __init__(self, workspace: SimpleNamespace | None = None) -> None:
        self._workspace = workspace
        self.flushed = False

    async def execute(self, stmt, *args, **kwargs):
        # Stub: return a fake scalar result that matches the
        # ``select(Workspace.settings)`` used by get_producer_toggles.
        class _Result:
            def scalar_one_or_none(self):
                return self._workspace.settings if self._workspace else None
        r = _Result()
        r._workspace = self._workspace
        return r

    async def get(self, model_cls, pk):
        if self._workspace and self._workspace.id == pk:
            return self._workspace
        return None

    async def flush(self):
        self.flushed = True


# ---------------------------------------------------------------------------
# Tests — ProducerToggles defaults
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_defaults_for_fresh_workspace() -> None:
    """No settings JSON → agent_turn/user_correction/pr_review_finding
    True, summarizer False."""
    ws = _workspace_row(settings=None)
    session = _FakeSession(ws)

    toggles = await get_producer_toggles(session, ws.id)  # type: ignore[arg-type]

    assert toggles.agent_turn is True
    assert toggles.user_correction is True
    assert toggles.pr_review_finding is True
    assert toggles.summarizer is False


@pytest.mark.asyncio
async def test_defaults_when_memory_producers_key_missing() -> None:
    """Settings JSON present but no ``memory_producers`` key."""
    ws = _workspace_row(settings={"ai_features": {}})
    session = _FakeSession(ws)

    toggles = await get_producer_toggles(session, ws.id)  # type: ignore[arg-type]

    assert toggles == ProducerToggles.defaults()


# ---------------------------------------------------------------------------
# Tests — set / get round-trip
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_set_persists_and_get_reflects() -> None:
    """set_producer_toggle writes to settings JSONB and subsequent get
    returns the new value."""
    ws = _workspace_row(settings={})
    session = _FakeSession(ws)

    with patch(_FM_PATCH):
        result = await set_producer_toggle(session, ws.id, "summarizer", True)  # type: ignore[arg-type]

    assert result.summarizer is True
    assert session.flushed is True

    # The workspace.settings dict has been updated in-place.
    assert ws.settings["memory_producers"]["summarizer"] is True

    # Re-read via get_producer_toggles
    toggles = await get_producer_toggles(session, ws.id)  # type: ignore[arg-type]
    assert toggles.summarizer is True


@pytest.mark.asyncio
async def test_unknown_producer_raises_validation_error() -> None:
    """Unknown producer name → ValidationError."""
    from pilot_space.domain.exceptions import ValidationError

    ws = _workspace_row(settings={})
    session = _FakeSession(ws)

    with patch(_FM_PATCH), pytest.raises(ValidationError, match="unknown memory producer"):
        await set_producer_toggle(session, ws.id, "nonexistent", True)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Tests — round-trip through WorkspaceAISettingsService thin wrapper
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_service_get_returns_defaults() -> None:
    """The service's get_producer_toggles delegates to the toggles module."""
    ws = _workspace_row(settings=None)
    session = _FakeSession(ws)
    repo = MagicMock()

    svc = WorkspaceAISettingsService(session=session, workspace_repository=repo)  # type: ignore[arg-type]
    toggles = await svc.get_producer_toggles(ws.id)

    assert toggles.agent_turn is True
    assert toggles.summarizer is False


# ---------------------------------------------------------------------------
# Tests — PATCH then producer drops when disabled
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_patch_settings_then_producer_drops_when_disabled() -> None:
    """After setting agent_turn=False, the producer records a
    ``dropped{opt_out}`` counter instead of enqueuing."""
    from pilot_space.ai.memory.producers.agent_turn_producer import (
        enqueue_agent_turn_memory,
    )

    workspace_id = uuid4()
    ws = _workspace_row(settings={})
    ws.id = workspace_id
    session = _FakeSession(ws)

    # Disable agent_turn producer
    with patch(_FM_PATCH):
        await set_producer_toggle(session, workspace_id, "agent_turn", False)  # type: ignore[arg-type]

    # Verify via get
    toggles = await get_producer_toggles(session, workspace_id)  # type: ignore[arg-type]
    assert toggles.agent_turn is False

    # Now call the producer with enabled=False — should short-circuit
    fake_queue = MagicMock()
    fake_queue.enqueue = AsyncMock()

    with patch(
        "pilot_space.ai.memory.producers.agent_turn_producer._derive_turn_index",
        AsyncMock(return_value=0),
    ):
        await enqueue_agent_turn_memory(
            queue_client=fake_queue,
            workspace_id=workspace_id,
            actor_user_id=uuid4(),
            session_id="s1",
            user_message="hi",
            assistant_text="hello",
            tools_used=[],
            metadata={},
            enabled=toggles.agent_turn,  # False
        )

    fake_queue.enqueue.assert_not_awaited()


# ---------------------------------------------------------------------------
# Tests — opt-out flag off drops enqueue (generic — maps to Wave 0 stub)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_opt_out_flag_off_drops_enqueue() -> None:
    """Same as above, but for user_correction to cover both producers."""
    from pilot_space.ai.memory.producers.user_correction_producer import (
        enqueue_user_correction_memory,
    )

    workspace_id = uuid4()
    ws = _workspace_row(settings={})
    ws.id = workspace_id
    session = _FakeSession(ws)

    with patch(_FM_PATCH):
        await set_producer_toggle(session, workspace_id, "user_correction", False)  # type: ignore[arg-type]
    toggles = await get_producer_toggles(session, workspace_id)  # type: ignore[arg-type]
    assert toggles.user_correction is False

    fake_queue = MagicMock()
    fake_queue.enqueue = AsyncMock()

    await enqueue_user_correction_memory(
        queue_client=fake_queue,
        workspace_id=workspace_id,
        actor_user_id=uuid4(),
        session_id="s1",
        subtype="deny",
        tool_name="test_tool",
        reason="test reason",
        referenced_turn_index=None,
        enabled=toggles.user_correction,  # False
    )

    fake_queue.enqueue.assert_not_awaited()
