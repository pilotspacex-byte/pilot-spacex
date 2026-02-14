"""Task repository for issue-scoped task management."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import asc, func, select, update

from pilot_space.infrastructure.database.models.task import Task, TaskStatus
from pilot_space.infrastructure.database.repositories.base import BaseRepository

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sqlalchemy.ext.asyncio import AsyncSession


class TaskRepository(BaseRepository[Task]):
    """Repository for task CRUD operations."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session=session, model_class=Task)

    async def list_by_issue(
        self,
        issue_id: UUID,
        *,
        include_deleted: bool = False,
    ) -> Sequence[Task]:
        """List all tasks for an issue, ordered by sort_order."""
        query = select(Task).where(Task.issue_id == issue_id)
        if not include_deleted:
            query = query.where(Task.is_deleted == False)  # noqa: E712
        query = query.order_by(asc(Task.sort_order), asc(Task.created_at))
        result = await self.session.execute(query)
        return result.scalars().all()

    async def bulk_create(self, tasks: list[Task]) -> list[Task]:
        """Create multiple tasks in a single transaction."""
        self.session.add_all(tasks)
        await self.session.flush()
        for task in tasks:
            await self.session.refresh(task)
        return tasks

    async def bulk_update_order(
        self,
        issue_id: UUID,
        task_ids: list[UUID],
    ) -> None:
        """Reorder tasks by updating sort_order based on position in list."""
        for idx, task_id in enumerate(task_ids):
            await self.session.execute(
                update(Task)
                .where(
                    Task.id == task_id,
                    Task.issue_id == issue_id,
                    Task.is_deleted == False,  # noqa: E712
                )
                .values(sort_order=idx)
            )
        await self.session.flush()

    async def count_by_issue(
        self,
        issue_id: UUID,
    ) -> tuple[int, int]:
        """Return (total, completed) task counts for an issue."""
        total_query = (
            select(func.count())
            .select_from(Task)
            .where(Task.issue_id == issue_id, Task.is_deleted == False)  # noqa: E712
        )
        total_result = await self.session.execute(total_query)
        total = total_result.scalar() or 0

        done_query = (
            select(func.count())
            .select_from(Task)
            .where(
                Task.issue_id == issue_id,
                Task.is_deleted == False,  # noqa: E712
                Task.status == TaskStatus.DONE,
            )
        )
        done_result = await self.session.execute(done_query)
        done = done_result.scalar() or 0

        return (total, done)
