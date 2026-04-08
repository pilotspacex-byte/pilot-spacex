"""AI memory telemetry admin endpoint (Phase 70 Wave 4).

Endpoints (mounted under ``/api/v1/workspaces/{workspace_id}/ai/memory/telemetry``):

* ``GET  ""``                       — memory stats + producer counters + toggles (admin)
* ``PUT  "/toggles/{producer}"``    — set a single producer toggle (admin)
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from pilot_space.ai.telemetry import memory_metrics
from pilot_space.application.services.workspace_ai_settings_toggles import (
    get_producer_toggles,
    set_producer_toggle,
)
from pilot_space.dependencies.auth import (
    DbSession,
    WorkspaceAdminId,
)

router = APIRouter(tags=["ai-memory-telemetry"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class ToggleUpdateRequest(BaseModel):
    """Request body for PUT /toggles/{producer}."""

    enabled: bool


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("")
async def get_memory_telemetry(
    workspace_id: WorkspaceAdminId,
    session: DbSession,
) -> dict[str, Any]:
    """Return memory recall stats, producer counters, and toggle state.

    Admin-only. ``workspace_id`` is validated by ``WorkspaceAdminId``.
    """
    snap = memory_metrics.snapshot()
    counters = memory_metrics.get_producer_counters()
    toggles = await get_producer_toggles(session, workspace_id)

    return {
        "memory": {
            "hit_rate": snap["memory_recall.hit_rate"],
            "recall_p95_ms": snap["memory_recall.latency_ms.p95"],
            "total_recalls": snap["memory_recall.latency_ms.samples"],
        },
        "producers": counters,
        "toggles": toggles.to_dict(),
    }


@router.put("/toggles/{producer}")
async def update_producer_toggle(
    workspace_id: WorkspaceAdminId,
    producer: str,
    body: ToggleUpdateRequest,
    session: DbSession,
) -> dict[str, Any]:
    """Set a single producer toggle and return the resulting state.

    Admin-only. Raises ``ValidationError`` (→ 422) for unknown producers.
    """
    result = await set_producer_toggle(session, workspace_id, producer, body.enabled)
    return result.to_dict()


__all__ = ["router"]
