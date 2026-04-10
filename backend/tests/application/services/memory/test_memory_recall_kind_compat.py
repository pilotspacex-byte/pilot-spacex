"""Phase 70-06 — GREEN: memory recall ``kind`` filter + legacy compat.

Contract:

* ``RecallPayload.kind=None`` → no filter, rows returned regardless of
  ``properties.kind`` (including legacy rows that predate the
  discriminator).
* ``RecallPayload.kind="raw"`` → rows with ``properties.kind == "raw"``
  AND legacy rows with no ``kind`` key at all (treated as raw so
  pre-Phase-70 data keeps flowing).
* ``RecallPayload.kind="summary"`` → only rows explicitly tagged
  ``properties.kind == "summary"``. Legacy rows do NOT leak into the
  summary bucket.
* Empty result returns an empty list, not an error.
"""

from __future__ import annotations

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


@pytest.fixture(autouse=True)
def _clear_inflight_locks():
    mrs_mod._inflight_locks.clear()
    yield
    mrs_mod._inflight_locks.clear()


def _scored_node(score: float, kind: str | None, label: str = "n") -> SimpleNamespace:
    props: dict[str, object] = {}
    if kind is not None:
        props["kind"] = kind
    node = SimpleNamespace(
        id=uuid4(),
        node_type="note_chunk",
        label=label,
        content=f"content-{label}",
        external_id=None,
        created_at=datetime.now(tz=UTC),
        properties=props,
    )
    return SimpleNamespace(node=node, score=score)


def _search_result(*scored_nodes: SimpleNamespace) -> SimpleNamespace:
    return SimpleNamespace(
        nodes=list(scored_nodes),
        edges=[],
        query="q",
        embedding_used=True,
    )


@pytest.mark.asyncio
async def test_recall_without_kind_filter_returns_all_rows() -> None:
    graph_search = AsyncMock()
    graph_search.execute.return_value = _search_result(
        _scored_node(0.9, "raw", "a"),
        _scored_node(0.9, "summary", "b"),
        _scored_node(0.9, None, "legacy"),
        _scored_node(0.9, "turn", "d"),
    )
    svc = MemoryRecallService(
        graph_search=graph_search, embedding=AsyncMock(), cache=None
    )

    result = await svc.recall(
        RecallPayload(workspace_id=uuid4(), query="q", k=10, min_score=0.0)
    )

    assert len(result.items) == 4


@pytest.mark.asyncio
async def test_recall_with_kind_summary_returns_only_summary_rows() -> None:
    graph_search = AsyncMock()
    graph_search.execute.return_value = _search_result(
        _scored_node(0.9, "raw", "a"),
        _scored_node(0.9, "summary", "b"),
        _scored_node(0.9, None, "legacy"),
        _scored_node(0.9, "summary", "c"),
    )
    svc = MemoryRecallService(
        graph_search=graph_search, embedding=AsyncMock(), cache=None
    )

    result = await svc.recall(
        RecallPayload(
            workspace_id=uuid4(),
            query="q",
            k=10,
            min_score=0.0,
            kind="summary",
        )
    )

    assert len(result.items) == 2
    # Legacy rows must NOT leak into the summary bucket.
    assert all("legacy" not in item.snippet for item in result.items)


@pytest.mark.asyncio
async def test_recall_with_kind_raw_includes_legacy_rows() -> None:
    graph_search = AsyncMock()
    graph_search.execute.return_value = _search_result(
        _scored_node(0.9, "raw", "a"),
        _scored_node(0.9, "summary", "b"),
        _scored_node(0.9, None, "legacy"),
        _scored_node(0.9, "turn", "d"),
    )
    svc = MemoryRecallService(
        graph_search=graph_search, embedding=AsyncMock(), cache=None
    )

    result = await svc.recall(
        RecallPayload(
            workspace_id=uuid4(),
            query="q",
            k=10,
            min_score=0.0,
            kind="raw",
        )
    )

    # "a" (raw) + "legacy" (None → treated as raw). Summary and turn dropped.
    assert len(result.items) == 2
    labels = {item.snippet for item in result.items}
    assert any("content-a" in lbl for lbl in labels)
    assert any("content-legacy" in lbl for lbl in labels)


@pytest.mark.asyncio
async def test_recall_empty_result_returns_empty_list() -> None:
    graph_search = AsyncMock()
    graph_search.execute.return_value = _search_result()
    svc = MemoryRecallService(
        graph_search=graph_search, embedding=AsyncMock(), cache=None
    )

    result = await svc.recall(
        RecallPayload(
            workspace_id=uuid4(), query="q", k=10, min_score=0.0, kind="summary"
        )
    )

    assert result.items == []
    assert result.cache_hit is False
