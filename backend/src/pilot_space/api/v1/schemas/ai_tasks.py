"""Pydantic schemas for AI task progress endpoints.

Covers TaskProgressResponse and SessionTasksResponse.

Reference: T074 (Task Progress Endpoint)
Design Decisions: DD-058 (SSE for streaming)
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


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


__all__ = ["SessionTasksResponse", "TaskProgressResponse"]
