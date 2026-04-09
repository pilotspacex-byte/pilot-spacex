"""Agent-turn memory producer (PROD-01, Phase 70 Wave 2).

Fire-and-forget helper that enqueues an ``agent_turn`` memory job on the
``ai_normal`` queue after a ``PilotSpaceAgent`` stream completes cleanly.
Co-located with ``_background_graph_extraction`` at the ``stream_completed``
finally hook in ``pilotspace_agent.py``.

Contract
--------

* Producer MUST NEVER raise into the user-facing flow. All failures are
  swallowed and recorded as ``dropped{reason}`` counters.
* Idempotency is DB-enforced via the partial unique index
  ``uq_graph_nodes_agent_turn_cache`` on
  ``(workspace_id, properties->>'session_id', (properties->>'turn_index')::int)``
  shipped in migration 106. On a re-run / replay, the handler catches the
  ``IntegrityError`` and ACKs the job.
* ``turn_index`` is derived by counting existing ``agent_turn`` graph nodes
  for ``(workspace_id, session_id)``. There is a race on reconnect — two
  concurrent turns can compute the same index — but the unique index catches
  the collision and the producer records ``dropped{reason="duplicate"}``.
* ``enabled=False`` is Wave 3's opt-out path; producer short-circuits and
  records ``dropped{reason="opt_out"}``.

The helper deliberately takes ``queue_client`` as a dependency and imports
nothing from ``pilotspace_agent`` to avoid circular imports.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import func, select

from pilot_space.ai.telemetry.memory_metrics import (
    record_producer_dropped,
    record_producer_enqueued,
)
from pilot_space.infrastructure.database.models.graph_node import GraphNodeModel
from pilot_space.infrastructure.queue.handlers.kg_populate_handler import (
    TASK_KG_POPULATE,
)
from pilot_space.infrastructure.queue.models import QueueName

if TYPE_CHECKING:
    from pilot_space.infrastructure.queue.supabase_queue import SupabaseQueueClient

logger = logging.getLogger(__name__)

_MEMORY_TYPE = "agent_turn"
_MAX_TEXT_CHARS = 2000


def _truncate(text: str, limit: int = _MAX_TEXT_CHARS) -> str:
    if not text:
        return ""
    return text if len(text) <= limit else text[:limit]


async def _derive_turn_index(workspace_id: UUID, session_id: str) -> int:
    """Count existing agent_turn nodes for (workspace, session).

    Uses a short-lived request-scoped session. Returns ``0`` if the query
    fails so the producer can still enqueue — the DB unique index is the
    source of truth for de-dupe.

    SEC-07: RLS context is NOT set here because ``set_rls_context`` requires
    a non-None ``user_id: UUID`` and this helper only has ``workspace_id``.
    Workspace isolation is enforced by the explicit
    ``WHERE workspace_id = :workspace_id`` filter in the query. The filter is
    the functional equivalent of RLS for this read-only count — removing it
    would require changing the function signature (which is a separate task).
    """
    try:
        from pilot_space.infrastructure.database import get_db_session

        async with get_db_session() as session:
            stmt = (
                select(func.count(GraphNodeModel.id))
                .where(GraphNodeModel.workspace_id == workspace_id)
                .where(GraphNodeModel.node_type == "agent_turn")
                .where(GraphNodeModel.properties["session_id"].astext == session_id)
            )
            result = await session.execute(stmt)
            return int(result.scalar_one() or 0)
    except Exception:
        logger.exception("agent_turn_producer: failed to derive turn_index; defaulting to 0")
        return 0


async def enqueue_agent_turn_memory(
    *,
    queue_client: SupabaseQueueClient,
    workspace_id: UUID,
    actor_user_id: UUID,
    session_id: str,
    user_message: str,
    assistant_text: str,
    tools_used: list[str],
    metadata: dict[str, Any],
    enabled: bool = True,
) -> None:
    """Enqueue an ``agent_turn`` memory job. Fire-and-forget, never raises.

    Args:
        queue_client: ``SupabaseQueueClient`` instance (typically
            ``PilotSpaceAgent._graph_queue_client``).
        workspace_id: Workspace for RLS + idempotency scope.
        actor_user_id: User who issued the turn (required by the fail-closed
            dispatcher from Wave 1).
        session_id: Conversation session UUID (stringified).
        user_message: Raw user prompt for the turn.
        assistant_text: Concatenated assistant text for the turn.
        tools_used: Ordered list of tool names invoked this turn.
        metadata: Extra provenance (``ttft_ms``, etc.). Merged into
            ``properties`` by the handler.
        enabled: Wave 3 opt-out flag. ``False`` → record ``dropped{opt_out}``
            and return without enqueuing.
    """
    if not enabled:
        record_producer_dropped(_MEMORY_TYPE, "opt_out")
        return

    turn_index = await _derive_turn_index(workspace_id, session_id)

    user_snippet = _truncate(user_message)
    assistant_snippet = _truncate(assistant_text)
    content = f"USER: {user_snippet}\n\nASSISTANT: {assistant_snippet}"

    # Fields under `metadata` end up merged into graph_node.properties by
    # KgPopulateHandler._handle_memory_type — session_id and turn_index MUST
    # be there for the uq_graph_nodes_agent_turn_cache partial index to fire.
    merged_metadata: dict[str, Any] = {
        **(metadata or {}),
        "session_id": session_id,
        "turn_index": turn_index,
        "tools_used": list(tools_used or []),
        # Phase 70-06: write-path discriminator — agent_turn rows are
        # conversational cache entries. Recall path filters on this key.
        "kind": "turn",
    }

    payload: dict[str, Any] = {
        "task_type": TASK_KG_POPULATE,
        "memory_type": _MEMORY_TYPE,
        "workspace_id": str(workspace_id),
        "actor_user_id": str(actor_user_id),
        # SEC-06: GDPR deletion key — enables "forget me" queries across all memory types.
        # Distinct from actor_user_id (who triggered) vs user_id (whose data this is).
        "user_id": str(actor_user_id),
        "session_id": session_id,
        "turn_index": turn_index,
        "user_text": user_snippet,
        "assistant_text": assistant_snippet,
        "content": content,
        "label": f"turn {turn_index}",
        "metadata": merged_metadata,
    }

    try:
        await queue_client.enqueue(QueueName.AI_NORMAL, payload)
        record_producer_enqueued(_MEMORY_TYPE)
    except Exception:
        logger.exception(
            "agent_turn_producer: enqueue failed (workspace=%s session=%s turn=%s)",
            workspace_id,
            session_id,
            turn_index,
        )
        record_producer_dropped(_MEMORY_TYPE, "enqueue_error")


__all__ = ["enqueue_agent_turn_memory"]
