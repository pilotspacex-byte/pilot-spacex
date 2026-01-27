"""AITask repository for managing AI task CRUD operations.

Provides data access layer for AI tasks within conversation sessions.
Supports progress tracking, status management, and dependency chains.

Reference: T071-T074 (Task Progress Tracking)
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import desc, select

from pilot_space.infrastructure.database.models.ai_task import AITask, TaskStatus
from pilot_space.infrastructure.database.repositories.base import BaseRepository

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sqlalchemy.ext.asyncio import AsyncSession


class AITaskRepository(BaseRepository[AITask]):  # type: ignore[type-var]
    """Repository for AITask model.

    Provides methods for creating, reading, updating tasks with
    progress tracking, status transitions, and dependency management.

    Example:
        repo = AITaskRepository(session)
        task = await repo.create_task(
            session_id=session_id,
            subject="Analyze code patterns",
            owner="code_analyzer",
        )
        await repo.update_progress(task.id, progress=50, status=TaskStatus.IN_PROGRESS)
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with session.

        Args:
            session: Async database session.
        """
        super().__init__(session, AITask)

    async def create_task(
        self,
        *,
        session_id: UUID,
        subject: str,
        description: str | None = None,
        owner: str | None = None,
        task_metadata: dict[str, object] | None = None,
        blocked_by_id: UUID | None = None,
    ) -> AITask:
        """Create a new task.

        Args:
            session_id: Session this task belongs to.
            subject: Brief task title.
            description: Optional detailed description.
            owner: Optional agent name or "user".
            task_metadata: Optional metadata dictionary.
            blocked_by_id: Optional blocking task ID.

        Returns:
            Created AITask instance.
        """
        task = AITask(
            session_id=session_id,
            subject=subject,
            description=description,
            owner=owner,
            task_metadata=task_metadata,
            blocked_by_id=blocked_by_id,
            status=TaskStatus.PENDING,
            progress=0,
        )
        self.session.add(task)
        await self.session.flush()
        await self.session.refresh(task)
        return task

    async def get_by_session(
        self,
        session_id: UUID,
        *,
        status: TaskStatus | None = None,
    ) -> Sequence[AITask]:
        """Get all tasks for a session.

        Args:
            session_id: Session ID to filter by.
            status: Optional status filter.

        Returns:
            List of tasks ordered by creation time.
        """
        query = select(AITask).where(AITask.session_id == session_id)

        if status:
            query = query.where(AITask.status == status)

        query = query.order_by(desc(AITask.created_at))
        result = await self.session.execute(query)
        return result.scalars().all()

    async def update_progress(
        self,
        task_id: UUID,
        *,
        progress: int,
        status: TaskStatus | None = None,
    ) -> AITask | None:
        """Update task progress and optionally status.

        Args:
            task_id: Task ID to update.
            progress: Progress percentage (0-100).
            status: Optional new status.

        Returns:
            Updated task or None if not found.
        """
        task = await self.get_by_id(task_id)
        if not task:
            return None

        task.progress = max(0, min(100, progress))  # Clamp 0-100
        if status:
            task.status = status

        await self.session.flush()
        await self.session.refresh(task)
        return task

    async def complete_task(self, task_id: UUID) -> AITask | None:
        """Mark task as completed.

        Args:
            task_id: Task ID to complete.

        Returns:
            Updated task or None if not found.
        """
        return await self.update_progress(
            task_id,
            progress=100,
            status=TaskStatus.COMPLETED,
        )

    async def fail_task(
        self,
        task_id: UUID,
        error_message: str | None = None,
    ) -> AITask | None:
        """Mark task as failed.

        Args:
            task_id: Task ID to fail.
            error_message: Optional error message to store in metadata.

        Returns:
            Updated task or None if not found.
        """
        task = await self.get_by_id(task_id)
        if not task:
            return None

        task.status = TaskStatus.FAILED
        if error_message:
            metadata = task.task_metadata or {}
            metadata["error"] = error_message
            task.task_metadata = metadata

        await self.session.flush()
        await self.session.refresh(task)
        return task

    async def get_pending_tasks(
        self,
        session_id: UUID,
    ) -> Sequence[AITask]:
        """Get all pending tasks for a session.

        Args:
            session_id: Session ID to filter by.

        Returns:
            List of pending tasks.
        """
        return await self.get_by_session(session_id, status=TaskStatus.PENDING)

    async def get_blocking_tasks(
        self,
        task_id: UUID,
    ) -> Sequence[AITask]:
        """Get all tasks blocked by the given task.

        Args:
            task_id: Task ID that is blocking others.

        Returns:
            List of blocked tasks.
        """
        query = select(AITask).where(AITask.blocked_by_id == task_id)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def unblock_dependent_tasks(self, task_id: UUID) -> int:
        """Unblock tasks that were waiting on the given task.

        When a task completes, this removes the dependency for all tasks
        that were blocked by it.

        Args:
            task_id: Completed task ID.

        Returns:
            Number of tasks unblocked.
        """
        blocked_tasks = await self.get_blocking_tasks(task_id)

        for task in blocked_tasks:
            if task.status == TaskStatus.BLOCKED:
                task.blocked_by_id = None
                task.status = TaskStatus.PENDING

        await self.session.flush()
        return len(blocked_tasks)

    async def get_task_progress_summary(
        self,
        session_id: UUID,
    ) -> dict[str, int]:
        """Get progress summary for a session.

        Args:
            session_id: Session ID.

        Returns:
            Dictionary with counts: total, pending, in_progress, completed, failed, blocked.
        """
        tasks = await self.get_by_session(session_id)

        return {
            "total": len(tasks),
            "pending": sum(1 for t in tasks if t.status == TaskStatus.PENDING),
            "in_progress": sum(1 for t in tasks if t.status == TaskStatus.IN_PROGRESS),
            "completed": sum(1 for t in tasks if t.status == TaskStatus.COMPLETED),
            "failed": sum(1 for t in tasks if t.status == TaskStatus.FAILED),
            "blocked": sum(1 for t in tasks if t.status == TaskStatus.BLOCKED),
        }


__all__ = ["AITaskRepository"]
