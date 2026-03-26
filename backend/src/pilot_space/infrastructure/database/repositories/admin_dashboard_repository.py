"""AdminDashboardRepository — cross-workspace read-only queries for super-admin.

TENANT-04: Uses service_role DB connection to bypass RLS for cross-workspace
aggregation queries. All queries are read-only (SELECT only).

Uses SQLAlchemy Core expressions (select, func, join) instead of raw SQL text()
for type safety and column validation at build time. Does NOT use ORM-mapped
models for loading — only references their table/column metadata.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import and_, func, literal_column, select
from sqlalchemy.ext.asyncio import AsyncSession

from pilot_space.infrastructure.database.models.audit_log import AuditLog
from pilot_space.infrastructure.database.models.user import User
from pilot_space.infrastructure.database.models.workspace import Workspace
from pilot_space.infrastructure.database.models.workspace_member import WorkspaceMember


class AdminDashboardRepository:
    """Read-only repository for cross-workspace admin dashboard queries.

    Requires a service_role session (bypasses RLS) to run cross-workspace
    aggregation queries. The caller (AdminDashboardService) is responsible
    for providing the correctly privileged session.

    All queries use SQLAlchemy Core expressions referencing ORM model column
    metadata for type safety. No raw SQL text() strings.

    Args:
        session: A service_role AsyncSession that bypasses RLS policies.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_workspaces(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Fetch all workspaces with aggregated health metrics.

        Args:
            limit: Maximum rows to return.
            offset: Number of rows to skip.

        Returns:
            List of row mappings as plain dicts.
        """
        # Subquery: active member count per workspace
        member_sub = (
            select(
                WorkspaceMember.workspace_id,
                func.count()
                .filter(
                    and_(
                        WorkspaceMember.is_active.is_(True),
                        WorkspaceMember.is_deleted.is_(False),
                    )
                )
                .label("member_count"),
            )
            .group_by(WorkspaceMember.workspace_id)
            .subquery("m")
        )

        # Subquery: last activity + AI action count per workspace
        audit_sub = (
            select(
                AuditLog.workspace_id,
                func.max(AuditLog.created_at).label("last_active"),
                func.count()
                .filter(AuditLog.actor_type == literal_column("'AI'"))
                .label("ai_action_count"),
            )
            .group_by(AuditLog.workspace_id)
            .subquery("al_agg")
        )

        stmt = (
            select(
                Workspace.id,
                Workspace.name,
                Workspace.slug,
                Workspace.created_at,
                func.coalesce(member_sub.c.member_count, 0).label("member_count"),
                User.email.label("owner_email"),
                audit_sub.c.last_active,
                Workspace.storage_used_bytes,
                func.coalesce(audit_sub.c.ai_action_count, 0).label("ai_action_count"),
            )
            .outerjoin(member_sub, member_sub.c.workspace_id == Workspace.id)
            .outerjoin(User, User.id == Workspace.owner_id)
            .outerjoin(audit_sub, audit_sub.c.workspace_id == Workspace.id)
            .where(Workspace.is_deleted.is_(False))
            .order_by(Workspace.created_at.desc())
            .limit(limit)
            .offset(offset)
        )

        result = await self._session.execute(stmt)
        return [dict(row) for row in result.mappings()]

    async def get_workspace_by_slug(
        self,
        slug: str,
    ) -> dict[str, Any] | None:
        """Fetch a single workspace row by slug.

        Args:
            slug: Workspace URL slug.

        Returns:
            Row mapping as a plain dict, or None if not found.
        """
        # Subquery: active member count per workspace
        member_sub = (
            select(
                WorkspaceMember.workspace_id,
                func.count()
                .filter(
                    and_(
                        WorkspaceMember.is_active.is_(True),
                        WorkspaceMember.is_deleted.is_(False),
                    )
                )
                .label("member_count"),
            )
            .group_by(WorkspaceMember.workspace_id)
            .subquery("m")
        )

        # Subquery: last activity + AI action count per workspace
        audit_sub = (
            select(
                AuditLog.workspace_id,
                func.max(AuditLog.created_at).label("last_active"),
                func.count()
                .filter(AuditLog.actor_type == literal_column("'AI'"))
                .label("ai_action_count"),
            )
            .group_by(AuditLog.workspace_id)
            .subquery("al_agg")
        )

        stmt = (
            select(
                Workspace.id,
                Workspace.name,
                Workspace.slug,
                Workspace.created_at,
                func.coalesce(member_sub.c.member_count, 0).label("member_count"),
                User.email.label("owner_email"),
                audit_sub.c.last_active,
                Workspace.storage_used_bytes,
                func.coalesce(audit_sub.c.ai_action_count, 0).label("ai_action_count"),
                Workspace.rate_limit_standard_rpm,
                Workspace.rate_limit_ai_rpm,
                Workspace.storage_quota_mb,
            )
            .outerjoin(member_sub, member_sub.c.workspace_id == Workspace.id)
            .outerjoin(User, User.id == Workspace.owner_id)
            .outerjoin(audit_sub, audit_sub.c.workspace_id == Workspace.id)
            .where(
                and_(
                    Workspace.slug == slug,
                    Workspace.is_deleted.is_(False),
                )
            )
        )

        result = await self._session.execute(stmt)
        row = result.mappings().one_or_none()
        return dict(row) if row is not None else None

    async def get_top_members(
        self,
        workspace_id: UUID,
    ) -> list[dict[str, Any]]:
        """Fetch the top 5 most active members for a workspace.

        Args:
            workspace_id: Workspace UUID.

        Returns:
            List of member row mappings as plain dicts.
        """
        stmt = (
            select(
                WorkspaceMember.user_id,
                User.email,
                User.full_name,
                WorkspaceMember.role,
                func.count(AuditLog.id).label("action_count"),
            )
            .join(User, User.id == WorkspaceMember.user_id)
            .outerjoin(
                AuditLog,
                and_(
                    AuditLog.workspace_id == WorkspaceMember.workspace_id,
                    AuditLog.actor_id == WorkspaceMember.user_id,
                ),
            )
            .where(
                and_(
                    WorkspaceMember.workspace_id == workspace_id,
                    WorkspaceMember.is_active.is_(True),
                    WorkspaceMember.is_deleted.is_(False),
                )
            )
            .group_by(
                WorkspaceMember.user_id,
                User.email,
                User.full_name,
                WorkspaceMember.role,
            )
            .order_by(func.count(AuditLog.id).desc())
            .limit(5)
        )

        result = await self._session.execute(stmt)
        return [dict(row) for row in result.mappings()]

    async def get_recent_ai_actions(
        self,
        workspace_id: UUID,
    ) -> list[dict[str, Any]]:
        """Fetch the last 10 AI audit log entries for a workspace.

        Args:
            workspace_id: Workspace UUID.

        Returns:
            List of audit log row mappings as plain dicts.
        """
        stmt = (
            select(
                AuditLog.id,
                AuditLog.action,
                AuditLog.resource_type,
                AuditLog.resource_id,
                AuditLog.actor_id,
                AuditLog.ai_model,
                AuditLog.ai_token_cost,
                AuditLog.created_at,
            )
            .where(
                and_(
                    AuditLog.workspace_id == workspace_id,
                    AuditLog.actor_type == literal_column("'AI'"),
                )
            )
            .order_by(AuditLog.created_at.desc())
            .limit(10)
        )

        result = await self._session.execute(stmt)
        return [dict(row) for row in result.mappings()]


__all__ = ["AdminDashboardRepository"]
