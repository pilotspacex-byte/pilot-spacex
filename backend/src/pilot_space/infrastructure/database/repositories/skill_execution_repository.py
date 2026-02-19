"""SkillExecution repository for AI workforce platform.

Provides typed data access for skill_executions with intent-scoped
queries and approval status filtering.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import desc, select, update

from pilot_space.infrastructure.database.models.skill_execution import (
    SkillApprovalStatus,
    SkillExecution,
)
from pilot_space.infrastructure.database.repositories.base import BaseRepository

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sqlalchemy.ext.asyncio import AsyncSession


class SkillExecutionRepository(BaseRepository[SkillExecution]):
    """Repository for SkillExecution audit records."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session=session, model_class=SkillExecution)

    async def list_by_intent(
        self,
        intent_id: UUID,
    ) -> Sequence[SkillExecution]:
        """List all executions for a given intent, ordered by created_at desc.

        Args:
            intent_id: Parent WorkIntent UUID.

        Returns:
            Sequence of SkillExecution models.
        """
        query = (
            select(SkillExecution)
            .where(
                SkillExecution.intent_id == intent_id,
                SkillExecution.is_deleted == False,  # noqa: E712
            )
            .order_by(desc(SkillExecution.created_at))
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def list_pending_approval(
        self,
        intent_id: UUID,
    ) -> Sequence[SkillExecution]:
        """List executions awaiting approval for a given intent.

        Args:
            intent_id: Parent WorkIntent UUID.

        Returns:
            Sequence of SkillExecution in pending_approval state.
        """
        query = (
            select(SkillExecution)
            .where(
                SkillExecution.intent_id == intent_id,
                SkillExecution.approval_status == SkillApprovalStatus.PENDING_APPROVAL,
                SkillExecution.is_deleted == False,  # noqa: E712
            )
            .order_by(SkillExecution.created_at.asc())
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def approve(self, execution_id: UUID) -> None:
        """Set approval_status to approved.

        Args:
            execution_id: SkillExecution UUID to approve.
        """
        await self.session.execute(
            update(SkillExecution)
            .where(SkillExecution.id == execution_id)
            .values(approval_status=SkillApprovalStatus.APPROVED)
        )
        await self.session.flush()

    async def reject(self, execution_id: UUID) -> None:
        """Set approval_status to rejected.

        Args:
            execution_id: SkillExecution UUID to reject.
        """
        await self.session.execute(
            update(SkillExecution)
            .where(SkillExecution.id == execution_id)
            .values(approval_status=SkillApprovalStatus.REJECTED)
        )
        await self.session.flush()
