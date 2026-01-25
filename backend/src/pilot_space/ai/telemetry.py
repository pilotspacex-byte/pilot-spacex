"""AI telemetry and metrics collection.

Provides observability for AI operations:
- Request latency tracking
- Token usage and cost estimation
- Error rate monitoring
- Provider health metrics

T091e: AI telemetry middleware.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import AsyncIterator
    from uuid import UUID

logger = logging.getLogger(__name__)


class AIProvider(Enum):
    """AI provider identifiers for metrics."""

    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    GOOGLE = "google"


class AIOperation(Enum):
    """AI operation types for metrics."""

    GHOST_TEXT = "ghost_text"
    MARGIN_ANNOTATION = "margin_annotation"
    ISSUE_EXTRACTION = "issue_extraction"
    ISSUE_ENHANCEMENT = "issue_enhancement"
    DUPLICATE_DETECTION = "duplicate_detection"
    PR_REVIEW = "pr_review"
    CONTEXT_GENERATION = "context_generation"
    CONVERSATION = "conversation"
    EMBEDDING = "embedding"


# Approximate cost per 1K tokens (USD) - updated as of 2025
# These should be configurable per workspace for BYOK
TOKEN_COSTS = {
    AIProvider.ANTHROPIC: {
        "claude-opus-4-5-20251101": {"input": 0.015, "output": 0.075},
        "claude-sonnet-4-20250514": {"input": 0.003, "output": 0.015},
        "claude-haiku-3-5-20241022": {"input": 0.00025, "output": 0.00125},
    },
    AIProvider.OPENAI: {
        "gpt-4o": {"input": 0.005, "output": 0.015},
        "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
        "text-embedding-3-large": {"input": 0.00013, "output": 0.0},
        "text-embedding-3-small": {"input": 0.00002, "output": 0.0},
    },
    AIProvider.GOOGLE: {
        "gemini-2.0-flash": {"input": 0.00035, "output": 0.0015},
        "gemini-2.0-pro": {"input": 0.00125, "output": 0.005},
    },
}


@dataclass
class AIMetrics:
    """Metrics for a single AI operation.

    Attributes:
        operation: Type of AI operation.
        provider: AI provider used.
        model: Model identifier.
        workspace_id: Workspace context.
        user_id: User who triggered the operation.
        correlation_id: Request correlation ID.
        start_time: Operation start timestamp.
        end_time: Operation end timestamp.
        duration_ms: Operation duration in milliseconds.
        input_tokens: Number of input tokens.
        output_tokens: Number of output tokens.
        estimated_cost_usd: Estimated cost in USD.
        success: Whether operation succeeded.
        error_type: Error type if failed.
        cached: Whether result was from cache.
    """

    operation: AIOperation
    provider: AIProvider
    model: str
    workspace_id: UUID
    user_id: UUID
    correlation_id: str
    start_time: datetime = field(default_factory=lambda: datetime.now(tz=UTC))
    end_time: datetime | None = None
    duration_ms: float | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost_usd: float = 0.0
    success: bool = True
    error_type: str | None = None
    cached: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)  # pyright: ignore[reportUnknownVariableType]

    def complete(
        self,
        *,
        input_tokens: int = 0,
        output_tokens: int = 0,
        success: bool = True,
        error_type: str | None = None,
        cached: bool = False,
    ) -> None:
        """Mark operation as complete and calculate metrics.

        Args:
            input_tokens: Number of input tokens used.
            output_tokens: Number of output tokens generated.
            success: Whether operation succeeded.
            error_type: Error type if failed.
            cached: Whether result was from cache.
        """
        self.end_time = datetime.now(tz=UTC)
        self.duration_ms = (self.end_time - self.start_time).total_seconds() * 1000
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.success = success
        self.error_type = error_type
        self.cached = cached

        # Calculate estimated cost
        self.estimated_cost_usd = self._calculate_cost()

    def _calculate_cost(self) -> float:
        """Calculate estimated cost based on token usage.

        Returns:
            Estimated cost in USD.
        """
        if self.cached:
            return 0.0

        provider_costs = TOKEN_COSTS.get(self.provider, {})
        model_costs = provider_costs.get(self.model, {"input": 0.0, "output": 0.0})

        input_cost = (self.input_tokens / 1000) * model_costs["input"]
        output_cost = (self.output_tokens / 1000) * model_costs["output"]

        return input_cost + output_cost

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for logging/storage.

        Returns:
            Dictionary representation of metrics.
        """
        return {
            "operation": self.operation.value,
            "provider": self.provider.value,
            "model": self.model,
            "workspace_id": str(self.workspace_id),
            "user_id": str(self.user_id),
            "correlation_id": self.correlation_id,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_ms": self.duration_ms,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "estimated_cost_usd": self.estimated_cost_usd,
            "success": self.success,
            "error_type": self.error_type,
            "cached": self.cached,
            "metadata": self.metadata,
        }


class TelemetryCollector:
    """Collects and aggregates AI telemetry data.

    Thread-safe collector for AI operation metrics.
    Designed to be used as a singleton or injected dependency.
    """

    def __init__(self) -> None:
        """Initialize telemetry collector."""
        self._metrics: list[AIMetrics] = []
        self._workspace_totals: dict[UUID, dict[str, float]] = {}

    def record(self, metrics: AIMetrics) -> None:
        """Record completed metrics.

        Args:
            metrics: Completed AI metrics to record.
        """
        self._metrics.append(metrics)

        # Update workspace totals
        ws_id = metrics.workspace_id
        if ws_id not in self._workspace_totals:
            self._workspace_totals[ws_id] = {
                "total_cost_usd": 0.0,
                "total_requests": 0,
                "total_input_tokens": 0,
                "total_output_tokens": 0,
                "total_errors": 0,
            }

        totals = self._workspace_totals[ws_id]
        totals["total_cost_usd"] += metrics.estimated_cost_usd
        totals["total_requests"] += 1
        totals["total_input_tokens"] += metrics.input_tokens
        totals["total_output_tokens"] += metrics.output_tokens
        if not metrics.success:
            totals["total_errors"] += 1

        # Log metrics
        logger.info(
            "AI operation completed",
            extra=metrics.to_dict(),
        )

    def get_workspace_summary(self, workspace_id: UUID) -> dict[str, Any]:
        """Get cost summary for a workspace.

        Args:
            workspace_id: Workspace to get summary for.

        Returns:
            Dictionary with cost and usage summary.
        """
        if workspace_id not in self._workspace_totals:
            return {
                "workspace_id": str(workspace_id),
                "total_cost_usd": 0.0,
                "total_requests": 0,
                "total_input_tokens": 0,
                "total_output_tokens": 0,
                "total_errors": 0,
                "error_rate": 0.0,
            }

        totals = self._workspace_totals[workspace_id]
        error_rate = (
            totals["total_errors"] / totals["total_requests"]
            if totals["total_requests"] > 0
            else 0.0
        )

        return {
            "workspace_id": str(workspace_id),
            **totals,
            "error_rate": error_rate,
        }

    def get_recent_metrics(
        self,
        workspace_id: UUID | None = None,
        operation: AIOperation | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Get recent metrics with optional filtering.

        Args:
            workspace_id: Filter by workspace.
            operation: Filter by operation type.
            limit: Maximum number of metrics to return.

        Returns:
            List of metrics dictionaries.
        """
        filtered = self._metrics

        if workspace_id:
            filtered = [m for m in filtered if m.workspace_id == workspace_id]

        if operation:
            filtered = [m for m in filtered if m.operation == operation]

        # Return most recent
        return [m.to_dict() for m in filtered[-limit:]]

    def clear(self) -> None:
        """Clear all collected metrics. Used for testing."""
        self._metrics.clear()
        self._workspace_totals.clear()


# Global singleton instance
_collector: TelemetryCollector | None = None


def get_telemetry_collector() -> TelemetryCollector:
    """Get the global telemetry collector instance.

    Returns:
        TelemetryCollector singleton.
    """
    global _collector  # noqa: PLW0603
    if _collector is None:
        _collector = TelemetryCollector()
    return _collector


@asynccontextmanager
async def track_ai_operation(
    operation: AIOperation,
    provider: AIProvider,
    model: str,
    workspace_id: UUID,
    user_id: UUID,
    correlation_id: str,
    **metadata: Any,
) -> AsyncIterator[AIMetrics]:
    """Context manager for tracking AI operation metrics.

    Args:
        operation: Type of AI operation.
        provider: AI provider being used.
        model: Model identifier.
        workspace_id: Workspace context.
        user_id: User triggering operation.
        correlation_id: Request correlation ID.
        **metadata: Additional metadata to record.

    Yields:
        AIMetrics instance to update with results.

    Usage:
        async with track_ai_operation(
            AIOperation.GHOST_TEXT,
            AIProvider.GOOGLE,
            "gemini-2.0-flash",
            workspace_id,
            user_id,
            correlation_id,
        ) as metrics:
            result = await provider.generate(prompt)
            metrics.complete(
                input_tokens=result.input_tokens,
                output_tokens=result.output_tokens,
            )
    """
    metrics = AIMetrics(
        operation=operation,
        provider=provider,
        model=model,
        workspace_id=workspace_id,
        user_id=user_id,
        correlation_id=correlation_id,
        metadata=metadata,
    )

    try:
        yield metrics
    except Exception as e:
        metrics.complete(
            success=False,
            error_type=type(e).__name__,
        )
        raise
    finally:
        # Only record if not already completed
        if metrics.end_time is None:
            metrics.complete()

        collector = get_telemetry_collector()
        collector.record(metrics)


def log_ai_latency(
    operation: str,
    duration_ms: float,
    provider: str,
    model: str,
    **extra: Any,
) -> None:
    """Log AI operation latency for monitoring.

    Args:
        operation: Operation name.
        duration_ms: Duration in milliseconds.
        provider: AI provider name.
        model: Model identifier.
        **extra: Additional context.
    """
    logger.info(
        "AI latency",
        extra={
            "operation": operation,
            "duration_ms": duration_ms,
            "provider": provider,
            "model": model,
            **extra,
        },
    )


__all__ = [
    "AIMetrics",
    "AIOperation",
    "AIProvider",
    "TelemetryCollector",
    "get_telemetry_collector",
    "log_ai_latency",
    "track_ai_operation",
]
