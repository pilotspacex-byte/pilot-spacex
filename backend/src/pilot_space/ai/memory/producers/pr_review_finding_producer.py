"""PR-review-finding memory producer (PROD-03, Phase 70 Wave 2).

Fire-and-forget helper that flattens the ``list[ReviewComment]`` emitted by
``PRReviewSubagent`` into one ``kg_populate`` job per comment on the
``ai_normal`` queue. The knowledge-graph handler persists each finding as a
``pr_review_finding`` graph node.

Contract
--------

* Producer MUST NEVER raise into the caller. Each per-comment enqueue runs
  inside its own try/except so a single failing enqueue cannot take down the
  rest of the batch. Failures are swallowed and counted as
  ``dropped{reason="enqueue_error"}`` telemetry.
* Idempotency is DB-enforced via the partial unique index
  ``uq_graph_nodes_pr_review_finding`` shipped in migration 107:

  .. code-block:: sql

      CREATE UNIQUE INDEX uq_graph_nodes_pr_review_finding
        ON graph_nodes (
          workspace_id,
          (properties->>'repo'),
          ((properties->>'pr_number')::int),
          (properties->>'file_path'),
          ((properties->>'line_number')::int)
        )
        WHERE node_type = 'pr_review_finding';

  Because the index reads ``properties->>'<key>'`` (text), we stringify
  ``repo``, ``pr_number``, ``file_path``, and ``line_number`` inside
  ``properties`` at enqueue-time. The ``::int`` cast still works because the
  stringified integers round-trip cleanly.
* ``enabled=False`` is the Wave 3 opt-out path. The producer short-circuits
  the whole batch with a single ``dropped{reason="opt_out"}`` record and
  returns without touching the queue.

The helper takes ``queue_client`` as an explicit dependency to avoid
circular imports and to make unit-testing trivial.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any
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
    from pilot_space.api.v1.schemas.pr_review import ReviewComment
    from pilot_space.infrastructure.queue.supabase_queue import SupabaseQueueClient

logger = logging.getLogger(__name__)

_MEMORY_TYPE = "pr_review_finding"
_MAX_TEXT_CHARS = 2000


def _truncate(text: str, limit: int = _MAX_TEXT_CHARS) -> str:
    if not text:
        return ""
    return text if len(text) <= limit else text[:limit]


def _severity_str(value: Any) -> str:
    return value.value if hasattr(value, "value") else str(value)


def _build_payload(
    *,
    workspace_id: UUID,
    actor_user_id: UUID,
    repo: str,
    pr_number: int,
    comment: ReviewComment,
) -> dict[str, Any]:
    severity = _severity_str(comment.severity)
    category = _severity_str(comment.category)
    message = _truncate(comment.message or "")
    # ``properties.*`` keys that back the migration 107 unique index MUST be
    # strings — the index uses ``properties->>'<key>'`` which returns text.
    properties: dict[str, Any] = {
        "repo": repo,
        "pr_number": str(pr_number),
        "file_path": comment.file_path,
        "line_number": str(comment.line_number),
        "end_line": comment.end_line,
        "severity": severity,
        "category": category,
        "suggestion": comment.suggestion,
        "code_snippet": comment.code_snippet,
        # Phase 70-06: write-path discriminator — PR review comments are
        # durable "finding" records. Recall path filters on this key.
        "kind": "finding",
    }
    label = f"{category}:{comment.file_path}:{comment.line_number}"
    return {
        "task_type": TASK_KG_POPULATE,
        "memory_type": _MEMORY_TYPE,
        "workspace_id": str(workspace_id),
        "actor_user_id": str(actor_user_id),
        # SEC-06: GDPR deletion key — enables "forget me" queries across all memory types.
        # Distinct from actor_user_id (who triggered) vs user_id (whose data this is).
        "user_id": str(actor_user_id),
        "content": message,
        "label": label[:120],
        "properties": properties,
        "metadata": properties,
    }


async def enqueue_pr_review_findings(
    *,
    queue_client: SupabaseQueueClient | None,
    workspace_id: UUID,
    actor_user_id: UUID,
    repo: str,
    pr_number: int,
    comments: list[ReviewComment],
    enabled: bool = True,
) -> None:
    """Enqueue one ``pr_review_finding`` memory job per review comment.

    Fire-and-forget. Never raises. Each comment's enqueue is wrapped in its
    own try/except so one failure cannot abort the rest of the batch.

    Args:
        queue_client: ``SupabaseQueueClient`` instance. ``None`` → the entire
            batch is dropped and counted as ``enqueue_error``.
        workspace_id: Workspace for RLS + idempotency scope.
        actor_user_id: User who ran the review (required by the fail-closed
            dispatcher from Wave 1).
        repo: Repository in ``owner/name`` format. Stored as-is under
            ``properties.repo``.
        pr_number: Pull request number (stored stringified under
            ``properties.pr_number``).
        comments: Review comments to flatten. Empty list is a no-op.
        enabled: Wave 3 opt-out flag. ``False`` → record a single
            ``dropped{opt_out}`` and return without enqueuing anything.
    """
    if not enabled:
        record_producer_dropped(_MEMORY_TYPE, "opt_out")
        return

    if not comments:
        return

    if queue_client is None:
        # Missing wiring is treated the same as an enqueue error so the drop
        # surfaces in telemetry rather than silently vanishing.
        for _ in comments:
            record_producer_dropped(_MEMORY_TYPE, "enqueue_error")
        return

    for comment in comments:
        payload = _build_payload(
            workspace_id=workspace_id,
            actor_user_id=actor_user_id,
            repo=repo,
            pr_number=pr_number,
            comment=comment,
        )
        try:
            await queue_client.enqueue(QueueName.AI_NORMAL, payload)
            record_producer_enqueued(_MEMORY_TYPE)
        except Exception:
            logger.exception(
                "pr_review_finding_producer: enqueue failed "
                "(workspace=%s repo=%s pr=%s file=%s line=%s)",
                workspace_id,
                repo,
                pr_number,
                comment.file_path,
                comment.line_number,
            )
            record_producer_dropped(_MEMORY_TYPE, "enqueue_error")


__all__ = ["enqueue_pr_review_findings"]
