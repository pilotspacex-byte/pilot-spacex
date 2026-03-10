"""Async health check functions for dependency probing.

Used by GET /health/ready to verify connectivity to external dependencies.
Each function returns a status dict with 'status' ('ok' or 'error') and
optional 'latency_ms' or 'error' fields.
"""

from __future__ import annotations

import time


async def check_database() -> dict[str, object]:
    """Check database connectivity by executing SELECT 1.

    Returns:
        dict with 'status' ('ok' or 'error'), 'latency_ms' on success,
        or 'error' message on failure.
    """
    from sqlalchemy import text

    from pilot_space.infrastructure.database import get_engine

    start = time.monotonic()
    try:
        engine = get_engine()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "ok", "latency_ms": round((time.monotonic() - start) * 1000, 1)}
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


async def check_redis() -> dict[str, object]:
    """Check Redis connectivity via PING.

    Returns:
        dict with 'status' ('ok' or 'error'), 'latency_ms' on success,
        or 'error' message on failure.
    """
    from pilot_space.config import get_settings
    from pilot_space.infrastructure.cache import RedisClient

    start = time.monotonic()
    try:
        settings = get_settings()
        client = RedisClient(redis_url=settings.redis_url)
        await client.connect()
        try:
            reachable = await client.ping()
            if not reachable:
                return {"status": "error", "error": "ping returned False"}
        finally:
            await client.disconnect()
        return {"status": "ok", "latency_ms": round((time.monotonic() - start) * 1000, 1)}
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


async def check_supabase() -> dict[str, object]:
    """Check Supabase health endpoint (non-critical).

    A failure here yields 'degraded' status, not 'unhealthy'.

    Returns:
        dict with 'status' ('ok' or 'error'), 'latency_ms' on success,
        or 'error' message on failure.
    """
    import httpx

    from pilot_space.config import get_settings

    start = time.monotonic()
    try:
        settings = get_settings()
        async with httpx.AsyncClient(timeout=2.0) as client:
            r = await client.get(f"{settings.supabase_url}/health")
            r.raise_for_status()
        return {"status": "ok", "latency_ms": round((time.monotonic() - start) * 1000, 1)}
    except Exception as exc:
        return {"status": "error", "error": str(exc)}
