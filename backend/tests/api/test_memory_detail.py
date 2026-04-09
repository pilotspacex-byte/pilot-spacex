"""Unit tests for MemoryListService.get_detail.

Covers MEM-UI-04 requirement.
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
from pilot_space.domain.exceptions import NotFoundError


def _mock_session_returning_node(node_or_none):
    """Build session mock for get_detail (single scalar_one_or_none)."""
    session = AsyncMock()

    class _Result:
        def scalar_one_or_none(self):
            return node_or_none

        def scalar(self):
            return node_or_none

    session.execute = AsyncMock(return_value=_Result())
    return session


@pytest.mark.asyncio
async def test_detail_returns_full_content():
    """get_detail returns full content and properties for an existing node."""
    workspace_id = uuid4()
    node_id = uuid4()
    now = datetime.now(tz=UTC)

    fake_node = SimpleNamespace(
        id=node_id,
        workspace_id=workspace_id,
        node_type="note",
        label="Test Memory",
        content="Full content of the memory node with all details.",
        properties={"kind": "raw", "pinned": False},
        embedding=[0.1] * 768,
        external_id=None,
        is_deleted=False,
        created_at=now,
        updated_at=now,
    )

    session = _mock_session_returning_node(fake_node)
    recall = MagicMock(spec=MemoryRecallService)
    lifecycle = MagicMock(spec=MemoryLifecycleService)

    svc = MemoryListService(session, recall, lifecycle)
    result = await svc.get_detail(workspace_id, node_id)

    assert result.id == node_id
    assert result.content == fake_node.content
    assert result.node_type == "note"
    assert result.kind == "raw"
    assert result.embedding_dim == 768
    assert result.pinned is False


@pytest.mark.asyncio
async def test_detail_not_found_raises():
    """get_detail raises NotFoundError for non-existent node."""
    workspace_id = uuid4()
    node_id = uuid4()

    session = _mock_session_returning_node(None)
    recall = MagicMock(spec=MemoryRecallService)
    lifecycle = MagicMock(spec=MemoryLifecycleService)

    svc = MemoryListService(session, recall, lifecycle)

    with pytest.raises(NotFoundError):
        await svc.get_detail(workspace_id, node_id)


@pytest.mark.asyncio
async def test_detail_pinned_node():
    """get_detail returns pinned=True for nodes with properties.pinned=True."""
    workspace_id = uuid4()
    node_id = uuid4()
    now = datetime.now(tz=UTC)

    fake_node = SimpleNamespace(
        id=node_id,
        workspace_id=workspace_id,
        node_type="decision",
        label="Pinned Memory",
        content="Important decision to remember.",
        properties={"pinned": True, "pinned_by": str(uuid4())},
        embedding=None,
        external_id=None,
        is_deleted=False,
        created_at=now,
        updated_at=now,
    )

    session = _mock_session_returning_node(fake_node)
    recall = MagicMock(spec=MemoryRecallService)
    lifecycle = MagicMock(spec=MemoryLifecycleService)

    svc = MemoryListService(session, recall, lifecycle)
    result = await svc.get_detail(workspace_id, node_id)

    assert result.pinned is True
    assert result.embedding_dim is None
