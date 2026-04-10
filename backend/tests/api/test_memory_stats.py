"""Unit tests for MemoryListService.get_stats.

Covers MEM-UI-06 requirement.
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
    MemoryRecallService,
)


@pytest.mark.asyncio
async def test_stats_returns_aggregates():
    """get_stats returns per-type counts and correct totals."""
    workspace_id = uuid4()
    now = datetime.now(tz=UTC)

    session = AsyncMock()

    # Call sequence: 1=group by type, 2=pinned count, 3=last ingestion
    call_count = 0

    async def execute_side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # GROUP BY node_type query returns list of (type, count) tuples
            return SimpleNamespace(
                all=lambda: [("note", 30), ("issue", 20), ("decision", 10)]
            )
        if call_count == 2:
            # Pinned count
            return SimpleNamespace(scalar=lambda: 5)
        # Last ingestion
        return SimpleNamespace(scalar=lambda: now)

    session.execute = AsyncMock(side_effect=execute_side_effect)
    recall = MagicMock(spec=MemoryRecallService)
    lifecycle = MagicMock(spec=MemoryLifecycleService)

    svc = MemoryListService(session, recall, lifecycle)
    result = await svc.get_stats(workspace_id)

    assert result.total == 60
    assert result.by_type == {"note": 30, "issue": 20, "decision": 10}
    assert result.pinned_count == 5
    assert result.last_ingestion == now


@pytest.mark.asyncio
async def test_stats_empty_workspace():
    """get_stats returns zero counts for an empty workspace."""
    workspace_id = uuid4()

    session = AsyncMock()

    call_count = 0

    async def execute_side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return SimpleNamespace(all=list)
        if call_count == 2:
            return SimpleNamespace(scalar=lambda: 0)
        return SimpleNamespace(scalar=lambda: None)

    session.execute = AsyncMock(side_effect=execute_side_effect)
    recall = MagicMock(spec=MemoryRecallService)
    lifecycle = MagicMock(spec=MemoryLifecycleService)

    svc = MemoryListService(session, recall, lifecycle)
    result = await svc.get_stats(workspace_id)

    assert result.total == 0
    assert result.by_type == {}
    assert result.pinned_count == 0
    assert result.last_ingestion is None


@pytest.mark.asyncio
async def test_stats_pinned_count_accurate():
    """get_stats pinned_count reflects only pinned nodes."""
    workspace_id = uuid4()
    now = datetime.now(tz=UTC)

    session = AsyncMock()

    call_count = 0

    async def execute_side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return SimpleNamespace(all=lambda: [("note", 10)])
        if call_count == 2:
            return SimpleNamespace(scalar=lambda: 2)
        return SimpleNamespace(scalar=lambda: now)

    session.execute = AsyncMock(side_effect=execute_side_effect)
    recall = MagicMock(spec=MemoryRecallService)
    lifecycle = MagicMock(spec=MemoryLifecycleService)

    svc = MemoryListService(session, recall, lifecycle)
    result = await svc.get_stats(workspace_id)

    assert result.total == 10
    assert result.pinned_count == 2
