"""Integration-style tests for the Sprint 1 agent loop pipeline (T-019).

Tests the full detect → SSE emit → confirm → resume chain:
    1. run_intent_pipeline_step emits correct SSE events
    2. ConfirmationBus resumes within 5s after confirm_intent_event()
    3. confirm_intent router signals the ConfirmationBus
    4. reject_intent router signals the ConfirmationBus with action='rejected'
    5. Pipeline proceeds to timeout gracefully when no confirmation arrives

These tests exercise the full observable pipeline without a real database or SDK.
They use the actual asyncio event loop to validate real timing behaviour.

Feature 015: AI Workforce Platform (T-016, T-017, T-018, T-019)
"""

from __future__ import annotations

import asyncio
import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from pilot_space.ai.agents.pilotspace_agent import PilotSpaceAgent
from pilot_space.ai.agents.pilotspace_intent_pipeline import (
    INTENT_DETECTED,
    ConfirmationBus,
    run_intent_pipeline_step,
    wait_for_confirmation,
)

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_sse(raw: str) -> tuple[str, dict[str, Any]]:
    lines = raw.strip().splitlines()
    event_type = lines[0].split(": ", 1)[1]
    data = json.loads(lines[1].split(": ", 1)[1])
    return event_type, data


def _make_mock_intent(what: str = "Build auth", confidence: float = 0.85) -> MagicMock:
    intent = MagicMock()
    intent.id = uuid4()
    intent.what = what
    intent.why = "Users need authentication"
    intent.confidence = confidence
    status_mock = MagicMock()
    status_mock.value = "detected"
    intent.status = status_mock
    intent.source_block_id = None
    return intent


def _make_detection_service(intents: list[MagicMock]) -> AsyncMock:
    """Build a mock IntentDetectionService that returns given intents."""
    service = AsyncMock()
    result = MagicMock()
    result.intents = intents
    result.total_detected = len(intents)
    service.detect.return_value = result
    return service


# ---------------------------------------------------------------------------
# T-016 + T-017: run_intent_pipeline_step emits correct SSE events
# ---------------------------------------------------------------------------


async def test_pipeline_step_no_service_returns_empty() -> None:
    """When detection_service is None, pipeline emits no events."""
    events = await run_intent_pipeline_step(
        detection_service=None,
        message="Build a login page",
        workspace_id=uuid4(),
        user_id=uuid4(),
        session_id="session-abc",
    )
    assert events == []


async def test_pipeline_step_no_workspace_id_returns_empty() -> None:
    """When workspace_id is None, pipeline skips detection."""
    service = _make_detection_service([_make_mock_intent()])
    events = await run_intent_pipeline_step(
        detection_service=service,
        message="Build auth",
        workspace_id=None,
        user_id=uuid4(),
        session_id="session-abc",
    )
    assert events == []
    service.detect.assert_not_called()


async def test_pipeline_step_no_user_id_returns_empty() -> None:
    """When user_id is None, pipeline skips detection."""
    service = _make_detection_service([_make_mock_intent()])
    events = await run_intent_pipeline_step(
        detection_service=service,
        message="Build auth",
        workspace_id=uuid4(),
        user_id=None,
        session_id="session-abc",
    )
    assert events == []


async def test_pipeline_step_no_intents_detected_returns_empty() -> None:
    """When detection finds no intents, pipeline emits no events."""
    service = _make_detection_service([])
    events = await run_intent_pipeline_step(
        detection_service=service,
        message="Hello world",
        workspace_id=uuid4(),
        user_id=uuid4(),
        session_id="session-abc",
    )
    assert events == []


async def test_pipeline_step_single_intent_emits_sse() -> None:
    """Single intent detected → one intent_detected SSE event emitted."""
    intent = _make_mock_intent(what="Implement user login", confidence=0.9)
    service = _make_detection_service([intent])

    events = await run_intent_pipeline_step(
        detection_service=service,
        message="We need user login",
        workspace_id=uuid4(),
        user_id=uuid4(),
        session_id="session-123",
    )

    assert len(events) == 1
    event_type, data = _parse_sse(events[0])
    assert event_type == INTENT_DETECTED
    assert data["what"] == "Implement user login"
    assert data["confidence"] == pytest.approx(0.9)
    assert data["status"] == "detected"
    assert "intent_id" in data


async def test_pipeline_step_multiple_intents_emits_multiple_events() -> None:
    """Multiple intents → one SSE event per intent."""
    intents = [_make_mock_intent(what=f"Task {i}") for i in range(3)]
    service = _make_detection_service(intents)

    events = await run_intent_pipeline_step(
        detection_service=service,
        message="Do these three things",
        workspace_id=uuid4(),
        user_id=uuid4(),
        session_id="session-456",
    )

    assert len(events) == 3
    for event_str in events:
        event_type, _ = _parse_sse(event_str)
        assert event_type == INTENT_DETECTED


async def test_pipeline_step_detection_exception_returns_empty() -> None:
    """If detection_service raises, pipeline swallows exception and returns empty."""
    service = AsyncMock()
    service.detect.side_effect = RuntimeError("LLM timeout")

    events = await run_intent_pipeline_step(
        detection_service=service,
        message="build login page",
        workspace_id=uuid4(),
        user_id=uuid4(),
        session_id="session-err",
    )

    assert events == []


# ---------------------------------------------------------------------------
# T-018: ConfirmationBus + wait_for_confirmation resume tests
# ---------------------------------------------------------------------------


async def test_confirmation_bus_signal_from_agent_method() -> None:
    """PilotSpaceAgent.confirm_intent_event() signals ConfirmationBus."""
    sid = f"test-session-{uuid4()}"
    intent_id = str(uuid4())

    event = ConfirmationBus.register(sid)
    assert not event.is_set()

    result = PilotSpaceAgent.confirm_intent_event(
        sid,
        intent_id=intent_id,
        action="confirmed",
    )

    assert result is True
    assert event.is_set()
    payload = ConfirmationBus.get_payload(sid)
    assert payload["intent_id"] == intent_id
    assert payload["action"] == "confirmed"
    ConfirmationBus.deregister(sid)


async def test_pipeline_resumes_within_5s_after_signal() -> None:
    """wait_for_confirmation() returns in <5s when signalled (FR-084)."""
    sid = f"resume-test-{uuid4()}"
    intent_id = str(uuid4())

    async def _confirm_after_delay() -> None:
        await asyncio.sleep(0.1)
        PilotSpaceAgent.confirm_intent_event(
            sid,
            intent_id=intent_id,
            action="confirmed",
        )

    task = asyncio.create_task(_confirm_after_delay())
    payload = await wait_for_confirmation(sid, wait_secs=5.0)
    await task

    assert payload.get("intent_id") == intent_id
    assert payload.get("action") == "confirmed"


async def test_rejection_signal_also_resumes_pipeline() -> None:
    """Rejection via confirm_intent_event(action='rejected') unblocks pipeline."""
    sid = f"reject-test-{uuid4()}"
    intent_id = str(uuid4())

    async def _reject_after_delay() -> None:
        await asyncio.sleep(0.05)
        PilotSpaceAgent.confirm_intent_event(
            sid,
            intent_id=intent_id,
            action="rejected",
        )

    task = asyncio.create_task(_reject_after_delay())
    payload = await wait_for_confirmation(sid, wait_secs=5.0)
    await task

    assert payload.get("action") == "rejected"


async def test_confirmation_timeout_proceeds_gracefully() -> None:
    """Pipeline proceeds gracefully after timeout — returns empty payload."""
    sid = f"timeout-test-{uuid4()}"
    payload = await wait_for_confirmation(sid, wait_secs=0.05)
    assert payload == {}


async def test_no_active_pipeline_signal_returns_false() -> None:
    """confirm_intent_event() returns False when no pipeline is waiting."""
    result = PilotSpaceAgent.confirm_intent_event(
        "nonexistent-session",
        intent_id="some-id",
    )
    assert result is False


async def test_pipeline_deregisters_after_resume() -> None:
    """After successful resume, session is deregistered from ConfirmationBus."""
    sid = f"deregister-test-{uuid4()}"

    async def _signal() -> None:
        await asyncio.sleep(0.02)
        ConfirmationBus.signal(sid)

    task = asyncio.create_task(_signal())
    await wait_for_confirmation(sid, wait_secs=2.0)
    await task

    # Session should be gone — further signals return False
    assert PilotSpaceAgent.confirm_intent_event(sid) is False


# ---------------------------------------------------------------------------
# T-019: Full Sprint 1 pipeline — detect → confirm → resume chain
# ---------------------------------------------------------------------------


async def test_full_sprint1_pipeline_detect_to_resume() -> None:
    """Full pipeline: detect intent → emit SSE → confirm → pipeline resumes.

    Verifies T-016 (detect), T-017 (SSE events), T-018 (resume within 5s).
    """
    sid = f"sprint1-e2e-{uuid4()}"
    ws_id = uuid4()
    user_id = uuid4()
    intent = _make_mock_intent(what="Set up CI/CD pipeline", confidence=0.95)
    detection_service = _make_detection_service([intent])

    # Step 1: T-016/T-017 — detect intents and emit SSE
    events = await run_intent_pipeline_step(
        detection_service=detection_service,
        message="We need to set up CI/CD",
        workspace_id=ws_id,
        user_id=user_id,
        session_id=sid,
    )
    assert len(events) == 1
    event_type, data = _parse_sse(events[0])
    assert event_type == INTENT_DETECTED
    assert data["what"] == "Set up CI/CD pipeline"
    detected_intent_id = data["intent_id"]

    # Step 2: T-018 — start waiting for confirmation
    async def _wait_task() -> dict[str, Any]:
        return await wait_for_confirmation(sid, wait_secs=5.0)

    # Step 3: User confirms via API (simulated via PilotSpaceAgent.confirm_intent_event)
    async def _confirm_task() -> None:
        await asyncio.sleep(0.05)
        PilotSpaceAgent.confirm_intent_event(
            sid,
            intent_id=detected_intent_id,
            action="confirmed",
        )

    confirm_task = asyncio.create_task(_confirm_task())
    wait_coro = asyncio.create_task(_wait_task())

    resume_payload = await wait_coro
    await confirm_task

    # Step 4: Verify pipeline resumed with correct payload (FR-084: <5s)
    assert resume_payload.get("intent_id") == detected_intent_id
    assert resume_payload.get("action") == "confirmed"


async def test_full_sprint1_pipeline_detect_to_reject() -> None:
    """Full pipeline: detect → emit SSE → reject → pipeline resumes with rejection."""
    sid = f"sprint1-reject-{uuid4()}"
    ws_id = uuid4()
    user_id = uuid4()
    intent = _make_mock_intent(what="Delete all test data", confidence=0.6)
    detection_service = _make_detection_service([intent])

    events = await run_intent_pipeline_step(
        detection_service=detection_service,
        message="Clean up test database",
        workspace_id=ws_id,
        user_id=user_id,
        session_id=sid,
    )
    assert len(events) == 1
    _, data = _parse_sse(events[0])
    intent_id = data["intent_id"]

    async def _wait_task() -> dict[str, Any]:
        return await wait_for_confirmation(sid, wait_secs=5.0)

    async def _reject_task() -> None:
        await asyncio.sleep(0.05)
        PilotSpaceAgent.confirm_intent_event(
            sid,
            intent_id=intent_id,
            action="rejected",
        )

    reject_task = asyncio.create_task(_reject_task())
    wait_coro = asyncio.create_task(_wait_task())

    resume_payload = await wait_coro
    await reject_task

    assert resume_payload.get("action") == "rejected"
    assert resume_payload.get("intent_id") == intent_id


async def test_full_sprint1_pipeline_timeout_proceeds() -> None:
    """Full pipeline: detect → timeout → pipeline proceeds without confirmation."""
    sid = f"sprint1-timeout-{uuid4()}"
    intent = _make_mock_intent()
    detection_service = _make_detection_service([intent])

    events = await run_intent_pipeline_step(
        detection_service=detection_service,
        message="Do something",
        workspace_id=uuid4(),
        user_id=uuid4(),
        session_id=sid,
    )
    assert len(events) == 1

    # Simulate timeout — no confirm signal arrives
    payload = await wait_for_confirmation(sid, wait_secs=0.05)
    assert payload == {}

    # Session cleaned up — no lingering registration
    assert PilotSpaceAgent.confirm_intent_event(sid) is False


async def test_pipeline_handles_concurrent_sessions() -> None:
    """Two concurrent pipelines with different session_ids are independent."""
    sid_a = f"concurrent-a-{uuid4()}"
    sid_b = f"concurrent-b-{uuid4()}"
    intent_id_a = str(uuid4())
    intent_id_b = str(uuid4())

    # Register both sessions
    event_a = ConfirmationBus.register(sid_a)
    event_b = ConfirmationBus.register(sid_b)

    # Signal only session A
    PilotSpaceAgent.confirm_intent_event(sid_a, intent_id=intent_id_a)

    assert event_a.is_set()
    assert not event_b.is_set()

    # Session B payload is empty (not signalled)
    assert ConfirmationBus.get_payload(sid_b) == {}

    # Cleanup
    ConfirmationBus.deregister(sid_a)
    ConfirmationBus.deregister(sid_b)
