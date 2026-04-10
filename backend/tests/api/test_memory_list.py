"""Unit tests for MemoryListService.list_memories + search.

Covers MEM-UI-01 and MEM-UI-02 requirements.

Uses AsyncMock for SQLAlchemy session and mocked recall/lifecycle services
to avoid SQLite/PostgreSQL divergence (JSONB @> operator).

Performance expectation: list endpoint with type filter p95 < 300ms on seeded
test data (100-1000 nodes). This is validated manually against the dev database
since SQLite test DB has different performance characteristics. Not measured in CI.
"""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from pilot_space.application.services.memory.memory_lifecycle_service import (
    MemoryLifecycleService,
)
from pilot_space.application.services.memory.memory_list_service import (
    MemoryListService,
)
from pilot_space.application.services.memory.memory_recall_service import (
    MemoryItem,
    MemoryRecallService,
    RecallResult,
)


def _make_node(
    *,
    workspace_id=None,
    node_type="note",
    label="Test Node",
    content="Some test content for the memory node",
    properties=None,
    external_id=None,
    is_deleted=False,
):
    """Build a fake GraphNodeModel-like object."""
    return SimpleNamespace(
        id=uuid4(),
        workspace_id=workspace_id or uuid4(),
        node_type=node_type,
        label=label,
        content=content,
        properties=properties or {},
        embedding=None,
        external_id=external_id,
        is_deleted=is_deleted,
        created_at=datetime.now(tz=UTC),
        updated_at=datetime.now(tz=UTC),
    )


def _mock_session_for_list(nodes, total=None):
    """Build a session mock that returns nodes for list queries.

    First execute() call -> count (scalar), second -> items (scalars().all()).
    """
    session = AsyncMock()
    actual_total = total if total is not None else len(nodes)

    call_count = 0

    async def side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # COUNT query
            return SimpleNamespace(scalar=lambda: actual_total)
        # Items query
        return SimpleNamespace(
            scalars=lambda: SimpleNamespace(all=lambda: nodes)
        )

    session.execute = AsyncMock(side_effect=side_effect)
    return session


@pytest.mark.asyncio
async def test_list_returns_paginated_items():
    """list_memories returns paginated response with correct total and has_next."""
    workspace_id = uuid4()
    nodes = [_make_node(workspace_id=workspace_id) for _ in range(2)]

    session = _mock_session_for_list(nodes, total=5)
    recall = MagicMock(spec=MemoryRecallService)
    lifecycle = MagicMock(spec=MemoryLifecycleService)

    svc = MemoryListService(session, recall, lifecycle)
    result = await svc.list_memories(workspace_id, offset=0, limit=2)

    assert result.total == 5
    assert len(result.items) == 2
    assert result.has_next is True
    assert result.offset == 0
    assert result.limit == 2


@pytest.mark.asyncio
async def test_list_without_search_returns_items_without_score():
    """Items from browse (no q) have score=None."""
    workspace_id = uuid4()
    nodes = [_make_node(workspace_id=workspace_id)]

    session = _mock_session_for_list(nodes, total=1)
    recall = MagicMock(spec=MemoryRecallService)
    lifecycle = MagicMock(spec=MemoryLifecycleService)

    svc = MemoryListService(session, recall, lifecycle)
    result = await svc.list_memories(workspace_id)

    assert len(result.items) == 1
    assert result.items[0].score is None


@pytest.mark.asyncio
async def test_semantic_search_returns_scored_results():
    """list_memories with q= calls recall service and returns items with scores."""
    workspace_id = uuid4()
    node_id = uuid4()
    nodes = [_make_node(workspace_id=workspace_id)]
    nodes[0].id = node_id  # Ensure ID matches recall result

    recall = AsyncMock(spec=MemoryRecallService)
    recall.recall = AsyncMock(
        return_value=RecallResult(
            items=[
                MemoryItem(
                    source_type="note",
                    source_id=str(uuid4()),
                    node_id=str(node_id),
                    score=0.85,
                    snippet="content",
                    created_at=datetime.now(tz=UTC).isoformat(),
                )
            ],
            cache_hit=False,
            elapsed_ms=50.0,
        )
    )

    # Session: first call = count, second = items
    session = _mock_session_for_list(nodes, total=1)
    lifecycle = MagicMock(spec=MemoryLifecycleService)

    svc = MemoryListService(session, recall, lifecycle)
    result = await svc.list_memories(workspace_id, q="test query")

    recall.recall.assert_called_once()
    assert len(result.items) == 1
    assert result.items[0].score == 0.85


@pytest.mark.asyncio
async def test_semantic_search_empty_recall_returns_empty():
    """list_memories with q= but no recall results returns empty."""
    workspace_id = uuid4()

    recall = AsyncMock(spec=MemoryRecallService)
    recall.recall = AsyncMock(
        return_value=RecallResult(items=[], cache_hit=False, elapsed_ms=10.0)
    )

    session = AsyncMock()
    lifecycle = MagicMock(spec=MemoryLifecycleService)

    svc = MemoryListService(session, recall, lifecycle)
    result = await svc.list_memories(workspace_id, q="no results query")

    assert result.total == 0
    assert len(result.items) == 0
    assert result.has_next is False


@pytest.mark.asyncio
async def test_list_content_snippet_truncated():
    """content_snippet is truncated to 200 characters."""
    workspace_id = uuid4()
    long_content = "x" * 500
    nodes = [_make_node(workspace_id=workspace_id, content=long_content)]

    session = _mock_session_for_list(nodes, total=1)
    recall = MagicMock(spec=MemoryRecallService)
    lifecycle = MagicMock(spec=MemoryLifecycleService)

    svc = MemoryListService(session, recall, lifecycle)
    result = await svc.list_memories(workspace_id)

    assert len(result.items[0].content_snippet) == 200


@pytest.mark.asyncio
async def test_list_pinned_item_has_pinned_flag():
    """Items with properties.pinned=True have pinned=True in response."""
    workspace_id = uuid4()
    nodes = [_make_node(workspace_id=workspace_id, properties={"pinned": True})]

    session = _mock_session_for_list(nodes, total=1)
    recall = MagicMock(spec=MemoryRecallService)
    lifecycle = MagicMock(spec=MemoryLifecycleService)

    svc = MemoryListService(session, recall, lifecycle)
    result = await svc.list_memories(workspace_id)

    assert result.items[0].pinned is True
