"""Unit tests for GraphWriteService.

Tests cover:
- Creating nodes and edges in a single batch.
- Enqueuing embedding jobs after write.
- Resolving edge endpoints by external_id.
- Returning correct node_ids and edge_ids in the result.
"""

from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest

from pilot_space.application.services.memory.graph_write_service import (
    EdgeInput,
    GraphWritePayload,
    GraphWriteResult,
    GraphWriteService,
    NodeInput,
)
from pilot_space.domain.graph_edge import EdgeType, GraphEdge
from pilot_space.domain.graph_node import GraphNode, NodeType
from pilot_space.infrastructure.queue.models import QueueName

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_persisted_node(
    workspace_id: UUID,
    *,
    label: str = "PS-1",
    external_id: UUID | None = None,
    user_id: UUID | None = None,
) -> GraphNode:
    return GraphNode.create(
        workspace_id=workspace_id,
        node_type=NodeType.ISSUE,
        label=label,
        content="test content",
        external_id=external_id,
        user_id=user_id,
    )


def _make_edge(source_id: UUID, target_id: UUID) -> GraphEdge:
    return GraphEdge(
        source_id=source_id,
        target_id=target_id,
        edge_type=EdgeType.RELATES_TO,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def workspace_id() -> UUID:
    return uuid4()


@pytest.fixture
def mock_repo() -> AsyncMock:
    repo = AsyncMock()
    repo.bulk_upsert_nodes = AsyncMock(return_value=[])
    repo.upsert_edge = AsyncMock(side_effect=lambda e: e)
    return repo


@pytest.fixture
def mock_queue() -> AsyncMock:
    queue = AsyncMock()
    queue.enqueue = AsyncMock(return_value="msg-id")
    return queue


@pytest.fixture
def mock_session() -> AsyncMock:
    session = AsyncMock()
    session.commit = AsyncMock()
    return session


@pytest.fixture
def service(
    mock_repo: AsyncMock,
    mock_queue: AsyncMock,
    mock_session: AsyncMock,
) -> GraphWriteService:
    return GraphWriteService(
        knowledge_graph_repository=mock_repo,
        queue=mock_queue,
        session=mock_session,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestGraphWriteServiceCreateNodesAndEdges:
    """Verify that nodes and edges are persisted correctly."""

    @pytest.mark.asyncio
    async def test_write_creates_nodes_and_edges(
        self,
        service: GraphWriteService,
        mock_repo: AsyncMock,
        mock_session: AsyncMock,
        workspace_id: UUID,
    ) -> None:
        """bulk_upsert_nodes and upsert_edge are called with correct data."""
        ext_a, ext_b = uuid4(), uuid4()
        node_a = _make_persisted_node(workspace_id, label="PS-1", external_id=ext_a)
        node_b = _make_persisted_node(workspace_id, label="PS-2", external_id=ext_b)
        mock_repo.bulk_upsert_nodes.return_value = [node_a, node_b]

        payload = GraphWritePayload(
            workspace_id=workspace_id,
            actor_user_id=uuid4(),
            nodes=[
                NodeInput(node_type=NodeType.ISSUE, label="PS-1", content="a", external_id=ext_a),
                NodeInput(node_type=NodeType.ISSUE, label="PS-2", content="b", external_id=ext_b),
            ],
            edges=[
                EdgeInput(
                    source_external_id=ext_a,
                    target_external_id=ext_b,
                    edge_type=EdgeType.RELATES_TO,
                )
            ],
        )
        result = await service.execute(payload)

        mock_repo.bulk_upsert_nodes.assert_awaited_once()
        assert mock_repo.upsert_edge.await_count >= 1
        mock_session.commit.assert_awaited()
        assert isinstance(result, GraphWriteResult)

    @pytest.mark.asyncio
    async def test_write_with_no_edges(
        self,
        service: GraphWriteService,
        mock_repo: AsyncMock,
        workspace_id: UUID,
    ) -> None:
        """Service succeeds with an empty edges list."""
        node = _make_persisted_node(workspace_id)
        mock_repo.bulk_upsert_nodes.return_value = [node]

        payload = GraphWritePayload(
            workspace_id=workspace_id,
            actor_user_id=uuid4(),
            nodes=[NodeInput(node_type=NodeType.ISSUE, label="PS-1", content="x")],
        )
        result = await service.execute(payload)

        assert node.id in result.node_ids
        # upsert_edge may be called by auto-detection but not for explicit edges
        assert isinstance(result.edge_ids, list)


class TestGraphWriteServiceEmbeddingEnqueue:
    """Verify embedding jobs are enqueued after a successful write."""

    @pytest.mark.asyncio
    async def test_write_enqueues_embedding_jobs(
        self,
        service: GraphWriteService,
        mock_repo: AsyncMock,
        mock_queue: AsyncMock,
        workspace_id: UUID,
    ) -> None:
        """One embedding job is enqueued per persisted node."""
        node_a = _make_persisted_node(workspace_id, label="PS-1")
        node_b = _make_persisted_node(workspace_id, label="PS-2")
        mock_repo.bulk_upsert_nodes.return_value = [node_a, node_b]

        payload = GraphWritePayload(
            workspace_id=workspace_id,
            actor_user_id=uuid4(),
            nodes=[
                NodeInput(node_type=NodeType.ISSUE, label="PS-1", content="a"),
                NodeInput(node_type=NodeType.ISSUE, label="PS-2", content="b"),
            ],
        )
        result = await service.execute(payload)

        assert result.embedding_enqueued is True
        assert mock_queue.enqueue.await_count == 2

        # Verify payload structure for first call
        first_call_args = mock_queue.enqueue.call_args_list[0]
        queue_name, job_payload = first_call_args[0]
        assert queue_name == QueueName.AI_NORMAL
        assert job_payload["task_type"] == "graph_embedding"
        assert "node_id" in job_payload
        assert "workspace_id" in job_payload

    @pytest.mark.asyncio
    async def test_write_embedding_enqueued_false_on_queue_failure(
        self,
        service: GraphWriteService,
        mock_repo: AsyncMock,
        mock_queue: AsyncMock,
        workspace_id: UUID,
    ) -> None:
        """embedding_enqueued is False when queue raises."""
        node = _make_persisted_node(workspace_id)
        mock_repo.bulk_upsert_nodes.return_value = [node]
        mock_queue.enqueue.side_effect = RuntimeError("queue unavailable")

        payload = GraphWritePayload(
            workspace_id=workspace_id,
            actor_user_id=uuid4(),
            nodes=[NodeInput(node_type=NodeType.ISSUE, label="PS-1", content="x")],
        )
        result = await service.execute(payload)

        assert result.embedding_enqueued is False


class TestGraphWriteServiceEdgeResolution:
    """Verify edge endpoint resolution by external_id."""

    @pytest.mark.asyncio
    async def test_write_resolves_edge_endpoints_by_external_id(
        self,
        service: GraphWriteService,
        mock_repo: AsyncMock,
        workspace_id: UUID,
    ) -> None:
        """external_id → node_id resolution produces correct source/target on the edge."""
        ext_source, ext_target = uuid4(), uuid4()
        node_source = _make_persisted_node(workspace_id, label="SRC", external_id=ext_source)
        node_target = _make_persisted_node(workspace_id, label="TGT", external_id=ext_target)
        mock_repo.bulk_upsert_nodes.return_value = [node_source, node_target]

        captured_edges: list[GraphEdge] = []

        async def capture_upsert_edge(edge: GraphEdge) -> GraphEdge:
            captured_edges.append(edge)
            return edge

        mock_repo.upsert_edge.side_effect = capture_upsert_edge

        payload = GraphWritePayload(
            workspace_id=workspace_id,
            actor_user_id=uuid4(),
            nodes=[
                NodeInput(
                    node_type=NodeType.ISSUE, label="SRC", content="s", external_id=ext_source
                ),
                NodeInput(
                    node_type=NodeType.ISSUE, label="TGT", content="t", external_id=ext_target
                ),
            ],
            edges=[
                EdgeInput(
                    source_external_id=ext_source,
                    target_external_id=ext_target,
                    edge_type=EdgeType.CAUSED_BY,
                    weight=0.7,
                )
            ],
        )
        await service.execute(payload)

        # Find the explicit (non-auto) edge with CAUSED_BY type
        caused_by_edges = [e for e in captured_edges if e.edge_type == EdgeType.CAUSED_BY]
        assert len(caused_by_edges) == 1
        assert caused_by_edges[0].source_id == node_source.id
        assert caused_by_edges[0].target_id == node_target.id
        assert caused_by_edges[0].weight == 0.7

    @pytest.mark.asyncio
    async def test_write_skips_edge_with_unresolvable_external_id(
        self,
        service: GraphWriteService,
        mock_repo: AsyncMock,
        workspace_id: UUID,
    ) -> None:
        """Edges referencing unknown external_ids are skipped without error."""
        node = _make_persisted_node(workspace_id)
        mock_repo.bulk_upsert_nodes.return_value = [node]

        unknown_ext = uuid4()
        payload = GraphWritePayload(
            workspace_id=workspace_id,
            actor_user_id=uuid4(),
            nodes=[NodeInput(node_type=NodeType.ISSUE, label="PS-1", content="x")],
            edges=[
                EdgeInput(
                    source_external_id=unknown_ext,  # not in batch
                    target_external_id=node.external_id,
                )
            ],
        )
        result = await service.execute(payload)

        # No crash; explicit edge skipped (upsert_edge may still be called for auto-edges)
        assert isinstance(result, GraphWriteResult)

    @pytest.mark.asyncio
    async def test_write_resolves_edge_by_direct_node_id(
        self,
        service: GraphWriteService,
        mock_repo: AsyncMock,
        workspace_id: UUID,
    ) -> None:
        """source_node_id/target_node_id take precedence over external_id lookup."""
        node_a = _make_persisted_node(workspace_id, label="A")
        node_b = _make_persisted_node(workspace_id, label="B")
        mock_repo.bulk_upsert_nodes.return_value = [node_a, node_b]

        captured_edges: list[GraphEdge] = []

        async def capture_upsert_edge(edge: GraphEdge) -> GraphEdge:
            captured_edges.append(edge)
            return edge

        mock_repo.upsert_edge.side_effect = capture_upsert_edge

        payload = GraphWritePayload(
            workspace_id=workspace_id,
            actor_user_id=uuid4(),
            nodes=[
                NodeInput(node_type=NodeType.ISSUE, label="A", content="a"),
                NodeInput(node_type=NodeType.ISSUE, label="B", content="b"),
            ],
            edges=[
                EdgeInput(
                    source_external_id=None,
                    target_external_id=None,
                    source_node_id=node_a.id,
                    target_node_id=node_b.id,
                    edge_type=EdgeType.BLOCKS,
                )
            ],
        )
        await service.execute(payload)

        blocks_edges = [e for e in captured_edges if e.edge_type == EdgeType.BLOCKS]
        assert len(blocks_edges) == 1
        assert blocks_edges[0].source_id == node_a.id
        assert blocks_edges[0].target_id == node_b.id


class TestGraphWriteServiceReturnValues:
    """Verify result contains correct ids."""

    @pytest.mark.asyncio
    async def test_write_returns_correct_ids(
        self,
        service: GraphWriteService,
        mock_repo: AsyncMock,
        workspace_id: UUID,
    ) -> None:
        """node_ids in result match persisted node ids; edge_ids list is non-empty."""
        node_a = _make_persisted_node(workspace_id, label="PS-A")
        node_b = _make_persisted_node(workspace_id, label="PS-B")
        mock_repo.bulk_upsert_nodes.return_value = [node_a, node_b]

        # upsert_edge returns its input edge so we can track what was persisted
        mock_repo.upsert_edge.side_effect = lambda edge: edge

        payload = GraphWritePayload(
            workspace_id=workspace_id,
            actor_user_id=uuid4(),
            nodes=[
                NodeInput(node_type=NodeType.ISSUE, label="PS-A", content="a"),
                NodeInput(node_type=NodeType.ISSUE, label="PS-B", content="b"),
            ],
            edges=[
                EdgeInput(
                    source_external_id=None,
                    target_external_id=None,
                    source_node_id=node_a.id,
                    target_node_id=node_b.id,
                )
            ],
        )
        result = await service.execute(payload)

        assert set(result.node_ids) == {node_a.id, node_b.id}
        # At minimum the one explicit edge should be present
        assert len(result.edge_ids) >= 1

    @pytest.mark.asyncio
    async def test_write_node_ids_ordered_by_bulk_upsert_return(
        self,
        service: GraphWriteService,
        mock_repo: AsyncMock,
        workspace_id: UUID,
    ) -> None:
        """node_ids preserve the order returned by bulk_upsert_nodes."""
        nodes = [_make_persisted_node(workspace_id, label=f"PS-{i}") for i in range(3)]
        mock_repo.bulk_upsert_nodes.return_value = nodes

        payload = GraphWritePayload(
            workspace_id=workspace_id,
            actor_user_id=uuid4(),
            nodes=[
                NodeInput(node_type=NodeType.ISSUE, label=f"PS-{i}", content=str(i))
                for i in range(3)
            ],
        )
        result = await service.execute(payload)

        assert result.node_ids == [n.id for n in nodes]


class TestGraphWriteServiceAutoCommit:
    """Verify auto_commit controls session commit/flush behavior."""

    @pytest.mark.asyncio
    async def test_auto_commit_false_flushes_but_does_not_commit(
        self,
        mock_repo: AsyncMock,
        mock_queue: AsyncMock,
        mock_session: AsyncMock,
        workspace_id: UUID,
    ) -> None:
        """With auto_commit=False, session.flush is called but commit is not."""
        service = GraphWriteService(
            knowledge_graph_repository=mock_repo,
            queue=mock_queue,
            session=mock_session,
            auto_commit=False,
        )
        node = _make_persisted_node(workspace_id)
        mock_repo.bulk_upsert_nodes.return_value = [node]

        payload = GraphWritePayload(
            workspace_id=workspace_id,
            actor_user_id=uuid4(),
            nodes=[NodeInput(node_type=NodeType.ISSUE, label="PS-1", content="x")],
        )
        await service.execute(payload)

        mock_session.flush.assert_awaited()
        mock_session.commit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_auto_commit_true_commits(
        self,
        service: GraphWriteService,
        mock_repo: AsyncMock,
        mock_session: AsyncMock,
        workspace_id: UUID,
    ) -> None:
        """Default auto_commit=True calls session.commit."""
        node = _make_persisted_node(workspace_id)
        mock_repo.bulk_upsert_nodes.return_value = [node]

        payload = GraphWritePayload(
            workspace_id=workspace_id,
            actor_user_id=uuid4(),
            nodes=[NodeInput(node_type=NodeType.ISSUE, label="PS-1", content="x")],
        )
        await service.execute(payload)

        mock_session.commit.assert_awaited()

    @pytest.mark.asyncio
    async def test_embedding_enqueued_before_commit(
        self,
        mock_repo: AsyncMock,
        mock_queue: AsyncMock,
        workspace_id: UUID,
    ) -> None:
        """Embedding jobs are enqueued before commit (C-2 fix)."""
        call_order: list[str] = []
        session = AsyncMock()
        session.flush = AsyncMock(side_effect=lambda: call_order.append("flush"))
        session.commit = AsyncMock(side_effect=lambda: call_order.append("commit"))

        mock_queue.enqueue = AsyncMock(side_effect=lambda *_args: call_order.append("enqueue"))

        service = GraphWriteService(
            knowledge_graph_repository=mock_repo,
            queue=mock_queue,
            session=session,
            auto_commit=True,
        )
        node = _make_persisted_node(workspace_id)
        mock_repo.bulk_upsert_nodes.return_value = [node]

        payload = GraphWritePayload(
            workspace_id=workspace_id,
            actor_user_id=uuid4(),
            nodes=[NodeInput(node_type=NodeType.ISSUE, label="PS-1", content="x")],
        )
        await service.execute(payload)

        flush_idx = call_order.index("flush")
        enqueue_idx = call_order.index("enqueue")
        commit_idx = call_order.index("commit")
        assert flush_idx < enqueue_idx < commit_idx


class TestGraphWriteServiceCrossBatchEdgeResolution:
    """Verify cross-batch external_id DB lookup (H-3 fix)."""

    @pytest.mark.asyncio
    async def test_edge_resolved_via_db_when_not_in_batch(
        self,
        mock_repo: AsyncMock,
        mock_queue: AsyncMock,
        mock_session: AsyncMock,
        workspace_id: UUID,
    ) -> None:
        """External ID not in current batch is resolved via DB query."""
        from unittest.mock import MagicMock

        node_a = _make_persisted_node(workspace_id, label="A")
        mock_repo.bulk_upsert_nodes.return_value = [node_a]

        # The target external_id exists in DB but not in this batch
        target_ext_id = uuid4()
        target_node_id = uuid4()

        # session.execute returns the DB lookup result
        mock_db_result = MagicMock()
        mock_db_result.scalar_one_or_none.return_value = target_node_id
        mock_session.execute = AsyncMock(return_value=mock_db_result)

        captured_edges: list[GraphEdge] = []

        async def capture(edge: GraphEdge) -> GraphEdge:
            captured_edges.append(edge)
            return edge

        mock_repo.upsert_edge.side_effect = capture

        service = GraphWriteService(
            knowledge_graph_repository=mock_repo,
            queue=mock_queue,
            session=mock_session,
        )
        payload = GraphWritePayload(
            workspace_id=workspace_id,
            actor_user_id=uuid4(),
            nodes=[NodeInput(node_type=NodeType.ISSUE, label="A", content="a")],
            edges=[
                EdgeInput(
                    source_external_id=None,
                    target_external_id=target_ext_id,
                    source_node_id=node_a.id,
                    edge_type=EdgeType.RELATES_TO,
                )
            ],
        )
        result = await service.execute(payload)

        relates_edges = [e for e in captured_edges if e.edge_type == EdgeType.RELATES_TO]
        assert len(relates_edges) >= 1
        assert relates_edges[0].target_id == target_node_id
