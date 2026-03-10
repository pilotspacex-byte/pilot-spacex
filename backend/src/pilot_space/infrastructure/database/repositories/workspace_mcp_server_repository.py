"""WorkspaceMcpServerRepository for database operations.

Provides workspace-scoped data access methods for MCP server registrations
with soft-delete lifecycle support.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import and_, select

from pilot_space.infrastructure.database.models.workspace_mcp_server import (
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
    CRUD lifecycle operations.
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
    ) -> Sequence[WorkspaceMcpServer]:
        """Get all non-deleted MCP servers for a workspace.

        Returns servers ordered by creation time descending (newest first).

        Args:
            workspace_id: The workspace UUID.

        Returns:
            List of active (non-deleted) MCP servers for the workspace.
        """
        query = (
            select(WorkspaceMcpServer)
            .where(
                and_(
                    WorkspaceMcpServer.workspace_id == workspace_id,
                    WorkspaceMcpServer.is_deleted == False,  # noqa: E712
                )
            )
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
