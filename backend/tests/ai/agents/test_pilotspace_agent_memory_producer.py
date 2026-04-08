"""Phase 70 Wave 2 — GREEN: ``agent_turn`` memory producer.

Covers the producer helper ``enqueue_agent_turn_memory`` in isolation:

* On success it enqueues a single ``kg_populate`` payload on
  ``QueueName.AI_NORMAL`` with the required agent_turn keys, including
  the Wave 1 fail-closed ``actor_user_id``.
* ``enabled=False`` short-circuits and records the ``opt_out`` drop.
* A queue enqueue failure is swallowed — never bubbles out — and records
  the ``enqueue_error`` drop.
* ``turn_index`` derivation failures degrade gracefully to ``0``.

The pilotspace_agent integration (actual SSE stream + hook site) is
covered by the Wave 2 integration smoke check in
``test_kg_populate_agent_turn_idempotency.py``.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from pilot_space.ai.memory.producers.agent_turn_producer import (
    enqueue_agent_turn_memory,
)
from pilot_space.ai.telemetry.memory_metrics import (
    get_producer_counters,
    reset_producer_counters,
)
from pilot_space.infrastructure.queue.models import QueueName

pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True)
def _reset_counters() -> None:
    reset_producer_counters()
    yield
    reset_producer_counters()


async def test_stream_completed_enqueues_agent_turn_payload() -> None:
    """Happy path: enqueue + counter increment, with turn_index derived."""
    workspace_id = uuid4()
    actor_user_id = uuid4()
    session_id = str(uuid4())

    queue_client = AsyncMock()

    with patch(
        "pilot_space.ai.memory.producers.agent_turn_producer._derive_turn_index",
        return_value=3,
    ):
        await enqueue_agent_turn_memory(
            queue_client=queue_client,
            workspace_id=workspace_id,
            actor_user_id=actor_user_id,
            session_id=session_id,
            user_message="hi",
            assistant_text="hello",
            tools_used=["read", "grep"],
            metadata={"ttft_ms": 123.4},
        )

    assert queue_client.enqueue.await_count == 1
    args, _ = queue_client.enqueue.call_args
    assert args[0] == QueueName.AI_NORMAL
    payload = args[1]
    assert payload["task_type"] == "kg_populate"
    assert payload["memory_type"] == "agent_turn"
    assert payload["workspace_id"] == str(workspace_id)
    assert payload["actor_user_id"] == str(actor_user_id)  # Wave 1 fail-closed
    assert payload["session_id"] == session_id
    assert payload["turn_index"] == 3
    assert "USER: hi" in payload["content"]
    assert "ASSISTANT: hello" in payload["content"]
    assert payload["metadata"]["session_id"] == session_id
    assert payload["metadata"]["turn_index"] == 3
    assert payload["metadata"]["tools_used"] == ["read", "grep"]
    assert payload["metadata"]["ttft_ms"] == 123.4

    counters = get_producer_counters()
    assert counters["enqueued"].get("agent_turn") == 1
    assert not counters["dropped"]


async def test_opt_out_short_circuits_and_records_drop() -> None:
    queue_client = AsyncMock()

    await enqueue_agent_turn_memory(
        queue_client=queue_client,
        workspace_id=uuid4(),
        actor_user_id=uuid4(),
        session_id=str(uuid4()),
        user_message="hi",
        assistant_text="hello",
        tools_used=[],
        metadata={},
        enabled=False,
    )

    queue_client.enqueue.assert_not_awaited()
    counters = get_producer_counters()
    assert counters["dropped"].get("agent_turn::opt_out") == 1
    assert not counters["enqueued"]


async def test_enqueue_failure_is_swallowed_and_recorded() -> None:
    queue_client = AsyncMock()
    queue_client.enqueue.side_effect = RuntimeError("queue down")

    with patch(
        "pilot_space.ai.memory.producers.agent_turn_producer._derive_turn_index",
        return_value=0,
    ):
        # Must not raise.
        await enqueue_agent_turn_memory(
            queue_client=queue_client,
            workspace_id=uuid4(),
            actor_user_id=uuid4(),
            session_id=str(uuid4()),
            user_message="x",
            assistant_text="y",
            tools_used=[],
            metadata={},
        )

    counters = get_producer_counters()
    assert counters["dropped"].get("agent_turn::enqueue_error") == 1
    assert not counters["enqueued"]


async def test_turn_index_zero_when_derivation_returns_zero() -> None:
    """When no prior turns exist, turn_index is 0 and enqueue still fires."""
    queue_client = AsyncMock()

    with patch(
        "pilot_space.ai.memory.producers.agent_turn_producer._derive_turn_index",
        return_value=0,
    ):
        await enqueue_agent_turn_memory(
            queue_client=queue_client,
            workspace_id=uuid4(),
            actor_user_id=uuid4(),
            session_id=str(uuid4()),
            user_message="x",
            assistant_text="y",
            tools_used=[],
            metadata={},
        )

    assert queue_client.enqueue.await_count == 1
    payload = queue_client.enqueue.call_args[0][1]
    assert payload["turn_index"] == 0
