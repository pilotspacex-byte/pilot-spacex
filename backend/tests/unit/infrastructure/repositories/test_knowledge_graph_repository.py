"""Unit tests for KnowledgeGraphRepository.

PostgreSQL-specific features (pgvector, ts_rank, recursive CTEs) are not
tested here — they require TEST_DATABASE_URL set to a real PostgreSQL instance.

All tests use SQLite-compatible operations: simple INSERT/SELECT, keyword
search via LIKE, BFS loop traversal.

A local ``test_engine`` fixture creates only the graph tables (nodes + edges)
so this test module does not depend on the full ``Base.metadata`` which
contains a raw JSONB column in pm_block_insights that crashes SQLite.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
import sqlalchemy as sa
from sqlalchemy import (
    select as _select,
    update as _update,
)
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from pilot_space.domain.graph_edge import EdgeType, GraphEdge
from pilot_space.domain.graph_node import GraphNode, NodeType
from pilot_space.infrastructure.database.models.graph_node import GraphNodeModel
from pilot_space.infrastructure.database.repositories.knowledge_graph_repository import (
    KnowledgeGraphRepository,
)

pytestmark = pytest.mark.asyncio

# ---------------------------------------------------------------------------
# Local fixtures: only create graph_nodes + graph_edges tables on SQLite
# ---------------------------------------------------------------------------

_GRAPH_METADATA = sa.MetaData()
# Copy only the two graph tables without FK constraints. SQLAlchemy's
# to_metadata() would attempt to resolve referenced tables (workspaces, users)
# which don't exist in the isolated SQLite schema. We create the columns as
# plain types — FKs are not enforced by SQLite anyway.
_GRAPH_NODE_TABLE = sa.Table(
    "graph_nodes",
    _GRAPH_METADATA,
    sa.Column("id", sa.Text, primary_key=True),
    sa.Column("workspace_id", sa.Text, nullable=False),
    sa.Column("user_id", sa.Text, nullable=True),
    sa.Column("node_type", sa.String(50), nullable=False),
    sa.Column("external_id", sa.Text, nullable=True),
    sa.Column("label", sa.String(500), nullable=False),
    sa.Column("content", sa.Text, nullable=False, default=""),
    sa.Column("properties", sa.JSON, nullable=False, default=dict),
    sa.Column("embedding", sa.Text, nullable=True),
    sa.Column("is_deleted", sa.Boolean, nullable=False, default=False),
    sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    sa.Column(
        "created_at",
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
    ),
    sa.Column(
        "updated_at",
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
        onupdate=sa.func.now(),
    ),
)
_GRAPH_EDGE_TABLE = sa.Table(
    "graph_edges",
    _GRAPH_METADATA,
    sa.Column("id", sa.Text, primary_key=True),
    sa.Column("source_id", sa.Text, nullable=False),
    sa.Column("target_id", sa.Text, nullable=False),
    sa.Column("workspace_id", sa.Text, nullable=False),
    sa.Column("edge_type", sa.String(50), nullable=False),
    sa.Column("properties", sa.JSON, nullable=False, default=dict),
    sa.Column("weight", sa.Float, nullable=False, default=0.5),
    sa.Column(
        "created_at",
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
    ),
)


@pytest.fixture
async def test_engine() -> AsyncGenerator[AsyncEngine, None]:
    """SQLite in-memory engine with only graph_nodes + graph_edges tables."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )
    async with engine.begin() as conn:
        await conn.run_sync(_GRAPH_METADATA.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(_GRAPH_METADATA.drop_all)
    await engine.dispose()


@pytest.fixture
async def db_session(test_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """Async session with rollback isolation for each test."""
    session_factory = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    async with session_factory() as session, session.begin():
        yield session


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_node(
    workspace_id: object | None = None,
    node_type: NodeType = NodeType.NOTE,
    label: str = "test node",
    content: str = "test content",
    external_id: object | None = None,
    user_id: object | None = None,
    pinned: bool = False,
) -> GraphNode:
    """Build a minimal GraphNode for testing."""
    return GraphNode.create(
        workspace_id=workspace_id or uuid4(),
        node_type=node_type,
        label=label,
        content=content,
        external_id=external_id,
        user_id=user_id,
        properties={"pinned": True} if pinned else {},
    )


def _make_edge(
    source_id: object,
    target_id: object,
    edge_type: EdgeType = EdgeType.RELATES_TO,
    weight: float = 0.5,
) -> GraphEdge:
    """Build a minimal GraphEdge for testing."""
    return GraphEdge(
        source_id=source_id,
        target_id=target_id,
        edge_type=edge_type,
        weight=weight,
    )


# ---------------------------------------------------------------------------
# upsert_node
# ---------------------------------------------------------------------------


class TestUpsertNode:
    async def test_upsert_node_creates_new(self, db_session: AsyncSession) -> None:
        """Upserting a node with no external_id creates a new row."""
        repo = KnowledgeGraphRepository(db_session)
        ws = uuid4()
        node = _make_node(workspace_id=ws, label="New node")

        result = await repo.upsert_node(node)

        assert result.id is not None
        assert result.label == "New node"
        assert result.workspace_id == ws

    async def test_upsert_node_creates_new_without_external_id(
        self, db_session: AsyncSession
    ) -> None:
        """Calling upsert twice with no external_id creates two rows."""
        repo = KnowledgeGraphRepository(db_session)
        ws = uuid4()
        node_a = _make_node(workspace_id=ws, label="Alpha")
        node_b = _make_node(workspace_id=ws, label="Beta")

        r1 = await repo.upsert_node(node_a)
        r2 = await repo.upsert_node(node_b)

        assert r1.id != r2.id

    async def test_upsert_node_updates_existing(self, db_session: AsyncSession) -> None:
        """Upserting with same external_id updates label and content."""
        repo = KnowledgeGraphRepository(db_session)
        ws = uuid4()
        ext_id = uuid4()

        first = _make_node(workspace_id=ws, label="Original", external_id=ext_id)
        await repo.upsert_node(first)

        updated = GraphNode.create(
            workspace_id=ws,
            node_type=NodeType.NOTE,
            label="Updated label",
            content="Updated content",
            external_id=ext_id,
        )
        result = await repo.upsert_node(updated)

        assert result.label == "Updated label"
        assert result.content == "Updated content"

    async def test_upsert_node_persists_properties(self, db_session: AsyncSession) -> None:
        """Properties dict is round-tripped correctly."""
        repo = KnowledgeGraphRepository(db_session)
        ws = uuid4()
        props = {"state": "open", "priority": "high"}
        node = GraphNode.create(
            workspace_id=ws,
            node_type=NodeType.ISSUE,
            label="Issue",
            content="...",
            properties=props,
        )

        result = await repo.upsert_node(node)
        assert result.properties["state"] == "open"
        assert result.properties["priority"] == "high"


# ---------------------------------------------------------------------------
# upsert_edge
# ---------------------------------------------------------------------------


class TestUpsertEdge:
    async def test_upsert_edge_creates(self, db_session: AsyncSession) -> None:
        """Upserting a new edge creates a row."""
        repo = KnowledgeGraphRepository(db_session)
        ws = uuid4()

        src_node = _make_node(workspace_id=ws, label="Source")
        tgt_node = _make_node(workspace_id=ws, label="Target")
        src = await repo.upsert_node(src_node)
        tgt = await repo.upsert_node(tgt_node)

        edge = _make_edge(src.id, tgt.id)
        result = await repo.upsert_edge(edge)

        assert result.id is not None
        assert result.source_id == src.id
        assert result.target_id == tgt.id
        assert result.edge_type == EdgeType.RELATES_TO

    async def test_upsert_edge_idempotent(self, db_session: AsyncSession) -> None:
        """Upserting the same edge twice returns same id, updates weight."""
        repo = KnowledgeGraphRepository(db_session)
        ws = uuid4()

        src_node = _make_node(workspace_id=ws)
        tgt_node = _make_node(workspace_id=ws)
        src = await repo.upsert_node(src_node)
        tgt = await repo.upsert_node(tgt_node)

        edge = _make_edge(src.id, tgt.id, weight=0.3)
        r1 = await repo.upsert_edge(edge)

        edge2 = GraphEdge(
            source_id=src.id,
            target_id=tgt.id,
            edge_type=EdgeType.RELATES_TO,
            weight=0.9,
        )
        r2 = await repo.upsert_edge(edge2)

        # Same record, updated weight
        assert r1.id == r2.id
        assert r2.weight == pytest.approx(0.9)

    async def test_upsert_edge_different_types_are_distinct(self, db_session: AsyncSession) -> None:
        """Edges with same endpoints but different types are independent."""
        repo = KnowledgeGraphRepository(db_session)
        ws = uuid4()

        src_node = _make_node(workspace_id=ws)
        tgt_node = _make_node(workspace_id=ws)
        src = await repo.upsert_node(src_node)
        tgt = await repo.upsert_node(tgt_node)

        e1 = await repo.upsert_edge(_make_edge(src.id, tgt.id, EdgeType.RELATES_TO))
        e2 = await repo.upsert_edge(_make_edge(src.id, tgt.id, EdgeType.BLOCKS))

        assert e1.id != e2.id


# ---------------------------------------------------------------------------
# get_neighbors
# ---------------------------------------------------------------------------


class TestGetNeighbors:
    async def test_get_neighbors_depth_1(self, db_session: AsyncSession) -> None:
        """Direct neighbors (depth=1) are returned."""
        repo = KnowledgeGraphRepository(db_session)
        ws = uuid4()

        n1 = await repo.upsert_node(_make_node(workspace_id=ws, label="N1"))
        n2 = await repo.upsert_node(_make_node(workspace_id=ws, label="N2"))
        n3 = await repo.upsert_node(_make_node(workspace_id=ws, label="N3"))

        await repo.upsert_edge(_make_edge(n1.id, n2.id))
        await repo.upsert_edge(_make_edge(n1.id, n3.id))

        neighbors = await repo.get_neighbors(n1.id, depth=1)
        neighbor_ids = {n.id for n in neighbors}

        assert n2.id in neighbor_ids
        assert n3.id in neighbor_ids
        assert n1.id not in neighbor_ids

    async def test_get_neighbors_depth_2(self, db_session: AsyncSession) -> None:
        """Second-hop neighbors appear when depth=2."""
        repo = KnowledgeGraphRepository(db_session)
        ws = uuid4()

        n1 = await repo.upsert_node(_make_node(workspace_id=ws, label="N1"))
        n2 = await repo.upsert_node(_make_node(workspace_id=ws, label="N2"))
        n3 = await repo.upsert_node(_make_node(workspace_id=ws, label="N3"))

        await repo.upsert_edge(_make_edge(n1.id, n2.id))
        await repo.upsert_edge(_make_edge(n2.id, n3.id))

        neighbors_d1 = await repo.get_neighbors(n1.id, depth=1)
        neighbors_d2 = await repo.get_neighbors(n1.id, depth=2)

        d1_ids = {n.id for n in neighbors_d1}
        d2_ids = {n.id for n in neighbors_d2}

        assert n3.id not in d1_ids
        assert n3.id in d2_ids

    async def test_get_neighbors_with_edge_type_filter(self, db_session: AsyncSession) -> None:
        """Edge type filter restricts traversal correctly."""
        repo = KnowledgeGraphRepository(db_session)
        ws = uuid4()

        n1 = await repo.upsert_node(_make_node(workspace_id=ws))
        n2 = await repo.upsert_node(_make_node(workspace_id=ws, label="BLOCKS target"))
        n3 = await repo.upsert_node(_make_node(workspace_id=ws, label="RELATES target"))

        await repo.upsert_edge(_make_edge(n1.id, n2.id, EdgeType.BLOCKS))
        await repo.upsert_edge(_make_edge(n1.id, n3.id, EdgeType.RELATES_TO))

        neighbors = await repo.get_neighbors(n1.id, edge_types=[EdgeType.BLOCKS], depth=1)
        ids = {n.id for n in neighbors}

        assert n2.id in ids
        assert n3.id not in ids

    async def test_get_neighbors_empty_for_isolated_node(self, db_session: AsyncSession) -> None:
        """Isolated node returns empty list."""
        repo = KnowledgeGraphRepository(db_session)
        ws = uuid4()
        isolated = await repo.upsert_node(_make_node(workspace_id=ws))

        result = await repo.get_neighbors(isolated.id, depth=1)
        assert result == []


# ---------------------------------------------------------------------------
# hybrid_search
# ---------------------------------------------------------------------------


class TestHybridSearch:
    async def test_hybrid_search_keyword_only(self, db_session: AsyncSession) -> None:
        """SQLite keyword search returns matching nodes."""
        repo = KnowledgeGraphRepository(db_session)
        ws = uuid4()

        n1 = await repo.upsert_node(
            _make_node(workspace_id=ws, label="auth service", content="login oauth")
        )
        n2 = await repo.upsert_node(
            _make_node(workspace_id=ws, label="billing service", content="stripe payments")
        )

        results = await repo.hybrid_search(
            query_embedding=None,
            query_text="auth",
            workspace_id=ws,
            limit=10,
        )

        result_ids = {sn.node.id for sn in results}
        assert n1.id in result_ids
        assert n2.id not in result_ids

    async def test_hybrid_search_returns_scored_nodes(self, db_session: AsyncSession) -> None:
        """ScoredNode fields are populated."""
        repo = KnowledgeGraphRepository(db_session)
        ws = uuid4()
        await repo.upsert_node(
            _make_node(workspace_id=ws, label="payment gateway", content="stripe api")
        )

        results = await repo.hybrid_search(
            query_embedding=None,
            query_text="payment",
            workspace_id=ws,
        )

        assert len(results) >= 1
        sn = results[0]
        assert 0.0 <= sn.score <= 2.0
        assert sn.recency_score > 0.0

    async def test_hybrid_search_respects_node_type_filter(self, db_session: AsyncSession) -> None:
        """node_types filter scopes results."""
        repo = KnowledgeGraphRepository(db_session)
        ws = uuid4()

        issue_node = await repo.upsert_node(
            _make_node(
                workspace_id=ws, node_type=NodeType.ISSUE, label="deploy issue", content="deploy"
            )
        )
        note_node = await repo.upsert_node(
            _make_node(
                workspace_id=ws, node_type=NodeType.NOTE, label="deploy note", content="deploy"
            )
        )

        results = await repo.hybrid_search(
            query_embedding=None,
            query_text="deploy",
            workspace_id=ws,
            node_types=[NodeType.ISSUE],
        )
        result_ids = {sn.node.id for sn in results}

        assert issue_node.id in result_ids
        assert note_node.id not in result_ids

    async def test_hybrid_search_workspace_isolation(self, db_session: AsyncSession) -> None:
        """Nodes in another workspace are not returned."""
        repo = KnowledgeGraphRepository(db_session)
        ws_a = uuid4()
        ws_b = uuid4()

        await repo.upsert_node(_make_node(workspace_id=ws_a, label="search me", content="findme"))
        await repo.upsert_node(_make_node(workspace_id=ws_b, label="search me", content="findme"))

        results = await repo.hybrid_search(
            query_embedding=None,
            query_text="findme",
            workspace_id=ws_a,
        )

        for sn in results:
            assert sn.node.workspace_id == ws_a


# ---------------------------------------------------------------------------
# get_subgraph
# ---------------------------------------------------------------------------


class TestGetSubgraph:
    async def test_get_subgraph_returns_root_and_neighbors(self, db_session: AsyncSession) -> None:
        """Subgraph includes root and connected nodes."""
        repo = KnowledgeGraphRepository(db_session)
        ws = uuid4()

        root = await repo.upsert_node(_make_node(workspace_id=ws, label="Root"))
        child = await repo.upsert_node(_make_node(workspace_id=ws, label="Child"))
        await repo.upsert_edge(_make_edge(root.id, child.id))

        nodes, edges = await repo.get_subgraph(root.id, max_depth=1)
        node_ids = {n.id for n in nodes}

        assert root.id in node_ids
        assert child.id in node_ids
        assert len(edges) >= 1

    async def test_get_subgraph_caps_at_max_nodes(self, db_session: AsyncSession) -> None:
        """Subgraph caps at max_nodes even when more are reachable."""
        repo = KnowledgeGraphRepository(db_session)
        ws = uuid4()

        root = await repo.upsert_node(_make_node(workspace_id=ws, label="Root"))
        # Create 10 direct children
        for i in range(10):
            child = await repo.upsert_node(_make_node(workspace_id=ws, label=f"Child {i}"))
            await repo.upsert_edge(_make_edge(root.id, child.id))

        nodes, _ = await repo.get_subgraph(root.id, max_depth=1, max_nodes=5)
        assert len(nodes) <= 5

    async def test_get_subgraph_edges_connect_returned_nodes(
        self, db_session: AsyncSession
    ) -> None:
        """Returned edges only connect nodes in the node set."""
        repo = KnowledgeGraphRepository(db_session)
        ws = uuid4()

        n1 = await repo.upsert_node(_make_node(workspace_id=ws))
        n2 = await repo.upsert_node(_make_node(workspace_id=ws))
        n3 = await repo.upsert_node(_make_node(workspace_id=ws))

        await repo.upsert_edge(_make_edge(n1.id, n2.id))
        await repo.upsert_edge(_make_edge(n2.id, n3.id))

        nodes, edges = await repo.get_subgraph(n1.id, max_depth=2)
        node_ids = {n.id for n in nodes}

        for edge in edges:
            assert edge.source_id in node_ids
            assert edge.target_id in node_ids


# ---------------------------------------------------------------------------
# get_user_context
# ---------------------------------------------------------------------------


class TestGetUserContext:
    async def test_get_user_context(self, db_session: AsyncSession) -> None:
        """Returns nodes scoped to the user."""
        repo = KnowledgeGraphRepository(db_session)
        ws = uuid4()
        user_id = uuid4()

        user_node = await repo.upsert_node(
            _make_node(workspace_id=ws, user_id=user_id, label="User pref node")
        )
        # Workspace node without user_id
        ws_node = await repo.upsert_node(_make_node(workspace_id=ws, label="Workspace node"))

        results = await repo.get_user_context(user_id=user_id, workspace_id=ws)
        result_ids = {n.id for n in results}

        assert user_node.id in result_ids
        assert ws_node.id in result_ids  # workspace nodes also included

    async def test_get_user_context_respects_limit(self, db_session: AsyncSession) -> None:
        """get_user_context respects the limit parameter."""
        repo = KnowledgeGraphRepository(db_session)
        ws = uuid4()

        for i in range(15):
            await repo.upsert_node(_make_node(workspace_id=ws, label=f"Node {i}"))

        results = await repo.get_user_context(user_id=uuid4(), workspace_id=ws, limit=5)
        assert len(results) <= 5

    async def test_get_user_context_workspace_isolation(self, db_session: AsyncSession) -> None:
        """User context is scoped to the workspace."""
        repo = KnowledgeGraphRepository(db_session)
        ws_a = uuid4()
        ws_b = uuid4()
        user_id = uuid4()

        await repo.upsert_node(_make_node(workspace_id=ws_a, user_id=user_id, label="WS-A node"))
        await repo.upsert_node(_make_node(workspace_id=ws_b, user_id=user_id, label="WS-B node"))

        results = await repo.get_user_context(user_id=user_id, workspace_id=ws_a)
        for node in results:
            assert node.workspace_id == ws_a


# ---------------------------------------------------------------------------
# bulk_upsert_nodes
# ---------------------------------------------------------------------------


class TestBulkUpsertNodes:
    async def test_bulk_upsert_nodes(self, db_session: AsyncSession) -> None:
        """bulk_upsert_nodes persists all nodes and returns them."""
        repo = KnowledgeGraphRepository(db_session)
        ws = uuid4()
        nodes = [_make_node(workspace_id=ws, label=f"Node {i}") for i in range(5)]

        results = await repo.bulk_upsert_nodes(nodes)

        assert len(results) == 5
        labels = {n.label for n in results}
        assert labels == {f"Node {i}" for i in range(5)}

    async def test_bulk_upsert_nodes_updates_existing(self, db_session: AsyncSession) -> None:
        """bulk_upsert_nodes updates nodes that share an external_id."""
        repo = KnowledgeGraphRepository(db_session)
        ws = uuid4()
        ext_id = uuid4()

        first = [
            GraphNode.create(
                workspace_id=ws,
                node_type=NodeType.NOTE,
                label="Original",
                content="v1",
                external_id=ext_id,
            )
        ]
        await repo.bulk_upsert_nodes(first)

        second = [
            GraphNode.create(
                workspace_id=ws,
                node_type=NodeType.NOTE,
                label="Updated",
                content="v2",
                external_id=ext_id,
            )
        ]
        results = await repo.bulk_upsert_nodes(second)

        assert results[0].label == "Updated"
        assert results[0].content == "v2"

    async def test_bulk_upsert_nodes_empty_list(self, db_session: AsyncSession) -> None:
        """bulk_upsert_nodes with empty list returns empty list."""
        repo = KnowledgeGraphRepository(db_session)
        results = await repo.bulk_upsert_nodes([])
        assert results == []


# ---------------------------------------------------------------------------
# delete_expired_nodes
# ---------------------------------------------------------------------------


class TestDeleteExpiredNodes:
    async def test_delete_expired_nodes(self, db_session: AsyncSession) -> None:
        """Nodes older than the cutoff are soft-deleted."""
        repo = KnowledgeGraphRepository(db_session)
        ws = uuid4()

        old_node = await repo.upsert_node(_make_node(workspace_id=ws, label="Old node"))

        # Manually backdate updated_at
        await db_session.execute(
            _update(GraphNodeModel)
            .where(GraphNodeModel.id == old_node.id)
            .values(updated_at=datetime.now(tz=UTC) - timedelta(days=30))
        )
        await db_session.flush()

        cutoff = datetime.now(tz=UTC) - timedelta(days=7)
        count = await repo.delete_expired_nodes(before=cutoff)

        assert count >= 1

    async def test_delete_expired_nodes_skips_pinned(self, db_session: AsyncSession) -> None:
        """Pinned nodes are not soft-deleted even if expired."""
        repo = KnowledgeGraphRepository(db_session)
        ws = uuid4()

        pinned_node = await repo.upsert_node(
            _make_node(workspace_id=ws, label="Pinned old node", pinned=True)
        )

        await db_session.execute(
            _update(GraphNodeModel)
            .where(GraphNodeModel.id == pinned_node.id)
            .values(updated_at=datetime.now(tz=UTC) - timedelta(days=30))
        )
        await db_session.flush()

        cutoff = datetime.now(tz=UTC) - timedelta(days=7)
        await repo.delete_expired_nodes(before=cutoff)

        # Verify pinned node still active
        result = await db_session.execute(
            _select(GraphNodeModel).where(GraphNodeModel.id == pinned_node.id)
        )
        model = result.scalar_one()
        assert model.is_deleted is False

    async def test_delete_expired_nodes_returns_zero_if_none_expired(
        self, db_session: AsyncSession
    ) -> None:
        """Returns 0 when no nodes qualify for expiry."""
        repo = KnowledgeGraphRepository(db_session)
        ws = uuid4()

        # Create a fresh node (not expired)
        await repo.upsert_node(_make_node(workspace_id=ws, label="Fresh"))

        cutoff = datetime.now(tz=UTC) - timedelta(days=365)
        count = await repo.delete_expired_nodes(before=cutoff)
        assert count == 0
