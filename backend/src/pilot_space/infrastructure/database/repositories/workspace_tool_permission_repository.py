"""Repository for per-workspace AI tool permission rows.

Phase 69 — granular tool permissions. Every read/write for the
``workspace_tool_permissions`` and ``tool_permission_audit_log`` tables
flows through this repository. The service layer owns the DD-003
invariant guard and cache invalidation; the repository is a thin
data-access shell.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import desc, select

from pilot_space.infrastructure.database.models.tool_permission_audit_log import (
    ToolPermissionAuditLog,
)
from pilot_space.infrastructure.database.models.workspace_tool_permission import (
    WorkspaceToolPermission,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class WorkspaceToolPermissionRepository:
    """CRUD + audit-log access for ``workspace_tool_permissions``.

    Absence of a row for a ``(workspace_id, tool_name)`` pair means
    "fall back to default policy" — the service layer resolves the
    fallback chain, not this repository.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository.

        Args:
            session: Async database session.
        """
        self._session = session

    async def get(
        self,
        workspace_id: uuid.UUID,
        tool_name: str,
    ) -> WorkspaceToolPermission | None:
        """Return the row for ``(workspace_id, tool_name)`` or None."""
        result = await self._session.execute(
            select(WorkspaceToolPermission).where(
                WorkspaceToolPermission.workspace_id == workspace_id,
                WorkspaceToolPermission.tool_name == tool_name,
            )
        )
        return result.scalar_one_or_none()

    async def list_for_workspace(
        self,
        workspace_id: uuid.UUID,
    ) -> list[WorkspaceToolPermission]:
        """Return all rows for a workspace, ordered by tool_name."""
        result = await self._session.execute(
            select(WorkspaceToolPermission)
            .where(WorkspaceToolPermission.workspace_id == workspace_id)
            .order_by(WorkspaceToolPermission.tool_name)
        )
        return list(result.scalars().all())

    async def upsert(
        self,
        workspace_id: uuid.UUID,
        tool_name: str,
        mode: str,
        actor_user_id: uuid.UUID,
    ) -> tuple[WorkspaceToolPermission, str | None]:
        """Insert or update a permission row.

        Args:
            workspace_id: Owning workspace.
            tool_name: Fully qualified MCP tool name.
            mode: One of ``auto`` | ``ask`` | ``deny``.
            actor_user_id: User who initiated the change.

        Returns:
            Tuple of (persisted row, previous mode or None). The previous
            mode is used by the service layer to write the audit log.
        """
        existing = await self.get(workspace_id, tool_name)
        if existing is None:
            row = WorkspaceToolPermission(
                workspace_id=workspace_id,
                tool_name=tool_name,
                mode=mode,
                updated_by=actor_user_id,
            )
            self._session.add(row)
            await self._session.flush()
            return row, None

        previous = existing.mode
        existing.mode = mode
        existing.updated_by = actor_user_id
        await self._session.flush()
        return existing, previous

    async def insert_audit_log(
        self,
        workspace_id: uuid.UUID,
        tool_name: str,
        old_mode: str | None,
        new_mode: str,
        actor_user_id: uuid.UUID,
        reason: str | None = None,
    ) -> ToolPermissionAuditLog:
        """Append an immutable audit-log row for a mode change."""
        row = ToolPermissionAuditLog(
            workspace_id=workspace_id,
            tool_name=tool_name,
            old_mode=old_mode,
            new_mode=new_mode,
            actor_user_id=actor_user_id,
            reason=reason,
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def list_audit_log(
        self,
        workspace_id: uuid.UUID,
        limit: int,
        offset: int,
    ) -> list[ToolPermissionAuditLog]:
        """Return audit-log rows for a workspace, most-recent first.

        Args:
            workspace_id: Owning workspace.
            limit: Max rows to return.
            offset: Rows to skip.
        """
        result = await self._session.execute(
            select(ToolPermissionAuditLog)
            .where(ToolPermissionAuditLog.workspace_id == workspace_id)
            .order_by(desc(ToolPermissionAuditLog.created_at))
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())


__all__ = ["WorkspaceToolPermissionRepository"]
