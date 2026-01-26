"""Cost tracking response schemas.

Pydantic models for AI cost analytics endpoints.

T091-T092: Cost tracking schemas.
"""

from __future__ import annotations

from datetime import date as date_type

from pydantic import BaseModel, ConfigDict, Field


class CostByAgent(BaseModel):
    """Cost breakdown by agent."""

    model_config = ConfigDict(frozen=True, strict=True)

    agent_name: str = Field(description="Agent name")
    total_cost_usd: float = Field(description="Total cost in USD", ge=0)
    request_count: int = Field(description="Number of requests", ge=0)
    input_tokens: int = Field(description="Total input tokens", ge=0)
    output_tokens: int = Field(description="Total output tokens", ge=0)


class CostByUser(BaseModel):
    """Cost breakdown by user."""

    model_config = ConfigDict(frozen=True, strict=True)

    user_id: str = Field(description="User ID")
    user_name: str = Field(description="User full name")
    total_cost_usd: float = Field(description="Total cost in USD", ge=0)
    request_count: int = Field(description="Number of requests", ge=0)


class CostByDay(BaseModel):
    """Daily cost summary."""

    model_config = ConfigDict(frozen=True, strict=True)

    date: date_type = Field(description="Date")
    total_cost_usd: float = Field(description="Total cost in USD", ge=0)
    request_count: int = Field(description="Number of requests", ge=0)


class CostSummaryResponse(BaseModel):
    """Cost summary response."""

    model_config = ConfigDict(strict=True)

    workspace_id: str = Field(description="Workspace ID")
    period_start: date_type = Field(description="Period start date")
    period_end: date_type = Field(description="Period end date")
    total_cost_usd: float = Field(description="Total cost in USD", ge=0)
    total_requests: int = Field(description="Total requests", ge=0)
    total_input_tokens: int = Field(description="Total input tokens", ge=0)
    total_output_tokens: int = Field(description="Total output tokens", ge=0)
    by_agent: list[CostByAgent] = Field(description="Cost breakdown by agent")
    by_user: list[CostByUser] = Field(description="Cost breakdown by user")
    by_day: list[CostByDay] = Field(description="Daily cost breakdown")


class CostByUserResponse(BaseModel):
    """Cost by user response."""

    model_config = ConfigDict(strict=True)

    workspace_id: str = Field(description="Workspace ID")
    period_start: date_type = Field(description="Period start date")
    period_end: date_type = Field(description="Period end date")
    users: list[CostByUser] = Field(description="User cost breakdown")
    total_cost_usd: float = Field(description="Total cost in USD", ge=0)


class TrendDataPoint(BaseModel):
    """Single trend data point."""

    model_config = ConfigDict(frozen=True, strict=True)

    period: str = Field(description="Period label (YYYY-MM-DD or YYYY-Wxx)")
    total_cost_usd: float = Field(description="Total cost in USD", ge=0)
    request_count: int = Field(description="Number of requests", ge=0)
    avg_cost_per_request: float = Field(description="Average cost per request", ge=0)


class CostTrendsResponse(BaseModel):
    """Cost trends response."""

    model_config = ConfigDict(strict=True)

    workspace_id: str = Field(description="Workspace ID")
    period_start: date_type = Field(description="Period start date")
    period_end: date_type = Field(description="Period end date")
    granularity: str = Field(description="Trend granularity (daily or weekly)")
    trends: list[TrendDataPoint] = Field(description="Trend data points")


__all__ = [
    "CostByAgent",
    "CostByDay",
    "CostByUser",
    "CostByUserResponse",
    "CostSummaryResponse",
    "CostTrendsResponse",
    "TrendDataPoint",
]
