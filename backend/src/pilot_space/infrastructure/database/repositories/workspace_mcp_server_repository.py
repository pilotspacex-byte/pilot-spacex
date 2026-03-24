"""WorkspaceMcpServerRepository for database operations.

Provides workspace-scoped data access methods for MCP server registrations
with soft-delete lifecycle support.

Extended in Phase 25 to support filtering, partial updates, and enable/disable.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import and_, or_, select
from sqlalchemy.sql.elements import ColumnElement

from pilot_space.infrastructure.database.models.workspace_mcp_server import (
    McpServerType,
    McpStatus,
    WorkspaceMcpServer,
)
from pilot_space.infrastructure.database.repositories.base import BaseRepository

if TYPE_CHECKING:
    from collections.abc import Sequence
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession


class WorkspaceMcpServerRepository(BaseRepository[WorkspaceMcpServer]):
    """Repository for WorkspaceMcpServer entities.

    Extends BaseRepository with workspace-scoped queries for MCP server
    CRUD lifecycle operations including filtering, partial updates,
    and enable/disable toggling.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with session.

        Args:
            session: Async database session.
        """
        super().__init__(session, WorkspaceMcpServer)

    async def get_active_by_workspace(
        self,
        workspace_id: UUID,
        enabled_only: bool = False,
    ) -> Sequence[WorkspaceMcpServer]:
        """Get all non-deleted MCP servers for a workspace.

        Returns servers ordered by creation time descending (newest first).

        Args:
            workspace_id: The workspace UUID.
            enabled_only: If True, only return servers where is_enabled=True.

        Returns:
            List of active (non-deleted) MCP servers for the workspace.
        """
        conditions = [
            WorkspaceMcpServer.workspace_id == workspace_id,
            WorkspaceMcpServer.is_deleted == False,  # noqa: E712
        ]
        if enabled_only:
            conditions.append(WorkspaceMcpServer.is_enabled == True)  # noqa: E712

        query = (
            select(WorkspaceMcpServer)
            .where(and_(*conditions))
            .order_by(WorkspaceMcpServer.created_at.desc())
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_filtered(
        self,
        workspace_id: UUID,
        server_type: McpServerType | None = None,
        status: McpStatus | None = None,
        search: str | None = None,
    ) -> Sequence[WorkspaceMcpServer]:
        """Get filtered MCP servers for a workspace.

        Supports optional filtering by server type, status, and name/URL search.
        Returns non-deleted servers ordered by creation time descending.

        Args:
            workspace_id: The workspace UUID.
            server_type: Optional server type filter (remote, npx, uvx).
            status: Optional status filter (enabled, disabled, etc.).
            search: Optional substring to match against display_name or url_or_command.

        Returns:
            Filtered list of MCP servers.
        """
        conditions: list[ColumnElement[bool]] = [
            WorkspaceMcpServer.workspace_id == workspace_id,
            WorkspaceMcpServer.is_deleted == False,  # noqa: E712
        ]

        if server_type is not None:
            conditions.append(WorkspaceMcpServer.server_type == server_type)

        if status is not None:
            conditions.append(WorkspaceMcpServer.last_status == status)

        if search is not None and search.strip():
            pattern = f"%{search.strip()}%"
            conditions.append(
                or_(
                    WorkspaceMcpServer.display_name.ilike(pattern),
                    WorkspaceMcpServer.url_or_command.ilike(pattern),
                )
            )

        query = (
            select(WorkspaceMcpServer)
            .where(and_(*conditions))
            .order_by(WorkspaceMcpServer.created_at.desc())
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_by_workspace_and_id(
        self,
        server_id: UUID,
        workspace_id: UUID,
    ) -> WorkspaceMcpServer | None:
        """Get a specific MCP server by ID scoped to a workspace.

        Args:
            server_id: The server UUID.
            workspace_id: The workspace UUID (scoping guard).

        Returns:
            The MCP server if found and not deleted, None otherwise.
        """
        query = select(WorkspaceMcpServer).where(
            and_(
                WorkspaceMcpServer.id == server_id,
                WorkspaceMcpServer.workspace_id == workspace_id,
                WorkspaceMcpServer.is_deleted == False,  # noqa: E712
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_display_name(
        self,
        workspace_id: UUID,
        display_name: str,
    ) -> WorkspaceMcpServer | None:
        """Get an active MCP server by workspace and display_name.

        Used to detect name collisions before insert/rename so the API can
        return a 409 rather than letting the DB unique index raise an
        IntegrityError.

        Args:
            workspace_id: The workspace UUID.
            display_name: Exact display_name to look up (case-sensitive).

        Returns:
            The active server with that name, or None if no match.
        """
        query = select(WorkspaceMcpServer).where(
            and_(
                WorkspaceMcpServer.workspace_id == workspace_id,
                WorkspaceMcpServer.display_name == display_name,
                WorkspaceMcpServer.is_deleted == False,  # noqa: E712
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def create(self, entity: WorkspaceMcpServer) -> WorkspaceMcpServer:  # type: ignore[override]
        """Persist a new MCP server row.

        Args:
            entity: The WorkspaceMcpServer instance to create.

        Returns:
            The created server with generated ID and timestamps.
        """
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def update(self, entity: WorkspaceMcpServer) -> WorkspaceMcpServer:  # type: ignore[override]
        """Flush pending changes to an existing MCP server row.

        Caller is responsible for mutating the model fields before calling update.

        Args:
            entity: The mutated WorkspaceMcpServer instance.

        Returns:
            The updated server (refreshed from DB).
        """
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def update_fields(
        self, entity: WorkspaceMcpServer, **kwargs: object
    ) -> WorkspaceMcpServer:
        """Apply partial field updates to an MCP server and flush.

        Only updates fields explicitly provided as keyword arguments.
        Does not update fields set to the sentinel value ``None`` unless
        None is explicitly passed as the value.

        Args:
            entity: The WorkspaceMcpServer instance to update.
            **kwargs: Field-name → new-value pairs to apply.

        Returns:
            The updated server (refreshed from DB).
        """
        for field, value in kwargs.items():
            setattr(entity, field, value)
        return await self.update(entity)

    async def set_enabled(self, entity: WorkspaceMcpServer, enabled: bool) -> WorkspaceMcpServer:
        """Set the is_enabled flag on an MCP server.

        When disabling, sets last_status to DISABLED.
        When enabling, clears last_status so the poller re-evaluates.

        Args:
            entity: The WorkspaceMcpServer instance to update.
            enabled: True to enable, False to disable.

        Returns:
            The updated server (refreshed from DB).
        """
        entity.is_enabled = enabled
        if not enabled:
            entity.last_status = McpStatus.DISABLED
        else:
            entity.last_status = None
        return await self.update(entity)

    async def soft_delete(self, entity: WorkspaceMcpServer) -> None:
        """Soft-delete an MCP server by setting is_deleted=True.

        The row is preserved in the database for audit purposes but excluded
        from all active queries.

        Args:
            entity: The WorkspaceMcpServer instance to soft-delete.
        """
        entity.soft_delete()
        await self.session.flush()


__all__ = ["WorkspaceMcpServerRepository"]
