"""Phase 70 memory producers.

Fire-and-forget helpers that enqueue ``kg_populate`` jobs carrying memory
payloads (``agent_turn``, ``user_correction``, ``pr_review_finding``).

Producers MUST NEVER raise into the user-facing flow. All failures are
logged and recorded as ``dropped`` counters in
``pilot_space.ai.telemetry.memory_metrics``.
"""

from __future__ import annotations

from pilot_space.ai.memory.producers.agent_turn_producer import (
    enqueue_agent_turn_memory,
)
from pilot_space.ai.memory.producers.pr_review_finding_producer import (
    enqueue_pr_review_findings,
)
from pilot_space.ai.memory.producers.user_correction_producer import (
    enqueue_user_correction_memory,
)

__all__ = [
    "enqueue_agent_turn_memory",
    "enqueue_pr_review_findings",
    "enqueue_user_correction_memory",
]
