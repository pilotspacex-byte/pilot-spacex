"""AI telemetry package.

Re-exports the legacy ``telemetry.py`` surface (kept in
``telemetry/legacy.py``) plus Phase 69 memory recall counters from
``memory_metrics``.

Public surface unchanged for callers using
``from pilot_space.ai.telemetry import AIMetrics, AIProvider, ...``.
"""

from pilot_space.ai.telemetry.legacy import (
    AIMetrics,
    AIOperation,
    AIProvider,
    TelemetryCollector,
    get_telemetry_collector,
    log_ai_latency,
    record_request_metrics,
    update_active_sessions_metric,
    update_circuit_breaker_metric,
)
from pilot_space.ai.telemetry.memory_metrics import (
    get_hit_rate,
    get_latency_p95_ms,
    record_recall_hit,
    record_recall_latency_ms,
    record_recall_miss,
    reset_metrics,
    snapshot,
)

__all__ = [
    "AIMetrics",
    "AIOperation",
    "AIProvider",
    "TelemetryCollector",
    "get_hit_rate",
    "get_latency_p95_ms",
    "get_telemetry_collector",
    "log_ai_latency",
    "record_recall_hit",
    "record_recall_latency_ms",
    "record_recall_miss",
    "record_request_metrics",
    "reset_metrics",
    "snapshot",
    "update_active_sessions_metric",
    "update_circuit_breaker_metric",
]
