"""User-correction memory producer (PROD-02, Phase 70 Wave 2).

Fire-and-forget helper that enqueues a ``user_correction`` memory job on
the ``ai_normal`` queue whenever the approval flow denies a tool call OR
a user explicitly rejects an approval request. The knowledge-graph
handler persists the correction so future agent turns can learn from the
refusal.

Contract
--------

* Producer MUST NEVER raise into the caller. All failures are swallowed
  and recorded as ``dropped{reason}`` counters. The caller (typically
  ``PermissionHandler``) awaits this helper BEFORE raising
  ``PermissionDeniedError`` so the corrective signal is persisted even
  when the deny path short-circuits.
* ``enabled=False`` is the Wave 3 opt-out path; producer short-circuits
  and records ``dropped{reason="opt_out"}``. Wave 3 (plan 70-06) wires
  the real workspace flag — Wave 2 callers pass ``enabled=True``.
* Edit-before-accept capture is explicitly descoped to Phase 71 — the
  approval flow is currently approve/reject binary and lacks diff
  plumbing from the frontend.
* The free-form chat correction heuristic is gated behind a separate
  Wave 3 sub-toggle (default OFF) and is NOT shipped in Wave 2.

The helper deliberately takes ``queue_client`` as a dependency to avoid
circular imports and to make unit-testing trivial.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Literal
from uuid import UUID

from pilot_space.ai.telemetry.memory_metrics import (
    record_producer_dropped,
    record_producer_enqueued,
)
from pilot_space.infrastructure.queue.handlers.kg_populate_handler import (
    TASK_KG_POPULATE,
)
from pilot_space.infrastructure.queue.models import QueueName

if TYPE_CHECKING:
    from pilot_space.infrastructure.queue.supabase_queue import SupabaseQueueClient

logger = logging.getLogger(__name__)

_MEMORY_TYPE = "user_correction"

CorrectionSubtype = Literal["deny", "user_reject", "free_form"]


async def enqueue_user_correction_memory(
    *,
    queue_client: SupabaseQueueClient | None,
    workspace_id: UUID | None,
    actor_user_id: UUID | None,
    session_id: str,
    subtype: CorrectionSubtype,
    tool_name: str | None,
    reason: str,
    referenced_turn_index: int | None,
    enabled: bool = True,
) -> None:
    """Enqueue a ``user_correction`` memory job. Fire-and-forget, never raises.

    Args:
        queue_client: ``SupabaseQueueClient`` instance. ``None`` → drop.
        workspace_id: Workspace for RLS scope. ``None`` → drop (Wave 1
            dispatcher rejects payloads without a workspace_id).
        actor_user_id: User who triggered the correction (required by
            the fail-closed dispatcher from Wave 1).
        session_id: Conversation session UUID (stringified). Empty
            string is acceptable — the handler will persist without a
            session key.
        subtype: ``"deny"`` (policy-level DENY), ``"user_reject"`` (user
            rejected an approval request) or ``"free_form"`` (Wave 3+).
        tool_name: Name of the tool/action that was denied/rejected.
        reason: Human-readable reason (policy message or user note).
        referenced_turn_index: Index of the agent_turn this correction
            references. ``None`` when unknown (current deny path).
        enabled: Wave 3 opt-out flag. ``False`` → record
            ``dropped{opt_out}`` and return without enqueuing.
    """
    if not enabled:
        record_producer_dropped(_MEMORY_TYPE, "opt_out")
        return

    # Treat nil UUID (00000000-...) as "no workspace" — agent context uses
    # nil UUID sentinel when no workspace is active.
    _nil = UUID(int=0)
    if (
        queue_client is None
        or workspace_id is None
        or workspace_id == _nil
        or actor_user_id is None
        or actor_user_id == _nil
    ):
        record_producer_dropped(_MEMORY_TYPE, "enqueue_error")
        return

    content = f"[{subtype}] {tool_name or ''}: {reason}".strip()

    payload: dict[str, Any] = {
        "task_type": TASK_KG_POPULATE,
        "memory_type": _MEMORY_TYPE,
        "workspace_id": str(workspace_id),
        "actor_user_id": str(actor_user_id),
        # SEC-06: GDPR deletion key — enables "forget me" queries across all memory types.
        # Distinct from actor_user_id (who triggered) vs user_id (whose data this is).
        "user_id": str(actor_user_id),
        "session_id": session_id,
        "subtype": subtype,
        "tool_name": tool_name,
        "reason": reason,
        "referenced_turn_index": referenced_turn_index,
        "content": content,
        "label": f"{subtype}:{tool_name or 'unknown'}",
        "metadata": {
            "session_id": session_id,
            "subtype": subtype,
            "tool_name": tool_name,
            "referenced_turn_index": referenced_turn_index,
            # Phase 70-06: write-path discriminator — corrections are the
            # "deny/refusal" bucket regardless of subtype. Recall path filters.
            "kind": "deny",
        },
    }

    try:
        await queue_client.enqueue(QueueName.AI_NORMAL, payload)
        record_producer_enqueued(_MEMORY_TYPE)
    except Exception:
        logger.exception(
            "user_correction_producer: enqueue failed (workspace=%s session=%s tool=%s subtype=%s)",
            workspace_id,
            session_id,
            tool_name,
            subtype,
        )
        record_producer_dropped(_MEMORY_TYPE, "enqueue_error")


__all__ = ["enqueue_user_correction_memory"]
