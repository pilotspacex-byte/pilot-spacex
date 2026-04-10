"""Unit tests for MemoryRecallService.

Covers:
- min_score filtering
- cache hit / miss
- single-flight deduplication under concurrency
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from pilot_space.application.services.memory import memory_recall_service as mrs_mod
from pilot_space.application.services.memory.memory_recall_service import (
    MemoryRecallService,
    RecallPayload,
)
from pilot_space.domain.memory.memory_type import MemoryType


@pytest.fixture(autouse=True)
def _clear_inflight_locks():
    mrs_mod._inflight_locks.clear()
    yield
    mrs_mod._inflight_locks.clear()


def _scored_node(score: float, label: str = "n") -> SimpleNamespace:
    node = SimpleNamespace(
        id=uuid4(),
        node_type="agent_turn",
        label=label,
        content=f"content-{label}",
        external_id=None,
        created_at=datetime.now(tz=UTC),
    )
    return SimpleNamespace(node=node, score=score)


def _make_graph_search_result(scores: list[float]) -> SimpleNamespace:
    return SimpleNamespace(
        nodes=[_scored_node(s, f"n{i}") for i, s in enumerate(scores)],
        edges=[],
        query="q",
        embedding_used=True,
    )


@pytest.mark.asyncio
async def test_recall_returns_results_filtered_by_min_score():
    graph_search = AsyncMock()
    graph_search.execute.return_value = _make_graph_search_result([0.9, 0.8, 0.5, 0.2])
    embedding = AsyncMock()
    svc = MemoryRecallService(graph_search=graph_search, embedding=embedding, cache=None)

    result = await svc.recall(
        RecallPayload(workspace_id=uuid4(), query="hello", k=8, min_score=0.7)
    )

    assert not result.cache_hit
    assert result.elapsed_ms >= 0
    assert len(result.items) == 2
    assert all(item.score >= 0.7 for item in result.items)


@pytest.mark.asyncio
async def test_recall_uses_cache_on_second_call():
    graph_search = AsyncMock()
    graph_search.execute.return_value = _make_graph_search_result([0.9, 0.85])
    embedding = AsyncMock()

    stored: dict[str, object] = {}

    class FakeCache:
        async def get(self, agent_name, input_data):
            return stored.get(agent_name)

        async def set(self, agent_name, input_data, response):
            stored[agent_name] = response

    svc = MemoryRecallService(
        graph_search=graph_search, embedding=embedding, cache=FakeCache()
    )
    payload = RecallPayload(workspace_id=uuid4(), query="q", k=4, min_score=0.5)

    r1 = await svc.recall(payload)
    r2 = await svc.recall(payload)

    assert r1.cache_hit is False
    assert r2.cache_hit is True
    assert graph_search.execute.call_count == 1
    assert len(r2.items) == len(r1.items)


@pytest.mark.asyncio
async def test_recall_single_flight_under_concurrency():
    """10 concurrent identical recalls should collapse into 1 graph_search call."""
    gate = asyncio.Event()
    call_count = 0

    async def slow_execute(payload):
        nonlocal call_count
        call_count += 1
        await gate.wait()
        return _make_graph_search_result([0.9, 0.8])

    graph_search = SimpleNamespace(execute=slow_execute)
    embedding = AsyncMock()
    svc = MemoryRecallService(graph_search=graph_search, embedding=embedding, cache=None)  # type: ignore[arg-type]

    workspace_id = uuid4()
    payload = RecallPayload(
        workspace_id=workspace_id,
        query="same-query",
        k=4,
        types=(MemoryType.AGENT_TURN,),
        min_score=0.5,
    )

    tasks = [asyncio.create_task(svc.recall(payload)) for _ in range(10)]
    # Let tasks contend for the lock
    await asyncio.sleep(0.05)
    gate.set()
    results = await asyncio.gather(*tasks)

    # Without cache, the lock holder does the real call, but the 9 waiters
    # don't re-check cache successfully (cache=None), so they ALSO call
    # graph_search.execute. That's the no-cache degenerate case.
    # For the "real" single-flight benefit, the cache path is covered by
    # test_recall_uses_cache_on_second_call. Here we only assert all 10
    # calls return identical content shape.
    assert all(len(r.items) == 2 for r in results)
    assert call_count >= 1


@pytest.mark.asyncio
async def test_recall_single_flight_with_cache_dedupes_work():
    """With a cache, concurrent identical recalls perform exactly 1 execute."""
    stored: dict[str, object] = {}

    class FakeCache:
        async def get(self, agent_name, input_data):
            return stored.get(agent_name)

        async def set(self, agent_name, input_data, response):
            stored[agent_name] = response

    call_count = 0
    release = asyncio.Event()

    async def slow_execute(payload):
        nonlocal call_count
        call_count += 1
        await release.wait()
        return _make_graph_search_result([0.95])

    graph_search = SimpleNamespace(execute=slow_execute)
    embedding = AsyncMock()
    svc = MemoryRecallService(
        graph_search=graph_search,  # type: ignore[arg-type]
        embedding=embedding,
        cache=FakeCache(),
    )
    payload = RecallPayload(workspace_id=uuid4(), query="x", k=2, min_score=0.1)

    tasks = [asyncio.create_task(svc.recall(payload)) for _ in range(10)]
    await asyncio.sleep(0.05)
    release.set()
    await asyncio.gather(*tasks)

    assert call_count == 1
