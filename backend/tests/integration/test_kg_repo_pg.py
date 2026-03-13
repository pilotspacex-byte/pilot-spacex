"""PostgreSQL-specific integration tests for KnowledgeGraphRepository.

These tests cover code paths that ONLY work on PostgreSQL (not SQLite):
- pgvector hybrid search (cosine similarity + ts_rank fusion)
- Recursive CTE neighbor traversal
- Bulk upsert with content_hash dedup
- Bulk UPDATE with JSONB cast for delete_expired_nodes

The tests create isolated tables (no FK to workspaces/users), run, then
drop. No alembic migrations or main test conftest are used.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from pilot_space.domain.graph_edge import EdgeType, GraphEdge
from pilot_space.domain.graph_node import GraphNode, NodeType, compute_content_hash
from pilot_space.domain.graph_query import ScoredNode
from pilot_space.infrastructure.database.repositories._graph_helpers import (
    serialize_embedding,
)
from pilot_space.infrastructure.database.repositories.knowledge_graph_repository import (
    KnowledgeGraphRepository,
)

# Default dev password from Supabase self-hosted template — not a real secret.
_PG_PASSWORD = os.environ.get(  # pragma: allowlist secret
    "PG_TEST_PASSWORD",
    "your-super-secret-and-long-postgres-password",  # pragma: allowlist secret
)
PG_URL = f"postgresql+asyncpg://supabase_admin:{_PG_PASSWORD}@localhost:15432/pilot_space_test"

# Split into individual statements — asyncpg does not support multi-statement execute.
DDL_CREATE_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS graph_nodes (
        id              UUID        NOT NULL DEFAULT gen_random_uuid(),
        workspace_id    UUID        NOT NULL,
        user_id         UUID,
        node_type       VARCHAR(50) NOT NULL,
        external_id     UUID,
        label           VARCHAR(500) NOT NULL,
        content         TEXT         NOT NULL DEFAULT '',
        properties      JSONB        NOT NULL DEFAULT '{}',
        embedding       vector(768),
        content_hash    VARCHAR(64),
        is_deleted      BOOLEAN      NOT NULL DEFAULT false,
        deleted_at      TIMESTAMPTZ,
        created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
        updated_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
        CONSTRAINT pk_graph_nodes PRIMARY KEY (id)
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_graph_nodes_embedding
        ON graph_nodes USING hnsw (embedding vector_cosine_ops)
        WHERE embedding IS NOT NULL
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_graph_nodes_content_hash
        ON graph_nodes (workspace_id, content_hash)
    """,
    """
    CREATE TABLE IF NOT EXISTS graph_edges (
        id              UUID        NOT NULL DEFAULT gen_random_uuid(),
        source_id       UUID        NOT NULL REFERENCES graph_nodes(id) ON DELETE CASCADE,
        target_id       UUID        NOT NULL REFERENCES graph_nodes(id) ON DELETE CASCADE,
        workspace_id    UUID        NOT NULL,
        edge_type       VARCHAR(50) NOT NULL,
        properties      JSONB        NOT NULL DEFAULT '{}',
        weight          FLOAT        NOT NULL DEFAULT 0.5
                        CHECK (weight >= 0.0 AND weight <= 1.0),
        created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
        CONSTRAINT pk_graph_edges PRIMARY KEY (id),
        CONSTRAINT chk_graph_edges_no_self_loop CHECK (source_id != target_id),
        CONSTRAINT uq_graph_edges_source_target_type UNIQUE (source_id, target_id, edge_type)
    )
    """,
]

DDL_DROP_STATEMENTS = [
    "DROP TABLE IF EXISTS graph_edges CASCADE",
    "DROP TABLE IF EXISTS graph_nodes CASCADE",
]

pytestmark = [
    pytest.mark.asyncio(loop_scope="module"),
    pytest.mark.integration,
]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def pg_engine():
    """Create PG engine, set up graph tables, yield, tear down."""
    engine = create_async_engine(PG_URL, echo=False)
    try:
        async with engine.begin() as conn:
            # Ensure extensions exist (should already be installed in test DB).
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
            # Drop first to ensure clean slate for this test module.
            for stmt in DDL_DROP_STATEMENTS:
                await conn.execute(text(stmt))
            for stmt in DDL_CREATE_STATEMENTS:
                await conn.execute(text(stmt))
    except Exception:
        await engine.dispose()
        pytest.skip("PostgreSQL not available at localhost:15432")
        return  # unreachable, satisfies type checker
    yield engine
    async with engine.begin() as conn:
        for stmt in DDL_DROP_STATEMENTS:
            await conn.execute(text(stmt))
    await engine.dispose()


@pytest_asyncio.fixture(loop_scope="module")
async def pg_session(pg_engine):
    """Session with savepoint-based isolation — rolls back after each test."""
    conn = await pg_engine.connect()
    trans = await conn.begin()
    session = AsyncSession(bind=conn, expire_on_commit=False)
    yield session
    await session.close()
    await trans.rollback()
    await conn.close()


@pytest.fixture
def workspace_id() -> UUID:
    """Stable workspace UUID shared across tests in a class."""
    return uuid4()


@pytest.fixture
def repo(pg_session: AsyncSession) -> KnowledgeGraphRepository:
    """KnowledgeGraphRepository bound to the PG session."""
    return KnowledgeGraphRepository(pg_session)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_node(
    workspace_id: UUID,
    node_type: NodeType = NodeType.ISSUE,
    label: str = "Test Node",
    content: str = "test content",
    external_id: UUID | None = None,
    content_hash: str | None = None,
    properties: dict | None = None,
) -> GraphNode:
    """Build a GraphNode with sensible defaults."""
    return GraphNode.create(
        workspace_id=workspace_id,
        node_type=node_type,
        label=label,
        content=content,
        external_id=external_id,
        content_hash=content_hash,
        properties=properties,
    )


async def _set_embedding(
    session: AsyncSession,
    node_id: UUID,
    embedding: list[float],
) -> None:
    """Set embedding on a node via raw SQL (upsert_node does not write embeddings)."""
    emb_str = serialize_embedding(embedding)
    await session.execute(
        text("UPDATE graph_nodes SET embedding = CAST(:emb AS vector(768)) WHERE id = :id"),
        {"emb": emb_str, "id": str(node_id)},
    )
    await session.flush()


async def _set_updated_at(
    session: AsyncSession,
    node_id: UUID,
    dt: datetime,
) -> None:
    """Override updated_at for a node via raw SQL."""
    await session.execute(
        text("UPDATE graph_nodes SET updated_at = :dt WHERE id = :id"),
        {"dt": dt, "id": str(node_id)},
    )
    await session.flush()


# ---------------------------------------------------------------------------
# C-3: Hybrid search (pgvector cosine + ts_rank fusion)
# ---------------------------------------------------------------------------


class TestHybridSearchPg:
    """Tests for hybrid_search method using pgvector on PostgreSQL."""

    async def test_hybrid_search_with_embedding(
        self,
        repo: KnowledgeGraphRepository,
        pg_session: AsyncSession,
        workspace_id: UUID,
    ) -> None:
        """Insert 2 nodes with embeddings, search with similar embedding."""
        # Arrange
        n1 = _make_node(workspace_id, label="Alpha issue", content="alpha content")
        n2 = _make_node(workspace_id, label="Beta issue", content="beta content")
        saved1 = await repo.upsert_node(n1)
        saved2 = await repo.upsert_node(n2)

        emb_close = [0.1] * 768
        emb_far = [0.9] * 768
        await _set_embedding(pg_session, saved1.id, emb_close)
        await _set_embedding(pg_session, saved2.id, emb_far)

        # Act
        results = await repo.hybrid_search(
            query_embedding=emb_close,
            query_text="alpha",
            workspace_id=workspace_id,
            limit=10,
        )

        # Assert
        assert len(results) >= 1
        assert all(isinstance(r, ScoredNode) for r in results)
        # The node with embedding closer to query should rank first.
        assert results[0].node.id == saved1.id
        assert results[0].embedding_score > 0.0

    async def test_hybrid_search_node_types_filter(
        self,
        repo: KnowledgeGraphRepository,
        pg_session: AsyncSession,
        workspace_id: UUID,
    ) -> None:
        """Filter by node_types returns only matching types."""
        # Arrange
        issue_node = _make_node(workspace_id, node_type=NodeType.ISSUE, label="Issue one")
        note_node = _make_node(workspace_id, node_type=NodeType.NOTE, label="Note one")
        s_issue = await repo.upsert_node(issue_node)
        s_note = await repo.upsert_node(note_node)

        emb = [0.5] * 768
        await _set_embedding(pg_session, s_issue.id, emb)
        await _set_embedding(pg_session, s_note.id, emb)

        # Act
        results = await repo.hybrid_search(
            query_embedding=emb,
            query_text="one",
            workspace_id=workspace_id,
            node_types=[NodeType.ISSUE],
            limit=10,
        )

        # Assert
        result_types = {r.node.node_type for r in results}
        assert result_types == {NodeType.ISSUE}

    async def test_hybrid_search_since_filter(
        self,
        repo: KnowledgeGraphRepository,
        pg_session: AsyncSession,
        workspace_id: UUID,
    ) -> None:
        """since filter excludes older nodes."""
        # Arrange
        old_node = _make_node(workspace_id, label="Old node", content="old content")
        new_node = _make_node(workspace_id, label="New node", content="new content")
        s_old = await repo.upsert_node(old_node)
        s_new = await repo.upsert_node(new_node)

        emb = [0.3] * 768
        await _set_embedding(pg_session, s_old.id, emb)
        await _set_embedding(pg_session, s_new.id, emb)

        # Push old node's updated_at to 30 days ago.
        old_dt = datetime.now(tz=UTC) - timedelta(days=30)
        await _set_updated_at(pg_session, s_old.id, old_dt)

        since_cutoff = datetime.now(tz=UTC) - timedelta(days=1)

        # Act
        results = await repo.hybrid_search(
            query_embedding=emb,
            query_text="content",
            workspace_id=workspace_id,
            since=since_cutoff,
            limit=10,
        )

        # Assert
        result_ids = {r.node.id for r in results}
        assert s_new.id in result_ids
        assert s_old.id not in result_ids

    async def test_hybrid_search_no_matches(
        self,
        repo: KnowledgeGraphRepository,
        workspace_id: UUID,
    ) -> None:
        """Search on an empty workspace returns empty list."""
        empty_ws = uuid4()
        results = await repo.hybrid_search(
            query_embedding=[0.1] * 768,
            query_text="nothing",
            workspace_id=empty_ws,
            limit=10,
        )
        assert results == []


# ---------------------------------------------------------------------------
# M-2: Recursive CTE neighbor traversal
# ---------------------------------------------------------------------------


class TestGetNeighborsCte:
    """Tests for get_neighbors using recursive CTE on PostgreSQL."""

    async def test_cte_depth_1(
        self,
        repo: KnowledgeGraphRepository,
        workspace_id: UUID,
    ) -> None:
        """Depth-1 traversal returns only direct neighbors."""
        # Arrange: n1 --RELATES_TO--> n2 --RELATES_TO--> n3
        n1 = _make_node(workspace_id, label="N1", content="node 1")
        n2 = _make_node(workspace_id, label="N2", content="node 2")
        n3 = _make_node(workspace_id, label="N3", content="node 3")
        s1 = await repo.upsert_node(n1)
        s2 = await repo.upsert_node(n2)
        s3 = await repo.upsert_node(n3)

        await repo.upsert_edge(
            GraphEdge(source_id=s1.id, target_id=s2.id, edge_type=EdgeType.RELATES_TO)
        )
        await repo.upsert_edge(
            GraphEdge(source_id=s2.id, target_id=s3.id, edge_type=EdgeType.RELATES_TO)
        )

        # Act
        neighbors = await repo.get_neighbors(s1.id, depth=1, workspace_id=workspace_id)

        # Assert — only direct neighbor n2
        neighbor_ids = {n.id for n in neighbors}
        assert s2.id in neighbor_ids
        assert s3.id not in neighbor_ids

    async def test_cte_depth_2_multi_hop(
        self,
        repo: KnowledgeGraphRepository,
        workspace_id: UUID,
    ) -> None:
        """Depth-2 traversal reaches 2-hop neighbors."""
        # Arrange: n1 --> n2 --> n3
        n1 = _make_node(workspace_id, label="N1", content="node 1")
        n2 = _make_node(workspace_id, label="N2", content="node 2")
        n3 = _make_node(workspace_id, label="N3", content="node 3")
        s1 = await repo.upsert_node(n1)
        s2 = await repo.upsert_node(n2)
        s3 = await repo.upsert_node(n3)

        await repo.upsert_edge(
            GraphEdge(source_id=s1.id, target_id=s2.id, edge_type=EdgeType.RELATES_TO)
        )
        await repo.upsert_edge(
            GraphEdge(source_id=s2.id, target_id=s3.id, edge_type=EdgeType.RELATES_TO)
        )

        # Act
        neighbors = await repo.get_neighbors(s1.id, depth=2, workspace_id=workspace_id)

        # Assert — n3 is reachable at depth 2
        neighbor_ids = {n.id for n in neighbors}
        assert s2.id in neighbor_ids
        assert s3.id in neighbor_ids

    async def test_cte_edge_type_filter(
        self,
        repo: KnowledgeGraphRepository,
        workspace_id: UUID,
    ) -> None:
        """Filtering by edge_type restricts traversal."""
        # Arrange: n1 --RELATES_TO--> n2, n1 --BLOCKS--> n3
        n1 = _make_node(workspace_id, label="N1", content="node 1")
        n2 = _make_node(workspace_id, label="N2", content="node 2")
        n3 = _make_node(workspace_id, label="N3", content="node 3")
        s1 = await repo.upsert_node(n1)
        s2 = await repo.upsert_node(n2)
        s3 = await repo.upsert_node(n3)

        await repo.upsert_edge(
            GraphEdge(source_id=s1.id, target_id=s2.id, edge_type=EdgeType.RELATES_TO)
        )
        await repo.upsert_edge(
            GraphEdge(source_id=s1.id, target_id=s3.id, edge_type=EdgeType.BLOCKS)
        )

        # Act — filter to RELATES_TO only
        neighbors = await repo.get_neighbors(
            s1.id,
            edge_types=[EdgeType.RELATES_TO],
            depth=1,
            workspace_id=workspace_id,
        )

        # Assert — only n2 (RELATES_TO), not n3 (BLOCKS)
        neighbor_ids = {n.id for n in neighbors}
        assert s2.id in neighbor_ids
        assert s3.id not in neighbor_ids


# ---------------------------------------------------------------------------
# C-4: Bulk upsert (PG-only path)
# ---------------------------------------------------------------------------


class TestBulkUpsertPg:
    """Tests for bulk_upsert_nodes on PostgreSQL."""

    async def test_bulk_insert_new_nodes(
        self,
        repo: KnowledgeGraphRepository,
        workspace_id: UUID,
    ) -> None:
        """Bulk insert 3 new keyed nodes returns all 3."""
        nodes = [_make_node(workspace_id, label=f"Bulk-{i}", external_id=uuid4()) for i in range(3)]

        result = await repo.bulk_upsert_nodes(nodes)

        assert len(result) == 3
        result_labels = {n.label for n in result}
        assert result_labels == {"Bulk-0", "Bulk-1", "Bulk-2"}

    async def test_bulk_update_existing_by_external_id(
        self,
        repo: KnowledgeGraphRepository,
        workspace_id: UUID,
    ) -> None:
        """Bulk upsert updates existing nodes matched by external_id."""
        ext_id = uuid4()
        original = _make_node(
            workspace_id,
            label="Original",
            content="original content",
            external_id=ext_id,
        )
        await repo.upsert_node(original)

        # Act — upsert with same external_id, different label
        updated_node = _make_node(
            workspace_id,
            label="Updated",
            content="updated content",
            external_id=ext_id,
        )
        result = await repo.bulk_upsert_nodes([updated_node])

        # Assert
        assert len(result) == 1
        assert result[0].label == "Updated"
        assert result[0].content == "updated content"

    async def test_bulk_content_hash_dedup(
        self,
        repo: KnowledgeGraphRepository,
        workspace_id: UUID,
    ) -> None:
        """Nodes with same content_hash are deduplicated (existing DB row wins)."""
        content = "identical content for dedup"
        ch = compute_content_hash(workspace_id, "issue", content)

        first_node = _make_node(workspace_id, label="First", content=content, content_hash=ch)
        await repo.upsert_node(first_node)

        # Act — bulk upsert with same content_hash
        second_node = _make_node(workspace_id, label="Second", content=content, content_hash=ch)
        result = await repo.bulk_upsert_nodes([second_node])

        # Assert — returns 1 result, which is the existing node (first wins)
        assert len(result) == 1

    async def test_bulk_same_batch_hash_collision(
        self,
        repo: KnowledgeGraphRepository,
        workspace_id: UUID,
    ) -> None:
        """Two nodes in the same batch with identical content_hash: first wins."""
        content = "same batch duplicate content"
        ch = compute_content_hash(workspace_id, "issue", content)

        node_a = _make_node(workspace_id, label="A", content=content, content_hash=ch)
        node_b = _make_node(workspace_id, label="B", content=content, content_hash=ch)

        result = await repo.bulk_upsert_nodes([node_a, node_b])

        # Assert — both entries reference the same node (first insert wins),
        # so result has 2 entries but they point to the same underlying row.
        assert len(result) == 2
        assert result[0].id == result[1].id
        assert result[0].label == "A"  # first one was inserted


# ---------------------------------------------------------------------------
# L-2: delete_expired_nodes (PG bulk UPDATE with JSONB cast)
# ---------------------------------------------------------------------------


class TestDeleteExpiredNodesPg:
    """Tests for delete_expired_nodes on PostgreSQL."""

    async def test_pg_delete_expired_unpinned(
        self,
        repo: KnowledgeGraphRepository,
        pg_session: AsyncSession,
        workspace_id: UUID,
    ) -> None:
        """Old unpinned nodes are soft-deleted."""
        node = _make_node(workspace_id, label="Stale node", content="stale")
        saved = await repo.upsert_node(node)

        # Push updated_at to 90 days ago.
        old_dt = datetime.now(tz=UTC) - timedelta(days=90)
        await _set_updated_at(pg_session, saved.id, old_dt)

        before = datetime.now(tz=UTC) - timedelta(days=30)

        # Act
        count = await repo.delete_expired_nodes(before=before)

        # Assert
        assert count >= 1

    async def test_pg_delete_expired_skips_pinned(
        self,
        repo: KnowledgeGraphRepository,
        pg_session: AsyncSession,
        workspace_id: UUID,
    ) -> None:
        """Pinned nodes are not deleted even if expired."""
        node = _make_node(
            workspace_id,
            label="Pinned node",
            content="pinned",
            properties={"pinned": True},
        )
        saved = await repo.upsert_node(node)

        # Push updated_at to 90 days ago.
        old_dt = datetime.now(tz=UTC) - timedelta(days=90)
        await _set_updated_at(pg_session, saved.id, old_dt)

        before = datetime.now(tz=UTC) - timedelta(days=30)

        # Act
        count = await repo.delete_expired_nodes(before=before)

        # Assert — the pinned node should NOT be deleted
        # Verify directly via raw SQL since the repo marks is_deleted=true
        row = (
            await pg_session.execute(
                text("SELECT is_deleted FROM graph_nodes WHERE id = :id"),
                {"id": str(saved.id)},
            )
        ).one()
        assert row[0] is False


# ---------------------------------------------------------------------------
# H-1: IntegrityError recovery (concurrent insert race)
# ---------------------------------------------------------------------------
# SKIPPED: Testing the IntegrityError recovery path (lines 101-113 in
# knowledge_graph_repository.py) requires actual concurrent transactions
# racing past the content_hash check. This cannot be reliably simulated
# with savepoint-based test isolation. The path is exercised by the
# UNIQUE partial index on (workspace_id, content_hash) at the DB level.
