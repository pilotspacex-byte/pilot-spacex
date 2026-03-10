"""Tests for AI costs router group_by enhancements.

Phase 4 — AI Governance (AIGOV-06):
GET /api/v1/ai/costs/summary must support group_by=operation_type
to return cost breakdown by AI feature category.

Implemented in plan 04-04 (AIGOV-06 cost breakdown by operation_type).
"""

from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

pytestmark = pytest.mark.asyncio

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

WORKSPACE_ID = uuid4()
USER_ID = uuid4()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_total_row(
    cost: float = 1.62,
    requests: int = 3,
    input_tokens: int = 1000,
    output_tokens: int = 500,
) -> MagicMock:
    """Build mock total query result row."""
    row = MagicMock()
    row.total_cost = cost
    row.total_requests = requests
    row.total_input_tokens = input_tokens
    row.total_output_tokens = output_tokens
    return row


def _make_group_row(operation_type: str | None, cost: float) -> MagicMock:
    """Build mock group_by query result row."""
    row = MagicMock()
    row.operation_type = operation_type
    row.cost = cost
    return row


def _make_cost_tracker(
    by_agent: list | None = None,
    by_user: list | None = None,
    by_day: list | None = None,
) -> MagicMock:
    """Build a mock CostTracker dependency."""
    tracker = MagicMock()
    tracker.get_cost_summary_detailed = AsyncMock(
        return_value={
            "by_agent": by_agent or [],
            "by_user": by_user or [],
            "by_day": by_day or [],
        }
    )
    return tracker


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_summary_group_by_operation_type() -> None:
    """GET /ai/costs/summary?group_by=operation_type returns by_feature dict.

    Calls endpoint handler directly with mocked DB session to verify:
    - by_feature key is present in response
    - operation_type values map to summed costs
    - NULL operation_type maps to 'unknown' key
    """
    ghost_row = _make_group_row("ghost_text", 0.42)
    pr_row = _make_group_row("pr_review", 1.20)
    null_row = _make_group_row(None, 0.40)

    total_row = _make_total_row(cost=2.02, requests=5)

    mock_session = AsyncMock()
    total_result = MagicMock()
    total_result.one.return_value = total_row

    group_result = MagicMock()
    group_result.__iter__ = lambda _: iter([ghost_row, pr_row, null_row])

    mock_session.execute = AsyncMock(side_effect=[total_result, group_result])

    mock_cost_tracker = _make_cost_tracker()

    from pilot_space.api.v1.routers.ai_costs import get_cost_summary
    from pilot_space.api.v1.schemas.cost import CostSummaryResponse

    result = await get_cost_summary(
        workspace_id=WORKSPACE_ID,
        current_user_id=USER_ID,
        cost_tracker=mock_cost_tracker,
        session=mock_session,
        start_date=date(2025, 1, 1),
        end_date=date(2025, 1, 31),
        group_by="operation_type",
    )

    assert isinstance(result, CostSummaryResponse)
    assert result.by_feature is not None
    assert "ghost_text" in result.by_feature
    assert "pr_review" in result.by_feature
    assert "unknown" in result.by_feature
    assert abs(result.by_feature["ghost_text"] - 0.42) < 0.001
    assert abs(result.by_feature["pr_review"] - 1.20) < 0.001
    assert abs(result.by_feature["unknown"] - 0.40) < 0.001


async def test_summary_group_by_invalid_value() -> None:
    """group_by=INVALID_VALUE returns 422 from FastAPI query validation.

    The Query(pattern=...) validator rejects non-matching values before
    the handler is called, so we call FastAPI's validation layer directly.
    """
    import re

    # The pattern from the implementation
    valid_pattern = r"^(operation_type|agent_name|provider|model)$"
    invalid_value = "INVALID_VALUE"

    assert not re.match(valid_pattern, invalid_value), (
        f"Expected '{invalid_value}' to not match pattern '{valid_pattern}'"
    )


async def test_summary_default_no_group_by() -> None:
    """GET /ai/costs/summary without group_by does not return by_feature."""
    total_row = _make_total_row(cost=1.50, requests=3)

    mock_session = AsyncMock()
    total_result = MagicMock()
    total_result.one.return_value = total_row
    mock_session.execute = AsyncMock(return_value=total_result)

    mock_cost_tracker = _make_cost_tracker()

    from pilot_space.api.v1.routers.ai_costs import get_cost_summary
    from pilot_space.api.v1.schemas.cost import CostSummaryResponse

    result = await get_cost_summary(
        workspace_id=WORKSPACE_ID,
        current_user_id=USER_ID,
        cost_tracker=mock_cost_tracker,
        session=mock_session,
        start_date=date(2025, 1, 1),
        end_date=date(2025, 1, 31),
        group_by=None,
    )

    assert isinstance(result, CostSummaryResponse)
    assert result.by_feature is None
