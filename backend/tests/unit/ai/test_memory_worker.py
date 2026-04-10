"""Unit tests for MemoryWorker._dispatch — graph_embedding branch.

Tests cover:
- graph_embedding task_type routes to MemoryEmbeddingJobHandler.handle_graph_node
- memory_embedding task_type routes to MemoryEmbeddingJobHandler.handle
- Unknown task_type results in nack (via _process)
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from pilot_space.ai.workers.memory_worker import (
    TASK_GRAPH_EMBEDDING,
    TASK_MEMORY_EMBEDDING,
    MemoryWorker,
)

pytestmark = pytest.mark.asyncio

_WORKSPACE_ID = str(uuid4())
_NODE_ID = str(uuid4())
_ENTRY_ID = str(uuid4())


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


def _make_worker(
    queue: AsyncMock | None = None,
    openai_api_key: str | None = "sk-test",  # pragma: allowlist secret
    google_api_key: str | None = None,
) -> tuple[MemoryWorker, AsyncMock]:
    session = _make_session()
    if queue is None:
        queue = _make_queue()
    factory = _make_session_factory(session)
    worker = MemoryWorker(
        queue=queue,
        session_factory=factory,
        google_api_key=google_api_key,
        openai_api_key=openai_api_key,
    )
    return worker, session


_HANDLER_PATCH_PATH = (
    "pilot_space.infrastructure.queue.handlers.memory_embedding_handler.MemoryEmbeddingJobHandler"
)


class TestMemoryWorkerDispatchGraphEmbedding:
    """Verify _dispatch routes graph_embedding to handle_graph_node."""

    async def test_graph_embedding_calls_handle_graph_node(self) -> None:
        worker, session = _make_worker()

        payload = {
            "task_type": TASK_GRAPH_EMBEDDING,
            "node_id": _NODE_ID,
            "workspace_id": _WORKSPACE_ID,
        }
        expected_result = {"success": True, "node_id": _NODE_ID, "dims": 1536}

        with patch(_HANDLER_PATCH_PATH) as MockHandler:
            mock_instance = MockHandler.return_value
            mock_instance.handle_graph_node = AsyncMock(return_value=expected_result)

            result = await worker._dispatch(TASK_GRAPH_EMBEDDING, payload, session)

        MockHandler.assert_called_once_with(
            session,
            google_api_key=None,
            embedding_service=worker._embedding_service,
        )
        mock_instance.handle_graph_node.assert_awaited_once_with(payload)
        assert result == expected_result

    async def test_graph_embedding_passes_openai_key_to_embedding_service(self) -> None:
        custom_key = "sk-custom-openai-key"  # pragma: allowlist secret
        session = _make_session()
        queue = _make_queue()
        factory = _make_session_factory(session)
        worker = MemoryWorker(
            queue=queue,
            session_factory=factory,
            openai_api_key=custom_key,
        )

        # EmbeddingService is built internally with the provided openai_api_key
        assert worker._embedding_service._config.openai_api_key == custom_key

        payload = {
            "task_type": TASK_GRAPH_EMBEDDING,
            "node_id": _NODE_ID,
            "workspace_id": _WORKSPACE_ID,
        }

        with patch(_HANDLER_PATCH_PATH) as MockHandler:
            mock_instance = MockHandler.return_value
            mock_instance.handle_graph_node = AsyncMock(
                return_value={"success": True, "node_id": _NODE_ID, "dims": 1536}
            )

            await worker._dispatch(TASK_GRAPH_EMBEDDING, payload, session)

        _call_kwargs = MockHandler.call_args.kwargs
        assert _call_kwargs["embedding_service"] is worker._embedding_service


class TestMemoryWorkerDispatchMemoryEmbedding:
    """Verify _dispatch routes memory_embedding to handler.handle."""

    async def test_memory_embedding_calls_handle(self) -> None:
        worker, session = _make_worker()

        payload = {
            "task_type": TASK_MEMORY_EMBEDDING,
            "entry_id": _ENTRY_ID,
            "workspace_id": _WORKSPACE_ID,
            "table": "memory_entries",
        }
        expected_result = {"success": True, "entry_id": _ENTRY_ID, "table": "memory_entries"}

        with patch(_HANDLER_PATCH_PATH) as MockHandler:
            mock_instance = MockHandler.return_value
            mock_instance.handle = AsyncMock(return_value=expected_result)

            result = await worker._dispatch(TASK_MEMORY_EMBEDDING, payload, session)

        mock_instance.handle.assert_awaited_once_with(payload)
        assert result == expected_result


class TestMemoryWorkerProcessGraphEmbedding:
    """Verify _process acks the message on successful graph_embedding dispatch."""

    async def test_process_acks_on_success(self) -> None:
        queue = _make_queue()
        session = _make_session()
        factory = _make_session_factory(session)
        worker = MemoryWorker(
            queue=queue,
            session_factory=factory,
            openai_api_key="sk-test",  # pragma: allowlist secret
        )

        msg = MagicMock()
        msg.id = "msg-001"
        msg.payload = {
            "task_type": TASK_GRAPH_EMBEDDING,
            "node_id": _NODE_ID,
            "workspace_id": _WORKSPACE_ID,
            "actor_user_id": "00000000-0000-0000-0000-000000000001",
        }
        msg.attempts = 0

        success_result = {"success": True, "node_id": _NODE_ID, "dims": 1536}

        with patch(_HANDLER_PATCH_PATH) as MockHandler:
            mock_instance = MockHandler.return_value
            mock_instance.handle_graph_node = AsyncMock(return_value=success_result)

            await worker._process(msg)

        queue.ack.assert_awaited_once()
        queue.nack.assert_not_called()
