"""xfail test stubs for AuditLogRepository actor_type filter.

Phase 4 — AI Governance (AIGOV-03):
AuditLogRepository.list_filtered() and list_for_export() must support
filtering by actor_type (AI | USER) to enable AI-specific audit views.

Implemented in plan 04-05 (AIGOV-03 audit log actor_type filter).
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.asyncio


@pytest.mark.xfail(
    strict=False,
    reason="Phase 4 AIGOV-03: list_filtered actor_type=AI filter — implemented in 04-05",
)
async def test_list_filtered_actor_type_ai() -> None:
    """actor_type='AI' filter returns only rows where actor_type=AI.

    AuditLogRepository.list_filtered(actor_type='AI') must exclude
    all rows with actor_type='USER' or other values.
    """


@pytest.mark.xfail(
    strict=False,
    reason="Phase 4 AIGOV-03: list_filtered actor_type=USER filter — implemented in 04-05",
)
async def test_list_filtered_actor_type_user() -> None:
    """actor_type='USER' filter excludes AI rows.

    AuditLogRepository.list_filtered(actor_type='USER') must exclude
    all rows with actor_type='AI'.
    """


@pytest.mark.xfail(
    strict=False,
    reason="Phase 4 AIGOV-03: list_for_export actor_type filter — implemented in 04-05",
)
async def test_list_for_export_actor_type_filter() -> None:
    """list_for_export also supports actor_type filter for streaming CSV/JSON.

    AuditLogRepository.list_for_export(actor_type='AI') must yield only
    AI-generated audit entries. Supports exporting AI-only audit trail.
    """
