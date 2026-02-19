"""Repository for PM Block read queries (sprint board, capacity, release notes, dependency map).

Centralises all direct DB access for the PM block API layer (C-4/C-5 fix).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.orm import selectinload

if TYPE_CHECKING:
    from collections.abc import Sequence
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from pilot_space.infrastructure.database.models import Cycle, Issue, IssueLink
    from pilot_space.infrastructure.database.models.workspace_member import WorkspaceMember


class PMBlockQueriesRepository:
    """Read-only repository for PM block aggregate queries."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_cycle(self, cycle_id: UUID, workspace_id: UUID) -> Cycle | None:
        from pilot_space.infrastructure.database.models import Cycle

        result = await self._session.execute(
            select(Cycle).where(
                Cycle.id == cycle_id,
                Cycle.workspace_id == workspace_id,
                Cycle.is_deleted == False,  # noqa: E712
            )
        )
        return result.scalar_one_or_none()

    async def get_cycle_issues_with_state_and_assignee(
        self, cycle_id: UUID, workspace_id: UUID
    ) -> Sequence[Issue]:
        from pilot_space.infrastructure.database.models import Issue

        result = await self._session.execute(
            select(Issue)
            .options(selectinload(Issue.state), selectinload(Issue.assignee))
            .where(
                Issue.cycle_id == cycle_id,
                Issue.workspace_id == workspace_id,
                Issue.is_deleted == False,  # noqa: E712
            )
        )
        return result.scalars().all()

    async def get_cycle_issues_with_state(
        self, cycle_id: UUID, workspace_id: UUID
    ) -> Sequence[Issue]:
        from pilot_space.infrastructure.database.models import Issue

        result = await self._session.execute(
            select(Issue)
            .options(selectinload(Issue.state))
            .where(
                Issue.cycle_id == cycle_id,
                Issue.workspace_id == workspace_id,
                Issue.is_deleted == False,  # noqa: E712
            )
        )
        return result.scalars().all()

    async def get_cycle_assigned_issues(
        self, cycle_id: UUID, workspace_id: UUID
    ) -> Sequence[Issue]:
        from pilot_space.infrastructure.database.models import Issue

        result = await self._session.execute(
            select(Issue).where(
                Issue.cycle_id == cycle_id,
                Issue.workspace_id == workspace_id,
                Issue.is_deleted == False,  # noqa: E712
                Issue.assignee_id.isnot(None),
            )
        )
        return result.scalars().all()

    async def get_issue_links_in_cycle(
        self, issue_ids: list[UUID], workspace_id: UUID
    ) -> Sequence[IssueLink]:
        from pilot_space.infrastructure.database.models import IssueLink

        result = await self._session.execute(
            select(IssueLink).where(
                IssueLink.source_issue_id.in_(issue_ids),
                IssueLink.workspace_id == workspace_id,
            )
        )
        return result.scalars().all()

    async def get_workspace_members_with_user(
        self, workspace_id: UUID
    ) -> Sequence[WorkspaceMember]:
        from pilot_space.infrastructure.database.models.workspace_member import WorkspaceMember

        result = await self._session.execute(
            select(WorkspaceMember)
            .options(selectinload(WorkspaceMember.user))
            .where(WorkspaceMember.workspace_id == workspace_id)
        )
        return result.scalars().all()
