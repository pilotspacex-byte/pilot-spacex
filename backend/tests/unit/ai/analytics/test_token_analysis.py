"""Tests for token usage analysis.

T317: Token usage analytics tests.
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest

from pilot_space.ai.analytics.token_analysis import (
    AgentTokenMetrics,
    analyze_agent_token_usage,
    generate_optimization_recommendations,
    get_high_cost_agents,
    get_token_efficiency_score,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
def mock_db_session() -> AsyncSession:
    """Create mock database session."""
    session = MagicMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def sample_token_metrics() -> list[tuple]:
    """Sample token metrics query results."""
    return [
        (
            "pr_review",
            100,
            3500.0,
            2000.0,
            5000.0,
            3500.0,
            Decimal("12.50"),
        ),
        (
            "ai_context",
            200,
            2000.0,
            4000.0,
            3500.0,
            6000.0,
            Decimal("8.25"),
        ),
        (
            "ghost_text",
            500,
            100.0,
            30.0,
            150.0,
            50.0,
            Decimal("0.85"),
        ),
    ]


class TestAnalyzeAgentTokenUsage:
    """Tests for analyze_agent_token_usage function."""

    @pytest.mark.asyncio
    async def test_returns_metrics_sorted_by_cost(
        self,
        mock_db_session: AsyncSession,
        sample_token_metrics: list[tuple],
    ) -> None:
        """Verify metrics are returned sorted by total cost descending."""
        # Setup mock query result
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            MagicMock(
                agent_name=row[0],
                request_count=row[1],
                avg_input=row[2],
                avg_output=row[3],
                p95_input=row[4],
                p95_output=row[5],
                total_cost=row[6],
            )
            for row in sample_token_metrics
        ]
        mock_db_session.execute.return_value = mock_result

        # Execute
        metrics = await analyze_agent_token_usage(mock_db_session, days=30)

        # Verify
        assert len(metrics) == 3
        assert metrics[0].agent_name == "pr_review"
        assert metrics[0].total_cost_usd == Decimal("12.50")
        assert metrics[1].agent_name == "ai_context"
        assert metrics[2].agent_name == "ghost_text"

    @pytest.mark.asyncio
    async def test_includes_workspace_filter_when_provided(
        self,
        mock_db_session: AsyncSession,
    ) -> None:
        """Verify workspace_id filter is applied to query."""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_db_session.execute.return_value = mock_result

        await analyze_agent_token_usage(
            mock_db_session,
            days=7,
            workspace_id="test-workspace-id",
        )

        # Verify execute was called with workspace_id
        call_args = mock_db_session.execute.call_args
        assert call_args is not None
        assert "workspace_id" in call_args[0][1]
        assert call_args[0][1]["workspace_id"] == "test-workspace-id"


class TestGetHighCostAgents:
    """Tests for get_high_cost_agents function."""

    @pytest.mark.asyncio
    async def test_filters_agents_above_threshold(
        self,
        mock_db_session: AsyncSession,
        sample_token_metrics: list[tuple],
    ) -> None:
        """Verify only agents above cost threshold are returned."""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            MagicMock(
                agent_name=row[0],
                request_count=row[1],
                avg_input=row[2],
                avg_output=row[3],
                p95_input=row[4],
                p95_output=row[5],
                total_cost=row[6],
            )
            for row in sample_token_metrics
        ]
        mock_db_session.execute.return_value = mock_result

        # Get agents costing more than $5
        high_cost = await get_high_cost_agents(
            mock_db_session,
            threshold_usd=Decimal("5.00"),
            days=7,
        )

        # Should return pr_review and ai_context, not ghost_text
        assert len(high_cost) == 2
        assert high_cost[0].agent_name == "pr_review"
        assert high_cost[1].agent_name == "ai_context"


class TestGetTokenEfficiencyScore:
    """Tests for get_token_efficiency_score function."""

    @pytest.mark.asyncio
    async def test_calculates_efficiency_correctly(
        self,
        mock_db_session: AsyncSession,
    ) -> None:
        """Verify efficiency score calculation."""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            MagicMock(
                agent_name="test_agent",
                request_count=100,
                avg_input=1000.0,
                avg_output=500.0,
                p95_input=1500.0,
                p95_output=700.0,
                total_cost=Decimal("5.00"),
            )
        ]
        mock_db_session.execute.return_value = mock_result

        efficiency = await get_token_efficiency_score(
            mock_db_session,
            "test_agent",
            days=30,
        )

        # Efficiency = 500 / (1000 + 500) = 0.333...
        assert 0.33 < efficiency < 0.34

    @pytest.mark.asyncio
    async def test_returns_zero_for_unknown_agent(
        self,
        mock_db_session: AsyncSession,
    ) -> None:
        """Verify returns 0.0 for unknown agent."""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_db_session.execute.return_value = mock_result

        efficiency = await get_token_efficiency_score(
            mock_db_session,
            "unknown_agent",
            days=30,
        )

        assert efficiency == 0.0


class TestGenerateOptimizationRecommendations:
    """Tests for generate_optimization_recommendations function."""

    @pytest.mark.asyncio
    async def test_recommends_reducing_high_input_tokens(
        self,
        mock_db_session: AsyncSession,
    ) -> None:
        """Verify recommendation for agents with high input tokens."""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            MagicMock(
                agent_name="high_input_agent",
                request_count=100,
                avg_input=5000.0,  # High input
                avg_output=1000.0,
                p95_input=6000.0,
                p95_output=1500.0,
                total_cost=Decimal("10.00"),
            )
        ]
        mock_db_session.execute.return_value = mock_result

        recommendations = await generate_optimization_recommendations(
            mock_db_session,
            days=7,
        )

        assert len(recommendations) > 0
        assert any("high_input_agent" in rec for rec in recommendations)
        assert any("High input tokens" in rec for rec in recommendations)

    @pytest.mark.asyncio
    async def test_recommends_investigating_high_p95_ratio(
        self,
        mock_db_session: AsyncSession,
    ) -> None:
        """Verify recommendation for high p95/avg ratio."""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            MagicMock(
                agent_name="inconsistent_agent",
                request_count=100,
                avg_input=1000.0,
                avg_output=500.0,
                p95_input=3000.0,  # 3x average
                p95_output=600.0,
                total_cost=Decimal("5.00"),
            )
        ]
        mock_db_session.execute.return_value = mock_result

        recommendations = await generate_optimization_recommendations(
            mock_db_session,
            days=7,
        )

        assert len(recommendations) > 0
        assert any("inconsistent_agent" in rec for rec in recommendations)
        assert any("p95/avg ratio" in rec for rec in recommendations)

    @pytest.mark.asyncio
    async def test_recommends_improving_low_efficiency(
        self,
        mock_db_session: AsyncSession,
    ) -> None:
        """Verify recommendation for low efficiency agents."""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            MagicMock(
                agent_name="low_efficiency_agent",
                request_count=100,
                avg_input=9000.0,  # Much more input than output
                avg_output=1000.0,  # Efficiency = 0.1
                p95_input=10000.0,
                p95_output=1200.0,
                total_cost=Decimal("8.00"),
            )
        ]
        mock_db_session.execute.return_value = mock_result

        recommendations = await generate_optimization_recommendations(
            mock_db_session,
            days=7,
        )

        assert len(recommendations) > 0
        assert any("low_efficiency_agent" in rec for rec in recommendations)
        assert any("Low efficiency" in rec for rec in recommendations)


class TestAgentTokenMetrics:
    """Tests for AgentTokenMetrics dataclass."""

    def test_creates_valid_metrics_object(self) -> None:
        """Verify AgentTokenMetrics can be created with valid data."""
        metrics = AgentTokenMetrics(
            agent_name="test_agent",
            request_count=100,
            avg_input_tokens=1500.0,
            avg_output_tokens=800.0,
            p95_input_tokens=2000.0,
            p95_output_tokens=1200.0,
            total_cost_usd=Decimal("5.25"),
        )

        assert metrics.agent_name == "test_agent"
        assert metrics.request_count == 100
        assert metrics.avg_input_tokens == 1500.0
        assert metrics.total_cost_usd == Decimal("5.25")

    def test_is_immutable(self) -> None:
        """Verify AgentTokenMetrics is immutable (frozen dataclass)."""
        metrics = AgentTokenMetrics(
            agent_name="test_agent",
            request_count=100,
            avg_input_tokens=1500.0,
            avg_output_tokens=800.0,
            p95_input_tokens=2000.0,
            p95_output_tokens=1200.0,
            total_cost_usd=Decimal("5.25"),
        )

        with pytest.raises(AttributeError):
            metrics.request_count = 200  # type: ignore[misc]
