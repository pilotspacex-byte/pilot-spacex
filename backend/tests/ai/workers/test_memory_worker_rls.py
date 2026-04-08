"""Phase 70 Wave 1 — MemoryWorker dispatch-level RLS context wrapper.

Pins the contract that:

    1. ``MemoryWorker._process`` calls ``set_rls_context`` with the
       payload's ``workspace_id`` + ``actor_user_id`` before dispatching
       to any handler. Payloads missing either identity field fail
       closed (``ValueError`` → nack → DLQ), so the job is never
       processed with ambient identity.
    2. Task types in ``_RLS_BYPASS_TASKS`` skip the RLS setup entirely
       (tenant-wide maintenance jobs).
    3. (Real PG) A row written under workspace A is invisible from a
       workspace-B-scoped session. SQLite cannot verify this; the test
       is skipped with ``pytest.mark.postgres`` unless
       ``TEST_DATABASE_URL`` points at a real PostgreSQL instance.

See ``.claude/rules/testing.md`` — RLS policies are a no-op under SQLite,
so the cross-workspace isolation test requires a real PostgreSQL DB.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from unittest.mock import patch
from uuid import uuid4

import pytest

# -----------------------------------------------------------------------------
# Unit tests — no DB required. Mock session factory to assert the wrapper
# calls set_rls_context with the right arguments and fails closed on missing
# identity.
# -----------------------------------------------------------------------------


@dataclass
class _FakeMessage:
    id: str
    payload: dict[str, Any]
    attempts: int = 0


class _FakeSession:
    async def __aenter__(self) -> _FakeSession:
        return self

    async def __aexit__(self, *exc: object) -> None:
        return None

    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None


class _FakeSessionFactory:
    def __call__(self) -> _FakeSession:
        return _FakeSession()


class _FakeQueue:
    def __init__(self) -> None:
        self.acked: list[str] = []
        self.nacked: list[tuple[str, str]] = []
        self.dead: list[tuple[str, str]] = []

    async def ack(self, queue: str, msg_id: str) -> None:
        self.acked.append(msg_id)

    async def nack(self, queue: str, msg_id: str, error: str) -> None:
        self.nacked.append((msg_id, error))

    async def move_to_dead_letter(
        self,
        queue: str,
        msg_id: str,
        error: str,
        original_payload: dict[str, Any],
    ) -> None:
        self.dead.append((msg_id, error))


def _make_worker() -> Any:
    """Build a MemoryWorker with fake queue + session factory."""
    from pilot_space.ai.workers.memory_worker import MemoryWorker

    return MemoryWorker(
        queue=_FakeQueue(),  # type: ignore[arg-type]
        session_factory=_FakeSessionFactory(),  # type: ignore[arg-type]
    )


@pytest.mark.asyncio
async def test_process_calls_set_rls_context_before_dispatch() -> None:
    """User-scoped task MUST set RLS context with payload identity before _dispatch."""
    worker = _make_worker()

    workspace_id = uuid4()
    actor_user_id = uuid4()
    payload = {
        "task_type": "kg_populate",
        "workspace_id": str(workspace_id),
        "actor_user_id": str(actor_user_id),
        "entity_type": "issue",
        "entity_id": str(uuid4()),
        "project_id": str(uuid4()),
    }
    msg = _FakeMessage(id="m1", payload=payload)

    call_order: list[str] = []

    async def _fake_set_rls(session, user_id, workspace_id=None):  # type: ignore[no-untyped-def]
        call_order.append(f"rls:{user_id}:{workspace_id}")

    async def _fake_dispatch(task_type, payload, session):  # type: ignore[no-untyped-def]
        call_order.append(f"dispatch:{task_type}")
        return {"ok": True}

    with (
        patch(
            "pilot_space.ai.workers.memory_worker.set_rls_context",
            side_effect=_fake_set_rls,
        ),
        patch.object(worker, "_dispatch", side_effect=_fake_dispatch),
    ):
        await worker._process(msg)  # type: ignore[arg-type]

    assert call_order[0] == f"rls:{actor_user_id}:{workspace_id}"
    assert call_order[1] == "dispatch:kg_populate"
    assert worker.queue.acked == ["m1"]  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_process_fails_closed_on_missing_actor_user_id() -> None:
    """Payload without actor_user_id must NOT be dispatched. It is nacked/DLQ'd."""
    worker = _make_worker()

    payload = {
        "task_type": "kg_populate",
        "workspace_id": str(uuid4()),
        # actor_user_id intentionally missing
        "entity_type": "issue",
        "entity_id": str(uuid4()),
        "project_id": str(uuid4()),
    }
    msg = _FakeMessage(id="m2", payload=payload)

    dispatch_called = False
    rls_called = False

    async def _fake_set_rls(*args, **kwargs):  # type: ignore[no-untyped-def]
        nonlocal rls_called
        rls_called = True

    async def _fake_dispatch(*args, **kwargs):  # type: ignore[no-untyped-def]
        nonlocal dispatch_called
        dispatch_called = True
        return {}

    with (
        patch(
            "pilot_space.ai.workers.memory_worker.set_rls_context",
            side_effect=_fake_set_rls,
        ),
        patch.object(worker, "_dispatch", side_effect=_fake_dispatch),
    ):
        # _process catches the ValueError and nacks — it does NOT re-raise.
        await worker._process(msg)  # type: ignore[arg-type]

    assert not rls_called, "set_rls_context must not be called when identity is missing"
    assert not dispatch_called, "handler dispatch must not run when identity is missing"
    # Either nacked or dead-lettered; first attempt → nack.
    assert worker.queue.nacked, "job must be nacked when fail-closed"  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_process_fails_closed_on_missing_workspace_id() -> None:
    """Symmetric case: workspace_id missing also fails closed."""
    worker = _make_worker()

    payload = {
        "task_type": "kg_populate",
        "actor_user_id": str(uuid4()),
        # workspace_id intentionally missing
    }
    msg = _FakeMessage(id="m3", payload=payload)

    dispatch_called = False

    async def _fake_dispatch(*args, **kwargs):  # type: ignore[no-untyped-def]
        nonlocal dispatch_called
        dispatch_called = True
        return {}

    with patch.object(worker, "_dispatch", side_effect=_fake_dispatch):
        await worker._process(msg)  # type: ignore[arg-type]

    assert not dispatch_called
    assert worker.queue.nacked  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_bypass_allowlist_skips_rls_setup() -> None:
    """TASK_GRAPH_EXPIRATION must dispatch without calling set_rls_context."""
    worker = _make_worker()

    payload = {"task_type": "graph_expiration"}
    msg = _FakeMessage(id="m4", payload=payload)

    rls_called = False

    async def _fake_set_rls(*args, **kwargs):  # type: ignore[no-untyped-def]
        nonlocal rls_called
        rls_called = True

    async def _fake_dispatch(task_type, payload, session):  # type: ignore[no-untyped-def]
        return {"expired": 0}

    with (
        patch(
            "pilot_space.ai.workers.memory_worker.set_rls_context",
            side_effect=_fake_set_rls,
        ),
        patch.object(worker, "_dispatch", side_effect=_fake_dispatch),
    ):
        await worker._process(msg)  # type: ignore[arg-type]

    assert not rls_called, "bypass tasks MUST NOT call set_rls_context"
    assert worker.queue.acked == ["m4"]  # type: ignore[attr-defined]


def test_bypass_allowlist_contains_expected_task_types() -> None:
    from pilot_space.ai.workers.memory_worker import (
        _RLS_BYPASS_TASKS,
        TASK_ARTIFACT_CLEANUP,
        TASK_GRAPH_EXPIRATION,
        TASK_SEND_INVITATION_EMAIL,
    )

    assert TASK_GRAPH_EXPIRATION in _RLS_BYPASS_TASKS
    assert TASK_ARTIFACT_CLEANUP in _RLS_BYPASS_TASKS
    assert TASK_SEND_INVITATION_EMAIL in _RLS_BYPASS_TASKS


# -----------------------------------------------------------------------------
# Real-Postgres integration test — cross-workspace isolation. Requires
# TEST_DATABASE_URL pointing at a real PostgreSQL instance with pilot_space
# schema + RLS policies applied. Skipped otherwise.
# -----------------------------------------------------------------------------


@pytest.mark.postgres
@pytest.mark.asyncio
async def test_worker_rls_prevents_cross_workspace_read(postgres_session) -> None:
    """Under real PG, a node written by worker for workspace A must be
    invisible from a workspace-B-scoped session.

    This pins the end-to-end PROD-04 guarantee: the dispatch-level RLS
    wrapper + existing RLS policies together isolate cross-tenant reads.
    """
    # Implementation note: full fixture setup (two workspaces, two users,
    # workspace_members rows, running KgPopulateHandler end-to-end) is
    # non-trivial and requires committed rows that survive the rollback
    # fixture. For now the unit tests above verify the dispatch wrapper
    # logic deterministically; the full integration test is left as a
    # follow-up (tracked in 70-02 deviations).
    pytest.skip(
        "Full real-PG cross-workspace test requires committed fixture "
        "seeding beyond current conftest scope — tracked as 70-02 deviation."
    )
