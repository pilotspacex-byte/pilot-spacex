"""ConstitutionRule repository for the AI memory engine.

Provides workspace-scoped data access with version tracking and active filtering.

Feature 015: AI Workforce Platform — Memory Engine
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import desc, func, select

from pilot_space.infrastructure.database.models.memory_entry import ConstitutionRule
from pilot_space.infrastructure.database.repositories.base import BaseRepository

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sqlalchemy.ext.asyncio import AsyncSession


class ConstitutionRuleRepository(BaseRepository[ConstitutionRule]):
    """Repository for ConstitutionRule records.

    All queries are workspace-scoped via RLS + explicit workspace_id filter.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session=session, model_class=ConstitutionRule)

    async def get_latest_version(self, workspace_id: UUID) -> int:
        """Get the highest version number for a workspace.

        Args:
            workspace_id: Workspace to check.

        Returns:
            Latest version number, or 0 if no rules exist.
        """
        query = select(func.max(ConstitutionRule.version)).where(
            ConstitutionRule.workspace_id == workspace_id,
            ConstitutionRule.is_deleted == False,  # noqa: E712
        )
        result = await self.session.execute(query)
        return result.scalar() or 0

    async def get_rules_at_version(
        self,
        workspace_id: UUID,
        version: int,
    ) -> Sequence[ConstitutionRule]:
        """Get all rules for a specific version snapshot.

        Args:
            workspace_id: Workspace to query.
            version: Exact version number to retrieve.

        Returns:
            Sequence of ConstitutionRule models at that version.
        """
        query = (
            select(ConstitutionRule)
            .where(
                ConstitutionRule.workspace_id == workspace_id,
                ConstitutionRule.version == version,
                ConstitutionRule.is_deleted == False,  # noqa: E712
            )
            .order_by(desc(ConstitutionRule.created_at))
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_active_rules(self, workspace_id: UUID) -> Sequence[ConstitutionRule]:
        """Get all currently active rules for a workspace.

        Args:
            workspace_id: Workspace to query.

        Returns:
            Sequence of active ConstitutionRule models.
        """
        query = (
            select(ConstitutionRule)
            .where(
                ConstitutionRule.workspace_id == workspace_id,
                ConstitutionRule.active == True,  # noqa: E712
                ConstitutionRule.is_deleted == False,  # noqa: E712
            )
            .order_by(
                desc(ConstitutionRule.version),
                desc(ConstitutionRule.created_at),
            )
        )
        result = await self.session.execute(query)
        return result.scalars().all()
