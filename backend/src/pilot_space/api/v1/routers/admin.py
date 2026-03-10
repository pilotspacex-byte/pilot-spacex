"""Super-admin operator dashboard routes — TENANT-04.

These routes bypass workspace JWT auth entirely. Access is controlled by
PILOT_SPACE_SUPER_ADMIN_TOKEN bearer token (see dependencies/admin.py).

Uses service_role DB connection — RLS is bypassed for cross-workspace queries.
All responses are read-only; no workspace data is mutated via admin routes.

Endpoints:
    GET /workspaces             — list all workspaces with health metrics
    GET /workspaces/{slug}      — workspace detail with member activity and AI actions
"""

from __future__ import annotations

import contextlib
import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from pilot_space.config import get_settings
from pilot_space.dependencies.admin import get_super_admin

logger = logging.getLogger(__name__)

router = APIRouter(tags=["super-admin"])

# ---------------------------------------------------------------------------
# Lazy-init service_role session factory (same pattern as SCIM router)
# ---------------------------------------------------------------------------


class _AdminSessionFactory:
    """Lazy-init container for the service_role async_sessionmaker.

    Using a class instance avoids the `global` statement (PLW0603).
    Service_role bypasses all RLS policies — suitable for cross-workspace queries.
    """

    def __init__(self) -> None:
        self._factory: async_sessionmaker[AsyncSession] | None = None

    def __call__(self) -> async_sessionmaker[AsyncSession]:
        if self._factory is None:
            settings = get_settings()
            db_url = settings.database_url.get_secret_value()
            engine = create_async_engine(db_url, pool_pre_ping=True)
            self._factory = async_sessionmaker(engine, expire_on_commit=False)
        return self._factory


_get_admin_session_factory = _AdminSessionFactory()


def _get_redis_client() -> Any | None:
    """Return Redis client from app container, or None if unavailable."""
    try:
        from pilot_space.container import get_container

        container = get_container()
        return container.redis_client()
    except Exception:
        return None


async def _get_rl_violation_count(redis_client: Any, workspace_id: str) -> int:
    """Sum rate-limit violation counts for a workspace from Redis.

    Keys pattern: rl_violations:{workspace_id}:{date}
    Uses SCAN to avoid blocking the server with KEYS command.

    Returns 0 if Redis is unavailable or no keys are found.
    """
    if redis_client is None:
        return 0
    try:
        pattern = f"rl_violations:{workspace_id}:*"
        total = 0
        # Use SCAN for production safety (non-blocking iteration)
        cursor = 0
        while True:
            cursor, keys = await redis_client.scan(cursor, match=pattern, count=100)
            if keys:
                values = await redis_client.mget(*keys)
                for v in values:
                    if v is not None:
                        with contextlib.suppress(ValueError, TypeError):
                            total += int(v)
            if cursor == 0:
                break
        return total
    except Exception:
        return 0


# ---------------------------------------------------------------------------
# GET /workspaces — list all workspaces with health metrics
# ---------------------------------------------------------------------------

_LIST_WORKSPACES_SQL = text("""
SELECT
    w.id,
    w.name,
    w.slug,
    w.created_at,
    COALESCE(m.member_count, 0) AS member_count,
    ou.email AS owner_email,
    al_agg.last_active,
    w.storage_used_bytes,
    COALESCE(al_agg.ai_action_count, 0) AS ai_action_count
FROM workspaces w
LEFT JOIN (
    SELECT workspace_id, COUNT(*) FILTER (WHERE is_active = true AND is_deleted = false) AS member_count
    FROM workspace_members
    GROUP BY workspace_id
) m ON m.workspace_id = w.id
LEFT JOIN users ou ON ou.id = w.owner_id
LEFT JOIN (
    SELECT
        workspace_id,
        MAX(created_at) AS last_active,
        COUNT(*) FILTER (WHERE actor_type = 'AI') AS ai_action_count
    FROM audit_log
    GROUP BY workspace_id
) al_agg ON al_agg.workspace_id = w.id
WHERE w.is_deleted = false
ORDER BY w.created_at DESC
LIMIT :limit OFFSET :offset
""")


@router.get("/workspaces")
async def list_workspaces(
    _: Annotated[None, Depends(get_super_admin)],
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[dict[str, Any]]:
    """List all workspaces with aggregated health metrics.

    Returns workspace list with member counts, owner email, storage usage,
    AI action counts, and rate-limit violation counts (from Redis).

    Requires: PILOT_SPACE_SUPER_ADMIN_TOKEN bearer token.
    """
    logger.info("super_admin_access", extra={"action": "list_workspaces", "token": "****"})

    session_factory = _get_admin_session_factory()
    redis_client = _get_redis_client()

    async with session_factory() as session:
        result = await session.execute(_LIST_WORKSPACES_SQL, {"limit": limit, "offset": offset})
        rows = result.mappings().all()

    workspaces = []
    for row in rows:
        ws_id = str(row["id"])
        rl_count = await _get_rl_violation_count(redis_client, ws_id)

        created_at = row["created_at"]
        last_active = row["last_active"]

        workspaces.append(
            {
                "id": ws_id,
                "name": row["name"],
                "slug": row["slug"],
                "created_at": created_at.isoformat() if created_at else None,
                "member_count": int(row["member_count"]),
                "owner_email": row["owner_email"],
                "last_active": last_active.isoformat() if last_active else None,
                "storage_used_bytes": int(row["storage_used_bytes"] or 0),
                "ai_action_count": int(row["ai_action_count"]),
                "rate_limit_violation_count": rl_count,
            }
        )

    return workspaces


# ---------------------------------------------------------------------------
# GET /workspaces/{workspace_slug} — workspace detail with expanded data
# ---------------------------------------------------------------------------

_WORKSPACE_DETAIL_SQL = text("""
SELECT
    w.id,
    w.name,
    w.slug,
    w.created_at,
    COALESCE(m.member_count, 0) AS member_count,
    ou.email AS owner_email,
    al_agg.last_active,
    w.storage_used_bytes,
    COALESCE(al_agg.ai_action_count, 0) AS ai_action_count,
    w.rate_limit_standard_rpm,
    w.rate_limit_ai_rpm,
    w.storage_quota_mb
FROM workspaces w
LEFT JOIN (
    SELECT workspace_id, COUNT(*) FILTER (WHERE is_active = true AND is_deleted = false) AS member_count
    FROM workspace_members
    GROUP BY workspace_id
) m ON m.workspace_id = w.id
LEFT JOIN users ou ON ou.id = w.owner_id
LEFT JOIN (
    SELECT
        workspace_id,
        MAX(created_at) AS last_active,
        COUNT(*) FILTER (WHERE actor_type = 'AI') AS ai_action_count
    FROM audit_log
    GROUP BY workspace_id
) al_agg ON al_agg.workspace_id = w.id
WHERE w.slug = :slug AND w.is_deleted = false
""")

_TOP_MEMBERS_SQL = text("""
SELECT
    wm.user_id,
    u.email,
    u.full_name,
    wm.role,
    COUNT(al.id) AS action_count
FROM workspace_members wm
JOIN users u ON u.id = wm.user_id
LEFT JOIN audit_log al ON al.workspace_id = wm.workspace_id AND al.actor_id = wm.user_id
WHERE wm.workspace_id = :workspace_id
  AND wm.is_active = true
  AND wm.is_deleted = false
GROUP BY wm.user_id, u.email, u.full_name, wm.role
ORDER BY action_count DESC
LIMIT 5
""")

_RECENT_AI_ACTIONS_SQL = text("""
SELECT
    id,
    action,
    resource_type,
    resource_id,
    actor_id,
    ai_model,
    ai_token_cost,
    created_at
FROM audit_log
WHERE workspace_id = :workspace_id AND actor_type = 'AI'
ORDER BY created_at DESC
LIMIT 10
""")


@router.get("/workspaces/{workspace_slug}")
async def get_workspace_detail(
    workspace_slug: str,
    _: Annotated[None, Depends(get_super_admin)],
) -> dict[str, Any]:
    """Get workspace detail with member activity and AI action history.

    Returns:
        Workspace summary + top 5 active members + last 10 AI actions
        + quota config + rate-limit violation count.

    Requires: PILOT_SPACE_SUPER_ADMIN_TOKEN bearer token.
    """
    logger.info("super_admin_access", extra={"action": "workspace_detail"})

    session_factory = _get_admin_session_factory()
    redis_client = _get_redis_client()

    async with session_factory() as session:
        # 1. Workspace summary row
        ws_result = await session.execute(_WORKSPACE_DETAIL_SQL, {"slug": workspace_slug})
        ws_row = ws_result.mappings().one_or_none()

        if ws_row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workspace '{workspace_slug}' not found",
            )

        workspace_id = ws_row["id"]

        # 2. Top 5 active members by audit log action count
        members_result = await session.execute(_TOP_MEMBERS_SQL, {"workspace_id": workspace_id})
        members_rows = members_result.mappings().all()

        # 3. Last 10 AI actions
        ai_result = await session.execute(_RECENT_AI_ACTIONS_SQL, {"workspace_id": workspace_id})
        ai_rows = ai_result.mappings().all()

    ws_id = str(ws_row["id"])
    rl_count = await _get_rl_violation_count(redis_client, ws_id)

    created_at = ws_row["created_at"]
    last_active = ws_row["last_active"]

    top_members = [
        {
            "user_id": str(m["user_id"]),
            "email": m["email"],
            "full_name": m["full_name"],
            "role": m["role"],
            "action_count": int(m["action_count"]),
        }
        for m in members_rows
    ]

    recent_ai_actions = [
        {
            "id": str(a["id"]),
            "action": a["action"],
            "resource_type": a["resource_type"],
            "resource_id": str(a["resource_id"]) if a["resource_id"] else None,
            "actor_id": str(a["actor_id"]) if a["actor_id"] else None,
            "ai_model": a["ai_model"],
            "ai_token_cost": a["ai_token_cost"],
            "created_at": a["created_at"].isoformat() if a["created_at"] else None,
        }
        for a in ai_rows
    ]

    return {
        "id": ws_id,
        "name": ws_row["name"],
        "slug": ws_row["slug"],
        "created_at": created_at.isoformat() if created_at else None,
        "member_count": int(ws_row["member_count"]),
        "owner_email": ws_row["owner_email"],
        "last_active": last_active.isoformat() if last_active else None,
        "storage_used_bytes": int(ws_row["storage_used_bytes"] or 0),
        "ai_action_count": int(ws_row["ai_action_count"]),
        "rate_limit_violation_count": rl_count,
        "quota": {
            "rate_limit_standard_rpm": ws_row["rate_limit_standard_rpm"],
            "rate_limit_ai_rpm": ws_row["rate_limit_ai_rpm"],
            "storage_quota_mb": ws_row["storage_quota_mb"],
        },
        "top_members": top_members,
        "recent_ai_actions": recent_ai_actions,
    }
