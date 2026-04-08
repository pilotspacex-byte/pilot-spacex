"""In-process counters for Phase 69 memory recall observability.

Lightweight, dependency-free, lock-free under asyncio (single event
loop per process). Counters live on a module-level singleton so they
survive across ``MemoryRecallService`` instances and across requests.

Public surface — function-style to match the plan 69-07 task spec and
to keep tests trivial:

* ``record_recall_hit()`` — increment hit counter
* ``record_recall_miss()`` — increment miss counter
* ``record_recall_latency_ms(value)`` — append to bounded ring buffer
* ``get_hit_rate()`` — hit / (hit + miss); ``0.0`` when both zero
* ``get_latency_p95_ms()`` — p95 over the latency buffer
* ``snapshot()`` — frozen dict (for ``/metrics`` endpoints, tests)
* ``reset_metrics()`` — clear all counters; tests only

The latency buffer is a fixed-size ``deque`` (1024 entries) so memory
stays bounded under sustained load.
"""

from __future__ import annotations

from collections import deque
from typing import Final

_LATENCY_BUFFER_SIZE: Final[int] = 1024

# ---------------------------------------------------------------------------
# Phase 70 — memory producer counters
# ---------------------------------------------------------------------------

_producer_enqueued: dict[str, int] = {}
_producer_dropped: dict[tuple[str, str], int] = {}


def record_producer_enqueued(memory_type: str) -> None:
    """Increment the successful enqueue counter for a memory producer."""
    _producer_enqueued[memory_type] = _producer_enqueued.get(memory_type, 0) + 1


def record_producer_dropped(memory_type: str, reason: str) -> None:
    """Increment the drop counter for a memory producer.

    ``reason`` is one of ``"opt_out"``, ``"enqueue_error"``, ``"duplicate"``.
    """
    key = (memory_type, reason)
    _producer_dropped[key] = _producer_dropped.get(key, 0) + 1


def get_producer_counters() -> dict[str, dict[str, int]]:
    """Return a point-in-time snapshot of producer counters."""
    return {
        "enqueued": dict(_producer_enqueued),
        "dropped": {f"{k[0]}::{k[1]}": v for k, v in _producer_dropped.items()},
    }


def reset_producer_counters() -> None:
    """Clear all producer counters. Tests only."""
    _producer_enqueued.clear()
    _producer_dropped.clear()


class _MemoryMetrics:
    """Singleton counter bag — avoids ``global`` boilerplate."""

    __slots__ = ("hits", "latency_ms", "misses")

    def __init__(self) -> None:
        self.hits: int = 0
        self.misses: int = 0
        self.latency_ms: deque[float] = deque(maxlen=_LATENCY_BUFFER_SIZE)

    def reset(self) -> None:
        self.hits = 0
        self.misses = 0
        self.latency_ms.clear()


_metrics = _MemoryMetrics()


def record_recall_hit() -> None:
    """Increment the recall hit counter."""
    _metrics.hits += 1


def record_recall_miss() -> None:
    """Increment the recall miss counter."""
    _metrics.misses += 1


def record_recall_latency_ms(value: float) -> None:
    """Append a recall latency sample (milliseconds) to the ring buffer."""
    _metrics.latency_ms.append(float(value))


def get_hit_rate() -> float:
    """Return ``hits / (hits + misses)``; ``0.0`` when no calls yet."""
    total = _metrics.hits + _metrics.misses
    if total == 0:
        return 0.0
    return _metrics.hits / total


def get_latency_p95_ms() -> float:
    """Return the p95 latency from the ring buffer (``0.0`` when empty)."""
    if not _metrics.latency_ms:
        return 0.0
    samples = sorted(_metrics.latency_ms)
    # Nearest-rank p95: index = ceil(0.95 * n) - 1
    idx = max(0, round(0.95 * len(samples)) - 1)
    return samples[idx]


def snapshot() -> dict[str, float | int]:
    """Return a point-in-time snapshot of all counters."""
    return {
        "memory_recall.hit": _metrics.hits,
        "memory_recall.miss": _metrics.misses,
        "memory_recall.hit_rate": get_hit_rate(),
        "memory_recall.latency_ms.p95": get_latency_p95_ms(),
        "memory_recall.latency_ms.samples": len(_metrics.latency_ms),
    }


def reset_metrics() -> None:
    """Clear all counters and the latency buffer. Tests only."""
    _metrics.reset()


__all__ = [
    "get_hit_rate",
    "get_latency_p95_ms",
    "get_producer_counters",
    "record_producer_dropped",
    "record_producer_enqueued",
    "record_recall_hit",
    "record_recall_latency_ms",
    "record_recall_miss",
    "reset_metrics",
    "reset_producer_counters",
    "snapshot",
]
