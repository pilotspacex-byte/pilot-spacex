"""Unit tests for pilotspace_intent_pipeline (T-016/T-017/T-018/T-019).

Covers:
    - ConfirmationBus registration, signal, timeout, deregister (T-018)
    - emit_intent_detected_events SSE format (T-017)
    - wait_for_confirmation timeout and signal paths (T-018)
    - detect_intents delegates to detection service (T-016)
    - recall_workspace_context stub returns empty list (T-016)
    - make_intent_* SSE helpers (T-017)

Feature 015: AI Workforce Platform
"""

from __future__ import annotations

import asyncio
import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from pilot_space.ai.agents.pilotspace_intent_pipeline import (
    INTENT_COMPLETED,
    INTENT_CONFIRMED,
    INTENT_DETECTED,
    INTENT_EXECUTING,
    ConfirmationBus,
    detect_intents,
    emit_intent_detected_events,
    make_intent_completed_event,
    make_intent_confirmed_event,
    make_intent_executing_event,
    recall_workspace_context,
    wait_for_confirmation,
)

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_intent(
    what: str = "Build login page",
    confidence: float = 0.85,
    why: str | None = "Users need authentication",
    source_block_id: UUID | None = None,
) -> MagicMock:
    """Create a mock WorkIntent ORM model."""
    intent = MagicMock()
    intent.id = uuid4()
    intent.what = what
    intent.why = why
    intent.confidence = confidence
    status_mock = MagicMock()
    status_mock.value = "detected"
    intent.status = status_mock
    intent.source_block_id = source_block_id
    return intent


def _parse_sse(sse_str: str) -> tuple[str, dict[str, Any]]:
    """Parse 'event: X\\ndata: {...}\\n\\n' into (event_type, data_dict)."""
    lines = sse_str.strip().splitlines()
    event_type = lines[0].split(": ", 1)[1]
    data = json.loads(lines[1].split(": ", 1)[1])
    return event_type, data


# ---------------------------------------------------------------------------
# ConfirmationBus tests (T-018)
# ---------------------------------------------------------------------------


async def test_confirmation_bus_register_returns_event() -> None:
    """register() creates and returns an asyncio.Event for session_id."""
    sid = str(uuid4())
    event = ConfirmationBus.register(sid)
    assert isinstance(event, asyncio.Event)
    assert not event.is_set()
    ConfirmationBus.deregister(sid)


async def test_confirmation_bus_signal_sets_event() -> None:
    """signal() sets the event and stores payload."""
    sid = str(uuid4())
    event = ConfirmationBus.register(sid)
    intent_id = str(uuid4())

    result = ConfirmationBus.signal(sid, intent_id=intent_id, action="confirmed")

    assert result is True
    assert event.is_set()
    payload = ConfirmationBus.get_payload(sid)
    assert payload["intent_id"] == intent_id
    assert payload["action"] == "confirmed"
    ConfirmationBus.deregister(sid)


async def test_confirmation_bus_signal_no_registration_returns_false() -> None:
    """signal() returns False if session is not registered."""
    sid = "not-registered-" + str(uuid4())
    result = ConfirmationBus.signal(sid, intent_id="x")
    assert result is False


async def test_confirmation_bus_deregister_cleans_up() -> None:
    """deregister() removes both event and payload."""
    sid = str(uuid4())
    ConfirmationBus.register(sid)
    ConfirmationBus.signal(sid, intent_id="abc")
    ConfirmationBus.deregister(sid)

    # Signal after deregister returns False (no registration)
    assert ConfirmationBus.signal(sid, intent_id="abc") is False
    assert ConfirmationBus.get_payload(sid) == {}


async def test_confirmation_bus_get_payload_unknown_returns_empty() -> None:
    """get_payload() returns empty dict for unregistered session_id."""
    assert ConfirmationBus.get_payload("ghost-session") == {}


# ---------------------------------------------------------------------------
# wait_for_confirmation tests (T-018)
# ---------------------------------------------------------------------------


async def test_wait_for_confirmation_returns_on_signal() -> None:
    """wait_for_confirmation() returns payload when signal arrives before timeout."""
    sid = str(uuid4())
    intent_id = str(uuid4())

    async def _signal_after_delay() -> None:
        await asyncio.sleep(0.05)
        ConfirmationBus.signal(sid, intent_id=intent_id, action="confirmed")

    task = asyncio.create_task(_signal_after_delay())
    payload = await wait_for_confirmation(sid, wait_secs=2.0)
    await task

    assert payload.get("intent_id") == intent_id
    assert payload.get("action") == "confirmed"


async def test_wait_for_confirmation_times_out() -> None:
    """wait_for_confirmation() returns empty dict on timeout."""
    sid = str(uuid4())
    payload = await wait_for_confirmation(sid, wait_secs=0.05)
    assert payload == {}


async def test_wait_for_confirmation_deregisters_after_timeout() -> None:
    """After timeout, session is deregistered from ConfirmationBus."""
    sid = str(uuid4())
    await wait_for_confirmation(sid, wait_secs=0.01)
    # Subsequent signal returns False (no active registration)
    assert ConfirmationBus.signal(sid, intent_id="x") is False


# ---------------------------------------------------------------------------
# emit_intent_detected_events tests (T-017)
# ---------------------------------------------------------------------------


def test_emit_intent_detected_events_format() -> None:
    """emit_intent_detected_events() produces correct SSE strings."""
    intent = _make_mock_intent(what="Create auth module", confidence=0.9)
    events = emit_intent_detected_events([intent])

    assert len(events) == 1
    event_type, data = _parse_sse(events[0])
    assert event_type == INTENT_DETECTED
    assert data["what"] == "Create auth module"
    assert data["confidence"] == pytest.approx(0.9)
    assert data["status"] == "detected"
    assert "intent_id" in data


def test_emit_intent_detected_events_multiple() -> None:
    """emit_intent_detected_events() emits one event per intent."""
    intents = [_make_mock_intent(what=f"Task {i}") for i in range(3)]
    events = emit_intent_detected_events(intents)
    assert len(events) == 3


def test_emit_intent_detected_events_empty_list() -> None:
    """emit_intent_detected_events() returns empty list for no intents."""
    events = emit_intent_detected_events([])
    assert events == []


def test_emit_intent_detected_includes_source_block_id() -> None:
    """source_block_id is serialised in SSE payload when set."""
    block_id = uuid4()
    intent = _make_mock_intent(source_block_id=block_id)
    events = emit_intent_detected_events([intent])
    _, data = _parse_sse(events[0])
    assert data["source_block_id"] == str(block_id)


def test_emit_intent_detected_null_source_block_id() -> None:
    """source_block_id is None in SSE payload when not set."""
    intent = _make_mock_intent(source_block_id=None)
    events = emit_intent_detected_events([intent])
    _, data = _parse_sse(events[0])
    assert data["source_block_id"] is None


# ---------------------------------------------------------------------------
# SSE helper functions tests (T-017)
# ---------------------------------------------------------------------------


async def test_make_intent_confirmed_event_format() -> None:
    """make_intent_confirmed_event() produces correct SSE string."""
    intent_id = str(uuid4())
    sse = make_intent_confirmed_event(intent_id)
    event_type, data = _parse_sse(sse)
    assert event_type == INTENT_CONFIRMED
    assert data["intent_id"] == intent_id


async def test_make_intent_executing_event_format() -> None:
    """make_intent_executing_event() includes intent_id and skill_name."""
    intent_id = str(uuid4())
    sse = make_intent_executing_event(intent_id, skill_name="generate-code")
    event_type, data = _parse_sse(sse)
    assert event_type == INTENT_EXECUTING
    assert data["intent_id"] == intent_id
    assert data["skill_name"] == "generate-code"


async def test_make_intent_completed_event_format() -> None:
    """make_intent_completed_event() includes artifacts list."""
    intent_id = str(uuid4())
    artifacts = [{"artifact_type": "note_block", "reference_id": str(uuid4())}]
    sse = make_intent_completed_event(intent_id, skill_name="generate-code", artifacts=artifacts)
    event_type, data = _parse_sse(sse)
    assert event_type == INTENT_COMPLETED
    assert data["artifacts"] == artifacts


async def test_make_intent_completed_event_empty_artifacts() -> None:
    """make_intent_completed_event() defaults to empty artifacts list."""
    sse = make_intent_completed_event(str(uuid4()), skill_name="test", artifacts=None)
    _, data = _parse_sse(sse)
    assert data["artifacts"] == []


# ---------------------------------------------------------------------------
# detect_intents delegate tests (T-016)
# ---------------------------------------------------------------------------


async def test_detect_intents_delegates_to_service() -> None:
    """detect_intents() calls detection_service.detect() with CHAT source."""
    mock_service = AsyncMock()
    mock_result = MagicMock()
    mock_result.intents = []
    mock_service.detect.return_value = mock_result

    workspace_id = uuid4()
    user_id = uuid4()

    result = await detect_intents(
        detection_service=mock_service,
        message="We need to build an auth system",
        workspace_id=workspace_id,
        user_id=user_id,
    )

    mock_service.detect.assert_awaited_once()
    call_args = mock_service.detect.call_args[0][0]
    assert str(call_args.workspace_id) == str(workspace_id)
    assert call_args.text == "We need to build an auth system"
    assert call_args.owner == str(user_id)
    assert result is mock_result


async def test_detect_intents_passes_source_block_id() -> None:
    """detect_intents() forwards source_block_id to payload when provided."""
    mock_service = AsyncMock()
    mock_service.detect.return_value = MagicMock(intents=[])
    block_id = uuid4()

    await detect_intents(
        detection_service=mock_service,
        message="text",
        workspace_id=uuid4(),
        user_id=uuid4(),
        source_block_id=block_id,
    )

    payload = mock_service.detect.call_args[0][0]
    assert payload.source_block_id == block_id


# ---------------------------------------------------------------------------
# recall_workspace_context stub test (T-016)
# ---------------------------------------------------------------------------


async def test_recall_workspace_context_stub_returns_empty() -> None:
    """Sprint 1 recall stub always returns empty list."""
    result = await recall_workspace_context(
        workspace_id=uuid4(),
        query="some query",
    )
    assert result == []
