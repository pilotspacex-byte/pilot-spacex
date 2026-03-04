"""Internal helper functions for KnowledgeGraphRepository.

Extracted to keep knowledge_graph_repository.py within the 700-line limit.
Not part of the public API — import from knowledge_graph_repository instead.
"""

from __future__ import annotations

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

# Score fusion weights (shared with graph_search_service)
GRAPH_EMBEDDING_WEIGHT = 0.5
GRAPH_TEXT_WEIGHT = 0.2
GRAPH_RECENCY_WEIGHT = 0.2
GRAPH_SECONDS_PER_DAY = 86_400.0

# Embedding vector dimension — must match migration 057 (resized from 1536 → 768)
GRAPH_EMBEDDING_DIMS = 768


def _ensure_utc_aware(dt: datetime) -> datetime:
    """Return dt with UTC tzinfo, adding it if the datetime is naive."""
    return dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt


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
        created_at=_ensure_utc_aware(model.created_at),
        updated_at=_ensure_utc_aware(model.updated_at),
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
        created_at=_ensure_utc_aware(model.created_at),
    )


async def enrich_edge_density(
    session: AsyncSession,
    scored: list[ScoredNode],
    workspace_id: UUID | None = None,
) -> list[ScoredNode]:
    """Add edge_density_score to each ScoredNode.

    Counts both outgoing and incoming edges in a single UNION ALL query so
    target-only nodes are not penalised. Normalises by max_degree within the
    result set. workspace_id filters edges to the owning workspace only.
    """
    if not scored:
        return scored

    node_ids = [sn.node.id for sn in scored]
    ws_conditions = (
        [GraphEdgeModel.workspace_id == workspace_id] if workspace_id is not None else []
    )
    out_q = (
        select(GraphEdgeModel.source_id.label("node_id"), func.count().label("degree"))
        .where(GraphEdgeModel.source_id.in_(node_ids), *ws_conditions)
        .group_by(GraphEdgeModel.source_id)
    )
    in_q = (
        select(GraphEdgeModel.target_id.label("node_id"), func.count().label("degree"))
        .where(GraphEdgeModel.target_id.in_(node_ids), *ws_conditions)
        .group_by(GraphEdgeModel.target_id)
    )
    combined = union_all(out_q, in_q).subquery()
    degree_q = select(combined.c.node_id, func.sum(combined.c.degree).label("total")).group_by(
        combined.c.node_id
    )

    degree_map: dict[UUID, int] = {
        row.node_id: int(row.total) for row in (await session.execute(degree_q)).fetchall()
    }

    max_degree = max(degree_map.values(), default=1)
    return [
        ScoredNode(
            node=sn.node,
            score=sn.score,
            embedding_score=sn.embedding_score,
            text_score=sn.text_score,
            recency_score=sn.recency_score,
            edge_density_score=degree_map.get(sn.node.id, 0) / (max_degree + 1),
        )
        for sn in scored
    ]


async def keyword_search(
    session: AsyncSession,
    query_text: str,
    workspace_id: UUID,
    node_types: list[NodeType] | None,
    limit: int,
) -> list[ScoredNode]:
    """SQLite-compatible LIKE keyword search."""
    pattern = f"%{query_text}%"
    conditions: list[Any] = [
        GraphNodeModel.workspace_id == workspace_id,
        GraphNodeModel.is_deleted == False,  # noqa: E712
        or_(GraphNodeModel.label.ilike(pattern), GraphNodeModel.content.ilike(pattern)),
    ]
    if node_types:
        conditions.append(GraphNodeModel.node_type.in_([str(nt) for nt in node_types]))

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
        updated = _ensure_utc_aware(model.updated_at)
        age_days = (now - updated).total_seconds() / GRAPH_SECONDS_PER_DAY
        recency = 1.0 / (1.0 + age_days)
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
) -> list[ScoredNode]:
    """PostgreSQL hybrid search using pgvector cosine + ts_rank fusion."""
    embedding_literal = "[" + ",".join(str(v) for v in query_embedding) + "]"

    # Use ANY(:node_types) to avoid f-string injection; pass None to skip filter.
    node_type_filter = "AND node_type = ANY(:node_types)" if node_types else ""
    node_types_param = [str(nt) for nt in node_types] if node_types else None

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
              AND embedding IS NOT NULL {node_type_filter}
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
    rows = await session.execute(raw, params)
    row_maps = rows.mappings().all()
    if not row_maps:
        return []

    node_ids = [row["id"] for row in row_maps]
    model_result = await session.execute(
        select(GraphNodeModel).where(GraphNodeModel.id.in_(node_ids))
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
