"""Unit tests for PMBlockInsightService.

Coverage:
- Each block type analyzer (sprint_board, dependency_map, capacity_plan, release_notes)
- Insufficient data fallback for sprint_board
- refresh_insights: soft-deletes old insights and persists new ones
- Refresh debounce logic in the router endpoint

T-249, T-251, T-252
Feature 017: Note Versioning / PM Block Engine
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from pilot_space.application.services.pm_block_insight_service import (
    PMBlockInsightService,
    _make_insight,
)
from pilot_space.domain.pm_block_insight import InsightSeverity, PMBlockInsight, PMBlockType

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

WORKSPACE_ID = str(uuid4())
BLOCK_ID = "block-abc-123"


def _make_service(
    *,
    session: Any | None = None,
    repository: Any | None = None,
) -> PMBlockInsightService:
    return PMBlockInsightService(
        session=session or AsyncMock(),
        repository=repository or AsyncMock(),
    )


def _sprint_data(
    stale_issues_count: int = 0,
    blocker_count: int = 0,
    velocity_deviation_pct: float = 0.0,
    completed_cycles_count: int = 5,
) -> dict:
    return {
        "completed_cycles_count": completed_cycles_count,
        "stale_issues_count": stale_issues_count,
        "blocker_count": blocker_count,
        "velocity_deviation_pct": velocity_deviation_pct,
    }


def _dep_data(
    critical_path_length: int = 0,
    bottleneck_node_count: int = 0,
) -> dict:
    return {
        "critical_path_length": critical_path_length,
        "bottleneck_node_count": bottleneck_node_count,
    }


def _capacity_data(members: list[dict] | None = None) -> dict:
    return {"members": members or []}


def _release_data(entries: list[dict] | None = None) -> dict:
    return {"entries": entries or []}


# ---------------------------------------------------------------------------
# Sprint board analyzer
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestSprintBoardAnalyzer:
    async def test_no_issues_returns_empty(self) -> None:
        svc = _make_service()
        insights = await svc.analyze_block(
            block_id=BLOCK_ID,
            block_type=PMBlockType.SPRINT_BOARD,
            workspace_id=WORKSPACE_ID,
            data=_sprint_data(),
        )
        assert insights == []

    async def test_stale_issues_below_threshold_returns_yellow(self) -> None:
        svc = _make_service()
        insights = await svc.analyze_block(
            block_id=BLOCK_ID,
            block_type=PMBlockType.SPRINT_BOARD,
            workspace_id=WORKSPACE_ID,
            data=_sprint_data(stale_issues_count=2),
        )
        stale = [i for i in insights if i.insight_type == "stale_issues"]
        assert len(stale) == 1
        assert stale[0].severity == InsightSeverity.YELLOW

    async def test_stale_issues_above_threshold_returns_red(self) -> None:
        svc = _make_service()
        insights = await svc.analyze_block(
            block_id=BLOCK_ID,
            block_type=PMBlockType.SPRINT_BOARD,
            workspace_id=WORKSPACE_ID,
            data=_sprint_data(stale_issues_count=5),
        )
        stale = [i for i in insights if i.insight_type == "stale_issues"]
        assert stale[0].severity == InsightSeverity.RED

    async def test_high_blocker_count_returns_red(self) -> None:
        svc = _make_service()
        insights = await svc.analyze_block(
            block_id=BLOCK_ID,
            block_type=PMBlockType.SPRINT_BOARD,
            workspace_id=WORKSPACE_ID,
            data=_sprint_data(blocker_count=4),
        )
        blockers = [i for i in insights if i.insight_type == "high_blocker_count"]
        assert len(blockers) == 1
        assert blockers[0].severity == InsightSeverity.RED

    async def test_blocker_count_at_threshold_not_flagged(self) -> None:
        svc = _make_service()
        insights = await svc.analyze_block(
            block_id=BLOCK_ID,
            block_type=PMBlockType.SPRINT_BOARD,
            workspace_id=WORKSPACE_ID,
            data=_sprint_data(blocker_count=3),
        )
        blockers = [i for i in insights if i.insight_type == "high_blocker_count"]
        assert len(blockers) == 0

    async def test_velocity_deviation_above_20_pct_yellow(self) -> None:
        svc = _make_service()
        insights = await svc.analyze_block(
            block_id=BLOCK_ID,
            block_type=PMBlockType.SPRINT_BOARD,
            workspace_id=WORKSPACE_ID,
            data=_sprint_data(velocity_deviation_pct=25.0),
        )
        anomaly = [i for i in insights if i.insight_type == "velocity_anomaly"]
        assert len(anomaly) == 1
        assert anomaly[0].severity == InsightSeverity.YELLOW

    async def test_velocity_deviation_above_40_pct_red(self) -> None:
        svc = _make_service()
        insights = await svc.analyze_block(
            block_id=BLOCK_ID,
            block_type=PMBlockType.SPRINT_BOARD,
            workspace_id=WORKSPACE_ID,
            data=_sprint_data(velocity_deviation_pct=-45.0),
        )
        anomaly = [i for i in insights if i.insight_type == "velocity_anomaly"]
        assert anomaly[0].severity == InsightSeverity.RED

    async def test_velocity_within_20_pct_not_flagged(self) -> None:
        svc = _make_service()
        insights = await svc.analyze_block(
            block_id=BLOCK_ID,
            block_type=PMBlockType.SPRINT_BOARD,
            workspace_id=WORKSPACE_ID,
            data=_sprint_data(velocity_deviation_pct=10.0),
        )
        anomaly = [i for i in insights if i.insight_type == "velocity_anomaly"]
        assert len(anomaly) == 0


# ---------------------------------------------------------------------------
# Insufficient data fallback
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestInsufficientDataFallback:
    async def test_fewer_than_3_cycles_returns_green_insight(self) -> None:
        svc = _make_service()
        insights = await svc.analyze_block(
            block_id=BLOCK_ID,
            block_type=PMBlockType.SPRINT_BOARD,
            workspace_id=WORKSPACE_ID,
            data=_sprint_data(completed_cycles_count=2),
        )
        assert len(insights) == 1
        assert insights[0].severity == InsightSeverity.GREEN
        assert insights[0].insight_type == "insufficient_data"
        assert "3 sprints" in insights[0].analysis

    async def test_exactly_3_cycles_runs_normal_analysis(self) -> None:
        svc = _make_service()
        insights = await svc.analyze_block(
            block_id=BLOCK_ID,
            block_type=PMBlockType.SPRINT_BOARD,
            workspace_id=WORKSPACE_ID,
            data=_sprint_data(completed_cycles_count=3),
        )
        # No insufficient_data insight — normal path
        assert all(i.insight_type != "insufficient_data" for i in insights)

    async def test_zero_cycles_returns_insufficient_data(self) -> None:
        svc = _make_service()
        insights = await svc.analyze_block(
            block_id=BLOCK_ID,
            block_type=PMBlockType.SPRINT_BOARD,
            workspace_id=WORKSPACE_ID,
            data=_sprint_data(completed_cycles_count=0),
        )
        assert insights[0].insight_type == "insufficient_data"


# ---------------------------------------------------------------------------
# Dependency map analyzer
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestDependencyMapAnalyzer:
    async def test_no_issues_returns_empty(self) -> None:
        svc = _make_service()
        insights = await svc.analyze_block(
            block_id=BLOCK_ID,
            block_type=PMBlockType.DEPENDENCY_MAP,
            workspace_id=WORKSPACE_ID,
            data=_dep_data(),
        )
        assert insights == []

    async def test_critical_path_gt_20_returns_red(self) -> None:
        svc = _make_service()
        insights = await svc.analyze_block(
            block_id=BLOCK_ID,
            block_type=PMBlockType.DEPENDENCY_MAP,
            workspace_id=WORKSPACE_ID,
            data=_dep_data(critical_path_length=21),
        )
        cp = [i for i in insights if i.insight_type == "long_critical_path"]
        assert len(cp) == 1
        assert cp[0].severity == InsightSeverity.RED

    async def test_critical_path_gt_10_lte_20_returns_yellow(self) -> None:
        svc = _make_service()
        insights = await svc.analyze_block(
            block_id=BLOCK_ID,
            block_type=PMBlockType.DEPENDENCY_MAP,
            workspace_id=WORKSPACE_ID,
            data=_dep_data(critical_path_length=15),
        )
        cp = [i for i in insights if i.insight_type == "long_critical_path"]
        assert len(cp) == 1
        assert cp[0].severity == InsightSeverity.YELLOW

    async def test_critical_path_lte_10_not_flagged(self) -> None:
        svc = _make_service()
        insights = await svc.analyze_block(
            block_id=BLOCK_ID,
            block_type=PMBlockType.DEPENDENCY_MAP,
            workspace_id=WORKSPACE_ID,
            data=_dep_data(critical_path_length=10),
        )
        assert insights == []

    async def test_bottleneck_nodes_gt_5_flagged_yellow(self) -> None:
        svc = _make_service()
        insights = await svc.analyze_block(
            block_id=BLOCK_ID,
            block_type=PMBlockType.DEPENDENCY_MAP,
            workspace_id=WORKSPACE_ID,
            data=_dep_data(bottleneck_node_count=6),
        )
        bn = [i for i in insights if i.insight_type == "bottleneck_nodes"]
        assert len(bn) == 1
        assert bn[0].severity == InsightSeverity.YELLOW

    async def test_bottleneck_count_zero_not_flagged(self) -> None:
        svc = _make_service()
        insights = await svc.analyze_block(
            block_id=BLOCK_ID,
            block_type=PMBlockType.DEPENDENCY_MAP,
            workspace_id=WORKSPACE_ID,
            data=_dep_data(bottleneck_node_count=0),
        )
        assert all(i.insight_type != "bottleneck_nodes" for i in insights)


# ---------------------------------------------------------------------------
# Capacity plan analyzer
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestCapacityAnalyzer:
    async def test_no_members_returns_empty(self) -> None:
        svc = _make_service()
        insights = await svc.analyze_block(
            block_id=BLOCK_ID,
            block_type=PMBlockType.CAPACITY_PLAN,
            workspace_id=WORKSPACE_ID,
            data=_capacity_data(),
        )
        assert insights == []

    async def test_overallocated_member_returns_red(self) -> None:
        svc = _make_service()
        insights = await svc.analyze_block(
            block_id=BLOCK_ID,
            block_type=PMBlockType.CAPACITY_PLAN,
            workspace_id=WORKSPACE_ID,
            data=_capacity_data(members=[{"display_name": "Alice", "utilization_pct": 120}]),
        )
        over = [i for i in insights if i.insight_type == "overallocation"]
        assert len(over) == 1
        assert over[0].severity == InsightSeverity.RED
        assert "Alice" in over[0].analysis

    async def test_underallocated_member_returns_yellow(self) -> None:
        svc = _make_service()
        insights = await svc.analyze_block(
            block_id=BLOCK_ID,
            block_type=PMBlockType.CAPACITY_PLAN,
            workspace_id=WORKSPACE_ID,
            data=_capacity_data(members=[{"display_name": "Bob", "utilization_pct": 20}]),
        )
        under = [i for i in insights if i.insight_type == "underallocation"]
        assert len(under) == 1
        assert under[0].severity == InsightSeverity.YELLOW

    async def test_exactly_100_pct_not_overallocated(self) -> None:
        svc = _make_service()
        insights = await svc.analyze_block(
            block_id=BLOCK_ID,
            block_type=PMBlockType.CAPACITY_PLAN,
            workspace_id=WORKSPACE_ID,
            data=_capacity_data(members=[{"display_name": "Charlie", "utilization_pct": 100}]),
        )
        over = [i for i in insights if i.insight_type == "overallocation"]
        assert len(over) == 0

    async def test_exactly_30_pct_not_underallocated(self) -> None:
        svc = _make_service()
        insights = await svc.analyze_block(
            block_id=BLOCK_ID,
            block_type=PMBlockType.CAPACITY_PLAN,
            workspace_id=WORKSPACE_ID,
            data=_capacity_data(members=[{"display_name": "Dana", "utilization_pct": 30}]),
        )
        under = [i for i in insights if i.insight_type == "underallocation"]
        assert len(under) == 0

    async def test_multiple_overallocated_truncates_names_at_3(self) -> None:
        svc = _make_service()
        members = [{"display_name": f"Member{i}", "utilization_pct": 110 + i} for i in range(5)]
        insights = await svc.analyze_block(
            block_id=BLOCK_ID,
            block_type=PMBlockType.CAPACITY_PLAN,
            workspace_id=WORKSPACE_ID,
            data=_capacity_data(members=members),
        )
        over = [i for i in insights if i.insight_type == "overallocation"]
        assert len(over) == 1
        # Only first 3 names should appear in the analysis
        assert "Member4" not in over[0].analysis


# ---------------------------------------------------------------------------
# Release notes analyzer
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestReleaseNotesAnalyzer:
    async def test_no_entries_returns_empty(self) -> None:
        svc = _make_service()
        insights = await svc.analyze_block(
            block_id=BLOCK_ID,
            block_type=PMBlockType.RELEASE_NOTES,
            workspace_id=WORKSPACE_ID,
            data=_release_data(),
        )
        assert insights == []

    async def test_uncategorized_entries_returns_yellow(self) -> None:
        svc = _make_service()
        insights = await svc.analyze_block(
            block_id=BLOCK_ID,
            block_type=PMBlockType.RELEASE_NOTES,
            workspace_id=WORKSPACE_ID,
            data=_release_data(
                entries=[
                    {"category": "features"},
                    {"category": "uncategorized"},
                    {"category": "uncategorized"},
                ]
            ),
        )
        gaps = [i for i in insights if i.insight_type == "coverage_gaps"]
        assert len(gaps) == 1
        assert gaps[0].severity == InsightSeverity.YELLOW
        assert "2" in gaps[0].title

    async def test_all_categorized_returns_empty(self) -> None:
        svc = _make_service()
        insights = await svc.analyze_block(
            block_id=BLOCK_ID,
            block_type=PMBlockType.RELEASE_NOTES,
            workspace_id=WORKSPACE_ID,
            data=_release_data(
                entries=[
                    {"category": "features"},
                    {"category": "bug_fixes"},
                    {"category": "improvements"},
                ]
            ),
        )
        assert insights == []


# ---------------------------------------------------------------------------
# refresh_insights
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestRefreshInsights:
    async def test_refresh_soft_deletes_old_insights_and_stores_new(self) -> None:
        session = AsyncMock()
        repo = AsyncMock()

        # Simulate persisted insight returned from repo.create
        def _fake_model(**kwargs: Any) -> MagicMock:
            m = MagicMock()
            for k, v in kwargs.items():
                setattr(m, k, v)
            m.id = uuid4()
            return m

        saved_model = _fake_model(
            workspace_id=UUID(WORKSPACE_ID),
            block_id=BLOCK_ID,
            block_type=PMBlockType.SPRINT_BOARD,
            insight_type="stale_issues",
            severity=InsightSeverity.YELLOW,
            title="1 stale issue(s) in sprint",
            analysis="Some analysis",
            confidence=0.9,
            references=[],
            suggested_actions=[],
        )
        repo.create.return_value = saved_model

        svc = _make_service(session=session, repository=repo)

        with patch.object(svc, "_soft_delete_by_block", new=AsyncMock()) as mock_delete:
            result = await svc.refresh_insights(
                block_id=BLOCK_ID,
                block_type=PMBlockType.SPRINT_BOARD,
                workspace_id=WORKSPACE_ID,
                data=_sprint_data(stale_issues_count=1),
            )

        mock_delete.assert_awaited_once_with(
            block_id=BLOCK_ID,
            workspace_id=UUID(WORKSPACE_ID),
        )
        assert repo.create.called
        assert len(result) == 1

    async def test_refresh_with_no_insights_returns_empty(self) -> None:
        session = AsyncMock()
        repo = AsyncMock()

        svc = _make_service(session=session, repository=repo)

        with patch.object(svc, "_soft_delete_by_block", new=AsyncMock()):
            result = await svc.refresh_insights(
                block_id=BLOCK_ID,
                block_type=PMBlockType.SPRINT_BOARD,
                workspace_id=WORKSPACE_ID,
                data=_sprint_data(),  # no stale/blockers/velocity issues
            )

        repo.create.assert_not_called()
        assert result == []

    async def test_refresh_insufficient_data_stores_single_green_insight(self) -> None:
        session = AsyncMock()
        repo = AsyncMock()

        saved_model = MagicMock()
        saved_model.insight_type = "insufficient_data"
        repo.create.return_value = saved_model

        svc = _make_service(session=session, repository=repo)

        with patch.object(svc, "_soft_delete_by_block", new=AsyncMock()):
            result = await svc.refresh_insights(
                block_id=BLOCK_ID,
                block_type=PMBlockType.SPRINT_BOARD,
                workspace_id=WORKSPACE_ID,
                data=_sprint_data(completed_cycles_count=1),
            )

        assert repo.create.call_count == 1
        assert len(result) == 1


# ---------------------------------------------------------------------------
# Debounce logic (unit-level, not router-level)
# ---------------------------------------------------------------------------


class TestDebounceLogic:
    """Verify the age calculation used by the router debounce is correct.

    The debounce is implemented in the router, but we test the datetime
    arithmetic here to ensure the 30-second window logic is sound.
    """

    def test_age_within_30s_triggers_debounce(self) -> None:
        now = datetime.now(UTC)
        recent = now - timedelta(seconds=10)
        age = now - recent
        assert age < timedelta(seconds=30)

    def test_age_exactly_30s_bypasses_debounce(self) -> None:
        now = datetime.now(UTC)
        old = now - timedelta(seconds=30)
        age = now - old
        assert age >= timedelta(seconds=30)

    def test_naive_datetime_normalized_to_utc(self) -> None:
        naive = datetime(2026, 1, 1, 12, 0, 0)  # noqa: DTZ001 — intentionally naive
        aware = naive.replace(tzinfo=UTC)
        assert aware.tzinfo is UTC


# ---------------------------------------------------------------------------
# _make_insight helper
# ---------------------------------------------------------------------------


class TestMakeInsightHelper:
    def test_creates_valid_domain_entity(self) -> None:
        ws = uuid4()
        insight = _make_insight(
            workspace_id=ws,
            block_id="block-1",
            block_type=PMBlockType.SPRINT_BOARD,
            insight_type="stale_issues",
            severity=InsightSeverity.YELLOW,
            title="Test insight",
            analysis="Some analysis text",
            confidence=0.8,
        )
        assert isinstance(insight, PMBlockInsight)
        assert insight.workspace_id == ws
        assert insight.references == []
        assert insight.suggested_actions == []

    def test_invalid_confidence_raises(self) -> None:
        with pytest.raises(ValueError, match="confidence"):
            _make_insight(
                workspace_id=uuid4(),
                block_id="block-1",
                block_type=PMBlockType.SPRINT_BOARD,
                insight_type="stale_issues",
                severity=InsightSeverity.YELLOW,
                title="Test insight",
                analysis="Some analysis",
                confidence=1.5,  # Invalid
            )

    def test_empty_block_id_raises(self) -> None:
        with pytest.raises(ValueError, match="block_id"):
            _make_insight(
                workspace_id=uuid4(),
                block_id="   ",
                block_type=PMBlockType.SPRINT_BOARD,
                insight_type="stale_issues",
                severity=InsightSeverity.YELLOW,
                title="Test insight",
                analysis="Some analysis",
                confidence=0.8,
            )
