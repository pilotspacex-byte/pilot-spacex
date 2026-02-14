"""Task API schemas for issue-scoped task management."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field

from pilot_space.api.v1.schemas.base import BaseSchema


class CodeReferenceSchema(BaseSchema):
    """Code reference within a task."""

    file: str = Field(..., max_length=500, description="File path")
    lines: str | None = Field(None, max_length=50, description="Line range e.g. '10-25'")
    description: str | None = Field(None, max_length=500, description="What this reference is for")
    badge: str | None = Field(None, max_length=50, description="Display badge text")


class TaskCreateRequest(BaseSchema):
    """Request to create a task."""

    title: str = Field(..., min_length=1, max_length=500, description="Task title")
    description: str | None = Field(None, max_length=10000, description="Task description")
    acceptance_criteria: list[dict[str, Any]] | None = Field(
        None,
        description="Acceptance criteria items as [{text: str, done: bool}]",
    )
    estimated_hours: float | None = Field(None, ge=0, le=999.9, description="Estimated hours")
    code_references: list[CodeReferenceSchema] | None = None
    dependency_ids: list[UUID] | None = None


class TaskUpdateRequest(BaseSchema):
    """Request to update a task."""

    title: str | None = Field(None, min_length=1, max_length=500)
    description: str | None = None
    acceptance_criteria: list[dict[str, Any]] | None = None
    estimated_hours: float | None = Field(None, ge=0, le=999.9)
    code_references: list[CodeReferenceSchema] | None = None
    ai_prompt: str | None = None
    dependency_ids: list[UUID] | None = None

    clear_description: bool = False
    clear_estimated_hours: bool = False
    clear_code_references: bool = False


class TaskStatusUpdate(BaseSchema):
    """Request to update task status."""

    status: str = Field(..., pattern="^(todo|in_progress|done)$", description="New status")


class TaskReorderRequest(BaseSchema):
    """Request to reorder tasks."""

    task_ids: list[UUID] = Field(..., min_length=1, description="Ordered list of task IDs")


class TaskResponse(BaseSchema):
    """Full task response."""

    id: UUID
    workspace_id: UUID
    issue_id: UUID
    title: str
    description: str | None
    acceptance_criteria: list[dict[str, Any]] = Field(default_factory=list)
    status: str
    sort_order: int
    estimated_hours: float | None
    code_references: list[dict[str, Any]] = Field(default_factory=list)
    ai_prompt: str | None
    ai_generated: bool
    dependency_ids: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_task(cls, task: Any) -> TaskResponse:
        """Create from Task model."""
        return cls(
            id=task.id,
            workspace_id=task.workspace_id,
            issue_id=task.issue_id,
            title=task.title,
            description=task.description,
            acceptance_criteria=task.acceptance_criteria or [],
            status=task.status.value if hasattr(task.status, "value") else task.status,
            sort_order=task.sort_order,
            estimated_hours=float(task.estimated_hours)
            if task.estimated_hours is not None
            else None,
            code_references=task.code_references or [],
            ai_prompt=task.ai_prompt,
            ai_generated=task.ai_generated,
            dependency_ids=task.dependency_ids or [],
            created_at=task.created_at,
            updated_at=task.updated_at,
        )


class TaskListResponse(BaseSchema):
    """Task list response with progress."""

    tasks: list[TaskResponse]
    total: int
    completed: int
    completion_percent: float


class ContextExportResponse(BaseSchema):
    """Context export response."""

    markdown: str
    format: str
    generated_at: datetime
    stats: dict[str, int] = Field(default_factory=dict, description="Counts of included items")


class DecomposeRequest(BaseSchema):
    """Request to decompose issue into subtasks via AI."""

    strategy: str | None = Field(
        None,
        max_length=50,
        description="Decomposition strategy (e.g., 'frontend', 'backend', 'full-stack')",
    )
    max_subtasks: int | None = Field(
        None, ge=1, le=20, description="Maximum number of subtasks to generate"
    )
    include_estimates: bool = Field(True, description="Include time estimates")


class SubtaskSchema(BaseSchema):
    """Subtask from decomposition output."""

    order: int
    name: str
    description: str | None
    confidence: str  # RECOMMENDED, DEFAULT, ALTERNATIVE
    estimated_days: float | None
    labels: list[str] | None
    dependencies: list[int] | None
    acceptance_criteria: list[dict[str, Any]] | None
    code_references: list[CodeReferenceSchema] | None
    ai_prompt: str | None


class DecomposeResponse(BaseSchema):
    """Response from AI decomposition."""

    subtasks: list[SubtaskSchema]
    summary: str | None = Field(None, description="Summary of decomposition")
    total_estimated_days: float | None = Field(None, description="Total estimated days")
    critical_path: list[int] | None = Field(None, description="Critical path task orders")
    parallel_opportunities: list[str] | None = Field(
        None, description="Tasks that can run in parallel"
    )


__all__ = [
    "CodeReferenceSchema",
    "ContextExportResponse",
    "DecomposeRequest",
    "DecomposeResponse",
    "SubtaskSchema",
    "TaskCreateRequest",
    "TaskListResponse",
    "TaskReorderRequest",
    "TaskResponse",
    "TaskStatusUpdate",
    "TaskUpdateRequest",
]
