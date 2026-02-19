"""PMBlockInsightRepository — async CRUD with RLS and workspace-scoped queries.

Feature 017: Note Versioning / PM Block Engine — Phase 2a (T-227)
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import and_, select, update

from pilot_space.domain.pm_block_insight import InsightSeverity, PMBlockType
from pilot_space.infrastructure.database.models.pm_block_insight import PMBlockInsight
from pilot_space.infrastructure.database.repositories.base import BaseRepository

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sqlalchemy.ext.asyncio import AsyncSession


class PMBlockInsightRepository(BaseRepository[PMBlockInsight]):
    """Repository for PMBlockInsight CRUD and workspace-scoped queries."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session=session, model_class=PMBlockInsight)

    async def list_by_block(
        self,
        block_id: str,
        workspace_id: UUID,
        *,
        include_dismissed: bool = False,
    ) -> Sequence[PMBlockInsight]:
        """List non-deleted insights for a block, optionally including dismissed.

        Args:
            block_id: TipTap block ID.
            workspace_id: Workspace UUID for RLS enforcement.
            include_dismissed: Whether to include dismissed insights.

        Returns:
            Insights ordered by severity (red first), then created_at desc.
        """
        query = select(PMBlockInsight).where(
            PMBlockInsight.block_id == block_id,
            PMBlockInsight.workspace_id == workspace_id,
            PMBlockInsight.is_deleted == False,  # noqa: E712
        )
        if not include_dismissed:
            query = query.where(PMBlockInsight.dismissed == False)  # noqa: E712
        # Sort: red > yellow > green, then newest first
        query = query.order_by(
            PMBlockInsight.severity.asc(),  # enum ordering: green < red < yellow (lexicographic)
            PMBlockInsight.created_at.desc(),
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def list_by_workspace_and_block_type(
        self,
        workspace_id: UUID,
        block_type: PMBlockType,
        *,
        include_dismissed: bool = False,
    ) -> Sequence[PMBlockInsight]:
        """List insights filtered by workspace and PM block type.

        Args:
            workspace_id: Workspace UUID for RLS enforcement.
            block_type: PM block type to filter by.
            include_dismissed: Whether to include dismissed insights.

        Returns:
            Insights ordered by created_at desc.
        """
        query = select(PMBlockInsight).where(
            PMBlockInsight.workspace_id == workspace_id,
            PMBlockInsight.block_type == block_type,
            PMBlockInsight.is_deleted == False,  # noqa: E712
        )
        if not include_dismissed:
            query = query.where(PMBlockInsight.dismissed == False)  # noqa: E712
        query = query.order_by(PMBlockInsight.created_at.desc())
        result = await self.session.execute(query)
        return result.scalars().all()

    async def list_by_severity(
        self,
        workspace_id: UUID,
        severity: InsightSeverity,
        *,
        include_dismissed: bool = False,
    ) -> Sequence[PMBlockInsight]:
        """List insights filtered by severity within a workspace.

        Args:
            workspace_id: Workspace UUID for RLS enforcement.
            severity: Severity level to filter by.
            include_dismissed: Whether to include dismissed insights.

        Returns:
            Insights ordered by created_at desc.
        """
        query = select(PMBlockInsight).where(
            PMBlockInsight.workspace_id == workspace_id,
            PMBlockInsight.severity == severity,
            PMBlockInsight.is_deleted == False,  # noqa: E712
        )
        if not include_dismissed:
            query = query.where(PMBlockInsight.dismissed == False)  # noqa: E712
        query = query.order_by(PMBlockInsight.created_at.desc())
        result = await self.session.execute(query)
        return result.scalars().all()

    async def batch_dismiss(
        self,
        block_id: str,
        workspace_id: UUID,
    ) -> int:
        """Dismiss all active insights for a block.

        Args:
            block_id: TipTap block ID.
            workspace_id: Workspace UUID for RLS enforcement.

        Returns:
            Number of rows updated.
        """
        result = await self.session.execute(
            update(PMBlockInsight)
            .where(
                and_(
                    PMBlockInsight.block_id == block_id,
                    PMBlockInsight.workspace_id == workspace_id,
                    PMBlockInsight.dismissed == False,  # noqa: E712
                    PMBlockInsight.is_deleted == False,  # noqa: E712
                )
            )
            .values(dismissed=True)
            .execution_options(synchronize_session="fetch")
        )
        return result.rowcount  # type: ignore[return-value]
