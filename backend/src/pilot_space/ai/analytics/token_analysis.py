"""Token usage analysis for AI agents.

Analyzes token consumption patterns across different agents
to identify optimization opportunities and high-cost operations.

T317: Token usage analytics per agent.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(frozen=True, slots=True)
class AgentTokenMetrics:
    """Token usage metrics for a specific agent.

    Attributes:
        agent_name: Name of the agent.
        request_count: Total number of requests.
        avg_input_tokens: Average input tokens per request.
        avg_output_tokens: Average output tokens per request.
        p95_input_tokens: 95th percentile input tokens.
        p95_output_tokens: 95th percentile output tokens.
        total_cost_usd: Total cost across all requests.
    """

    agent_name: str
    request_count: int
    avg_input_tokens: float
    avg_output_tokens: float
    p95_input_tokens: float
    p95_output_tokens: float
    total_cost_usd: Decimal


async def analyze_agent_token_usage(
    db_session: AsyncSession,
    *,
    days: int = 30,
    workspace_id: str | None = None,
) -> list[AgentTokenMetrics]:
    """Generate token usage report by agent.

    Queries ai_cost_records to analyze token consumption patterns
    across different agents. Useful for identifying high-cost agents
    and optimization opportunities.

    Args:
        db_session: Active database session.
        days: Number of days to analyze (default 30).
        workspace_id: Optional workspace ID to filter by.

    Returns:
        List of AgentTokenMetrics sorted by total cost descending.

    Example:
        metrics = await analyze_agent_token_usage(db, days=7)
        for metric in metrics:
            print(f"{metric.agent_name}: ${metric.total_cost_usd:.2f}")
            print(f"  Avg tokens: {metric.avg_input_tokens:.0f} in, {metric.avg_output_tokens:.0f} out")
    """
    from sqlalchemy import text

    # Build query with optional workspace filter
    workspace_filter = ""
    params: dict[str, int | str] = {"days": days}

    if workspace_id:
        workspace_filter = "AND workspace_id = :workspace_id"
        params["workspace_id"] = workspace_id

    query = text(f"""
        SELECT
            agent_name,
            COUNT(*) as request_count,
            AVG(input_tokens) as avg_input,
            AVG(output_tokens) as avg_output,
            PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY input_tokens) as p95_input,
            PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY output_tokens) as p95_output,
            SUM(cost_usd) as total_cost
        FROM ai_cost_records
        WHERE created_at > NOW() - INTERVAL ':days days'
        {workspace_filter}
        GROUP BY agent_name
        ORDER BY total_cost DESC
    """)

    result = await db_session.execute(query, params)
    rows = result.fetchall()

    return [
        AgentTokenMetrics(
            agent_name=row.agent_name,
            request_count=row.request_count,
            avg_input_tokens=float(row.avg_input),
            avg_output_tokens=float(row.avg_output),
            p95_input_tokens=float(row.p95_input),
            p95_output_tokens=float(row.p95_output),
            total_cost_usd=Decimal(str(row.total_cost)),
        )
        for row in rows
    ]


async def get_high_cost_agents(
    db_session: AsyncSession,
    *,
    threshold_usd: Decimal = Decimal("10.00"),
    days: int = 7,
) -> list[AgentTokenMetrics]:
    """Identify agents exceeding cost threshold.

    Args:
        db_session: Active database session.
        threshold_usd: Cost threshold in USD.
        days: Number of days to analyze.

    Returns:
        List of high-cost agents sorted by cost descending.
    """
    all_metrics = await analyze_agent_token_usage(db_session, days=days)
    return [m for m in all_metrics if m.total_cost_usd > threshold_usd]


async def get_token_efficiency_score(
    db_session: AsyncSession,
    agent_name: str,
    *,
    days: int = 30,
) -> float:
    """Calculate token efficiency score for an agent.

    Efficiency = output_tokens / (input_tokens + output_tokens)
    Higher score indicates more output per input.

    Args:
        db_session: Active database session.
        agent_name: Name of the agent to analyze.
        days: Number of days to analyze.

    Returns:
        Efficiency score between 0 and 1.
    """
    metrics = await analyze_agent_token_usage(db_session, days=days)

    for metric in metrics:
        if metric.agent_name == agent_name:
            total_tokens = metric.avg_input_tokens + metric.avg_output_tokens
            if total_tokens > 0:
                return metric.avg_output_tokens / total_tokens
            return 0.0

    return 0.0


async def get_daily_token_trend(
    db_session: AsyncSession,
    agent_name: str,
    *,
    days: int = 30,
) -> list[dict[str, Any]]:
    """Get daily token usage trend for an agent.

    Args:
        db_session: Active database session.
        agent_name: Name of the agent.
        days: Number of days to retrieve.

    Returns:
        List of daily statistics with date, input_tokens, output_tokens.
    """
    from sqlalchemy import text

    query = text("""
        SELECT
            DATE(created_at) as date,
            SUM(input_tokens) as total_input,
            SUM(output_tokens) as total_output,
            COUNT(*) as request_count
        FROM ai_cost_records
        WHERE agent_name = :agent_name
          AND created_at > NOW() - INTERVAL ':days days'
        GROUP BY DATE(created_at)
        ORDER BY date DESC
    """)

    result = await db_session.execute(
        query,
        {"agent_name": agent_name, "days": days},
    )
    rows = result.fetchall()

    return [
        {
            "date": row.date.isoformat(),
            "total_input_tokens": row.total_input,
            "total_output_tokens": row.total_output,
            "request_count": row.request_count,
        }
        for row in rows
    ]


async def generate_optimization_recommendations(
    db_session: AsyncSession,
    *,
    days: int = 7,
) -> list[str]:
    """Generate recommendations for token usage optimization.

    Args:
        db_session: Active database session.
        days: Number of days to analyze.

    Returns:
        List of recommendation strings.
    """
    recommendations: list[str] = []
    metrics = await analyze_agent_token_usage(db_session, days=days)

    for metric in metrics:
        # High average input tokens
        if metric.avg_input_tokens > 4000:
            recommendations.append(
                f"{metric.agent_name}: High input tokens ({metric.avg_input_tokens:.0f}). "
                f"Consider reducing context or chunking requests."
            )

        # High p95 suggests inconsistent usage
        if metric.p95_input_tokens > metric.avg_input_tokens * 2:
            recommendations.append(
                f"{metric.agent_name}: High p95/avg ratio. "
                f"Investigate outlier requests that may need optimization."
            )

        # Low efficiency (more input than output)
        efficiency = metric.avg_output_tokens / (metric.avg_input_tokens + metric.avg_output_tokens)
        if efficiency < 0.2:
            recommendations.append(
                f"{metric.agent_name}: Low efficiency ({efficiency:.2%}). "
                f"Consider whether all input context is necessary."
            )

    return recommendations


__all__ = [
    "AgentTokenMetrics",
    "analyze_agent_token_usage",
    "generate_optimization_recommendations",
    "get_daily_token_trend",
    "get_high_cost_agents",
    "get_token_efficiency_score",
]
