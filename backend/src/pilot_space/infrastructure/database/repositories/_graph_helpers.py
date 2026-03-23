"""Internal helper functions for KnowledgeGraphRepository.

Extracted to keep knowledge_graph_repository.py within the 700-line limit.
Not part of the public API — import from knowledge_graph_repository instead.
"""

from __future__ import annotations

import math
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import and_, func, or_, select, text, union_all

from pilot_space.domain.graph_edge import EdgeType, GraphEdge
from pilot_space.domain.graph_node import GraphNode, NodeType
from pilot_space.domain.graph_query import ScoredNode
from pilot_space.infrastructure.database.models.graph_edge import GraphEdgeModel
from pilot_space.infrastructure.database.models.graph_node import GraphNodeModel
from pilot_space.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)

# Score fusion weights — all four co-located so the sum (1.0) is verifiable here.
# SQL hybrid_search_pg uses the first three (embedding + text + recency = 0.9).
# The fourth (edge_density = 0.1) is applied post-query by enrich_edge_density.
GRAPH_EMBEDDING_WEIGHT = 0.5
GRAPH_TEXT_WEIGHT = 0.2
GRAPH_RECENCY_WEIGHT = 0.2
GRAPH_EDGE_DENSITY_WEIGHT = 0.1  # Must sum: 0.5+0.2+0.2+0.1 = 1.0
GRAPH_SECONDS_PER_DAY = 86_400.0

# Embedding vector dimension — must match migration 057 (resized from 1536 → 768)
GRAPH_EMBEDDING_DIMS = 768


def serialize_embedding(embedding: list[float]) -> str:
    """Serialize an embedding vector to '[v1,v2,...]' string for pgvector storage."""
    return "[" + ",".join(str(v) for v in embedding) + "]"


def ensure_utc_aware(dt: datetime) -> datetime:
    """Return dt with UTC tzinfo, adding it if the datetime is naive."""
    return dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt


def compute_recency_score(updated_at: datetime, now: datetime | None = None) -> float:
    """Recency score: 1.0 / (1.0 + age_in_days). Handles naive datetimes."""
    if now is None:
        now = datetime.now(tz=UTC)
    age_days = (now - ensure_utc_aware(updated_at)).total_seconds() / GRAPH_SECONDS_PER_DAY
    return 1.0 / (1.0 + age_days)


async def compute_degree_map(
    session: AsyncSession,
    node_ids: list[UUID],
    workspace_id: UUID | None = None,
) -> dict[UUID, int]:
    """Count total degree (in + out edges) for each node in a single UNION ALL query."""
    if not node_ids:
        return {}
    ws_conditions = (
        [GraphEdgeModel.workspace_id == workspace_id] if workspace_id is not None else []
    )
    out_q = (
        select(GraphEdgeModel.source_id.label("node_id"), func.count().label("cnt"))
        .where(GraphEdgeModel.source_id.in_(node_ids), *ws_conditions)
        .group_by(GraphEdgeModel.source_id)
    )
    in_q = (
        select(GraphEdgeModel.target_id.label("node_id"), func.count().label("cnt"))
        .where(GraphEdgeModel.target_id.in_(node_ids), *ws_conditions)
        .group_by(GraphEdgeModel.target_id)
    )
    combined = union_all(out_q, in_q).subquery()
    degree_q = select(combined.c.node_id, func.sum(combined.c.cnt).label("total")).group_by(
        combined.c.node_id
    )
    return {row.node_id: int(row.total) for row in (await session.execute(degree_q)).fetchall()}


def node_model_to_domain(model: GraphNodeModel) -> GraphNode:
    """Map GraphNodeModel ORM to GraphNode domain object."""
    embedding: list[float] | None = None
    raw = model.embedding
    if raw is not None:
        if isinstance(raw, str):
            embedding = [float(v) for v in raw.strip("[]").split(",") if v.strip()]
        elif hasattr(raw, "__iter__"):
            embedding = list(raw)
        if embedding is not None and len(embedding) != GRAPH_EMBEDDING_DIMS:
            logger.warning(
                "Embedding dim mismatch: expected %d, got %d for node %s",
                GRAPH_EMBEDDING_DIMS,
                len(embedding),
                model.id,
            )
            embedding = None

    return GraphNode(
        id=model.id,
        workspace_id=model.workspace_id,
        node_type=NodeType(model.node_type),
        label=model.label,
        content=model.content or "",
        properties=dict(model.properties) if model.properties else {},
        embedding=embedding,
        user_id=model.user_id,
        external_id=model.external_id,
        content_hash=model.content_hash,
        created_at=ensure_utc_aware(model.created_at),
        updated_at=ensure_utc_aware(model.updated_at),
    )


def edge_model_to_domain(model: GraphEdgeModel) -> GraphEdge:
    """Map GraphEdgeModel ORM to GraphEdge domain object."""
    return GraphEdge(
        id=model.id,
        source_id=model.source_id,
        target_id=model.target_id,
        edge_type=EdgeType(model.edge_type),
        properties=dict(model.properties) if model.properties else {},
        weight=model.weight,
        created_at=ensure_utc_aware(model.created_at),
    )


async def enrich_edge_density(
    session: AsyncSession,
    scored: list[ScoredNode],
    workspace_id: UUID | None = None,
) -> list[ScoredNode]:
    """Add edge_density_score to each ScoredNode.

    Counts both outgoing and incoming edges in a single UNION ALL query so
    target-only nodes are not penalised. Uses stable log-based normalization
    (``log1p(degree) / log1p(100)``) so the same node always gets the same
    score regardless of other nodes in the result set.
    workspace_id filters edges to the owning workspace only.
    """
    if not scored:
        return scored

    node_ids = [sn.node.id for sn in scored]
    degree_map = await compute_degree_map(session, node_ids, workspace_id)
    # Stable normalization: degree 0→0.0, 10→~0.52, 100→1.0
    log_100 = math.log1p(100)
    return [
        ScoredNode(
            node=sn.node,
            score=sn.score,
            embedding_score=sn.embedding_score,
            text_score=sn.text_score,
            recency_score=sn.recency_score,
            edge_density_score=min(1.0, math.log1p(degree_map.get(sn.node.id, 0)) / log_100),
        )
        for sn in scored
    ]


async def keyword_search(
    session: AsyncSession,
    query_text: str,
    workspace_id: UUID,
    node_types: list[NodeType] | None,
    limit: int,
    since: datetime | None = None,
) -> list[ScoredNode]:
    """SQLite-compatible LIKE keyword search."""
    # Escape LIKE metacharacters so user input like "%" or "_" is treated
    # as a literal character rather than a wildcard.
    escaped = query_text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    pattern = f"%{escaped}%"
    conditions: list[Any] = [
        GraphNodeModel.workspace_id == workspace_id,
        GraphNodeModel.is_deleted == False,  # noqa: E712
        or_(
            GraphNodeModel.label.ilike(pattern, escape="\\"),
            GraphNodeModel.content.ilike(pattern, escape="\\"),
        ),
    ]
    if node_types:
        conditions.append(GraphNodeModel.node_type.in_([str(nt) for nt in node_types]))
    if since is not None:
        conditions.append(GraphNodeModel.updated_at >= since)

    stmt = (
        select(GraphNodeModel)
        .where(and_(*conditions))
        .order_by(GraphNodeModel.updated_at.desc())
        .limit(limit)
    )
    result = await session.execute(stmt)
    models = result.scalars().all()

    now = datetime.now(tz=UTC)
    scored: list[ScoredNode] = []
    for model in models:
        recency = compute_recency_score(model.updated_at, now)
        scored.append(
            ScoredNode(
                node=node_model_to_domain(model),
                score=GRAPH_RECENCY_WEIGHT * recency + GRAPH_TEXT_WEIGHT,
                embedding_score=0.0,
                text_score=1.0,
                recency_score=recency,
                edge_density_score=0.0,
            )
        )
    return await enrich_edge_density(session, scored, workspace_id)


async def hybrid_search_pg(
    session: AsyncSession,
    query_embedding: list[float],
    query_text: str,
    workspace_id: UUID,
    node_types: list[NodeType] | None,
    limit: int,
    since: datetime | None = None,
) -> list[ScoredNode]:
    """PostgreSQL hybrid search using pgvector cosine + ts_rank fusion."""
    embedding_literal = serialize_embedding(query_embedding)

    # Use ANY(:node_types) to avoid f-string injection; pass None to skip filter.
    node_type_filter = "AND node_type = ANY(:node_types)" if node_types else ""
    node_types_param = [str(nt) for nt in node_types] if node_types else None

    since_filter = "AND updated_at >= :since" if since is not None else ""

    # CTE computes each component score once; ORDER BY references the alias
    # to avoid recomputing the expensive embedding <=> operation twice.
    raw = text(f"""
        WITH scored AS (
            SELECT id,
                (1 - (embedding <=> CAST(:embedding AS vector({GRAPH_EMBEDDING_DIMS})))) AS embedding_score,
                COALESCE(ts_rank(
                    to_tsvector('english', COALESCE(content,'') || ' ' || COALESCE(label,'')),
                    plainto_tsquery('english', :query_text)
                ), 0.0) AS text_score,
                1.0 / (1.0 + EXTRACT(EPOCH FROM (NOW() - updated_at)) / :spd) AS recency_score
            FROM graph_nodes
            WHERE workspace_id = :workspace_id AND is_deleted = false
              AND embedding IS NOT NULL {node_type_filter} {since_filter}
        )
        SELECT id, embedding_score, text_score, recency_score,
               :ew * embedding_score + :tw * text_score + :rw * recency_score AS combined_score
        FROM scored
        ORDER BY combined_score DESC
        LIMIT :limit
    """)
    params: dict[str, object] = {
        "embedding": embedding_literal,
        "query_text": query_text,
        "workspace_id": str(workspace_id),
        "spd": GRAPH_SECONDS_PER_DAY,
        "ew": GRAPH_EMBEDDING_WEIGHT,
        "tw": GRAPH_TEXT_WEIGHT,
        "rw": GRAPH_RECENCY_WEIGHT,
        "limit": limit,
    }
    if node_types_param is not None:
        params["node_types"] = node_types_param
    if since is not None:
        params["since"] = since
    rows = await session.execute(raw, params)
    row_maps = rows.mappings().all()
    if not row_maps:
        return []

    node_ids = [row["id"] for row in row_maps]
    model_result = await session.execute(
        select(GraphNodeModel).where(
            GraphNodeModel.id.in_(node_ids),
            GraphNodeModel.is_deleted == False,  # noqa: E712
        )
    )
    model_map: dict[UUID, GraphNodeModel] = {m.id: m for m in model_result.scalars().all()}

    scored: list[ScoredNode] = []
    for row in row_maps:
        model = model_map.get(row["id"])
        if model is None:
            continue
        emb, txt, rec = (
            float(row["embedding_score"]),
            float(row["text_score"]),
            float(row["recency_score"]),
        )
        scored.append(
            ScoredNode(
                node=node_model_to_domain(model),
                score=GRAPH_EMBEDDING_WEIGHT * emb
                + GRAPH_TEXT_WEIGHT * txt
                + GRAPH_RECENCY_WEIGHT * rec,
                embedding_score=emb,
                text_score=txt,
                recency_score=rec,
                edge_density_score=0.0,
            )
        )
    return await enrich_edge_density(session, scored, workspace_id)


# ---------------------------------------------------------------------------
# Node persistence helpers (extracted from KnowledgeGraphRepository to keep
# the repository file within the 700-line limit)
# ---------------------------------------------------------------------------


def build_graph_node_model(node: GraphNode) -> GraphNodeModel:
    """Build a GraphNodeModel from a GraphNode domain object.

    Uses all fields from the node as-is. Callers that need explicit
    external_id=None or content_hash=None should ensure the node object
    carries those values (already the case for unkeyed/unhashed subsets).
    """
    return GraphNodeModel(
        id=node.id,
        workspace_id=node.workspace_id,
        node_type=str(node.node_type),
        label=node.label,
        content=node.content,
        properties=node.properties,
        embedding=node.embedding,
        user_id=node.user_id,
        external_id=node.external_id,
        content_hash=node.content_hash,
    )


async def insert_node_helper(session: AsyncSession, node: GraphNode) -> GraphNode:
    """Insert a new GraphNode model, flush, refresh, and return domain object."""
    model = build_graph_node_model(node)
    session.add(model)
    await session.flush()
    await session.refresh(model)
    return node_model_to_domain(model)


async def update_node_helper(
    session: AsyncSession, model: GraphNodeModel, node: GraphNode
) -> GraphNode:
    """Apply mutable field updates from node to model, flush, refresh."""
    model.label = node.label
    model.content = node.content
    model.properties = node.properties
    model.updated_at = datetime.now(UTC)
    if node.embedding is not None:
        model.embedding = node.embedding
    await session.flush()
    await session.refresh(model)
    return node_model_to_domain(model)


async def find_node_by_external(
    session: AsyncSession,
    workspace_id: UUID,
    node_type: NodeType,
    external_id: UUID,
) -> GraphNodeModel | None:
    """Find an active node by (workspace_id, node_type, external_id)."""
    stmt = select(GraphNodeModel).where(
        GraphNodeModel.workspace_id == workspace_id,
        GraphNodeModel.node_type == str(node_type),
        GraphNodeModel.external_id == external_id,
        GraphNodeModel.is_deleted == False,  # noqa: E712
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def find_node_by_content_hash(
    session: AsyncSession,
    workspace_id: UUID,
    content_hash: str,
) -> GraphNodeModel | None:
    """Find an active node by (workspace_id, content_hash)."""
    stmt = select(GraphNodeModel).where(
        GraphNodeModel.workspace_id == workspace_id,
        GraphNodeModel.content_hash == content_hash,
        GraphNodeModel.is_deleted == False,  # noqa: E712
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def workspace_overview(
    session: AsyncSession,
    workspace_id: UUID,
    max_nodes: int = 200,
    node_types: list[NodeType] | None = None,
) -> tuple[list[GraphNode], list[GraphEdge]]:
    """Return all nodes and their inter-edges for a workspace.

    Nodes ordered by updated_at DESC, capped at max_nodes.
    Edges filtered to only include those between returned nodes.
    """
    conditions: list[Any] = [
        GraphNodeModel.workspace_id == workspace_id,
        GraphNodeModel.is_deleted == False,  # noqa: E712
    ]
    if node_types:
        conditions.append(GraphNodeModel.node_type.in_([nt.value for nt in node_types]))
    else:
        # Exclude chunk nodes from default overview — they crowd out structural nodes
        conditions.append(GraphNodeModel.node_type != NodeType.NOTE_CHUNK.value)

    stmt = (
        select(GraphNodeModel)
        .where(and_(*conditions))
        .order_by(GraphNodeModel.updated_at.desc())
        .limit(max_nodes)
    )
    node_models = (await session.execute(stmt)).scalars().all()
    nodes = [node_model_to_domain(m) for m in node_models]

    if not nodes:
        return nodes, []

    node_ids = [n.id for n in nodes]
    edge_filters: list[Any] = [
        GraphEdgeModel.source_id.in_(node_ids),
        GraphEdgeModel.target_id.in_(node_ids),
        GraphEdgeModel.workspace_id == workspace_id,
    ]
    edge_result = await session.execute(select(GraphEdgeModel).where(*edge_filters))
    edges = [edge_model_to_domain(m) for m in edge_result.scalars().all()]

    return nodes, edges
