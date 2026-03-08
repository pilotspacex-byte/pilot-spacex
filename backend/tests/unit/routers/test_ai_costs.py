"""xfail test stubs for AI costs router group_by enhancements.

Phase 4 — AI Governance (AIGOV-06):
GET /workspaces/{slug}/costs/summary must support group_by=operation_type
to return cost breakdown by AI feature category.

Implemented in plan 04-06 (AIGOV-06 cost breakdown by operation_type).
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.asyncio


@pytest.mark.xfail(
    strict=False,
    reason="Phase 4 AIGOV-06: GET costs/summary?group_by=operation_type — implemented in 04-06",
)
async def test_summary_group_by_operation_type() -> None:
    """GET /workspaces/{slug}/costs/summary?group_by=operation_type returns by_feature dict.

    Response must include a by_feature dict mapping operation_type values
    (e.g. 'ghost_text', 'issue_extraction') to their aggregated cost totals.
    Rows where operation_type IS NULL are grouped under key 'unknown'.
    """


@pytest.mark.xfail(
    strict=False,
    reason="Phase 4 AIGOV-06: invalid group_by returns 422 — implemented in 04-06",
)
async def test_summary_group_by_invalid_value() -> None:
    """GET /workspaces/{slug}/costs/summary?group_by=invalid returns 422 Unprocessable Entity.

    Only 'provider', 'agent', 'model', and 'operation_type' are valid group_by
    values. Any other value must return 422 with a field validation error.
    """
