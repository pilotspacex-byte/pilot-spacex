"""Unit tests for MemoryListService.bulk_action.

Covers MEM-UI-03 requirement.
"""

from __future__ import annotations

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


@pytest.mark.asyncio
async def test_bulk_pin_succeeds():
    """bulk_action(pin) delegates to lifecycle.pin for each ID."""
    workspace_id = uuid4()
    ids = [uuid4() for _ in range(3)]

    session = AsyncMock()
    recall = MagicMock(spec=MemoryRecallService)
    lifecycle = AsyncMock(spec=MemoryLifecycleService)
    lifecycle.pin = AsyncMock(return_value=None)

    svc = MemoryListService(session, recall, lifecycle)
    result = await svc.bulk_action(workspace_id, "pin", ids, actor_user_id=uuid4())

    assert result.total_processed == 3
    assert len(result.succeeded) == 3
    assert len(result.failed) == 0
    assert lifecycle.pin.call_count == 3


@pytest.mark.asyncio
async def test_bulk_forget_succeeds():
    """bulk_action(forget) delegates to lifecycle.forget for each ID."""
    workspace_id = uuid4()
    ids = [uuid4() for _ in range(2)]

    session = AsyncMock()
    recall = MagicMock(spec=MemoryRecallService)
    lifecycle = AsyncMock(spec=MemoryLifecycleService)
    lifecycle.forget = AsyncMock(return_value=None)

    svc = MemoryListService(session, recall, lifecycle)
    result = await svc.bulk_action(workspace_id, "forget", ids, actor_user_id=uuid4())

    assert result.total_processed == 2
    assert len(result.succeeded) == 2
    assert len(result.failed) == 0
    assert lifecycle.forget.call_count == 2


@pytest.mark.asyncio
async def test_bulk_partial_failure():
    """bulk_action reports failed IDs when lifecycle raises NotFoundError."""
    workspace_id = uuid4()
    good_id = uuid4()
    bad_id = uuid4()

    session = AsyncMock()
    recall = MagicMock(spec=MemoryRecallService)
    lifecycle = AsyncMock(spec=MemoryLifecycleService)

    async def pin_side_effect(payload):
        if payload.node_id == bad_id:
            raise NotFoundError(f"memory node {bad_id} not found")

    lifecycle.pin = AsyncMock(side_effect=pin_side_effect)

    svc = MemoryListService(session, recall, lifecycle)
    result = await svc.bulk_action(
        workspace_id, "pin", [good_id, bad_id], actor_user_id=uuid4()
    )

    assert result.total_processed == 2
    assert len(result.succeeded) == 1
    assert result.succeeded[0] == good_id
    assert len(result.failed) == 1
    assert result.failed[0]["id"] == str(bad_id)


@pytest.mark.asyncio
async def test_bulk_empty_ids_rejected_by_schema():
    """BulkMemoryRequest schema rejects empty memory_ids."""
    from pydantic import ValidationError

    from pilot_space.api.v1.schemas.memory import BulkMemoryRequest

    with pytest.raises(ValidationError):
        BulkMemoryRequest(action="pin", memory_ids=[])
