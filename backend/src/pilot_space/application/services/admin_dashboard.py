"""Admin dashboard service — TENANT-04.

Provides read-only cross-workspace metrics for super-admin operator dashboard.
Uses service_role DB connection (bypasses RLS) for cross-workspace queries.
All SQL is encapsulated in AdminDashboardRepository.
"""

from __future__ import annotations

import contextlib
import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from pilot_space.config import get_settings
from pilot_space.infrastructure.database.repositories.admin_dashboard_repository import (
    AdminDashboardRepository,
)
from pilot_space.schemas.admin_dashboard import (
    QuotaConfig,
    RecentAIAction,
    TopMember,
    WorkspaceDetail,
    WorkspaceOverview,
)

logger = logging.getLogger(__name__)


class _AdminSessionFactory:
    """Lazy-init container for the service_role async_sessionmaker.

    Using a class instance avoids the `global` statement (PLW0603).
    Service_role bypasses all RLS policies -- suitable for cross-workspace queries.
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


class AdminDashboardService:
    """Read-only cross-workspace metrics for the super-admin dashboard.

    Args:
        redis: Optional Redis client for rate-limit violation lookups.
    """

    def __init__(self, redis: Any | None = None) -> None:
        self._redis = redis

    async def _get_rl_violation_count(self, workspace_id: str) -> int:
        """Sum rate-limit violation counts for a workspace from Redis.

        Keys pattern: rl_violations:{workspace_id}:{date}
        Uses SCAN to avoid blocking the server with KEYS command.
        Returns 0 if Redis is unavailable or no keys are found.
        """
        if self._redis is None:
            return 0
        try:
            pattern = f"rl_violations:{workspace_id}:*"
            total = 0
            cursor = 0
            while True:
                cursor, keys = await self._redis.scan(cursor, match=pattern, count=100)
                if keys:
                    values = await self._redis.mget(*keys)
                    for v in values:
                        if v is not None:
                            with contextlib.suppress(ValueError, TypeError):
                                total += int(v)
                if cursor == 0:
                    break
            return total
        except Exception:
            return 0

    async def list_workspaces(
        self, *, limit: int = 100, offset: int = 0
    ) -> list[WorkspaceOverview]:
        """List all workspaces with aggregated health metrics.

        Returns workspace list with member counts, owner email, storage usage,
        AI action counts, and rate-limit violation counts (from Redis).
        """
        session_factory = _get_admin_session_factory()

        async with session_factory() as session:
            repo = AdminDashboardRepository(session)
            rows = await repo.list_workspaces(limit=limit, offset=offset)

        workspaces: list[WorkspaceOverview] = []
        for row in rows:
            ws_id = str(row["id"])
            rl_count = await self._get_rl_violation_count(ws_id)

            workspaces.append(
                WorkspaceOverview(
                    id=row["id"],
                    name=row["name"],
                    slug=row["slug"],
                    created_at=row["created_at"],
                    member_count=int(row["member_count"]),
                    owner_email=row["owner_email"],
                    last_active=row["last_active"],
                    storage_used_bytes=int(row["storage_used_bytes"] or 0),
                    ai_action_count=int(row["ai_action_count"]),
                    rate_limit_violation_count=rl_count,
                )
            )

        return workspaces

    async def get_workspace_detail(self, workspace_slug: str) -> WorkspaceDetail:
        """Get workspace detail with member activity and AI action history.

        Returns:
            Workspace summary + top 5 active members + last 10 AI actions
            + quota config + rate-limit violation count.

        Raises:
            NotFoundError: If workspace not found.
        """
        from pilot_space.domain.exceptions import NotFoundError

        session_factory = _get_admin_session_factory()

        async with session_factory() as session:
            repo = AdminDashboardRepository(session)

            ws_row = await repo.get_workspace_by_slug(workspace_slug)
            if ws_row is None:
                raise NotFoundError(f"Workspace '{workspace_slug}' not found")

            workspace_id = ws_row["id"]

            members_rows = await repo.get_top_members(workspace_id)
            ai_rows = await repo.get_recent_ai_actions(workspace_id)

        ws_id = str(ws_row["id"])
        rl_count = await self._get_rl_violation_count(ws_id)

        top_members = [
            TopMember(
                user_id=m["user_id"],
                email=m["email"],
                full_name=m["full_name"],
                role=m["role"],
                action_count=int(m["action_count"]),
            )
            for m in members_rows
        ]

        recent_ai_actions = [
            RecentAIAction(
                id=a["id"],
                action=a["action"],
                resource_type=a["resource_type"],
                resource_id=a["resource_id"],
                actor_id=a["actor_id"],
                ai_model=a["ai_model"],
                ai_token_cost=a["ai_token_cost"],
                created_at=a["created_at"],
            )
            for a in ai_rows
        ]

        return WorkspaceDetail(
            id=ws_row["id"],
            name=ws_row["name"],
            slug=ws_row["slug"],
            created_at=ws_row["created_at"],
            member_count=int(ws_row["member_count"]),
            owner_email=ws_row["owner_email"],
            last_active=ws_row["last_active"],
            storage_used_bytes=int(ws_row["storage_used_bytes"] or 0),
            ai_action_count=int(ws_row["ai_action_count"]),
            rate_limit_violation_count=rl_count,
            quota=QuotaConfig(
                rate_limit_standard_rpm=ws_row["rate_limit_standard_rpm"],
                rate_limit_ai_rpm=ws_row["rate_limit_ai_rpm"],
                storage_quota_mb=ws_row["storage_quota_mb"],
            ),
            top_members=top_members,
            recent_ai_actions=recent_ai_actions,
        )
