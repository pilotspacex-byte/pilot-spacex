"""AI Task Progress API endpoints.

Provides endpoints for querying task progress and status within
AI conversation sessions.

Reference: T074 (Task Progress Endpoint)
Design Decisions: DD-058 (SSE for streaming)
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter
from pydantic import BaseModel, Field

from pilot_space.dependencies import CurrentUserId, DbSession
from pilot_space.domain.exceptions import ForbiddenError, NotFoundError

router = APIRouter(prefix="/ai/tasks", tags=["ai-tasks"])


class TaskProgressResponse(BaseModel):
    """Task progress response.

    Attributes:
        task_id: Task UUID.
        subject: Task title.
        status: Current status (pending, in_progress, completed, failed, blocked).
        progress: Progress percentage (0-100).
        current_step: Optional current step description.
        total_steps: Optional total steps count.
        metadata: Additional task metadata.
        created_at: Task creation timestamp.
        updated_at: Last update timestamp.
    """

    task_id: UUID = Field(..., description="Task ID")
    subject: str = Field(..., description="Task title")
    status: str = Field(..., description="Task status")
    progress: int = Field(..., ge=0, le=100, description="Progress percentage")
    current_step: str | None = Field(None, description="Current step description")
    total_steps: int | None = Field(None, description="Total steps count")
    metadata: dict[str, Any] | None = Field(None, description="Task metadata")
    created_at: str = Field(..., description="Creation timestamp (ISO 8601)")
    updated_at: str = Field(..., description="Last update timestamp (ISO 8601)")


class SessionTasksResponse(BaseModel):
    """Session tasks summary response.

    Attributes:
        session_id: Session UUID.
        tasks: List of tasks.
        summary: Task status summary.
    """

    session_id: UUID = Field(..., description="Session ID")
    tasks: list[TaskProgressResponse] = Field(..., description="List of tasks")
    summary: dict[str, int] = Field(..., description="Task status summary")


@router.get("/{task_id}/progress")
async def get_task_progress(
    task_id: UUID,
    user_id: CurrentUserId,
    session: DbSession,
) -> TaskProgressResponse:
    """Get progress for a specific task.

    Args:
        task_id: Task UUID.
        user_id: Current user ID (from auth).
        session: Database session.

    Returns:
        Task progress details.

    Raises:
        HTTPException: 404 if task not found or 403 if unauthorized.
    """
    from sqlalchemy import select

    from pilot_space.infrastructure.database.models.ai_session import AISession
    from pilot_space.infrastructure.database.repositories.ai_task_repository import (
        AITaskRepository,
    )

    repo = AITaskRepository(session)
    task = await repo.get_by_id(task_id)

    if not task:
        raise NotFoundError("Task not found")

    # Verify task ownership via session
    stmt = select(AISession).where(AISession.id == task.session_id)
    result = await session.execute(stmt)
    ai_session = result.scalar_one_or_none()

    if not ai_session or ai_session.user_id != user_id:
        raise ForbiddenError("Not authorized to access this task")

    # Extract metadata fields
    metadata = task.task_metadata or {}
    current_step = metadata.get("current_step")
    total_steps = metadata.get("total_steps")

    return TaskProgressResponse(
        task_id=task.id,
        subject=task.subject,
        status=task.status.value,
        progress=task.progress,
        current_step=current_step,
        total_steps=total_steps,
        metadata=task.task_metadata,
        created_at=task.created_at.isoformat(),
        updated_at=task.updated_at.isoformat(),
    )


@router.get("/session/{session_id}")
async def get_session_tasks(
    session_id: UUID,
    user_id: CurrentUserId,
    session: DbSession,
) -> SessionTasksResponse:
    """Get all tasks for a session with summary.

    Args:
        session_id: Session UUID.
        user_id: Current user ID (from auth).
        session: Database session.

    Returns:
        List of tasks and summary statistics.
    """
    from pilot_space.infrastructure.database.repositories.ai_task_repository import (
        AITaskRepository,
    )

    repo = AITaskRepository(session)

    # Get all tasks
    tasks = await repo.get_by_session(session_id)

    # Get summary
    summary = await repo.get_task_progress_summary(session_id)

    # Convert to response format
    task_responses = [
        TaskProgressResponse(
            task_id=task.id,
            subject=task.subject,
            status=task.status.value,
            progress=task.progress,
            current_step=(task.task_metadata or {}).get("current_step"),
            total_steps=(task.task_metadata or {}).get("total_steps"),
            metadata=task.task_metadata,
            created_at=task.created_at.isoformat(),
            updated_at=task.updated_at.isoformat(),
        )
        for task in tasks
    ]

    return SessionTasksResponse(
        session_id=session_id,
        tasks=task_responses,
        summary=summary,
    )


__all__ = ["router"]
