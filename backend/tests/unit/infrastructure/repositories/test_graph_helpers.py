"""Unit tests for _graph_helpers.py internal functions.

Tests cover:
- compute_recency_score: time-decay scoring for recent and old nodes.
- node_model_to_domain: embedding dimension validation and mapping.
- serialize_embedding: round-trip serialization of float vectors.
- enrich_edge_density: log-based edge density scoring with DB queries.
- keyword_search: LIKE-based search with node_types and since filters.

All tests use SQLite-compatible operations via the same isolated
graph_nodes + graph_edges schema from test_knowledge_graph_repository.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
import sqlalchemy as sa
from sqlalchemy import update as _update
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from pilot_space.domain.graph_edge import EdgeType, GraphEdge
from pilot_space.domain.graph_node import GraphNode, NodeType
from pilot_space.domain.graph_query import ScoredNode
from pilot_space.infrastructure.database.models.graph_node import GraphNodeModel
from pilot_space.infrastructure.database.repositories._graph_helpers import (
    GRAPH_EMBEDDING_DIMS,
    compute_degree_map,
    compute_recency_score,
    enrich_edge_density,
    keyword_search,
    node_model_to_domain,
    serialize_embedding,
)
from pilot_space.infrastructure.database.repositories.knowledge_graph_repository import (
    KnowledgeGraphRepository,
)

pytestmark = pytest.mark.asyncio

# ---------------------------------------------------------------------------
# Local fixtures: only create graph_nodes + graph_edges tables on SQLite
# ---------------------------------------------------------------------------

_GRAPH_METADATA = sa.MetaData()

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
    sa.Column("content_hash", sa.String(64), nullable=True),
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


class _FakeNodeModel:
    """Lightweight stand-in for GraphNodeModel to avoid SQLAlchemy instrumentation.

    node_model_to_domain reads plain attributes via duck typing — it does not
    need a real ORM instance. This avoids the ``__new__`` + attribute-set
    issue with SQLAlchemy mapped classes.
    """

    def __init__(
        self,
        *,
        workspace_id: object | None = None,
        node_type: str = "note",
        label: str = "test",
        content: str = "test content",
        embedding: str | None = None,
        is_deleted: bool = False,
        updated_at: datetime | None = None,
    ) -> None:
        now = updated_at or datetime.now(UTC)
        self.id = uuid4()
        self.workspace_id = workspace_id or uuid4()
        self.user_id = None
        self.node_type = node_type
        self.external_id = None
        self.label = label
        self.content = content
        self.properties: dict[str, object] = {}
        self.embedding = embedding
        self.content_hash = None
        self.is_deleted = is_deleted
        self.deleted_at = None
        self.created_at = now
        self.updated_at = now


def _make_node(
    workspace_id: object | None = None,
    node_type: NodeType = NodeType.NOTE,
    label: str = "test node",
    content: str = "test content",
) -> GraphNode:
    """Build a minimal GraphNode for testing."""
    return GraphNode.create(
        workspace_id=workspace_id or uuid4(),
        node_type=node_type,
        label=label,
        content=content,
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


def _make_scored_node(
    node: GraphNode,
    *,
    score: float = 0.5,
    embedding_score: float = 0.3,
    text_score: float = 0.2,
    recency_score: float = 0.5,
    edge_density_score: float = 0.0,
) -> ScoredNode:
    return ScoredNode(
        node=node,
        score=score,
        embedding_score=embedding_score,
        text_score=text_score,
        recency_score=recency_score,
        edge_density_score=edge_density_score,
    )


# ---------------------------------------------------------------------------
# TestComputeRecencyScore (M-9)
# ---------------------------------------------------------------------------


class TestComputeRecencyScore:
    """Verify time-decay recency scoring formula."""

    async def test_recency_score_now(self) -> None:
        """Node updated just now produces a score very close to 1.0."""
        now = datetime.now(UTC)
        score = compute_recency_score(now, now)
        assert score == pytest.approx(1.0, abs=0.01)

    async def test_recency_score_old(self) -> None:
        """Node updated 365 days ago produces a score near 0.003."""
        now = datetime.now(UTC)
        old = now - timedelta(days=365)
        score = compute_recency_score(old, now)
        # 1 / (1 + 365) ≈ 0.00273
        assert score == pytest.approx(1.0 / 366.0, abs=0.001)
        assert score < 0.01

    async def test_recency_score_default_now(self) -> None:
        """Calling without explicit now uses current time (default branch)."""
        recent = datetime.now(UTC) - timedelta(seconds=1)
        score = compute_recency_score(recent)
        assert score == pytest.approx(1.0, abs=0.01)


# ---------------------------------------------------------------------------
# TestNodeModelToDomain (M-1)
# ---------------------------------------------------------------------------


class TestNodeModelToDomain:
    """Verify GraphNodeModel -> GraphNode domain mapping."""

    async def test_embedding_dim_mismatch_discards_embedding(self) -> None:
        """Embedding with wrong dimension (1536 instead of 768) is discarded."""
        wrong_dim_embedding = "[" + ",".join("0.1" for _ in range(1536)) + "]"
        model = _FakeNodeModel(embedding=wrong_dim_embedding)

        domain = node_model_to_domain(model)  # type: ignore[arg-type]

        assert domain.embedding is None

    async def test_embedding_correct_dim(self) -> None:
        """Embedding with correct 768 dimensions is preserved."""
        correct_embedding = "[" + ",".join(str(i * 0.001) for i in range(768)) + "]"
        model = _FakeNodeModel(embedding=correct_embedding)

        domain = node_model_to_domain(model)  # type: ignore[arg-type]

        assert domain.embedding is not None
        assert len(domain.embedding) == GRAPH_EMBEDDING_DIMS
        assert domain.embedding[0] == pytest.approx(0.0, abs=0.001)
        assert domain.embedding[1] == pytest.approx(0.001, abs=0.0001)

    async def test_embedding_none_stays_none(self) -> None:
        """Model with embedding=None maps to domain with embedding=None."""
        model = _FakeNodeModel(embedding=None)

        domain = node_model_to_domain(model)  # type: ignore[arg-type]

        assert domain.embedding is None

    async def test_embedding_iterable_non_string(self) -> None:
        """Model with iterable (non-string) embedding is converted via list()."""
        vector = [0.1] * GRAPH_EMBEDDING_DIMS
        model = _FakeNodeModel()
        model.embedding = vector  # type: ignore[assignment]  # simulate pgvector return

        domain = node_model_to_domain(model)  # type: ignore[arg-type]

        assert domain.embedding is not None
        assert len(domain.embedding) == GRAPH_EMBEDDING_DIMS


# ---------------------------------------------------------------------------
# TestSerializeEmbedding
# ---------------------------------------------------------------------------


class TestSerializeEmbedding:
    """Verify embedding serialization to pgvector-compatible string."""

    async def test_serialize_round_trip(self) -> None:
        """serialize_embedding produces '[v1,v2,v3]' format."""
        result = serialize_embedding([0.1, 0.2, 0.3])
        assert result == "[0.1,0.2,0.3]"


# ---------------------------------------------------------------------------
# TestEnrichEdgeDensity (M-10)
# ---------------------------------------------------------------------------


class TestComputeDegreeMap:
    """Verify degree map computation."""

    async def test_empty_node_ids_returns_empty(self, db_session: AsyncSession) -> None:
        """Empty node_ids returns empty dict without DB query."""
        result = await compute_degree_map(db_session, [])
        assert result == {}


class TestEnrichEdgeDensity:
    """Verify edge density enrichment via degree counting."""

    async def test_empty_scored_list(self, db_session: AsyncSession) -> None:
        """Empty input returns empty output without DB queries."""
        result = await enrich_edge_density(db_session, [])
        assert result == []

    async def test_node_with_edges_gets_density(self, db_session: AsyncSession) -> None:
        """Node with edges receives a positive edge_density_score."""
        ws = uuid4()
        repo = KnowledgeGraphRepository(db_session)

        node1 = await repo.upsert_node(_make_node(workspace_id=ws, label="N1"))
        node2 = await repo.upsert_node(_make_node(workspace_id=ws, label="N2"))
        await repo.upsert_edge(_make_edge(node1.id, node2.id))

        scored = _make_scored_node(node1)
        result = await enrich_edge_density(db_session, [scored], workspace_id=ws)

        assert len(result) == 1
        assert result[0].edge_density_score > 0.0


# ---------------------------------------------------------------------------
# TestKeywordSearch (M-11)
# ---------------------------------------------------------------------------


class TestKeywordSearch:
    """Verify SQLite-compatible LIKE keyword search with filters."""

    async def test_keyword_search_with_node_types_filter(self, db_session: AsyncSession) -> None:
        """Search with node_types filter returns only matching types."""
        ws = uuid4()
        repo = KnowledgeGraphRepository(db_session)

        await repo.upsert_node(
            _make_node(
                workspace_id=ws,
                node_type=NodeType.NOTE,
                label="deploy note",
                content="deployment pipeline keyword",
            )
        )
        await repo.upsert_node(
            _make_node(
                workspace_id=ws,
                node_type=NodeType.ISSUE,
                label="deploy issue",
                content="deployment pipeline keyword",
            )
        )

        results = await keyword_search(
            session=db_session,
            query_text="keyword",
            workspace_id=ws,
            node_types=[NodeType.ISSUE],
            limit=10,
        )

        assert len(results) == 1
        assert results[0].node.node_type == NodeType.ISSUE

    async def test_keyword_search_with_since_filter(self, db_session: AsyncSession) -> None:
        """Search with since filter returns only recently updated nodes."""
        ws = uuid4()
        repo = KnowledgeGraphRepository(db_session)
        now = datetime.now(UTC)

        old_node = await repo.upsert_node(
            _make_node(workspace_id=ws, label="old node", content="findable keyword")
        )
        new_node = await repo.upsert_node(
            _make_node(workspace_id=ws, label="new node", content="findable keyword")
        )

        # Backdate the old node's updated_at to 30 days ago
        await db_session.execute(
            _update(GraphNodeModel)
            .where(GraphNodeModel.id == old_node.id)
            .values(updated_at=now - timedelta(days=30))
        )
        await db_session.flush()

        since_cutoff = now - timedelta(days=1)
        results = await keyword_search(
            session=db_session,
            query_text="findable",
            workspace_id=ws,
            node_types=None,
            limit=10,
            since=since_cutoff,
        )

        assert len(results) == 1
        assert results[0].node.label == "new node"
