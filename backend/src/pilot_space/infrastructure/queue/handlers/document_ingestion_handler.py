"""Background job handler: ingest uploaded documents into the Knowledge Graph.

Triggered after Office extraction (Phase 41) or OCR (Phase 42) finishes.
Creates DOCUMENT + DOCUMENT_CHUNK graph nodes with embedding similarity edges
to related notes and issues.

Feature 020: Chat Context Attachments — KG document ingestion pipeline.
Requirements: KG-01, KG-02, KG-03, KG-04

T-068 route: 'document_ingestion' → DocumentIngestionHandler
"""

from __future__ import annotations

import contextlib
import logging
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import delete, text
from sqlalchemy.ext.asyncio import AsyncSession

from pilot_space.application.services.embedding_service import EmbeddingService
from pilot_space.application.services.memory.graph_write_service import (
    GraphWritePayload,
    GraphWriteService,
    NodeInput,
)
from pilot_space.application.services.note.contextual_enrichment import (
    enrich_chunks_with_context,
)
from pilot_space.application.services.note.markdown_chunker import (
    chunk_markdown_by_headings,
)
from pilot_space.domain.graph_edge import EdgeType, GraphEdge
from pilot_space.domain.graph_node import NodeType
from pilot_space.domain.graph_query import ScoredNode
from pilot_space.infrastructure.database.models.chat_attachment import ChatAttachment
from pilot_space.infrastructure.database.models.graph_node import GraphNodeModel
from pilot_space.infrastructure.database.repositories.knowledge_graph_repository import (
    KnowledgeGraphRepository,
)
from pilot_space.infrastructure.queue.supabase_queue import SupabaseQueueClient

__all__ = ["TASK_DOCUMENT_INGESTION", "DocumentIngestionHandler"]

logger = logging.getLogger(__name__)

TASK_DOCUMENT_INGESTION = "document_ingestion"

_SIMILARITY_THRESHOLD = 0.75
_MAX_SIMILAR_EDGES = 5
_MIN_CHUNK_CHARS = 50
_MAX_CHUNK_CHARS = 2000
_OVERLAP_CHARS = 100

# Binary MIME types that have no inline text and should skip ingestion
# when no extraction result is available.
_BINARY_MIME_PREFIXES = ("image/", "audio/", "video/")
_BINARY_MIME_TYPES = frozenset(
    {
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "application/msword",
        "application/vnd.ms-excel",
        "application/vnd.ms-powerpoint",
        "application/octet-stream",
    }
)


@dataclass(frozen=True, slots=True)
class _DocumentIngestionPayload:
    workspace_id: UUID
    project_id: UUID
    attachment_id: UUID
    actor_user_id: UUID

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> _DocumentIngestionPayload:
        return cls(
            workspace_id=UUID(d["workspace_id"]),
            project_id=UUID(d["project_id"]),
            attachment_id=UUID(d["attachment_id"]),
            actor_user_id=UUID(d["actor_user_id"]),
        )


async def _resolve_extracted_text(
    session: AsyncSession,
    attachment: ChatAttachment,
) -> tuple[str, str] | None:
    """Return (extracted_text, source_label) or None if no text available.

    Priority:
      1. OCR result from ocr_results table (Phase 42 output)
      2. Office extraction result cache (Phase 41 output) — attachment.extracted_text
      3. Raw text for text/* MIME types
      4. None for binary files without extraction

    source_label: "ocr" | "office" | "raw"

    Notes:
        - OCR results table does not exist yet at planning time; query is
          wrapped in try/except to degrade gracefully until Phase 42 is wired.
        - TODO(Phase 42): Uncomment and finalize OCR query once ocr_results
          model is available.
        - Office extraction result is cached on attachment.extracted_text
          by AttachmentContentService (Phase 41).
    """
    mime_type = attachment.mime_type or ""

    # 1. OCR result (Phase 42 — ocr_results table)
    try:
        from sqlalchemy import select

        from pilot_space.infrastructure.database.models.ocr_result import OcrResultModel

        ocr_row = await session.execute(
            select(OcrResultModel)
            .where(OcrResultModel.attachment_id == attachment.id)
            .order_by(OcrResultModel.created_at.desc())
            .limit(1)
        )
        ocr = ocr_row.scalar()
        if ocr is not None and ocr.extracted_text:
            return (ocr.extracted_text, "ocr")
    except Exception:
        pass  # ocr_results table may not exist in test environments

    # 2. Office extraction result (Phase 41 — cached in attachment.extracted_text)
    extracted_text = getattr(attachment, "extracted_text", None)
    if extracted_text:
        return (extracted_text, "office")

    # 3. Raw text for text/* MIME types (no extraction needed)
    is_binary = mime_type.startswith(_BINARY_MIME_PREFIXES) or mime_type in _BINARY_MIME_TYPES
    if not is_binary and mime_type.startswith("text/"):
        # For text/* MIME types without extraction, the content is readable as-is.
        # The real implementation must read raw bytes from Supabase Storage via
        # AttachmentContentService when Phase 40 is complete.
        # For now: plain text attachments provide their filename as minimal content
        # so the DOCUMENT node exists and can be matched in the KG.
        return (f"# {attachment.filename}\n\n(text content not yet loaded)", "raw")

    # 4. Binary with no extraction available → skip KG ingestion
    return None


class DocumentIngestionHandler:
    """Ingest an uploaded document into the Knowledge Graph.

    Creates a DOCUMENT node + DOCUMENT_CHUNK nodes (stale chunks replaced on
    re-ingestion), then links to similar notes/issues via RELATES_TO edges.

    Invariants (same as KgPopulateHandler):
    - Validation errors return {"success": False} — worker ACKs, no retry.
    - Infrastructure errors propagate — worker retries or dead-letters.
    - Handler does NOT commit — worker owns the single commit per job.
    - Chunk nodes never carry external_id (only the parent DOCUMENT node does).
    """

    def __init__(
        self,
        session: AsyncSession,
        embedding_service: EmbeddingService,
        queue: SupabaseQueueClient | None,
        anthropic_api_key: str | None = None,
    ) -> None:
        self._session = session
        self._embedding = embedding_service
        self._queue = queue
        self._anthropic_api_key = anthropic_api_key
        self._repo = KnowledgeGraphRepository(session)

    async def handle(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Parse payload, resolve extracted text, and build KG nodes.

        Returns:
            {"success": True, "node_ids": [...], "chunks": N, "edges": N} on success.
            {"success": False, "error": str} for bad payload or missing attachment.
            {"success": False, "reason": "no_text_available"} for binary without extraction.
        """
        try:
            p = _DocumentIngestionPayload.from_dict(payload)
        except (KeyError, ValueError) as exc:
            logger.warning("DocumentIngestionHandler: invalid payload %r — %s", payload, exc)
            return {"success": False, "error": str(exc)}

        # Advisory lock — prevents concurrent chunk delete/recreate races.
        # Transaction-scoped; contextlib.suppress handles SQLite (no advisory locks in tests).
        lock_key = int.from_bytes(p.attachment_id.bytes[:8], "big") & 0x7FFFFFFFFFFFFFFF
        with contextlib.suppress(Exception):
            await self._session.execute(
                text("SELECT pg_advisory_xact_lock(:key)"), {"key": lock_key}
            )

        # Fetch ChatAttachment record for metadata
        attachment = await self._session.get(ChatAttachment, p.attachment_id)
        if attachment is None:
            logger.warning("DocumentIngestionHandler: attachment %s not found", p.attachment_id)
            return {"success": False, "error": "attachment not found"}

        # Resolve extracted text — OCR preferred, then Office, then raw text
        text_result = await _resolve_extracted_text(self._session, attachment)
        if text_result is None:
            logger.warning(
                "DocumentIngestionHandler: no extracted text for attachment %s "
                "(mime_type=%s) — skipping KG ingestion",
                p.attachment_id,
                attachment.mime_type,
            )
            return {"success": False, "reason": "no_text_available"}

        extracted_text, extraction_source = text_result
        filename: str = attachment.filename
        mime_type: str = attachment.mime_type
        size_bytes: int = attachment.size_bytes

        write_svc = GraphWriteService(
            knowledge_graph_repository=self._repo,
            queue=self._queue,
            session=self._session,
            auto_commit=False,
        )

        # Upsert parent DOCUMENT node (attachment_id is the stable external_id for upsert)
        parent_result = await write_svc.execute(
            GraphWritePayload(
                workspace_id=p.workspace_id,
                actor_user_id=p.actor_user_id,
                nodes=[
                    NodeInput(
                        node_type=NodeType.DOCUMENT,
                        label=filename[:120],
                        content=extracted_text[:2000],
                        external_id=p.attachment_id,  # upsert key — stable across re-ingestion
                        properties={
                            "filename": filename,
                            "mime_type": mime_type,
                            "size_bytes": size_bytes,
                            "extraction_source": extraction_source,
                            "project_id": str(p.project_id),
                        },
                    )
                ],
            )
        )

        parent_node_ids = parent_result.node_ids

        # Delete stale DOCUMENT_CHUNK nodes before recreating (idempotent on re-upload)
        await self._delete_stale_chunks(p.workspace_id, p.attachment_id)

        # Chunk extracted markdown
        chunks = chunk_markdown_by_headings(
            extracted_text,
            min_chunk_chars=_MIN_CHUNK_CHARS,
            max_chunk_chars=_MAX_CHUNK_CHARS,
            overlap_chars=_OVERLAP_CHARS,
        )

        # Optional LLM enrichment — BYOK guard: no-op when anthropic_api_key is None
        try:
            chunks = await enrich_chunks_with_context(
                chunks, extracted_text, api_key=self._anthropic_api_key
            )
        except Exception as exc:
            logger.warning("DocumentIngestionHandler: chunk enrichment failed: %s", exc)

        all_node_ids: list[UUID] = list(parent_node_ids)

        if chunks:
            # Pitfall 3 guard: NO external_id on chunk nodes
            chunk_nodes = [
                NodeInput(
                    node_type=NodeType.DOCUMENT_CHUNK,
                    label=(
                        f"{filename[:80]} \u203a {chunk.heading}"
                        if chunk.heading
                        else filename[:120]
                    ),
                    content=chunk.content[:2000],
                    properties={
                        "chunk_index": chunk.chunk_index,
                        "heading": chunk.heading,
                        "heading_level": chunk.heading_level,
                        "parent_document_id": str(p.attachment_id),
                        "project_id": str(p.project_id),
                    },
                    # NOTE: external_id intentionally NOT set on chunk nodes
                )
                for chunk in chunks
            ]

            chunk_result = await write_svc.execute(
                GraphWritePayload(
                    workspace_id=p.workspace_id,
                    actor_user_id=p.actor_user_id,
                    nodes=chunk_nodes,
                )
            )
            all_node_ids.extend(chunk_result.node_ids)

            # PARENT_OF edges: DOCUMENT node → each DOCUMENT_CHUNK node
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
                        logger.warning("DocumentIngestionHandler: PARENT_OF edge failed: %s", exc)
                await self._session.flush()

        edges_created = await self._find_and_link_similar(
            all_node_ids, p.workspace_id, p.project_id, extracted_text[:500]
        )

        n_chunks = len(all_node_ids) - len(parent_node_ids)
        logger.info(
            "DocumentIngestionHandler: attachment %s → %d nodes (%d chunks), %d similarity edges",
            p.attachment_id,
            len(all_node_ids),
            n_chunks,
            edges_created,
        )
        return {
            "success": True,
            "node_ids": [str(n) for n in all_node_ids],
            "chunks": n_chunks,
            "edges": edges_created,
        }

    async def _find_and_link_similar(
        self,
        node_ids: list[UUID],
        workspace_id: UUID,
        project_id: UUID,
        query_text: str,
    ) -> int:
        """Search for similar same-project nodes and create RELATES_TO edges.

        Mirrors KgPopulateHandler._find_and_link_similar() exactly.
        Threshold: 0.75, max edges: 5 (same as notes for consistency).
        """
        if not node_ids:
            return 0

        embedding = await self._embedding.embed(query_text)

        similar_nodes: list[ScoredNode] = await self._repo.hybrid_search(
            query_embedding=embedding,
            query_text=query_text,
            workspace_id=workspace_id,
            limit=_MAX_SIMILAR_EDGES + len(node_ids),
        )

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
        source_node_id = node_ids[0]  # anchor on the parent DOCUMENT node
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
                    "DocumentIngestionHandler: edge upsert failed %s→%s: %s",
                    source_node_id,
                    sn.node.id,
                    exc,
                )
        await self._session.flush()
        return edges_created

    async def _delete_stale_chunks(self, workspace_id: UUID, attachment_id: UUID) -> None:
        """Delete existing DOCUMENT_CHUNK nodes for this attachment before recreating.

        Mirrors KgPopulateHandler._delete_stale_chunks() for NOTE_CHUNK nodes.
        Uses parent_document_id property (not external_id — chunks have none).
        """
        await self._session.execute(
            delete(GraphNodeModel).where(
                GraphNodeModel.workspace_id == workspace_id,
                GraphNodeModel.node_type == NodeType.DOCUMENT_CHUNK.value,
                GraphNodeModel.properties["parent_document_id"].as_string() == str(attachment_id),
                GraphNodeModel.is_deleted == False,  # noqa: E712
            )
        )
