"""Phase 70-06 — ``summarize_note`` queue handler (Task 2).

Background summarizer that rolls up all ``NOTE_CHUNK`` rows for a given
note into a single ``NOTE_CHUNK`` row tagged ``properties.kind="summary"``
with a back-reference to the source note (``source_note_id``) and the
list of source chunk IDs. Triggered via a delayed (~5 min) pgmq message
from ``KgPopulateHandler._handle_note`` after the raw chunks are written.

Contract
--------

* Non-fatal: every failure mode (settings read, LLM call, Redis
  throttle, DB write) is logged and swallowed. The worker must never
  crash on a summarizer job.
* Opt-in: ``workspace.settings["memory_producers"]["summarizer"]`` must
  be ``True`` (default ``False``); otherwise the handler short-circuits.
* Throttled per workspace: at most 10 summarizations per hour, keyed
  by ``summarize:throttle:{workspace_id}`` in Redis. Redis failures are
  treated as "not throttled" (fail-open on a soft limit).
* Dedup at enqueue time: the producer (in ``kg_populate_handler``)
  checks pgmq for an existing unconsumed ``summarize_note`` message
  with the same ``note_id`` and skips the delayed enqueue if one is
  already in flight. The handler itself does NOT re-check; by the time
  it runs, any duplicate enqueue has been absorbed by the debounce
  window.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import select

from pilot_space.ai.providers.provider_selector import TaskType
from pilot_space.application.services.memory.graph_write_service import (
    GraphWritePayload,
    GraphWriteService,
    NodeInput,
)
from pilot_space.application.services.workspace_ai_settings_toggles import (
    get_producer_toggles,
)
from pilot_space.domain.graph_node import NodeType
from pilot_space.infrastructure.database.models.graph_node import GraphNodeModel
from pilot_space.infrastructure.database.repositories.knowledge_graph_repository import (
    KnowledgeGraphRepository,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from pilot_space.ai.proxy.llm_gateway import LLMGateway
    from pilot_space.infrastructure.queue.supabase_queue import SupabaseQueueClient

logger = logging.getLogger(__name__)

TASK_SUMMARIZE_NOTE = "summarize_note"

_THROTTLE_KEY_FMT = "summarize:throttle:{workspace_id}"
_THROTTLE_LIMIT = 10  # max summarizations per workspace per hour
_THROTTLE_TTL_S = 3600
_MAX_INPUT_CHARS = 40_000  # concatenation cap before LLM call
_MAX_OUTPUT_CHARS = 2000  # graph_nodes.content cap


@dataclass(frozen=True, slots=True)
class _SummarizePayload:
    workspace_id: UUID
    actor_user_id: UUID
    note_id: UUID

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> _SummarizePayload:
        return cls(
            workspace_id=UUID(str(d["workspace_id"])),
            actor_user_id=UUID(str(d["actor_user_id"])),
            note_id=UUID(str(d["note_id"])),
        )


class SummarizeNoteHandler:
    """Rolls up raw NOTE_CHUNK rows for a note into a single summary row."""

    def __init__(
        self,
        session: AsyncSession,
        llm_gateway: LLMGateway | None,
        queue: SupabaseQueueClient | None = None,
        redis_client: Any = None,
    ) -> None:
        self._session = session
        self._llm_gateway = llm_gateway
        self._queue = queue
        self._redis = redis_client
        self._repo = KnowledgeGraphRepository(session)

    async def handle(self, payload: dict[str, Any]) -> dict[str, Any]:  # noqa: PLR0911
        """Consume one ``summarize_note`` queue message. Never raises."""
        try:
            p = _SummarizePayload.from_dict(payload)
        except (KeyError, ValueError) as exc:
            logger.warning("SummarizeNoteHandler: invalid payload %r — %s", payload, exc)
            return {"success": False, "error": "invalid_payload"}

        # 1. Opt-in gate
        try:
            toggles = await get_producer_toggles(self._session, p.workspace_id)
        except Exception:
            logger.exception(
                "SummarizeNoteHandler: settings read failed (workspace=%s) — skip",
                p.workspace_id,
            )
            return {"success": False, "error": "settings_read_failed"}

        if not toggles.summarizer:
            logger.info(
                "SummarizeNoteHandler: summarizer disabled for workspace %s — skip",
                p.workspace_id,
            )
            return {"success": True, "skipped": "opt_in_off"}

        # 2. Throttle (best-effort — Redis failures fall through)
        if await self._throttle_exceeded(p.workspace_id):
            logger.info(
                "SummarizeNoteHandler: throttle exceeded for workspace %s — skip",
                p.workspace_id,
            )
            return {"success": True, "skipped": "throttled"}

        # 3. Fetch raw chunks
        chunks = await self._fetch_raw_chunks(p.workspace_id, p.note_id)
        if not chunks:
            logger.info(
                "SummarizeNoteHandler: no raw chunks for note %s — skip",
                p.note_id,
            )
            return {"success": True, "skipped": "no_chunks"}

        concatenated = self._concat_chunks(chunks)
        if not concatenated.strip():
            return {"success": True, "skipped": "empty_content"}

        # 4. LLM call — swallow failure
        summary_text = await self._summarize(
            workspace_id=p.workspace_id,
            actor_user_id=p.actor_user_id,
            concatenated=concatenated,
        )
        if not summary_text:
            return {"success": False, "error": "llm_failed"}

        # 5. Write summary row
        try:
            node_ids = await self._write_summary(
                workspace_id=p.workspace_id,
                actor_user_id=p.actor_user_id,
                note_id=p.note_id,
                source_chunk_ids=[c.id for c in chunks],
                summary_text=summary_text,
            )
        except Exception:
            logger.exception(
                "SummarizeNoteHandler: summary write failed (workspace=%s note=%s)",
                p.workspace_id,
                p.note_id,
            )
            return {"success": False, "error": "write_failed"}

        await self._bump_throttle(p.workspace_id)
        logger.info(
            "SummarizeNoteHandler: note %s → %d summary node(s) from %d chunks",
            p.note_id,
            len(node_ids),
            len(chunks),
        )
        return {
            "success": True,
            "note_id": str(p.note_id),
            "summary_node_ids": [str(n) for n in node_ids],
            "source_chunks": len(chunks),
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _throttle_exceeded(self, workspace_id: UUID) -> bool:
        if self._redis is None:
            return False
        key = _THROTTLE_KEY_FMT.format(workspace_id=workspace_id)
        try:
            raw = await self._redis.get(key)
        except Exception:
            logger.exception(
                "SummarizeNoteHandler: Redis get failed (workspace=%s) — treat as not throttled",
                workspace_id,
            )
            return False
        try:
            count = int(raw) if raw is not None else 0
        except (TypeError, ValueError):
            count = 0
        return count >= _THROTTLE_LIMIT

    async def _bump_throttle(self, workspace_id: UUID) -> None:
        if self._redis is None:
            return
        key = _THROTTLE_KEY_FMT.format(workspace_id=workspace_id)
        try:
            new_val = await self._redis.incr(key)
            if int(new_val) == 1:
                # Only set expiry on the first increment in the window.
                await self._redis.expire(key, _THROTTLE_TTL_S)
        except Exception:
            logger.exception(
                "SummarizeNoteHandler: Redis incr failed (workspace=%s) — non-fatal",
                workspace_id,
            )

    async def _fetch_raw_chunks(
        self, workspace_id: UUID, note_id: UUID
    ) -> list[GraphNodeModel]:
        """Fetch all raw NOTE_CHUNK rows for a note, oldest first."""
        stmt = (
            select(GraphNodeModel)
            .where(GraphNodeModel.workspace_id == workspace_id)
            .where(GraphNodeModel.node_type == NodeType.NOTE_CHUNK.value)
            .where(
                GraphNodeModel.properties["parent_note_id"].as_string() == str(note_id)
            )
            .where(GraphNodeModel.is_deleted == False)  # noqa: E712
            .order_by(GraphNodeModel.created_at.asc())
        )
        result = await self._session.execute(stmt)
        rows = list(result.scalars().all())
        # Prefer rows explicitly tagged kind='raw'; fall back to legacy
        # (kind-absent) rows which Task 1 treats as raw semantically.
        return [
            r
            for r in rows
            if (r.properties or {}).get("kind", "raw") == "raw"
        ]

    def _concat_chunks(self, chunks: list[GraphNodeModel]) -> str:
        parts: list[str] = []
        remaining = _MAX_INPUT_CHARS
        for c in chunks:
            body = (c.content or "").strip()
            if not body:
                continue
            heading = ((c.properties or {}).get("heading") or "").strip()
            prefix = f"## {heading}\n" if heading else ""
            piece = f"{prefix}{body}"
            if len(piece) > remaining:
                piece = piece[:remaining]
            parts.append(piece)
            remaining -= len(piece)
            if remaining <= 0:
                break
        return "\n\n".join(parts)

    async def _summarize(
        self,
        *,
        workspace_id: UUID,
        actor_user_id: UUID,
        concatenated: str,
    ) -> str | None:
        if self._llm_gateway is None:
            logger.warning("SummarizeNoteHandler: no LLMGateway wired — skip summarization")
            return None
        try:
            response = await self._llm_gateway.complete(
                workspace_id=workspace_id,
                user_id=actor_user_id,
                task_type=TaskType.MEMORY_SUMMARIZATION,
                messages=[{"role": "user", "content": concatenated}],
                system=(
                    "You are a concise technical editor. Produce a dense "
                    "bullet-point summary (6-10 bullets, <400 words) of "
                    "the following note content. Preserve concrete "
                    "decisions, names, numbers, and open questions. Omit "
                    "boilerplate and repetition."
                ),
                max_tokens=800,
                temperature=0.2,
                agent_name="summarize_note_handler",
            )
        except Exception:
            logger.exception(
                "SummarizeNoteHandler: LLM call failed (workspace=%s)",
                workspace_id,
            )
            return None
        text = (response.text or "").strip()
        return text[:_MAX_OUTPUT_CHARS] if text else None

    async def _write_summary(
        self,
        *,
        workspace_id: UUID,
        actor_user_id: UUID,
        note_id: UUID,
        source_chunk_ids: list[UUID],
        summary_text: str,
    ) -> list[UUID]:
        write_svc = GraphWriteService(
            knowledge_graph_repository=self._repo,
            queue=self._queue,
            session=self._session,
            auto_commit=False,
        )
        result = await write_svc.execute(
            GraphWritePayload(
                workspace_id=workspace_id,
                actor_user_id=actor_user_id,
                nodes=[
                    NodeInput(
                        node_type=NodeType.NOTE_CHUNK,
                        label=f"summary: {note_id}"[:120],
                        content=summary_text,
                        properties={
                            # Phase 70-06: summary discriminator. The
                            # recall path uses this to separate rolled-up
                            # summaries from raw content.
                            "kind": "summary",
                            "source_note_id": str(note_id),
                            "parent_note_id": str(note_id),
                            "source_chunk_ids": [str(c) for c in source_chunk_ids],
                        },
                    )
                ],
            )
        )
        return list(result.node_ids)


__all__ = ["TASK_SUMMARIZE_NOTE", "SummarizeNoteHandler"]
