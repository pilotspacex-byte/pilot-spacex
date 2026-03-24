"""KnowledgeGraphRepository — data access for the knowledge graph.

Provides upsert, traversal, hybrid search, and subgraph extraction.
PostgreSQL-specific features guarded by dialect detection; SQLite
falls back to loop-based or keyword-only implementations for testing.
"""

from __future__ import annotations

from collections import deque
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import and_, or_, select, text
from sqlalchemy.exc import IntegrityError

from pilot_space.domain.graph_edge import EdgeType, GraphEdge
from pilot_space.domain.graph_node import GraphNode, NodeType
from pilot_space.domain.graph_query import ScoredNode
from pilot_space.infrastructure.database.models.graph_edge import GraphEdgeModel
from pilot_space.infrastructure.database.models.graph_node import GraphNodeModel
from pilot_space.infrastructure.database.repositories._graph_helpers import (
    build_graph_node_model,
    compute_degree_map,
    edge_model_to_domain,
    ensure_utc_aware,
    find_node_by_content_hash,
    find_node_by_external,
    hybrid_search_pg,
    insert_node_helper,
    keyword_search,
    node_model_to_domain,
    update_node_helper,
    workspace_overview,
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
        bind = session.get_bind()
        self._is_sqlite: bool = (
            getattr(bind, "dialect", None) is not None and bind.dialect.name == "sqlite"
        )

    # ------------------------------------------------------------------
    # Node upsert
    # ------------------------------------------------------------------

    async def _touch_and_return(self, model: GraphNodeModel) -> GraphNode:
        """Refresh the updated_at timestamp, flush, and return domain object."""
        model.updated_at = datetime.now(UTC)
        await self._session.flush()
        await self._session.refresh(model)
        return node_model_to_domain(model)

    async def upsert_node(self, node: GraphNode) -> GraphNode:
        """Idempotently persist a graph node.

        Lookup: 1) external_id, 2) content_hash, 3) insert new.
        """
        if node.external_id is not None:
            existing = await self._find_node_by_external(
                workspace_id=node.workspace_id,
                node_type=node.node_type,
                external_id=node.external_id,
            )
            if existing is not None:
                return await self._update_node_model(existing, node)
        elif node.content_hash is not None:
            existing = await self._find_node_by_content_hash(
                workspace_id=node.workspace_id,
                content_hash=node.content_hash,
            )
            if existing is not None:
                # Same normalized content — just refresh the timestamp.
                # Hash collision here means semantically identical content.
                return await self._touch_and_return(existing)
        try:
            return await self._insert_node(node)
        except IntegrityError:
            # Concurrent insert raced past the content_hash check above.
            # The UNIQUE partial index on (workspace_id, content_hash) enforces
            # dedup at the DB level — recover by querying the winner.
            await self._session.rollback()
            if node.content_hash is not None:
                existing = await self._find_node_by_content_hash(
                    workspace_id=node.workspace_id,
                    content_hash=node.content_hash,
                )
                if existing is not None:
                    return await self._touch_and_return(existing)
            raise

    async def _find_node_by_external(
        self, workspace_id: UUID, node_type: NodeType, external_id: UUID
    ) -> GraphNodeModel | None:
        return await find_node_by_external(self._session, workspace_id, node_type, external_id)

    async def _find_node_by_content_hash(
        self, workspace_id: UUID, content_hash: str
    ) -> GraphNodeModel | None:
        return await find_node_by_content_hash(self._session, workspace_id, content_hash)

    async def _insert_node(self, node: GraphNode) -> GraphNode:
        return await insert_node_helper(self._session, node)

    async def _update_node_model(self, model: GraphNodeModel, node: GraphNode) -> GraphNode:
        return await update_node_helper(self._session, model, node)

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

        # Derive workspace_id from source node; validate both endpoints are active.
        ws_result = await self._session.execute(
            select(GraphNodeModel.workspace_id).where(
                GraphNodeModel.id == edge.source_id,
                GraphNodeModel.is_deleted == False,  # noqa: E712
            )
        )
        workspace_id = ws_result.scalar_one_or_none()
        if workspace_id is None:
            raise ValueError(f"Source node {edge.source_id} not found or is deleted")

        target_ws = (
            await self._session.execute(
                select(GraphNodeModel.workspace_id).where(
                    GraphNodeModel.id == edge.target_id,
                    GraphNodeModel.is_deleted == False,  # noqa: E712
                )
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
        if self._is_sqlite:
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
        edge_type_clause = "AND e.edge_type = ANY(:edge_types)" if edge_types else ""
        ws_clause = "AND e.workspace_id = :workspace_id" if workspace_id is not None else ""

        raw = text(
            f"""
            WITH RECURSIVE neighbors(id, depth) AS (
                -- Anchor: direct neighbors in both directions (exclude deleted)
                SELECT cand.id, 1
                  FROM graph_edges e
                  JOIN graph_nodes cand
                    ON cand.id = CASE WHEN e.source_id = :nid THEN e.target_id ELSE e.source_id END
                   AND cand.is_deleted = false
                  WHERE (e.source_id = :nid OR e.target_id = :nid) {edge_type_clause} {ws_clause}
                UNION ALL
                -- Recursive: expand bidirectionally, skip deleted + anti-backtrack
                SELECT cand.id, n.depth + 1
                  FROM graph_edges e
                  JOIN neighbors n ON (e.source_id = n.id OR e.target_id = n.id)
                  JOIN graph_nodes cand
                    ON cand.id = CASE WHEN e.source_id = n.id THEN e.target_id ELSE e.source_id END
                   AND cand.is_deleted = false
                  WHERE n.depth < :md
                    AND cand.id != n.id
                    {edge_type_clause} {ws_clause}
            )
            SELECT DISTINCT nb.id FROM neighbors nb
            WHERE nb.id != :nid
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
        since: datetime | None = None,
    ) -> list[ScoredNode]:
        """Hybrid vector + full-text + recency search.

        Falls back to keyword-only LIKE search on SQLite or when no embedding
        is provided. Fusion: 0.5 * embedding + 0.2 * text + 0.2 * recency.
        """
        if self._is_sqlite or not query_embedding:
            return await keyword_search(
                self._session, query_text, workspace_id, node_types, limit, since=since
            )
        return await hybrid_search_pg(
            self._session, query_embedding, query_text, workspace_id, node_types, limit, since=since
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
        frontier: deque[UUID] = deque([root_id])
        all_ids: list[UUID] = [root_id]
        for _ in range(max_depth):
            if not frontier:
                break
            next_frontier: deque[UUID] = deque()
            for current_id in frontier:
                for nid in await self._direct_neighbors(current_id, None, workspace_id):
                    if nid not in visited:
                        visited.add(nid)
                        all_ids.append(nid)
                        next_frontier.append(nid)
            frontier = next_frontier

        if len(all_ids) > max_nodes:
            all_ids = await self._prioritize_nodes(all_ids, root_id, max_nodes, workspace_id)

        node_result = await self._session.execute(
            select(GraphNodeModel).where(
                GraphNodeModel.id.in_(all_ids),
                GraphNodeModel.is_deleted == False,  # noqa: E712
            )
        )
        nodes = [node_model_to_domain(m) for m in node_result.scalars().all()]
        edge_filters: list[Any] = [
            GraphEdgeModel.source_id.in_(all_ids),
            GraphEdgeModel.target_id.in_(all_ids),
        ]
        if workspace_id is not None:
            edge_filters.append(GraphEdgeModel.workspace_id == workspace_id)
        edge_result = await self._session.execute(select(GraphEdgeModel).where(*edge_filters))
        edges = [edge_model_to_domain(m) for m in edge_result.scalars().all()]
        return nodes, edges

    async def _prioritize_nodes(
        self,
        node_ids: list[UUID],
        root_id: UUID,
        max_nodes: int,
        workspace_id: UUID | None = None,
    ) -> list[UUID]:
        # Count outgoing + incoming edges in one UNION ALL query via shared helper.
        degree_map = await compute_degree_map(self._session, node_ids, workspace_id)
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
            updated = (
                ensure_utc_aware(model.updated_at) if model else datetime.min.replace(tzinfo=UTC)
            )
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

    async def get_workspace_overview(
        self,
        workspace_id: UUID,
        max_nodes: int = 200,
        node_types: list[NodeType] | None = None,
    ) -> tuple[list[GraphNode], list[GraphEdge]]:
        """Return all workspace nodes + inter-edges (delegates to _graph_helpers)."""
        return await workspace_overview(self._session, workspace_id, max_nodes, node_types)

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
        if self._is_sqlite:
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
                    existing.updated_at = datetime.now(UTC)
                    if node.embedding is not None:
                        existing.embedding = node.embedding
                    final_ids.append(existing.id)
                else:
                    self._session.add(build_graph_node_model(node))
                    final_ids.append(node.id)

        # (1b) Batch-find unkeyed nodes with content_hash for dedup
        hashed_unkeyed = [n for n in unkeyed if n.content_hash is not None]
        unhashed_unkeyed = [n for n in unkeyed if n.content_hash is None]

        if hashed_unkeyed:
            hash_conditions = or_(
                *[
                    and_(
                        GraphNodeModel.workspace_id == n.workspace_id,
                        GraphNodeModel.content_hash == n.content_hash,
                        GraphNodeModel.is_deleted == False,  # noqa: E712
                    )
                    for n in hashed_unkeyed
                ]
            )
            existing_hash_models = (
                (await self._session.execute(select(GraphNodeModel).where(hash_conditions)))
                .scalars()
                .all()
            )
            hash_map: dict[str, GraphNodeModel] = {
                m.content_hash: m for m in existing_hash_models if m.content_hash
            }
            # Track hashes already added in this batch to avoid same-batch
            # IntegrityError when two NodeInputs normalize to the same content_hash.
            # Maps content_hash → the winning node id so duplicates can reference it.
            batch_hash_to_id: dict[str, UUID] = {}
            for node in hashed_unkeyed:
                node_hash = node.content_hash or ""
                existing = hash_map.get(node_hash)
                if existing is not None:
                    existing.updated_at = datetime.now(UTC)
                    final_ids.append(existing.id)
                    batch_hash_to_id[node_hash] = existing.id
                elif node_hash and node_hash in batch_hash_to_id:
                    # Duplicate in this batch — the first insert wins; reference its id.
                    final_ids.append(batch_hash_to_id[node_hash])
                else:
                    self._session.add(build_graph_node_model(node))
                    final_ids.append(node.id)
                    if node_hash:
                        batch_hash_to_id[node_hash] = node.id

        for node in unhashed_unkeyed:
            self._session.add(build_graph_node_model(node))
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
        """Soft-delete stale unpinned nodes (updated_at < before). Returns count."""
        now = datetime.now(tz=UTC)
        if not self._is_sqlite:
            # PostgreSQL: bulk UPDATE — filters pinned via JSONB cast
            result = await self._session.execute(
                text(
                    "UPDATE graph_nodes "
                    "SET is_deleted = true, deleted_at = :now "
                    "WHERE updated_at < :before "
                    "  AND is_deleted = false "
                    "  AND COALESCE((properties->>'pinned')::boolean, false) = false"
                ),
                {"before": before, "now": now},
            )
            count = result.rowcount  # type: ignore[union-attr]
            if count:
                await self._session.flush()
            return count

        # SQLite fallback: Python loop (tests only)
        result = await self._session.execute(
            select(GraphNodeModel).where(
                GraphNodeModel.updated_at < before,
                GraphNodeModel.is_deleted == False,  # noqa: E712
            )
        )
        candidates = result.scalars().all()
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

    async def get_node_by_id(self, node_id: UUID, workspace_id: UUID) -> GraphNode | None:
        """Fetch a single active node by id within the given workspace."""
        stmt = select(GraphNodeModel).where(
            GraphNodeModel.id == node_id,
            GraphNodeModel.workspace_id == workspace_id,
            GraphNodeModel.is_deleted == False,  # noqa: E712
        )
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return node_model_to_domain(model) if model else None

    async def find_node_by_external_id(
        self, external_id: UUID, workspace_id: UUID
    ) -> GraphNode | None:
        """Fetch a single active node by external_id within the given workspace."""
        stmt = (
            select(GraphNodeModel)
            .where(
                GraphNodeModel.external_id == external_id,
                GraphNodeModel.workspace_id == workspace_id,
                GraphNodeModel.is_deleted == False,  # noqa: E712
            )
            .limit(1)
        )
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return node_model_to_domain(model) if model else None

    async def get_edges_between(
        self,
        node_ids: list[UUID],
        workspace_id: UUID | None = None,
    ) -> list[GraphEdge]:
        """Return all edges where both source and target are in node_ids.

        Single SELECT — no N+1. Used by GraphSearchService to build the
        intra-result sub-graph for display.

        Args:
            node_ids: Pool of node UUIDs to check membership.
            workspace_id: Optional workspace scope filter.

        Returns:
            Edges where both endpoints appear in node_ids.
        """
        if not node_ids:
            return []
        filters: list[Any] = [
            GraphEdgeModel.source_id.in_(node_ids),
            GraphEdgeModel.target_id.in_(node_ids),
        ]
        if workspace_id is not None:
            filters.append(GraphEdgeModel.workspace_id == workspace_id)
        stmt = select(GraphEdgeModel).where(*filters)
        result = await self._session.execute(stmt)
        return [edge_model_to_domain(m) for m in result.scalars().all()]


__all__ = ["KnowledgeGraphRepository"]
