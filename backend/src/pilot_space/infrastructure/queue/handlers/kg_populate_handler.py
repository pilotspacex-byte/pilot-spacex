"""KG populate handler: build graph nodes from SDLC entities.

Triggered on entity create/update. Upserts nodes, creates BELONGS_TO
edges to project, PARENT_OF edges to chunks, and RELATES_TO edges
via embedding similarity.
"""

from __future__ import annotations

import contextlib
import logging
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import and_, delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from pilot_space.application.services.embedding_service import (
    EmbeddingConfig,
    EmbeddingService,
)
from pilot_space.application.services.memory.graph_write_service import (
    GraphWritePayload,
    GraphWriteService,
    NodeInput,
)
from pilot_space.application.services.note.content_converter import ContentConverter
from pilot_space.application.services.note.contextual_enrichment import (
    enrich_chunks_with_context,
)
from pilot_space.application.services.note.markdown_chunker import (
    chunk_markdown_by_headings,
)
from pilot_space.domain.graph_edge import EdgeType, GraphEdge
from pilot_space.domain.graph_node import NodeType
from pilot_space.domain.graph_query import ScoredNode
from pilot_space.infrastructure.database.models.cycle import Cycle as CycleModel
from pilot_space.infrastructure.database.models.graph_edge import GraphEdgeModel
from pilot_space.infrastructure.database.models.graph_node import GraphNodeModel
from pilot_space.infrastructure.database.models.issue import Issue as IssueModel
from pilot_space.infrastructure.database.models.note import Note as NoteModel
from pilot_space.infrastructure.database.models.project import Project as ProjectModel
from pilot_space.infrastructure.database.repositories.knowledge_graph_repository import (
    KnowledgeGraphRepository,
)
from pilot_space.infrastructure.queue.supabase_queue import SupabaseQueueClient

__all__ = ["TASK_KG_POPULATE", "KgPopulateHandler"]

logger = logging.getLogger(__name__)

TASK_KG_POPULATE = "kg_populate"

_SIMILARITY_THRESHOLD = 0.75
_MAX_SIMILAR_EDGES = 5
_MIN_CHUNK_CHARS = 50  # merge heading sections shorter than this


@dataclass(frozen=True, slots=True)
class _KgPopulatePayload:
    workspace_id: UUID
    project_id: UUID
    entity_type: str  # "issue" | "note" | "project" | "cycle"
    entity_id: UUID

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> _KgPopulatePayload:
        return cls(
            workspace_id=UUID(d["workspace_id"]),
            project_id=UUID(d["project_id"]),
            entity_type=d["entity_type"],
            entity_id=UUID(d["entity_id"]),
        )


class KgPopulateHandler:
    """Populate KG nodes for SDLC entities, then link similar project content.

    Validation errors return {"success": False} (non-retryable).
    Infrastructure errors propagate for worker retry/dead-letter.
    Handler does NOT commit — the worker owns the single commit per job.
    """

    def __init__(
        self,
        session: AsyncSession,
        embedding_service: EmbeddingService,
        queue: SupabaseQueueClient | None,
        anthropic_api_key: str | None = None,
    ) -> None:
        self._session = session
        self._fallback_embedding = embedding_service
        self._embedding = embedding_service
        self._queue = queue
        self._anthropic_api_key = anthropic_api_key
        self._repo = KnowledgeGraphRepository(session)
        self._converter = ContentConverter()

    async def _resolve_workspace_embedding(self, workspace_id: UUID) -> None:
        """Resolve workspace BYOK embedding key, falling back to server key."""
        try:
            from pilot_space.ai.agents.pilotspace_stream_utils import get_workspace_embedding_key

            key = await get_workspace_embedding_key(self._session, workspace_id)
            if key:
                self._embedding = EmbeddingService(EmbeddingConfig(openai_api_key=key))
                return
        except Exception:
            pass
        self._embedding = self._fallback_embedding

    async def handle(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Dispatch to _handle_issue or _handle_note based on entity_type.

        Validation errors (bad payload, unknown entity_type) return
        ``{"success": False}`` so the worker ACKs them. Infrastructure
        errors propagate as exceptions for worker retry / dead-letter.
        """
        try:
            p = _KgPopulatePayload.from_dict(payload)
        except (KeyError, ValueError) as exc:
            logger.warning("KgPopulateHandler: invalid payload %r — %s", payload, exc)
            return {"success": False, "error": str(exc)}

        # Resolve workspace BYOK embedding key (falls back to server key)
        await self._resolve_workspace_embedding(p.workspace_id)

        if p.entity_type == "issue":
            return await self._handle_issue(p)
        if p.entity_type == "note":
            return await self._handle_note(p)
        if p.entity_type == "project":
            return await self._handle_project(p)
        if p.entity_type == "cycle":
            return await self._handle_cycle(p)
        logger.warning("KgPopulateHandler: unknown entity_type %r", p.entity_type)
        return {"success": False, "error": f"unknown entity_type: {p.entity_type}"}

    async def _handle_issue(self, p: _KgPopulatePayload) -> dict[str, Any]:
        issue = await self._session.get(IssueModel, p.entity_id)
        if issue is None or issue.is_deleted:
            logger.warning("KgPopulateHandler: issue %s not found", p.entity_id)
            return {"success": False, "error": "issue not found"}

        content = f"{issue.name}\n\n{issue.description or ''}".strip()
        label = issue.name[:120]
        issue_props: dict[str, object] = {
            "project_id": str(issue.project_id),
            "identifier": getattr(issue, "identifier", ""),
            "state": str(getattr(issue, "state_id", "") or ""),
        }

        write_svc = GraphWriteService(
            knowledge_graph_repository=self._repo,
            queue=self._queue,
            session=self._session,
            auto_commit=False,
        )
        result = await write_svc.execute(
            GraphWritePayload(
                workspace_id=issue.workspace_id,
                nodes=[
                    NodeInput(
                        node_type=NodeType.ISSUE,
                        label=label,
                        content=content[:2000],
                        external_id=p.entity_id,
                        properties=issue_props,
                    )
                ],
            )
        )

        all_node_ids: list[UUID] = list(result.node_ids)

        # Chunk long issue descriptions into NOTE_CHUNK nodes
        # Delete stale issue chunks first (idempotent regeneration)
        await self._delete_stale_issue_chunks(issue.workspace_id, p.entity_id)
        description = issue.description or ""
        if len(description) > _MIN_CHUNK_CHARS:
            issue_md = f"# {issue.name}\n\n{description}"
            chunks = chunk_markdown_by_headings(issue_md, min_chunk_chars=_MIN_CHUNK_CHARS)
            try:
                chunks = await enrich_chunks_with_context(
                    chunks, issue_md, api_key=self._anthropic_api_key
                )
            except Exception as exc:
                logger.warning("KgPopulateHandler: issue chunk enrichment failed: %s", exc)
            if len(chunks) > 1:
                chunk_nodes = [
                    NodeInput(
                        node_type=NodeType.NOTE_CHUNK,
                        label=f"{label} › {chunk.heading}" if chunk.heading else label,
                        content=chunk.content[:2000],
                        properties={
                            **issue_props,
                            "chunk_index": chunk.chunk_index,
                            "heading": chunk.heading,
                            "parent_issue_id": str(p.entity_id),
                        },
                    )
                    for chunk in chunks
                ]
                chunk_result = await write_svc.execute(
                    GraphWritePayload(
                        workspace_id=issue.workspace_id,
                        nodes=chunk_nodes,
                    )
                )
                all_node_ids.extend(chunk_result.node_ids)

                # PARENT_OF edges: issue node → each chunk
                if result.node_ids and chunk_result.node_ids:
                    parent_id = result.node_ids[0]
                    for chunk_node_id in chunk_result.node_ids:
                        try:
                            edge = GraphEdge(
                                source_id=parent_id,
                                target_id=chunk_node_id,
                                edge_type=EdgeType.PARENT_OF,
                                weight=1.0,
                            )
                            await self._repo.upsert_edge(edge)
                        except Exception as exc:
                            logger.warning(
                                "KgPopulateHandler: issue chunk PARENT_OF edge failed: %s", exc
                            )
                    await self._session.flush()

        # BELONGS_TO edge: issue → project (use loaded model, not stale payload)
        belongs_to = False
        if result.node_ids:
            belongs_to = await self._link_to_project(
                result.node_ids[0], issue.workspace_id, issue.project_id
            )

        edges_created = 0
        if all_node_ids:
            edges_created = await self._find_and_link_similar(
                all_node_ids, issue.workspace_id, issue.project_id, content
            )

        n_chunks = len(all_node_ids) - len(result.node_ids)
        logger.info(
            "KgPopulateHandler: issue %s → %d nodes (%d chunks), %d similarity edges, belongs_to=%s",
            p.entity_id,
            len(all_node_ids),
            n_chunks,
            edges_created,
            belongs_to,
        )
        return {
            "success": True,
            "node_ids": [str(n) for n in all_node_ids],
            "chunks": n_chunks,
            "edges": edges_created,
        }

    async def _handle_note(self, p: _KgPopulatePayload) -> dict[str, Any]:
        # C-3: Advisory lock prevents concurrent chunk delete/recreate races.
        # Transaction-scoped — auto-releases on worker commit/rollback.
        # contextlib.suppress: SQLite (tests) has no advisory locks.
        lock_key = int.from_bytes(p.entity_id.bytes[:8], "big") & 0x7FFFFFFFFFFFFFFF
        with contextlib.suppress(Exception):
            await self._session.execute(
                text("SELECT pg_advisory_xact_lock(:key)"), {"key": lock_key}
            )

        result_row = await self._session.execute(
            select(NoteModel).where(
                NoteModel.id == p.entity_id,
                NoteModel.is_deleted == False,  # noqa: E712
            )
        )
        note = result_row.scalar_one_or_none()
        if note is None:
            logger.warning("KgPopulateHandler: note %s not found", p.entity_id)
            return {"success": False, "error": "note not found"}

        # Convert TipTap JSON → Markdown
        tiptap_content: dict[str, Any] = note.content or {}
        markdown = self._converter.tiptap_to_markdown(tiptap_content)
        label = (note.title or "Untitled")[:120]

        write_svc = GraphWriteService(
            knowledge_graph_repository=self._repo,
            queue=self._queue,
            session=self._session,
            auto_commit=False,
        )

        # Upsert the parent NOTE node
        parent_result = await write_svc.execute(
            GraphWritePayload(
                workspace_id=note.workspace_id,
                nodes=[
                    NodeInput(
                        node_type=NodeType.NOTE,
                        label=label,
                        content=markdown[:2000],  # cap for embedding token budget
                        external_id=p.entity_id,
                        properties={
                            "project_id": str(note.project_id),
                            "title": note.title or "",
                        },
                    )
                ],
            )
        )

        parent_node_ids = parent_result.node_ids

        # Delete stale NOTE_CHUNK nodes for this note (replaced on each run)
        await self._delete_stale_chunks(note.workspace_id, p.entity_id)

        # Chunk markdown and upsert chunk nodes with PARENT_OF edges
        chunks = chunk_markdown_by_headings(markdown, min_chunk_chars=_MIN_CHUNK_CHARS)
        try:
            chunks = await enrich_chunks_with_context(
                chunks, markdown, api_key=self._anthropic_api_key
            )
        except Exception as exc:
            logger.warning("KgPopulateHandler: note chunk enrichment failed: %s", exc)
        all_node_ids: list[UUID] = list(parent_node_ids)

        if chunks:
            chunk_nodes = [
                NodeInput(
                    node_type=NodeType.NOTE_CHUNK,
                    label=f"{label} › {chunk.heading}" if chunk.heading else label,
                    content=chunk.content[:2000],
                    properties={
                        "chunk_index": chunk.chunk_index,
                        "heading": chunk.heading,
                        "heading_level": chunk.heading_level,
                        "parent_note_id": str(p.entity_id),
                        "project_id": str(note.project_id),
                    },
                )
                for chunk in chunks
            ]

            chunk_result = await write_svc.execute(
                GraphWritePayload(
                    workspace_id=note.workspace_id,
                    nodes=chunk_nodes,
                )
            )
            all_node_ids.extend(chunk_result.node_ids)

            # Add PARENT_OF edges: parent note node → each chunk node
            if parent_node_ids and chunk_result.node_ids:
                parent_node_id = parent_node_ids[0]
                for chunk_node_id in chunk_result.node_ids:
                    try:
                        edge = GraphEdge(
                            source_id=parent_node_id,
                            target_id=chunk_node_id,
                            edge_type=EdgeType.PARENT_OF,
                            weight=1.0,
                        )
                        await self._repo.upsert_edge(edge)
                    except Exception as exc:
                        logger.warning("KgPopulateHandler: PARENT_OF edge failed: %s", exc)
                await self._session.flush()

        # BELONGS_TO edge: note → project (use loaded model, not stale payload)
        belongs_to = False
        if parent_node_ids and note.project_id is not None:
            belongs_to = await self._link_to_project(
                parent_node_ids[0], note.workspace_id, note.project_id
            )

        edges_created = 0
        if note.project_id is not None:
            edges_created = await self._find_and_link_similar(
                all_node_ids, note.workspace_id, note.project_id, markdown[:500]
            )

        logger.info(
            "KgPopulateHandler: note %s → %d nodes (%d chunks), %d similarity edges, belongs_to=%s",
            p.entity_id,
            len(all_node_ids),
            len(chunks),
            edges_created,
            belongs_to,
        )
        return {
            "success": True,
            "node_ids": [str(n) for n in all_node_ids],
            "chunks": len(chunks),
            "edges": edges_created,
        }

    async def _handle_project(self, p: _KgPopulatePayload) -> dict[str, Any]:
        project = await self._session.get(ProjectModel, p.entity_id)
        if project is None or project.is_deleted:
            logger.warning("KgPopulateHandler: project %s not found", p.entity_id)
            return {"success": False, "error": "project not found"}

        content = f"{project.name}\n\n{project.description or ''}".strip()
        label = project.name[:120]

        write_svc = GraphWriteService(
            knowledge_graph_repository=self._repo,
            queue=self._queue,
            session=self._session,
            auto_commit=False,
        )
        result = await write_svc.execute(
            GraphWritePayload(
                workspace_id=project.workspace_id,
                nodes=[
                    NodeInput(
                        node_type=NodeType.PROJECT,
                        label=label,
                        content=content,
                        external_id=p.entity_id,
                        properties={
                            "project_id": str(project.id),
                            "identifier": getattr(project, "identifier", ""),
                            "icon": getattr(project, "icon", "") or "",
                            "lead_id": str(project.lead_id) if project.lead_id else "",
                        },
                    )
                ],
            )
        )

        # Link existing child entities (issues/notes/cycles) to this project node
        children_linked = 0
        if result.node_ids:
            children_linked = await self._link_existing_children(
                result.node_ids[0], project.workspace_id, project.id
            )

        edges_created = 0
        if result.node_ids:
            edges_created = await self._find_and_link_similar(
                result.node_ids, project.workspace_id, project.id, content
            )

        logger.info(
            "KgPopulateHandler: project %s → node %s, %d children linked, %d similarity edges",
            p.entity_id,
            result.node_ids[0] if result.node_ids else None,
            children_linked,
            edges_created,
        )
        return {
            "success": True,
            "node_ids": [str(n) for n in result.node_ids],
            "children_linked": children_linked,
            "edges": edges_created,
        }

    async def _handle_cycle(self, p: _KgPopulatePayload) -> dict[str, Any]:
        cycle = await self._session.get(CycleModel, p.entity_id)
        if cycle is None or cycle.is_deleted:
            logger.warning("KgPopulateHandler: cycle %s not found", p.entity_id)
            return {"success": False, "error": "cycle not found"}

        date_range = ""
        if cycle.start_date and cycle.end_date:
            date_range = f" [{cycle.start_date} → {cycle.end_date}]"
        elif cycle.start_date:
            date_range = f" [from {cycle.start_date}]"

        status_str = cycle.status.value if cycle.status else ""
        content = f"{cycle.name} ({status_str}){date_range}\n\n{cycle.description or ''}".strip()
        label = cycle.name[:120]

        write_svc = GraphWriteService(
            knowledge_graph_repository=self._repo,
            queue=self._queue,
            session=self._session,
            auto_commit=False,
        )
        result = await write_svc.execute(
            GraphWritePayload(
                workspace_id=cycle.workspace_id,
                nodes=[
                    NodeInput(
                        node_type=NodeType.CYCLE,
                        label=label,
                        content=content,
                        external_id=p.entity_id,
                        properties={
                            "project_id": str(cycle.project_id),
                            "status": status_str,
                            "start_date": str(cycle.start_date) if cycle.start_date else "",
                            "end_date": str(cycle.end_date) if cycle.end_date else "",
                            "owned_by_id": str(cycle.owned_by_id) if cycle.owned_by_id else "",
                        },
                    )
                ],
            )
        )

        # BELONGS_TO edge: cycle → project (use loaded model, not stale payload)
        belongs_to = False
        if result.node_ids:
            belongs_to = await self._link_to_project(
                result.node_ids[0], cycle.workspace_id, cycle.project_id
            )

        edges_created = 0
        if result.node_ids:
            edges_created = await self._find_and_link_similar(
                result.node_ids, cycle.workspace_id, cycle.project_id, content
            )

        logger.info(
            "KgPopulateHandler: cycle %s → node %s, %d similarity edges, belongs_to=%s",
            p.entity_id,
            result.node_ids[0] if result.node_ids else None,
            edges_created,
            belongs_to,
        )
        return {
            "success": True,
            "node_ids": [str(n) for n in result.node_ids],
            "edges": edges_created,
        }

    async def _link_to_project(
        self,
        entity_node_id: UUID,
        workspace_id: UUID,
        project_id: UUID,
    ) -> bool:
        """Create BELONGS_TO edge entity→project. Returns False if project node missing."""
        project_node = await self._repo.find_node_by_external_id(project_id, workspace_id)
        if project_node is None:
            logger.debug(
                "KgPopulateHandler: project node not found for %s, skipping BELONGS_TO",
                project_id,
            )
            return False
        if entity_node_id == project_node.id:
            return False
        # Remove stale BELONGS_TO edges (entity may have moved to a different project)
        await self._session.execute(
            delete(GraphEdgeModel).where(
                GraphEdgeModel.source_id == entity_node_id,
                GraphEdgeModel.edge_type == EdgeType.BELONGS_TO.value,
                GraphEdgeModel.target_id != project_node.id,
            )
        )
        try:
            edge = GraphEdge(
                source_id=entity_node_id,
                target_id=project_node.id,
                edge_type=EdgeType.BELONGS_TO,
                weight=1.0,
            )
            await self._repo.upsert_edge(edge)
            await self._session.flush()
            return True
        except ValueError as exc:
            logger.warning(
                "KgPopulateHandler: BELONGS_TO edge failed %s→%s: %s",
                entity_node_id,
                project_node.id,
                exc,
            )
            return False

    async def _link_existing_children(
        self,
        project_node_id: UUID,
        workspace_id: UUID,
        project_id: UUID,
    ) -> int:
        """Create BELONGS_TO edges from existing child nodes to the project node."""
        child_types = [
            NodeType.ISSUE.value,
            NodeType.NOTE.value,
            NodeType.CYCLE.value,
        ]
        stmt = select(GraphNodeModel).where(
            and_(
                GraphNodeModel.workspace_id == workspace_id,
                GraphNodeModel.node_type.in_(child_types),
                GraphNodeModel.properties["project_id"].as_string() == str(project_id),
                GraphNodeModel.is_deleted == False,  # noqa: E712
            )
        )
        result = await self._session.execute(stmt)
        children = result.scalars().all()

        edges_created = 0
        for child in children:
            if child.id == project_node_id:
                continue
            try:
                edge = GraphEdge(
                    source_id=child.id,
                    target_id=project_node_id,
                    edge_type=EdgeType.BELONGS_TO,
                    weight=1.0,
                )
                await self._repo.upsert_edge(edge)
                edges_created += 1
            except ValueError as exc:
                logger.warning(
                    "KgPopulateHandler: BELONGS_TO edge failed %s→%s: %s",
                    child.id,
                    project_node_id,
                    exc,
                )
        if edges_created:
            await self._session.flush()
        return edges_created

    async def _find_and_link_similar(
        self,
        node_ids: list[UUID],
        workspace_id: UUID,
        project_id: UUID,
        query_text: str,
    ) -> int:
        """Search for similar same-project nodes and create RELATES_TO edges."""
        if not node_ids:
            return 0

        # Generate embedding for the query text
        embedding = await self._embedding.embed(query_text)

        similar_nodes: list[ScoredNode] = await self._repo.hybrid_search(
            query_embedding=embedding,
            query_text=query_text,
            workspace_id=workspace_id,
            limit=_MAX_SIMILAR_EDGES + len(node_ids),
        )

        # Filter: same project, above threshold, not self
        node_id_set = set(node_ids)
        candidates = [
            sn
            for sn in similar_nodes
            if sn.score >= _SIMILARITY_THRESHOLD
            and sn.node.id not in node_id_set
            and sn.node.properties.get("project_id") == str(project_id)
        ][:_MAX_SIMILAR_EDGES]

        if not candidates:
            return 0

        edges_created = 0
        source_node_id = node_ids[0]  # anchor on the first node (parent/issue)
        for sn in candidates:
            if source_node_id == sn.node.id:
                continue
            try:
                edge = GraphEdge(
                    source_id=source_node_id,
                    target_id=sn.node.id,
                    edge_type=EdgeType.RELATES_TO,
                    weight=min(max(round(sn.score, 4), 0.0), 1.0),
                )
                await self._repo.upsert_edge(edge)
                edges_created += 1
            except Exception as exc:
                logger.warning(
                    "KgPopulateHandler: edge upsert failed %s→%s: %s",
                    source_node_id,
                    sn.node.id,
                    exc,
                )
        await self._session.flush()
        return edges_created

    async def _delete_stale_chunks(self, workspace_id: UUID, note_id: UUID) -> None:
        """Remove previous NOTE_CHUNK nodes for this note before recreating them."""
        await self._session.execute(
            delete(GraphNodeModel).where(
                GraphNodeModel.workspace_id == workspace_id,
                GraphNodeModel.node_type == NodeType.NOTE_CHUNK.value,
                GraphNodeModel.properties["parent_note_id"].as_string() == str(note_id),
                GraphNodeModel.is_deleted == False,  # noqa: E712
            )
        )

    async def _delete_stale_issue_chunks(self, workspace_id: UUID, issue_id: UUID) -> None:
        """Remove previous NOTE_CHUNK nodes for this issue before recreating them."""
        await self._session.execute(
            delete(GraphNodeModel).where(
                GraphNodeModel.workspace_id == workspace_id,
                GraphNodeModel.node_type == NodeType.NOTE_CHUNK.value,
                GraphNodeModel.properties["parent_issue_id"].as_string() == str(issue_id),
                GraphNodeModel.is_deleted == False,  # noqa: E712
            )
        )
