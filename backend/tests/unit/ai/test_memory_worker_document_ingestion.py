"""Unit tests for MemoryWorker dispatch — document_ingestion branch.

KG-01: MemoryWorker routes 'document_ingestion' task_type to DocumentIngestionHandler.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from pilot_space.ai.workers.memory_worker import MemoryWorker

pytestmark = pytest.mark.asyncio

_WORKSPACE_ID = str(uuid4())
_PROJECT_ID = str(uuid4())
_ATTACHMENT_ID = str(uuid4())


def _make_queue() -> AsyncMock:
    queue = AsyncMock()
    queue.dequeue = AsyncMock(return_value=[])
    queue.ack = AsyncMock()
    queue.nack = AsyncMock()
    queue.move_to_dead_letter = AsyncMock()
    return queue


def _make_session_factory(session: AsyncMock) -> MagicMock:
    """Build an async context-manager-compatible session factory."""
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=session)
    cm.__aexit__ = AsyncMock(return_value=False)
    return MagicMock(return_value=cm)


def _make_session() -> AsyncMock:
    session = AsyncMock()
    session.commit = AsyncMock()
    return session


def _make_worker(queue: AsyncMock | None = None) -> tuple[MemoryWorker, AsyncMock]:
    session = _make_session()
    if queue is None:
        queue = _make_queue()
    factory = _make_session_factory(session)
    worker = MemoryWorker(
        queue=queue,
        session_factory=factory,
        openai_api_key="sk-test",  # pragma: allowlist secret
    )
    return worker, session


@pytest.mark.asyncio
async def test_dispatch_document_ingestion() -> None:
    """KG-01: task_type='document_ingestion' is routed to DocumentIngestionHandler, not nacked."""
    queue = _make_queue()
    worker, session = _make_worker(queue=queue)

    payload = {
        "task_type": "document_ingestion",
        "workspace_id": _WORKSPACE_ID,
        "project_id": _PROJECT_ID,
        "attachment_id": _ATTACHMENT_ID,
    }

    with patch(
        "pilot_space.infrastructure.queue.handlers.document_ingestion_handler.DocumentIngestionHandler"
    ) as MockHandler:
        mock_handler_instance = AsyncMock()
        mock_handler_instance.handle = AsyncMock(
            return_value={"success": True, "node_ids": [], "chunks": 0, "edges": 0}
        )
        MockHandler.return_value = mock_handler_instance

        await worker._dispatch("document_ingestion", payload, session)

    MockHandler.assert_called_once()
    mock_handler_instance.handle.assert_called_once_with(payload)
    queue.nack.assert_not_called()


@pytest.mark.asyncio
async def test_unknown_task_nacked() -> None:
    """Unrecognized task_type triggers nack (regression guard — document_ingestion must be in allowlist)."""
    queue = _make_queue()
    worker, session = _make_worker(queue=queue)

    message = MagicMock()
    message.id = "msg-1"
    message.attempts = 0
    message.payload = {
        "task_type": "nonexistent_task_xyz",
        "workspace_id": _WORKSPACE_ID,
        "actor_user_id": "00000000-0000-0000-0000-000000000001",
    }

    await worker._process(message)

    queue.move_to_dead_letter.assert_called_once()
