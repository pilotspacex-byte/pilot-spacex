"""Phase 69 latency SLO benchmarks.

Pins the two perf budgets that the ROADMAP promises:

* ``MemoryRecallService.recall()`` p95 < 200ms (cache warm)
* ``PermissionService.resolve()`` p95 < 5ms (cache warm)

Plus a unit-style assertion that the in-process hit-rate counter
reflects ``hit / (hit + miss)``.

These tests are deterministic — all I/O is mocked. They measure the
service-layer overhead only (cache lookup, dict path, single-flight
guards). The real graph-search + embedding round-trip is excluded by
design: the cache-warm path is the SLO-critical hot path.
"""

from __future__ import annotations

import statistics
import time
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest

from pilot_space.ai.telemetry.memory_metrics import (
    get_hit_rate,
    record_recall_hit,
    record_recall_miss,
    reset_metrics,
)
from pilot_space.application.services.memory import memory_recall_service as mrs_mod
from pilot_space.application.services.memory.memory_recall_service import (
    MemoryRecallService,
    RecallPayload,
)
from pilot_space.application.services.permissions.permission_cache import PermissionCache
from pilot_space.application.services.permissions.permission_service import PermissionService
from pilot_space.domain.permissions.tool_permission_mode import ToolPermissionMode

pytestmark = pytest.mark.benchmark


# ---------------------------------------------------------------------------
# Fixtures — fast, deterministic, no DB / network
# ---------------------------------------------------------------------------


def _scored_node(score: float) -> SimpleNamespace:
    node = SimpleNamespace(
        id=uuid4(),
        node_type="agent_turn",
        label="n",
        content="content",
        external_id=None,
        created_at=datetime.now(tz=UTC),
    )
    return SimpleNamespace(node=node, score=score)


def _graph_search_result() -> SimpleNamespace:
    return SimpleNamespace(
        nodes=[_scored_node(0.95), _scored_node(0.9), _scored_node(0.85)],
        edges=[],
        query="q",
        embedding_used=True,
    )


@pytest.fixture(autouse=True)
def _clear_inflight_locks_and_metrics():
    mrs_mod._inflight_locks.clear()
    reset_metrics()
    yield
    mrs_mod._inflight_locks.clear()
    reset_metrics()


class _StubCache:
    """Minimal AIResponseCache stand-in: in-memory dict, no Redis."""

    def __init__(self) -> None:
        self._store: dict[str, object] = {}

    async def get(self, agent: str, params: dict[str, object]) -> object | None:
        return self._store.get(self._key(agent, params))

    async def set(self, agent: str, params: dict[str, object], value: object) -> None:
        self._store[self._key(agent, params)] = value

    @staticmethod
    def _key(agent: str, params: dict[str, object]) -> str:
        import json

        return f"{agent}:{json.dumps(params, sort_keys=True, default=str)}"


@pytest.fixture
async def memory_recall_service_warm() -> MemoryRecallService:
    """Return a MemoryRecallService with its cache pre-warmed for one query."""
    graph_search = AsyncMock()
    graph_search.execute.return_value = _graph_search_result()
    embedding = AsyncMock()
    cache = _StubCache()
    svc = MemoryRecallService(
        graph_search=graph_search,
        embedding=embedding,
        cache=cache,  # type: ignore[arg-type]
    )
    # Warm the cache: first call is a miss; subsequent calls are hits.
    await svc.recall(
        RecallPayload(
            workspace_id=UUID("00000000-0000-0000-0000-000000000001"),
            query="warm",
        )
    )
    return svc


@pytest.fixture
async def permission_service_warm() -> tuple[PermissionService, UUID]:
    """Return a PermissionService with one tool entry pre-warmed in the LRU."""
    cache = PermissionCache()
    workspace_id = UUID("00000000-0000-0000-0000-000000000002")
    cache.set(workspace_id, "update_note", ToolPermissionMode.AUTO)
    svc = PermissionService(cache=cache, redis_client=None)
    return svc, workspace_id


# ---------------------------------------------------------------------------
# SLO tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_recall_latency_p95_under_200ms(
    memory_recall_service_warm: MemoryRecallService,
) -> None:
    """Cache-hot recall p95 must stay under 200ms."""
    payload = RecallPayload(
        workspace_id=UUID("00000000-0000-0000-0000-000000000001"),
        query="warm",
    )
    latencies: list[float] = []
    for _ in range(100):
        result = await memory_recall_service_warm.recall(payload)
        assert result.cache_hit, "expected cache-warm fixture to serve hits"
        latencies.append(result.elapsed_ms)
    p95 = statistics.quantiles(latencies, n=20)[18]
    assert p95 < 200.0, f"Recall p95={p95:.3f}ms exceeds 200ms budget"


@pytest.mark.asyncio
async def test_resolver_latency_p95_under_5ms(
    permission_service_warm: tuple[PermissionService, UUID],
) -> None:
    """Cache-hot PermissionService.resolve p95 must stay under 5ms."""
    svc, workspace_id = permission_service_warm
    latencies: list[float] = []
    for _ in range(1000):
        t0 = time.perf_counter_ns()
        mode = await svc.resolve(workspace_id, "update_note")
        latencies.append((time.perf_counter_ns() - t0) / 1_000_000.0)
        assert mode is ToolPermissionMode.AUTO
    p95 = statistics.quantiles(latencies, n=20)[18]
    assert p95 < 5.0, f"Resolver p95={p95:.4f}ms exceeds 5ms budget"


def test_hit_rate_metric_increments() -> None:
    """``get_hit_rate()`` reflects observed hit/miss ratio."""
    reset_metrics()
    for _ in range(4):
        record_recall_hit()
    for _ in range(6):
        record_recall_miss()
    assert abs(get_hit_rate() - 0.4) < 0.01
