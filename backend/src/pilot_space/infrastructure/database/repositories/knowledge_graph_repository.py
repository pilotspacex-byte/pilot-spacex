"""KnowledgeGraphRepository — data access layer for the knowledge graph.

Provides upsert, traversal, hybrid search, and subgraph extraction for
graph nodes and edges. PostgreSQL-specific features (recursive CTEs,
pgvector) are guarded by dialect detection; SQLite falls back to
equivalent loop-based or keyword-only implementations for testing.

Feature 016: Knowledge Graph — Memory Engine replacement
"""

from __future__ import annotations

from collections import deque
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import and_, func, or_, select, text, union_all

from pilot_space.domain.graph_edge import EdgeType, GraphEdge
from pilot_space.domain.graph_node import GraphNode, NodeType
from pilot_space.domain.graph_query import ScoredNode
from pilot_space.infrastructure.database.models.graph_edge import GraphEdgeModel
from pilot_space.infrastructure.database.models.graph_node import GraphNodeModel
from pilot_space.infrastructure.database.repositories._graph_helpers import (
    edge_model_to_domain,
    hybrid_search_pg,
    keyword_search,
    node_model_to_domain,
)
from pilot_space.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)


class KnowledgeGraphRepository:
    """Data access layer for knowledge graph nodes and edges.

    All methods are workspace-scoped. PostgreSQL-specific features
    (recursive CTE traversal, pgvector similarity) activate automatically;
    SQLite test environments fall back to BFS loops and LIKE keyword search.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with an async session."""
        self._session = session

    # Expose mappers as class attributes for external callers
    _model_to_domain = staticmethod(node_model_to_domain)
    edge_model_to_domain = staticmethod(edge_model_to_domain)

    def _is_sqlite(self) -> bool:
        """Return True when the session is connected to SQLite."""
        bind = self._session.get_bind()
        return getattr(bind, "dialect", None) is not None and bind.dialect.name == "sqlite"

    # ------------------------------------------------------------------
    # Node upsert
    # ------------------------------------------------------------------

    async def upsert_node(self, node: GraphNode) -> GraphNode:
        """Idempotently persist a graph node.

        Matches by ``(workspace_id, node_type, external_id)`` when external_id
        is set; otherwise always inserts.
        """
        if node.external_id is not None:
            existing = await self._find_node_by_external(
                workspace_id=node.workspace_id,
                node_type=node.node_type,
                external_id=node.external_id,
            )
            if existing is not None:
                return await self._update_node_model(existing, node)
        return await self._insert_node(node)

    async def _find_node_by_external(
        self, workspace_id: UUID, node_type: NodeType, external_id: UUID
    ) -> GraphNodeModel | None:
        stmt = select(GraphNodeModel).where(
            GraphNodeModel.workspace_id == workspace_id,
            GraphNodeModel.node_type == str(node_type),
            GraphNodeModel.external_id == external_id,
            GraphNodeModel.is_deleted == False,  # noqa: E712
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def _insert_node(self, node: GraphNode) -> GraphNode:
        model = GraphNodeModel(
            id=node.id,
            workspace_id=node.workspace_id,
            node_type=str(node.node_type),
            label=node.label,
            content=node.content,
            properties=node.properties,
            embedding=node.embedding,
            user_id=node.user_id,
            external_id=node.external_id,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return node_model_to_domain(model)

    async def _update_node_model(self, model: GraphNodeModel, node: GraphNode) -> GraphNode:
        model.label = node.label
        model.content = node.content
        model.properties = node.properties
        if node.embedding is not None:
            model.embedding = node.embedding
        await self._session.flush()
        await self._session.refresh(model)
        return node_model_to_domain(model)

    # ------------------------------------------------------------------
    # Edge upsert
    # ------------------------------------------------------------------

    async def upsert_edge(self, edge: GraphEdge) -> GraphEdge:
        """Idempotently persist an edge by (source_id, target_id, edge_type)."""
        stmt = select(GraphEdgeModel).where(
            GraphEdgeModel.source_id == edge.source_id,
            GraphEdgeModel.target_id == edge.target_id,
            GraphEdgeModel.edge_type == str(edge.edge_type),
        )
        existing = (await self._session.execute(stmt)).scalar_one_or_none()
        if existing is not None:
            existing.weight = edge.weight
            existing.properties = edge.properties
            await self._session.flush()
            await self._session.refresh(existing)
            return edge_model_to_domain(existing)

        # Derive workspace_id from source node; validate both endpoints exist.
        ws_result = await self._session.execute(
            select(GraphNodeModel.workspace_id).where(GraphNodeModel.id == edge.source_id)
        )
        workspace_id = ws_result.scalar_one_or_none()
        if workspace_id is None:
            raise ValueError(f"Source node {edge.source_id} not found")

        target_ws = (
            await self._session.execute(
                select(GraphNodeModel.workspace_id).where(GraphNodeModel.id == edge.target_id)
            )
        ).scalar_one_or_none()
        if target_ws != workspace_id:
            raise ValueError(f"Target node {edge.target_id} not in same workspace or not found")

        model = GraphEdgeModel(
            id=edge.id,
            source_id=edge.source_id,
            target_id=edge.target_id,
            workspace_id=workspace_id,
            edge_type=str(edge.edge_type),
            properties=edge.properties,
            weight=edge.weight,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return edge_model_to_domain(model)

    # ------------------------------------------------------------------
    # Neighbor traversal
    # ------------------------------------------------------------------

    async def get_neighbors(
        self,
        node_id: UUID,
        edge_types: list[EdgeType] | None = None,
        depth: int = 1,
        workspace_id: UUID | None = None,
    ) -> list[GraphNode]:
        """Return nodes reachable from node_id within depth hops.

        Uses recursive CTE on PostgreSQL; iterative BFS on SQLite.
        workspace_id is required to enforce cross-workspace boundary.
        """
        if self._is_sqlite():
            return await self._get_neighbors_bfs(node_id, edge_types, depth, workspace_id)
        return await self._get_neighbors_cte(node_id, edge_types, depth, workspace_id)

    async def _get_neighbors_bfs(
        self,
        node_id: UUID,
        edge_types: list[EdgeType] | None,
        max_depth: int,
        workspace_id: UUID | None = None,
    ) -> list[GraphNode]:
        visited: set[UUID] = {node_id}
        frontier: deque[UUID] = deque([node_id])
        result_ids: list[UUID] = []
        for _ in range(max_depth):
            if not frontier:
                break
            next_frontier: list[UUID] = []
            for current_id in frontier:
                for nid in await self._direct_neighbors(current_id, edge_types, workspace_id):
                    if nid not in visited:
                        visited.add(nid)
                        result_ids.append(nid)
                        next_frontier.append(nid)
            frontier = deque(next_frontier)
        if not result_ids:
            return []
        conditions: list[Any] = [
            GraphNodeModel.id.in_(result_ids),
            GraphNodeModel.is_deleted == False,  # noqa: E712
        ]
        if workspace_id is not None:
            conditions.append(GraphNodeModel.workspace_id == workspace_id)
        rows = await self._session.execute(select(GraphNodeModel).where(and_(*conditions)))
        return [node_model_to_domain(m) for m in rows.scalars().all()]

    async def _direct_neighbors(
        self,
        node_id: UUID,
        edge_types: list[EdgeType] | None,
        workspace_id: UUID | None = None,
    ) -> list[UUID]:
        """IDs of directly adjacent non-deleted nodes (both directions).

        Joining GraphNodeModel ensures soft-deleted nodes are excluded at the
        query level rather than filtered after the fact (M-3 fix).
        """
        edge_type_strs = [str(et) for et in edge_types] if edge_types else None

        conditions_out: list[Any] = [GraphEdgeModel.source_id == node_id]
        conditions_in: list[Any] = [GraphEdgeModel.target_id == node_id]
        if edge_type_strs is not None:
            conditions_out.append(GraphEdgeModel.edge_type.in_(edge_type_strs))
            conditions_in.append(GraphEdgeModel.edge_type.in_(edge_type_strs))
        if workspace_id is not None:
            conditions_out.append(GraphEdgeModel.workspace_id == workspace_id)
            conditions_in.append(GraphEdgeModel.workspace_id == workspace_id)

        # Join to graph_nodes so soft-deleted neighbors are excluded at DB level (M-3).
        stmt_out = (
            select(GraphEdgeModel.target_id)
            .join(GraphNodeModel, GraphEdgeModel.target_id == GraphNodeModel.id)
            .where(and_(*conditions_out), GraphNodeModel.is_deleted == False)  # noqa: E712
        )
        stmt_in = (
            select(GraphEdgeModel.source_id)
            .join(GraphNodeModel, GraphEdgeModel.source_id == GraphNodeModel.id)
            .where(and_(*conditions_in), GraphNodeModel.is_deleted == False)  # noqa: E712
        )
        stmt = stmt_out.union(stmt_in)
        return list((await self._session.execute(stmt)).scalars().all())

    async def _get_neighbors_cte(
        self,
        node_id: UUID,
        edge_types: list[EdgeType] | None,
        max_depth: int,
        workspace_id: UUID | None = None,
    ) -> list[GraphNode]:
        """Recursive CTE traversal for PostgreSQL.

        edge_types filtering uses ANY(:edge_types) to prevent SQL injection
        (C-1). workspace_id is pushed into the CTE anchor and final filter to
        enforce cross-workspace boundary (C-2).
        """
        # Only static SQL string fragments are f-string-interpolated — no user
        # data ever enters the SQL text directly.
        edge_type_clause = "AND edge_type = ANY(:edge_types)" if edge_types else ""
        ws_clause = "AND workspace_id = :workspace_id" if workspace_id is not None else ""
        ws_node_clause = "AND gn.workspace_id = :workspace_id" if workspace_id is not None else ""

        raw = text(
            f"""
            WITH RECURSIVE neighbors(id, depth) AS (
                SELECT target_id, 1 FROM graph_edges
                  WHERE source_id = :nid {edge_type_clause} {ws_clause}
                UNION ALL
                SELECT source_id, 1 FROM graph_edges
                  WHERE target_id = :nid {edge_type_clause} {ws_clause}
                UNION ALL
                SELECT e.target_id, n.depth+1 FROM graph_edges e
                  JOIN neighbors n ON e.source_id = n.id
                  WHERE n.depth < :md {edge_type_clause} {ws_clause}
                UNION ALL
                SELECT e.source_id, n.depth+1 FROM graph_edges e
                  JOIN neighbors n ON e.target_id = n.id
                  WHERE n.depth < :md {edge_type_clause} {ws_clause}
            )
            SELECT DISTINCT gn.id FROM graph_nodes gn JOIN neighbors nb ON gn.id = nb.id
            WHERE gn.is_deleted = false AND gn.id != :nid {ws_node_clause}
            """
        )
        params: dict[str, object] = {"nid": str(node_id), "md": max_depth}
        if edge_types:
            params["edge_types"] = [str(et) for et in edge_types]
        if workspace_id is not None:
            params["workspace_id"] = str(workspace_id)

        rows = await self._session.execute(raw, params)
        neighbor_ids = [row[0] for row in rows.fetchall()]
        if not neighbor_ids:
            return []
        node_conditions: list[Any] = [
            GraphNodeModel.id.in_(neighbor_ids),
            GraphNodeModel.is_deleted == False,  # noqa: E712
        ]
        if workspace_id is not None:
            node_conditions.append(GraphNodeModel.workspace_id == workspace_id)
        result = await self._session.execute(select(GraphNodeModel).where(and_(*node_conditions)))
        return [node_model_to_domain(m) for m in result.scalars().all()]

    # ------------------------------------------------------------------
    # Hybrid search (delegates to module-level helpers)
    # ------------------------------------------------------------------

    async def hybrid_search(
        self,
        query_embedding: list[float] | None,
        query_text: str,
        workspace_id: UUID,
        node_types: list[NodeType] | None = None,
        limit: int = 10,
    ) -> list[ScoredNode]:
        """Hybrid vector + full-text + recency search.

        Falls back to keyword-only LIKE search on SQLite or when no embedding
        is provided. Fusion: 0.5 * embedding + 0.2 * text + 0.2 * recency.
        """
        if self._is_sqlite() or not query_embedding:
            return await keyword_search(self._session, query_text, workspace_id, node_types, limit)
        return await hybrid_search_pg(
            self._session, query_embedding, query_text, workspace_id, node_types, limit
        )

    # ------------------------------------------------------------------
    # Subgraph extraction
    # ------------------------------------------------------------------

    async def get_subgraph(
        self,
        root_id: UUID,
        max_depth: int = 2,
        max_nodes: int = 50,
        workspace_id: UUID | None = None,
    ) -> tuple[list[GraphNode], list[GraphEdge]]:
        """BFS subgraph rooted at root_id, capped at max_nodes.

        Pruning priority: root first, then degree DESC, then recency DESC.
        workspace_id enforces cross-workspace isolation during BFS (C-2).
        """
        visited: set[UUID] = {root_id}
        frontier: list[UUID] = [root_id]
        all_ids: list[UUID] = [root_id]
        for _ in range(max_depth):
            if not frontier:
                break
            next_frontier: list[UUID] = []
            for current_id in frontier:
                for nid in await self._direct_neighbors(current_id, None, workspace_id):
                    if nid not in visited:
                        visited.add(nid)
                        all_ids.append(nid)
                        next_frontier.append(nid)
            frontier = next_frontier

        if len(all_ids) > max_nodes:
            all_ids = await self._prioritize_nodes(all_ids, root_id, max_nodes)

        node_result = await self._session.execute(
            select(GraphNodeModel).where(
                GraphNodeModel.id.in_(all_ids),
                GraphNodeModel.is_deleted == False,  # noqa: E712
            )
        )
        nodes = [node_model_to_domain(m) for m in node_result.scalars().all()]
        edge_result = await self._session.execute(
            select(GraphEdgeModel).where(
                GraphEdgeModel.source_id.in_(all_ids),
                GraphEdgeModel.target_id.in_(all_ids),
            )
        )
        edges = [edge_model_to_domain(m) for m in edge_result.scalars().all()]
        return nodes, edges

    async def _prioritize_nodes(
        self, node_ids: list[UUID], root_id: UUID, max_nodes: int
    ) -> list[UUID]:
        # Count outgoing and incoming edges separately, then union and sum so
        # that nodes which only receive edges still accumulate degree (H-1).
        out_q = (
            select(GraphEdgeModel.source_id.label("node_id"), func.count().label("cnt"))
            .where(GraphEdgeModel.source_id.in_(node_ids))
            .group_by(GraphEdgeModel.source_id)
        )
        in_q = (
            select(GraphEdgeModel.target_id.label("node_id"), func.count().label("cnt"))
            .where(GraphEdgeModel.target_id.in_(node_ids))
            .group_by(GraphEdgeModel.target_id)
        )
        combined = union_all(out_q, in_q).subquery()
        degree_q = select(
            combined.c.node_id, func.sum(combined.c.cnt).label("total_degree")
        ).group_by(combined.c.node_id)
        degree_result = await self._session.execute(degree_q)
        degree_map: dict[UUID, int] = {row.node_id: row.total_degree for row in degree_result}
        models = {
            m.id: m
            for m in (
                await self._session.execute(
                    select(GraphNodeModel).where(GraphNodeModel.id.in_(node_ids))
                )
            )
            .scalars()
            .all()
        }

        def _sort_key(nid: UUID) -> tuple[int, int, float]:
            model = models.get(nid)
            updated = model.updated_at if model else datetime.min.replace(tzinfo=UTC)
            return (0 if nid == root_id else 1, -degree_map.get(nid, 0), -updated.timestamp())

        return sorted(node_ids, key=_sort_key)[:max_nodes]

    # ------------------------------------------------------------------
    # User context
    # ------------------------------------------------------------------

    async def get_user_context(
        self,
        user_id: UUID,
        workspace_id: UUID,
        limit: int = 10,
    ) -> list[GraphNode]:
        """Recent nodes scoped to a user or belonging to their workspace."""
        stmt = (
            select(GraphNodeModel)
            .where(
                GraphNodeModel.workspace_id == workspace_id,
                GraphNodeModel.is_deleted == False,  # noqa: E712
                or_(
                    GraphNodeModel.user_id == user_id,
                    GraphNodeModel.user_id == None,  # noqa: E711
                ),
            )
            .order_by(GraphNodeModel.updated_at.desc())
            .limit(limit)
        )
        return [
            node_model_to_domain(m) for m in (await self._session.execute(stmt)).scalars().all()
        ]

    # ------------------------------------------------------------------
    # Bulk operations
    # ------------------------------------------------------------------

    async def bulk_upsert_nodes(self, nodes: list[GraphNode]) -> list[GraphNode]:
        """Batch upsert: 3 queries for PostgreSQL regardless of N.

        SQLite falls back to serial upsert (test environments only).
        PostgreSQL path:
          1. SELECT batch-find all keyed nodes
          2. Single flush for all updates + inserts
          3. SELECT batch-refresh all final node IDs
        """
        if not nodes:
            return []
        if self._is_sqlite():
            return [await self.upsert_node(node) for node in nodes]
        return await self._bulk_upsert_pg(nodes)

    async def _bulk_upsert_pg(self, nodes: list[GraphNode]) -> list[GraphNode]:
        """PostgreSQL-only batch upsert implementation."""
        keyed = [n for n in nodes if n.external_id is not None]
        unkeyed = [n for n in nodes if n.external_id is None]

        final_ids: list[UUID] = []

        # (1) Batch-find all existing keyed nodes in one SELECT
        if keyed:
            conditions = or_(
                *[
                    and_(
                        GraphNodeModel.workspace_id == n.workspace_id,
                        GraphNodeModel.node_type == str(n.node_type),
                        GraphNodeModel.external_id == n.external_id,
                        GraphNodeModel.is_deleted == False,  # noqa: E712
                    )
                    for n in keyed
                ]
            )
            existing_models = (
                (await self._session.execute(select(GraphNodeModel).where(conditions)))
                .scalars()
                .all()
            )
            existing_map: dict[tuple[UUID, str, UUID | None], GraphNodeModel] = {
                (m.workspace_id, m.node_type, m.external_id): m for m in existing_models
            }

            for node in keyed:
                key = (node.workspace_id, str(node.node_type), node.external_id)
                existing = existing_map.get(key)
                if existing is not None:
                    existing.label = node.label
                    existing.content = node.content
                    existing.properties = node.properties
                    if node.embedding is not None:
                        existing.embedding = node.embedding
                    final_ids.append(existing.id)
                else:
                    self._session.add(
                        GraphNodeModel(
                            id=node.id,
                            workspace_id=node.workspace_id,
                            node_type=str(node.node_type),
                            label=node.label,
                            content=node.content,
                            properties=node.properties,
                            embedding=node.embedding,
                            user_id=node.user_id,
                            external_id=node.external_id,
                        )
                    )
                    final_ids.append(node.id)

        for node in unkeyed:
            self._session.add(
                GraphNodeModel(
                    id=node.id,
                    workspace_id=node.workspace_id,
                    node_type=str(node.node_type),
                    label=node.label,
                    content=node.content,
                    properties=node.properties,
                    embedding=node.embedding,
                    user_id=node.user_id,
                    external_id=None,
                )
            )
            final_ids.append(node.id)

        # (2) Single flush for all pending changes
        await self._session.flush()

        # (3) Batch refresh
        refreshed = (
            (
                await self._session.execute(
                    select(GraphNodeModel).where(GraphNodeModel.id.in_(final_ids))
                )
            )
            .scalars()
            .all()
        )
        id_to_model: dict[UUID, GraphNodeModel] = {m.id: m for m in refreshed}
        return [node_model_to_domain(id_to_model[nid]) for nid in final_ids if nid in id_to_model]

    # ------------------------------------------------------------------
    # Soft-delete expiry
    # ------------------------------------------------------------------

    async def delete_expired_nodes(self, before: datetime) -> int:
        """Soft-delete stale unpinned nodes with updated_at < before.

        Returns count of nodes soft-deleted.
        """
        result = await self._session.execute(
            select(GraphNodeModel).where(
                GraphNodeModel.updated_at < before,
                GraphNodeModel.is_deleted == False,  # noqa: E712
            )
        )
        candidates = result.scalars().all()
        now = datetime.now(tz=UTC)
        count = 0
        for model in candidates:
            if (model.properties or {}).get("pinned"):
                continue
            model.is_deleted = True
            model.deleted_at = now
            count += 1
        if count:
            await self._session.flush()
        return count


__all__ = ["KnowledgeGraphRepository"]
