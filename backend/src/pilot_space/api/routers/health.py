"""Health check endpoints for Kubernetes probes and monitoring tools.

Two-tier health check design (OPS-03):
- /health/live  — shallow liveness probe, never touches external deps
- /health/ready — deep readiness probe, checks DB, Redis, and Supabase
- /health        — legacy alias for /health/ready (backward compatibility)

Liveness: Kubernetes uses this to decide whether to restart a pod. It MUST
not check external dependencies — a slow DB should not cause a restart.

Readiness: Kubernetes uses this to route traffic. If DB or Redis are down,
the pod correctly reports itself as not ready (unhealthy). Non-critical
checks like Supabase only cause a 'degraded' status.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import structlog
from fastapi import APIRouter

from pilot_space.infrastructure.health_checks import check_database, check_redis, check_supabase

router = APIRouter(tags=["Health"])
logger = structlog.get_logger(__name__)

HEALTH_VERSION = "1.0.0"
CHECK_TIMEOUT_S = 2.0
TOTAL_TIMEOUT_S = 5.0
# Checks whose failure causes status="unhealthy" (traffic should stop)
CRITICAL_CHECKS: frozenset[str] = frozenset({"database", "redis"})


@router.get("/health/live")
async def liveness() -> dict[str, str]:
    """Shallow liveness probe — never touches external deps.

    Kubernetes uses this to decide whether to restart a pod.
    A pod that is slow (DB unreachable) should NOT be restarted.
    """
    return {"status": "ok"}


@router.get("/health/ready")
@router.get("/health")
async def readiness() -> dict[str, object]:
    """Deep readiness probe — checks all dependencies in parallel.

    /health is kept as a backward-compatible alias for /health/ready.

    Status logic:
    - unhealthy: any CRITICAL_CHECK (database, redis) has status=error
    - degraded:  a non-critical check (supabase) has status=error
    - healthy:   all checks pass

    Kubernetes uses this to decide whether to route traffic to the pod.
    """
    check_coros: dict[str, object] = {
        "database": check_database(),
        "redis": check_redis(),
        "supabase": check_supabase(),
    }
    results: dict[str, dict[str, object]] = {}

    try:
        async with asyncio.timeout(TOTAL_TIMEOUT_S):
            for name, coro in check_coros.items():
                try:
                    async with asyncio.timeout(CHECK_TIMEOUT_S):
                        results[name] = await coro  # type: ignore[misc]
                except TimeoutError:
                    results[name] = {"status": "error", "error": "timeout"}
    except TimeoutError:
        # Total timeout — fill in any missing checks
        for name in check_coros:
            if name not in results:
                results[name] = {"status": "error", "error": "total_timeout"}

    # Determine overall status
    if any(results.get(c, {}).get("status") == "error" for c in CRITICAL_CHECKS):
        overall = "unhealthy"
    elif any(v.get("status") == "error" for v in results.values()):
        overall = "degraded"
    else:
        overall = "healthy"

    logger.debug(
        "health_check_complete",
        overall=overall,
        checks={k: v.get("status") for k, v in results.items()},
    )

    return {
        "status": overall,
        "version": HEALTH_VERSION,
        "timestamp": datetime.now(UTC).isoformat(),
        "checks": results,
    }
