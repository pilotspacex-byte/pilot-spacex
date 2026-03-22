"""AI cost tracking and reporting for LLM and STT usage.

Tracks token usage and costs across providers for budget monitoring
and cost optimization.

T013: CostTracker class with provider pricing.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Final
from uuid import UUID

from sqlalchemy import Date, cast, func, literal_column, select

from pilot_space.infrastructure.database.models.ai_cost_record import AICostRecord
from pilot_space.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)

# Sentinel UUID for cost records where user_id is unknown.
_ZERO_UUID: Final[UUID] = UUID("00000000-0000-0000-0000-000000000000")

# Pricing per million tokens (as of 2026-01)
# Structure: {provider: {model: (input_cost, output_cost)}}
PRICING_TABLE: Final[dict[str, dict[str, tuple[Decimal, Decimal]]]] = {
    "anthropic": {
        "claude-opus-4-5-20251101": (Decimal("15.00"), Decimal("75.00")),
        "claude-sonnet-4-20250514": (Decimal("3.00"), Decimal("15.00")),
        "claude-3-5-haiku-20241022": (Decimal("1.00"), Decimal("5.00")),
    },
    "google": {
        "gemini-2.0-pro": (Decimal("1.25"), Decimal("5.00")),
        "gemini-2.0-flash": (Decimal("0.075"), Decimal("0.30")),
    },
    "openai": {
        "gpt-4o": (Decimal("5.00"), Decimal("15.00")),
        "gpt-4o-mini": (Decimal("0.15"), Decimal("0.60")),
        "text-embedding-3-large": (Decimal("0.13"), Decimal("0.00")),
    },
}

# Tokens per million for calculation
TOKENS_PER_MILLION: Final[int] = 1_000_000


@dataclass(frozen=True, slots=True)
class CostSummary:
    """Summary of AI costs for a time period."""

    total_cost: float
    total_requests: int
    total_input_tokens: int
    total_output_tokens: int
    by_provider: dict[str, float]
    by_agent: dict[str, float]
    by_model: dict[str, float]
    start_date: datetime
    end_date: datetime

    @property
    def total_tokens(self) -> int:
        """Get total token count."""
        return self.total_input_tokens + self.total_output_tokens

    @property
    def avg_cost_per_request(self) -> float:
        """Calculate average cost per request."""
        return self.total_cost / self.total_requests if self.total_requests > 0 else 0.0


@dataclass(frozen=True, slots=True)
class CostRecord:
    """Single cost record (immutable value object)."""

    id: UUID
    user_id: UUID
    workspace_id: UUID
    agent_name: str
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    created_at: datetime
    operation_type: str | None = None


class CostTracker:
    """Track and report AI usage costs.

    Calculates costs based on token usage and provider pricing,
    records costs to database, and generates cost summaries.

    Usage:
        tracker = CostTracker(session)
        cost = tracker.calculate_cost("anthropic", "claude-sonnet-4-20250514", 1000, 500)
        await tracker.track(workspace_id, user_id, "note_enhancer", "anthropic", ...)
        summary = await tracker.get_workspace_summary(workspace_id, days=30)
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize CostTracker.

        Args:
            session: Async database session.
        """
        self.session = session

    def calculate_cost(
        self,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        """Calculate cost for token usage.

        Args:
            provider: LLM provider (anthropic, openai, google).
            model: Model identifier.
            input_tokens: Number of input tokens.
            output_tokens: Number of output tokens.

        Returns:
            Cost in USD as float. Returns 0.0 for unknown providers/models
            (logged as warning) so cost tracking never crashes callers.
        """
        if provider not in PRICING_TABLE:
            logger.warning(
                "cost_tracker_unknown_provider",
                provider=provider,
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            )
            return 0.0

        provider_pricing = PRICING_TABLE[provider]
        if model not in provider_pricing:
            logger.warning(
                "cost_tracker_unknown_model",
                provider=provider,
                model=model,
                supported=list(provider_pricing.keys()),
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            )
            return 0.0

        input_price, output_price = provider_pricing[model]

        # Calculate cost: (tokens / 1M) * price_per_million
        input_cost = (Decimal(input_tokens) / TOKENS_PER_MILLION) * input_price
        output_cost = (Decimal(output_tokens) / TOKENS_PER_MILLION) * output_price
        total_cost = input_cost + output_cost

        return float(total_cost)

    async def track(
        self,
        workspace_id: UUID,
        user_id: UUID,
        agent_name: str,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        operation_type: str | None = None,
        cost_usd_override: float | None = None,
    ) -> CostRecord:
        """Track AI usage cost to database.

        When *cost_usd_override* is given, the token-based calculation is
        skipped (used for duration-based STT pricing).
        """
        cost_usd = (
            cost_usd_override
            if cost_usd_override is not None
            else self.calculate_cost(provider, model, input_tokens, output_tokens)
        )

        record = AICostRecord(
            workspace_id=workspace_id,
            user_id=user_id,
            agent_name=agent_name,
            provider=provider,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost_usd,
            operation_type=operation_type,
        )

        self.session.add(record)
        await self.session.flush()
        await self.session.refresh(record)

        logger.info(
            "cost_tracker_tracked",
            workspace_id=str(workspace_id),
            user_id=str(user_id),
            agent=agent_name,
            provider=provider,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost_usd,
        )

        return CostRecord(
            id=record.id,
            user_id=record.user_id,
            workspace_id=record.workspace_id,
            agent_name=record.agent_name,
            provider=record.provider,
            model=record.model,
            input_tokens=record.input_tokens,
            output_tokens=record.output_tokens,
            cost_usd=float(record.cost_usd),
            created_at=record.created_at,
            operation_type=record.operation_type,
        )

    async def get_workspace_summary(
        self,
        workspace_id: UUID,
        days: int = 30,
    ) -> CostSummary:
        """Get aggregated cost summary for a workspace over the last *days* days."""
        end_date = datetime.now(UTC)
        start_date = end_date - timedelta(days=days)

        # Base query filter
        base_filter = (
            (AICostRecord.workspace_id == workspace_id)
            & (AICostRecord.created_at >= start_date)
            & (AICostRecord.created_at <= end_date)
            & (AICostRecord.is_deleted == False)  # noqa: E712
        )

        # Total metrics
        total_query = select(
            func.coalesce(func.sum(AICostRecord.cost_usd), 0).label("total_cost"),
            func.count(AICostRecord.id).label("total_requests"),
            func.coalesce(func.sum(AICostRecord.input_tokens), 0).label("total_input_tokens"),
            func.coalesce(func.sum(AICostRecord.output_tokens), 0).label("total_output_tokens"),
        ).where(base_filter)

        result = await self.session.execute(total_query)
        row = result.one()

        total_cost = float(row.total_cost)
        total_requests = int(row.total_requests)
        total_input_tokens = int(row.total_input_tokens)
        total_output_tokens = int(row.total_output_tokens)

        # Breakdown by provider
        provider_query = (
            select(
                AICostRecord.provider,
                func.sum(AICostRecord.cost_usd).label("cost"),
            )
            .where(base_filter)
            .group_by(AICostRecord.provider)
        )
        provider_result = await self.session.execute(provider_query)
        by_provider = {row.provider: float(row.cost) for row in provider_result}

        # Breakdown by agent
        agent_query = (
            select(
                AICostRecord.agent_name,
                func.sum(AICostRecord.cost_usd).label("cost"),
            )
            .where(base_filter)
            .group_by(AICostRecord.agent_name)
        )
        agent_result = await self.session.execute(agent_query)
        by_agent = {row.agent_name: float(row.cost) for row in agent_result}

        # Breakdown by model
        model_query = (
            select(
                AICostRecord.model,
                func.sum(AICostRecord.cost_usd).label("cost"),
            )
            .where(base_filter)
            .group_by(AICostRecord.model)
        )
        model_result = await self.session.execute(model_query)
        by_model = {row.model: float(row.cost) for row in model_result}

        return CostSummary(
            total_cost=total_cost,
            total_requests=total_requests,
            total_input_tokens=total_input_tokens,
            total_output_tokens=total_output_tokens,
            by_provider=by_provider,
            by_agent=by_agent,
            by_model=by_model,
            start_date=start_date,
            end_date=end_date,
        )

    async def get_user_summary(
        self,
        user_id: UUID,
        days: int = 30,
    ) -> CostSummary:
        """Get aggregated cost summary for a user.

        Args:
            user_id: User UUID.
            days: Number of days to include in summary (default 30).

        Returns:
            CostSummary with aggregated costs and breakdowns.
        """
        end_date = datetime.now(UTC)
        start_date = end_date - timedelta(days=days)

        # Base query filter
        base_filter = (
            (AICostRecord.user_id == user_id)
            & (AICostRecord.created_at >= start_date)
            & (AICostRecord.created_at <= end_date)
            & (AICostRecord.is_deleted == False)  # noqa: E712
        )

        # Total metrics
        total_query = select(
            func.coalesce(func.sum(AICostRecord.cost_usd), 0).label("total_cost"),
            func.count(AICostRecord.id).label("total_requests"),
            func.coalesce(func.sum(AICostRecord.input_tokens), 0).label("total_input_tokens"),
            func.coalesce(func.sum(AICostRecord.output_tokens), 0).label("total_output_tokens"),
        ).where(base_filter)

        result = await self.session.execute(total_query)
        row = result.one()

        total_cost = float(row.total_cost)
        total_requests = int(row.total_requests)
        total_input_tokens = int(row.total_input_tokens)
        total_output_tokens = int(row.total_output_tokens)

        # Breakdown by provider
        provider_query = (
            select(
                AICostRecord.provider,
                func.sum(AICostRecord.cost_usd).label("cost"),
            )
            .where(base_filter)
            .group_by(AICostRecord.provider)
        )
        provider_result = await self.session.execute(provider_query)
        by_provider = {row.provider: float(row.cost) for row in provider_result}

        # Breakdown by agent
        agent_query = (
            select(
                AICostRecord.agent_name,
                func.sum(AICostRecord.cost_usd).label("cost"),
            )
            .where(base_filter)
            .group_by(AICostRecord.agent_name)
        )
        agent_result = await self.session.execute(agent_query)
        by_agent = {row.agent_name: float(row.cost) for row in agent_result}

        # Breakdown by model
        model_query = (
            select(
                AICostRecord.model,
                func.sum(AICostRecord.cost_usd).label("cost"),
            )
            .where(base_filter)
            .group_by(AICostRecord.model)
        )
        model_result = await self.session.execute(model_query)
        by_model = {row.model: float(row.cost) for row in model_result}

        return CostSummary(
            total_cost=total_cost,
            total_requests=total_requests,
            total_input_tokens=total_input_tokens,
            total_output_tokens=total_output_tokens,
            by_provider=by_provider,
            by_agent=by_agent,
            by_model=by_model,
            start_date=start_date,
            end_date=end_date,
        )

    async def get_cost_summary_detailed(
        self,
        workspace_id: UUID,
        start_date: date,
        end_date: date,
    ) -> dict[str, list[dict[str, Any]]]:
        """Get detailed cost summary with user and daily breakdowns.

        Args:
            workspace_id: Workspace UUID.
            start_date: Start date (inclusive).
            end_date: End date (inclusive).

        Returns:
            Dict with by_agent, by_user, by_day lists.
        """
        # Convert dates to datetime for comparison
        start_datetime = datetime.combine(start_date, datetime.min.time()).replace(tzinfo=UTC)
        end_datetime = datetime.combine(
            end_date, datetime.max.time().replace(microsecond=0)
        ).replace(tzinfo=UTC)

        base_filter = (
            (AICostRecord.workspace_id == workspace_id)
            & (AICostRecord.created_at >= start_datetime)
            & (AICostRecord.created_at <= end_datetime)
            & (AICostRecord.is_deleted == False)  # noqa: E712
        )

        # By agent
        agent_query = (
            select(
                AICostRecord.agent_name,
                func.sum(AICostRecord.cost_usd).label("total_cost_usd"),
                func.count(AICostRecord.id).label("request_count"),
                func.sum(AICostRecord.input_tokens).label("input_tokens"),
                func.sum(AICostRecord.output_tokens).label("output_tokens"),
            )
            .where(base_filter)
            .group_by(AICostRecord.agent_name)
            .order_by(func.sum(AICostRecord.cost_usd).desc())
        )
        agent_result = await self.session.execute(agent_query)
        by_agent = [
            {
                "agent_name": row.agent_name,
                "total_cost_usd": float(row.total_cost_usd),
                "request_count": int(row.request_count),
                "input_tokens": int(row.input_tokens),
                "output_tokens": int(row.output_tokens),
            }
            for row in agent_result
        ]

        # By user (with user name from relationship)
        user_query = (
            select(
                AICostRecord.user_id,
                func.sum(AICostRecord.cost_usd).label("total_cost_usd"),
                func.count(AICostRecord.id).label("request_count"),
            )
            .where(base_filter)
            .group_by(AICostRecord.user_id)
            .order_by(func.sum(AICostRecord.cost_usd).desc())
        )
        user_result = await self.session.execute(user_query)
        by_user = [
            {
                "user_id": str(row.user_id),
                "total_cost_usd": float(row.total_cost_usd),
                "request_count": int(row.request_count),
            }
            for row in user_result
        ]

        # By day
        day_query = (
            select(
                cast(AICostRecord.created_at, Date).label("date"),
                func.sum(AICostRecord.cost_usd).label("total_cost_usd"),
                func.count(AICostRecord.id).label("request_count"),
            )
            .where(base_filter)
            .group_by(cast(AICostRecord.created_at, Date))
            .order_by(cast(AICostRecord.created_at, Date))
        )
        day_result = await self.session.execute(day_query)
        by_day = [
            {
                "date": row.date,
                "total_cost_usd": float(row.total_cost_usd),
                "request_count": int(row.request_count),
            }
            for row in day_result
        ]

        return {
            "by_agent": by_agent,
            "by_user": by_user,
            "by_day": by_day,
        }

    async def get_cost_by_user_detailed(
        self,
        workspace_id: UUID,
        start_date: date,
        end_date: date,
    ) -> list[dict[str, Any]]:
        """Get cost breakdown by user with user details.

        Args:
            workspace_id: Workspace UUID.
            start_date: Start date (inclusive).
            end_date: End date (inclusive).

        Returns:
            List of user cost records with names.
        """
        start_datetime = datetime.combine(start_date, datetime.min.time()).replace(tzinfo=UTC)
        end_datetime = datetime.combine(
            end_date, datetime.max.time().replace(microsecond=0)
        ).replace(tzinfo=UTC)

        base_filter = (
            (AICostRecord.workspace_id == workspace_id)
            & (AICostRecord.created_at >= start_datetime)
            & (AICostRecord.created_at <= end_datetime)
            & (AICostRecord.is_deleted == False)  # noqa: E712
        )

        query = (
            select(
                AICostRecord.user_id,
                func.sum(AICostRecord.cost_usd).label("total_cost_usd"),
                func.count(AICostRecord.id).label("request_count"),
            )
            .where(base_filter)
            .group_by(AICostRecord.user_id)
            .order_by(func.sum(AICostRecord.cost_usd).desc())
        )
        result = await self.session.execute(query)

        return [
            {
                "user_id": str(row.user_id),
                "total_cost_usd": float(row.total_cost_usd),
                "request_count": int(row.request_count),
            }
            for row in result
        ]

    async def get_cost_trends(
        self,
        workspace_id: UUID,
        start_date: date,
        end_date: date,
        granularity: str = "daily",
    ) -> list[dict[str, Any]]:
        """Get cost trends over time.

        Args:
            workspace_id: Workspace UUID.
            start_date: Start date (inclusive).
            end_date: End date (inclusive).
            granularity: "daily" or "weekly".

        Returns:
            List of trend data points.
        """
        start_datetime = datetime.combine(start_date, datetime.min.time()).replace(tzinfo=UTC)
        end_datetime = datetime.combine(
            end_date, datetime.max.time().replace(microsecond=0)
        ).replace(tzinfo=UTC)

        base_filter = (
            (AICostRecord.workspace_id == workspace_id)
            & (AICostRecord.created_at >= start_datetime)
            & (AICostRecord.created_at <= end_datetime)
            & (AICostRecord.is_deleted == False)  # noqa: E712
        )

        if granularity == "weekly":
            # PostgreSQL week aggregation (ISO week)
            period_expr = func.to_char(AICostRecord.created_at, "IYYY-IW")
        else:
            # Daily aggregation — cast to Date for simple day grouping
            period_expr = cast(AICostRecord.created_at, Date)

        query = (
            select(
                period_expr.label("period"),
                func.sum(AICostRecord.cost_usd).label("total_cost_usd"),
                func.count(AICostRecord.id).label("request_count"),
            )
            .where(base_filter)
            .group_by(literal_column("period"))
            .order_by(literal_column("period"))
        )

        result = await self.session.execute(query)

        trends = []
        for row in result:
            total_cost = float(row.total_cost_usd)
            count = int(row.request_count)
            period = row.period
            if isinstance(period, date):
                period = period.isoformat()
            trends.append(
                {
                    "period": str(period),
                    "total_cost_usd": total_cost,
                    "request_count": count,
                    "avg_cost_per_request": total_cost / count if count > 0 else 0.0,
                }
            )

        return trends


def extract_response_usage(response: Any) -> tuple[int, int]:
    """Extract (input_tokens, output_tokens) from an Anthropic API Message response.

    Works with both the direct Anthropic client ``response.usage.input_tokens``
    shape and the Claude Agent SDK ``ResultMessage.usage`` shape where attributes
    may be ``None``.

    Returns (0, 0) when usage information is unavailable.
    """
    usage = getattr(response, "usage", None)
    if usage is None:
        return 0, 0
    return (
        getattr(usage, "input_tokens", 0) or 0,
        getattr(usage, "output_tokens", 0) or 0,
    )


async def track_cost(
    session: AsyncSession,
    *,
    workspace_id: UUID,
    user_id: UUID | None,
    agent_name: str,
    provider: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    operation_type: str | None = None,
    cost_usd_override: float | None = None,
) -> None:
    """Fire-and-forget cost tracking for services without DI-injected CostTracker.

    Uses an independent session so cost records survive a caller rollback.
    """
    from sqlalchemy.ext.asyncio import AsyncSession as _AsyncSession

    try:
        # Derive the engine from the caller's session so we can open an
        # independent transaction — cost rows must not be rolled back with the caller.
        conn = await session.connection()
        engine = conn.engine
        async with _AsyncSession(engine) as independent_session, independent_session.begin():
            tracker = CostTracker(independent_session)
            await tracker.track(
                workspace_id=workspace_id,
                user_id=user_id or _ZERO_UUID,
                agent_name=agent_name,
                provider=provider,
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                operation_type=operation_type,
                cost_usd_override=cost_usd_override,
            )
    except Exception:
        logger.warning(
            "track_cost_failed",
            agent_name=agent_name,
            provider=provider,
            model=model,
        )


__all__ = [
    "PRICING_TABLE",
    "CostRecord",
    "CostSummary",
    "CostTracker",
    "extract_response_usage",
    "track_cost",
]
