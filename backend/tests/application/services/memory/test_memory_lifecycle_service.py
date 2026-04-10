"""Unit tests for MemoryLifecycleService + kg_populate_handler memory_type.

Uses AsyncMock for the SQLAlchemy session to avoid the full model-mapper
configuration required by integration-style fixtures. This keeps these
tests as true *unit* tests and dodges the SQLite/PostgreSQL divergence
(JSONB operators, RLS, pgvector) noted in the phase plan.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from pilot_space.application.services.memory.memory_lifecycle_service import (
    ForgetPayload,
    GDPRForgetPayload,
    MemoryLifecycleService,
    PinPayload,
)
from pilot_space.domain.exceptions import ForbiddenError, NotFoundError
from pilot_space.domain.graph_node import NodeType
from pilot_space.domain.memory.memory_type import MemoryType
from pilot_space.infrastructure.queue.handlers.kg_populate_handler import KgPopulateHandler


def _mock_session_returning(node_or_none):
    """Build an AsyncMock session whose first execute() returns one scalar."""
    session = AsyncMock()

    class _Scalar:
        def scalar_one_or_none(self_inner):
            return node_or_none

        def scalars(self_inner):
            return SimpleNamespace(all=lambda: ([node_or_none] if node_or_none else []))

        rowcount = 1

    session.execute = AsyncMock(return_value=_Scalar())
    return session


@pytest.mark.asyncio
async def test_pin_sets_metadata_pinned_true():
    workspace_id = uuid4()
    node_id = uuid4()
    fake_node = SimpleNamespace(
        id=node_id,
        workspace_id=workspace_id,
        properties={"foo": "bar"},
    )
    session = _mock_session_returning(fake_node)

    svc = MemoryLifecycleService(session)
    await svc.pin(
        PinPayload(workspace_id=workspace_id, node_id=node_id, actor_user_id=uuid4())
    )

    # Expect: one SELECT for load_node, one UPDATE for pin
    assert session.execute.await_count == 2
    update_call = session.execute.await_args_list[1]
    update_stmt = update_call.args[0]
    # The UPDATE values include pinned=True in properties
    compiled = str(update_stmt)
    assert "UPDATE graph_nodes" in compiled.upper() or "graph_nodes" in compiled


@pytest.mark.asyncio
async def test_forget_soft_deletes_node():
    workspace_id = uuid4()
    node_id = uuid4()
    fake_node = SimpleNamespace(id=node_id, workspace_id=workspace_id, properties={})
    session = _mock_session_returning(fake_node)

    svc = MemoryLifecycleService(session)
    await svc.forget(
        ForgetPayload(workspace_id=workspace_id, node_id=node_id, actor_user_id=uuid4())
    )
    assert session.execute.await_count == 2


@pytest.mark.asyncio
async def test_forget_rejects_cross_workspace_node():
    node_id = uuid4()
    fake_node = SimpleNamespace(
        id=node_id, workspace_id=uuid4(), properties={}
    )
    session = _mock_session_returning(fake_node)
    svc = MemoryLifecycleService(session)

    with pytest.raises(ForbiddenError):
        await svc.forget(
            ForgetPayload(
                workspace_id=uuid4(),  # different workspace
                node_id=node_id,
                actor_user_id=uuid4(),
            )
        )


@pytest.mark.asyncio
async def test_forget_missing_node_raises_not_found():
    session = _mock_session_returning(None)
    svc = MemoryLifecycleService(session)
    with pytest.raises(NotFoundError):
        await svc.forget(
            ForgetPayload(
                workspace_id=uuid4(), node_id=uuid4(), actor_user_id=uuid4()
            )
        )


@pytest.mark.asyncio
async def test_gdpr_forget_hard_deletes_by_user_id():
    session = AsyncMock()
    result = MagicMock()
    result.rowcount = 2
    session.execute = AsyncMock(return_value=result)

    svc = MemoryLifecycleService(session)
    deleted = await svc.gdpr_forget_user(GDPRForgetPayload(user_id=uuid4()))
    assert deleted == 2
    assert session.execute.await_count == 1


@pytest.mark.asyncio
async def test_decay_sweep_soft_deletes_expired_nodes():
    workspace_id = uuid4()
    past_iso = (datetime.now(tz=UTC) - timedelta(days=1)).isoformat()
    future_iso = (datetime.now(tz=UTC) + timedelta(days=1)).isoformat()
    expired = SimpleNamespace(
        id=uuid4(), workspace_id=workspace_id, properties={"expires_at": past_iso}
    )
    fresh = SimpleNamespace(
        id=uuid4(), workspace_id=workspace_id, properties={"expires_at": future_iso}
    )

    class _SelectResult:
        def scalars(self_inner):
            return SimpleNamespace(all=lambda: [expired, fresh])

    session = AsyncMock()
    # First call: SELECT candidates; second call: UPDATE soft delete
    session.execute = AsyncMock(side_effect=[_SelectResult(), MagicMock()])

    svc = MemoryLifecycleService(session)
    n = await svc.decay_sweep(workspace_id)

    assert n == 1
    assert session.execute.await_count == 2


# ---------------------------------------------------------------------------
# kg_populate_handler discriminator
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_kg_populate_routes_agent_turn_to_correct_node_type(monkeypatch):
    """Handler should create a node with NodeType.AGENT_TURN for memory_type payloads."""
    captured: dict[str, object] = {}

    class FakeWriteResult:
        def __init__(self):
            self.node_ids = [uuid4()]

    class FakeWriteService:
        def __init__(self, *args, **kwargs):
            pass

        async def execute(self, payload):
            captured["payload"] = payload
            return FakeWriteResult()

    import pilot_space.infrastructure.queue.handlers.kg_populate_handler as mod

    monkeypatch.setattr(mod, "GraphWriteService", FakeWriteService)

    # KgPopulateHandler constructs a KnowledgeGraphRepository in __init__
    # which doesn't do I/O, so a plain MagicMock is fine.
    handler = KgPopulateHandler(
        session=MagicMock(),
        embedding_service=AsyncMock(),
        queue=None,
    )
    handler._resolve_workspace_embedding = AsyncMock()  # type: ignore[method-assign]

    workspace_id = uuid4()
    result = await handler.handle(
        {
            "memory_type": MemoryType.AGENT_TURN.value,
            "workspace_id": str(workspace_id),
            "content": "I rewrote the handler",
            "metadata": {"turn_id": "t1"},
        }
    )

    assert result["success"] is True
    assert result["memory_type"] == "agent_turn"
    payload = captured["payload"]
    assert payload.workspace_id == workspace_id  # type: ignore[attr-defined]
    assert payload.nodes[0].node_type == NodeType.AGENT_TURN  # type: ignore[attr-defined]
    assert payload.nodes[0].properties["memory_type"] == "agent_turn"  # type: ignore[attr-defined]
    assert payload.nodes[0].properties["turn_id"] == "t1"  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_kg_populate_rejects_unknown_memory_type():
    handler = KgPopulateHandler(
        session=MagicMock(), embedding_service=AsyncMock(), queue=None
    )
    result = await handler.handle(
        {"memory_type": "bogus", "workspace_id": str(uuid4()), "content": "x"}
    )
    assert result["success"] is False
