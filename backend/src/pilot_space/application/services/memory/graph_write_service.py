"""GraphWriteService — bulk node/edge upsert with async embedding enqueue.

Persists graph nodes and edges in a single transaction, resolves
external-id references for edge endpoints, and enqueues embedding
generation jobs to the ai_normal queue.

Feature 016: Knowledge Graph — Memory Engine replacement
"""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import and_, select

from pilot_space.domain.graph_edge import EdgeType, GraphEdge
from pilot_space.domain.graph_node import GraphNode, NodeType, compute_content_hash
from pilot_space.infrastructure.database.models.graph_node import GraphNodeModel
from pilot_space.infrastructure.logging import get_logger
from pilot_space.infrastructure.queue.models import QueueName

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from pilot_space.infrastructure.database.repositories.knowledge_graph_repository import (
        KnowledgeGraphRepository,
    )
    from pilot_space.infrastructure.queue.supabase_queue import SupabaseQueueClient

logger = get_logger(__name__)

_GRAPH_EMBEDDING_TASK_TYPE = "graph_embedding"
_MAX_EMBEDDING_CONCURRENCY = 10  # max in-flight enqueue coroutines per batch

# Node types that carry per-user identity in their content hash.
# For all other types the hash is workspace-scoped only, so two agents writing the
# same DECISION content under different user contexts share a single node.
_USER_SCOPED_NODE_TYPES: frozenset[NodeType] = frozenset(
    {NodeType.USER_PREFERENCE, NodeType.LEARNED_PATTERN}
)

# Regex for detecting issue identifiers like "PS-42" inside node content
_ISSUE_REF_PATTERN = re.compile(r"\b([A-Z]{1,10}-\d+)\b")


@dataclass(frozen=True, slots=True)
class NodeInput:
    """Input specification for a single graph node to upsert.

    Attributes:
        node_type: Discriminator type for the node.
        label: Human-readable display name.
        content: Searchable text content.
        properties: Type-specific metadata (JSONB).
        external_id: FK reference to the originating entity.
        user_id: Optional user scope for personal nodes.
    """

    node_type: NodeType
    label: str
    content: str
    properties: dict[str, object] = field(default_factory=dict)
    external_id: UUID | None = None
    user_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class EdgeInput:
    """Input specification for a directed graph edge.

    Exactly one of (source_external_id, source_node_id) must be set,
    and exactly one of (target_external_id, target_node_id) must be set.

    Attributes:
        source_external_id: External FK of the source entity (resolved to node_id).
        target_external_id: External FK of the target entity (resolved to node_id).
        source_node_id: Direct node UUID (takes precedence over external lookup).
        target_node_id: Direct node UUID (takes precedence over external lookup).
        edge_type: Semantic relationship type.
        weight: Relationship strength [0.0, 1.0].
        properties: Optional JSONB metadata for this edge.
    """

    source_external_id: UUID | None
    target_external_id: UUID | None
    source_node_id: UUID | None = None
    target_node_id: UUID | None = None
    edge_type: EdgeType = EdgeType.RELATES_TO
    weight: float = 0.5
    properties: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class GraphWritePayload:
    """Payload for a bulk graph write operation.

    Attributes:
        workspace_id: Owning workspace for all nodes and edges.
        nodes: Node inputs to upsert.
        edges: Edge inputs to upsert (optional).
        user_id: Optional user scope applied to all nodes.
    """

    workspace_id: UUID
    nodes: list[NodeInput]
    actor_user_id: UUID
    edges: list[EdgeInput] = field(default_factory=list)
    user_id: UUID | None = None
    issue_id: UUID | None = None


@dataclass
class GraphWriteResult:
    """Result from a bulk graph write operation.

    Attributes:
        node_ids: UUIDs of all persisted (inserted or updated) nodes.
        edge_ids: UUIDs of all persisted (inserted or updated) edges.
        embedding_enqueued: True when embedding jobs were submitted successfully.
        failed_edge_count: Number of edges that failed to persist (M-2).
    """

    node_ids: list[UUID]
    edge_ids: list[UUID]
    embedding_enqueued: bool
    failed_edge_count: int = 0


class GraphWriteService:
    """Bulk graph write service.

    Converts NodeInput/EdgeInput into domain objects, upserts them in a
    single transaction, optionally auto-detects issue references in content
    to create RELATES_TO edges, then enqueues embedding jobs for all
    persisted nodes.

    Example:
        service = GraphWriteService(knowledge_graph_repository, queue_client, session)
        result = await service.execute(GraphWritePayload(
            workspace_id=workspace_id,
            actor_user_id=user_id,
            nodes=[NodeInput(node_type=NodeType.ISSUE, label="PS-1", content="...")],
        ))
    """

    def __init__(
        self,
        knowledge_graph_repository: KnowledgeGraphRepository,
        queue: SupabaseQueueClient | None,
        session: AsyncSession,
        *,
        auto_commit: bool = True,
    ) -> None:
        """Initialize service.

        Args:
            knowledge_graph_repository: Repository for graph persistence.
            queue: Queue client for embedding job enqueue (None to skip enqueue).
            session: Async DB session.
            auto_commit: If True (default), commit the session after write.
                Set to False when the caller (e.g. worker) owns the commit.
        """
        self._repo = knowledge_graph_repository
        self._queue = queue
        self._session = session
        self._auto_commit = auto_commit

    async def execute(self, payload: GraphWritePayload) -> GraphWriteResult:
        """Upsert nodes and edges, then enqueue embedding jobs.

        Steps:
          1. Convert NodeInput → GraphNode domain objects.
          2. Bulk upsert nodes (single transaction).
          3. Resolve edge endpoints by external_id or direct node_id.
          4. Upsert each edge.
          5. Commit session.
          6. Auto-detect issue cross-references in node content.
          7. Enqueue embedding jobs for all persisted nodes.

        Args:
            payload: Bulk write specification.

        Returns:
            GraphWriteResult with persisted IDs and enqueue status.
        """
        # Step 1: build domain nodes (compute content_hash for unkeyed nodes)
        domain_nodes: list[GraphNode] = []
        for ni in payload.nodes:
            node = GraphNode.create(
                workspace_id=payload.workspace_id,
                node_type=ni.node_type,
                label=ni.label,
                content=ni.content,
                properties=dict(ni.properties),
                user_id=ni.user_id if ni.user_id is not None else payload.user_id,
                external_id=ni.external_id,
                content_hash=(
                    compute_content_hash(
                        payload.workspace_id,
                        str(ni.node_type),
                        ni.content,
                        # Only include user_id for user-scoped types so that
                        # workspace-shared nodes (DECISION, SKILL_OUTCOME, etc.)
                        # are not duplicated per-user when payload.user_id is set.
                        (ni.user_id if ni.user_id is not None else payload.user_id)
                        if ni.node_type in _USER_SCOPED_NODE_TYPES
                        else None,
                    )
                    if ni.external_id is None and ni.content
                    else None
                ),
            )
            domain_nodes.append(node)

        # Step 2: bulk upsert — returns persisted nodes (ids may differ on update)
        persisted_nodes = await self._repo.bulk_upsert_nodes(domain_nodes)

        # Build external_id → node_id lookup for edge resolution
        ext_id_map: dict[UUID, UUID] = {}
        for node in persisted_nodes:
            if node.external_id is not None:
                ext_id_map[node.external_id] = node.id

        # Step 3 + 4: resolve and upsert edges
        persisted_edges: list[GraphEdge] = []
        failed_edge_count = 0
        for ei in payload.edges:
            edge, failed = await self._upsert_edge_input(ei, ext_id_map, payload.workspace_id)
            if edge is not None:
                persisted_edges.append(edge)
            failed_edge_count += failed

        # Step 5 + 6: auto-detect issue references, then flush to assign IDs
        auto_edges = await self._detect_issue_references(persisted_nodes)
        persisted_edges = persisted_edges + auto_edges
        await self._session.flush()

        # Step 7: enqueue embedding jobs BEFORE commit so crash-recovery
        # doesn't leave nodes without embeddings (C-2 fix)
        node_ids = [n.id for n in persisted_nodes]
        embedding_enqueued = (
            await self._enqueue_embedding_jobs(node_ids, payload.workspace_id, payload.actor_user_id)
            if self._queue is not None
            else False
        )

        # Step 8: commit only when we own the transaction
        if self._auto_commit:
            await self._session.commit()

        logger.info(
            "GraphWriteService: workspace=%s nodes=%d edges=%d embedding=%s",
            payload.workspace_id,
            len(node_ids),
            len(persisted_edges),
            embedding_enqueued,
        )

        return GraphWriteResult(
            node_ids=node_ids,
            edge_ids=[e.id for e in persisted_edges],
            embedding_enqueued=embedding_enqueued,
            failed_edge_count=failed_edge_count,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _upsert_edge_input(
        self,
        ei: EdgeInput,
        ext_id_map: dict[UUID, UUID],
        workspace_id: UUID,
    ) -> tuple[GraphEdge | None, int]:
        """Resolve edge endpoints and upsert.

        Args:
            ei: Edge input specification.
            ext_id_map: Mapping from external_id to node_id for nodes
                persisted in the current batch.
            workspace_id: Workspace for cross-batch DB lookup.

        Returns:
            Tuple of (persisted GraphEdge or None, failed_count: 0 or 1).
        """
        source_id = ei.source_node_id or (
            ext_id_map.get(ei.source_external_id) if ei.source_external_id else None
        )
        target_id = ei.target_node_id or (
            ext_id_map.get(ei.target_external_id) if ei.target_external_id else None
        )

        # H-3: Fall back to DB lookup for cross-batch external IDs
        if source_id is None and ei.source_external_id is not None:
            source_id = await self._resolve_external_id(ei.source_external_id, workspace_id)
        if target_id is None and ei.target_external_id is not None:
            target_id = await self._resolve_external_id(ei.target_external_id, workspace_id)

        if source_id is None or target_id is None:
            logger.warning(
                "GraphWriteService: cannot resolve edge endpoints "
                "source_external=%s target_external=%s — skipping",
                ei.source_external_id,
                ei.target_external_id,
            )
            return None, 1

        if source_id == target_id:
            logger.warning("GraphWriteService: skipping self-loop edge for node %s", source_id)
            return None, 0

        edge = GraphEdge(
            source_id=source_id,
            target_id=target_id,
            edge_type=ei.edge_type,
            weight=ei.weight,
            properties=dict(ei.properties),
        )
        try:
            persisted = await self._repo.upsert_edge(edge)
            return persisted, 0
        except Exception:
            logger.error(
                "GraphWriteService: failed to upsert edge %s -> %s",
                source_id,
                target_id,
                exc_info=True,
            )
            return None, 1

    async def _resolve_external_id(self, external_id: UUID, workspace_id: UUID) -> UUID | None:
        """Look up a node by external_id in the DB (cross-batch fallback)."""
        stmt = (
            select(GraphNodeModel.id)
            .where(
                GraphNodeModel.workspace_id == workspace_id,
                GraphNodeModel.external_id == external_id,
                GraphNodeModel.is_deleted == False,  # noqa: E712
            )
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def _detect_issue_references(
        self,
        nodes: list[GraphNode],
    ) -> list[GraphEdge]:
        """Best-effort: detect issue identifiers (e.g. "PS-42") in content.

        For each ISSUE node whose content references another node, create a
        RELATES_TO edge. Checks both the current batch (by label) and
        previously persisted nodes in the same workspace (cross-batch).

        Args:
            nodes: Persisted nodes from the current batch.

        Returns:
            List of auto-detected and persisted edges.
        """
        label_map: dict[str, UUID] = {n.label: n.id for n in nodes}

        # Cache regex results per-node to avoid scanning content twice.
        issue_refs: dict[UUID, list[str]] = {
            node.id: _ISSUE_REF_PATTERN.findall(node.content)
            for node in nodes
            if node.node_type == NodeType.ISSUE
        }

        # Collect all referenced labels and resolve cross-batch ones from DB.
        all_refs: set[str] = {ref for refs in issue_refs.values() for ref in refs}
        cross_batch_refs = all_refs - label_map.keys()
        if cross_batch_refs:
            workspace_ids = {n.workspace_id for n in nodes}
            for workspace_id in workspace_ids:
                rows = await self._session.execute(
                    select(GraphNodeModel.label, GraphNodeModel.id).where(
                        and_(
                            GraphNodeModel.workspace_id == workspace_id,
                            GraphNodeModel.label.in_(list(cross_batch_refs)),
                            GraphNodeModel.is_deleted == False,  # noqa: E712
                        )
                    )
                )
                for label, node_id in rows.all():
                    if label not in label_map:
                        label_map[label] = node_id

        auto_edges: list[GraphEdge] = []
        for node in nodes:
            if node.node_type != NodeType.ISSUE:
                continue
            matches = issue_refs.get(node.id, [])
            for ref in matches:
                target_id = label_map.get(ref)
                if target_id is None or target_id == node.id:
                    continue
                try:
                    edge = GraphEdge(
                        source_id=node.id,
                        target_id=target_id,
                        edge_type=EdgeType.RELATES_TO,
                        weight=0.5,
                    )
                    persisted = await self._repo.upsert_edge(edge)
                    auto_edges.append(persisted)
                except Exception:
                    logger.debug(
                        "GraphWriteService: auto-edge upsert failed %s -> %s",
                        node.id,
                        target_id,
                        exc_info=True,
                    )
        return auto_edges

    async def _enqueue_embedding_jobs(
        self, node_ids: list[UUID], workspace_id: UUID, actor_user_id: UUID
    ) -> bool:
        """Enqueue graph_embedding jobs for all persisted nodes in parallel.

        Concurrency is bounded by a semaphore (max 10 in-flight) to prevent
        unbounded asyncio.gather from overwhelming the queue (H-2).

        Args:
            node_ids: Node UUIDs to embed.
            workspace_id: Workspace for context.
            actor_user_id: Acting user id for RLS context.

        Returns:
            True if all jobs enqueued successfully, False if any failed.
        """
        enqueued_at = datetime.now(tz=UTC).isoformat()
        sem = asyncio.Semaphore(_MAX_EMBEDDING_CONCURRENCY)

        async def _enqueue_one(node_id: UUID) -> bool:
            async with sem:
                job_payload: dict[str, Any] = {
                    "task_type": _GRAPH_EMBEDDING_TASK_TYPE,
                    "node_id": str(node_id),
                    "workspace_id": str(workspace_id),
                    "actor_user_id": str(actor_user_id),
                    "enqueued_at": enqueued_at,
                }
                try:
                    await self._queue.enqueue(QueueName.AI_NORMAL, job_payload)  # type: ignore[union-attr]
                    return True
                except Exception:
                    logger.error(
                        "GraphWriteService: failed to enqueue embedding for node %s",
                        node_id,
                        exc_info=True,
                    )
                    return False

        results = await asyncio.gather(*(_enqueue_one(nid) for nid in node_ids))
        return all(results)


__all__ = [
    "EdgeInput",
    "GraphWritePayload",
    "GraphWriteResult",
    "GraphWriteService",
    "NodeInput",
]
