"""Task service for issue-scoped task management.

Provides CRUD, status transitions, reordering, AI decomposition,
and context export for tasks.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from pilot_space.infrastructure.database.models.task import Task, TaskStatus
from pilot_space.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from pilot_space.infrastructure.database.repositories.issue_repository import (
        IssueRepository,
    )
    from pilot_space.infrastructure.database.repositories.task_repository import (
        TaskRepository,
    )

logger = get_logger(__name__)


@dataclass
class CreateTaskPayload:
    """Payload for creating a task."""

    workspace_id: UUID
    issue_id: UUID
    title: str
    description: str | None = None
    acceptance_criteria: list[dict[str, Any]] | None = None
    estimated_hours: float | None = None
    code_references: list[dict[str, Any]] | None = None
    dependency_ids: list[str] | None = None
    ai_prompt: str | None = None
    ai_generated: bool = False


@dataclass
class UpdateTaskPayload:
    """Payload for updating a task."""

    task_id: UUID
    workspace_id: UUID
    title: str | None = None
    description: str | None = None
    acceptance_criteria: list[dict[str, Any]] | None = None
    estimated_hours: float | None = None
    code_references: list[dict[str, Any]] | None = None
    ai_prompt: str | None = None
    dependency_ids: list[str] | None = None
    clear_description: bool = False
    clear_estimated_hours: bool = False
    clear_code_references: bool = False


class TaskService:
    """Service for task CRUD, reordering, and context export."""

    def __init__(
        self,
        session: AsyncSession,
        task_repository: TaskRepository,
        issue_repository: IssueRepository,
    ) -> None:
        self._session = session
        self._task_repo = task_repository
        self._issue_repo = issue_repository

    async def list_tasks(
        self,
        issue_id: UUID,
        workspace_id: UUID,
    ) -> dict[str, Any]:
        """List all tasks for an issue with progress stats."""
        issue = await self._issue_repo.get_by_id_scalar(issue_id)
        if not issue:
            raise ValueError(f"Issue {issue_id} not found")
        if issue.workspace_id != workspace_id:
            raise ValueError("Issue does not belong to workspace")

        tasks = await self._task_repo.list_by_issue(issue_id)
        total = len(tasks)
        completed = sum(1 for t in tasks if t.status == TaskStatus.DONE)
        completion_percent = (completed / total * 100) if total > 0 else 0.0

        return {
            "tasks": tasks,
            "total": total,
            "completed": completed,
            "completion_percent": round(completion_percent, 1),
        }

    async def create_task(self, payload: CreateTaskPayload) -> Task:
        """Create a new task for an issue."""
        # Validate issue exists
        issue = await self._issue_repo.get_by_id_scalar(payload.issue_id)
        if not issue:
            raise ValueError(f"Issue {payload.issue_id} not found")
        if issue.workspace_id != payload.workspace_id:
            raise ValueError("Issue does not belong to workspace")

        # Get next sort order
        existing = await self._task_repo.list_by_issue(payload.issue_id)
        next_order = len(existing)

        task = Task(
            workspace_id=payload.workspace_id,
            issue_id=payload.issue_id,
            title=payload.title.strip(),
            description=payload.description,
            acceptance_criteria=payload.acceptance_criteria,
            status=TaskStatus.TODO,
            sort_order=next_order,
            estimated_hours=payload.estimated_hours,
            code_references=payload.code_references,
            dependency_ids=payload.dependency_ids,
            ai_prompt=payload.ai_prompt,
            ai_generated=payload.ai_generated,
        )

        task = await self._task_repo.create(task)
        logger.info(
            "Task created", extra={"task_id": str(task.id), "issue_id": str(payload.issue_id)}
        )
        return task

    async def update_task(self, payload: UpdateTaskPayload) -> Task:
        """Update an existing task."""
        task = await self._task_repo.get_by_id(payload.task_id)
        if not task:
            raise ValueError(f"Task {payload.task_id} not found")
        if task.workspace_id != payload.workspace_id:
            raise ValueError("Task does not belong to workspace")

        if payload.title is not None:
            task.title = payload.title.strip()
        if payload.clear_description:
            task.description = None
        elif payload.description is not None:
            task.description = payload.description
        if payload.acceptance_criteria is not None:
            task.acceptance_criteria = payload.acceptance_criteria
        if payload.clear_estimated_hours:
            task.estimated_hours = None
        elif payload.estimated_hours is not None:
            task.estimated_hours = payload.estimated_hours
        if payload.clear_code_references:
            task.code_references = None
        elif payload.code_references is not None:
            task.code_references = payload.code_references
        if payload.ai_prompt is not None:
            task.ai_prompt = payload.ai_prompt
        if payload.dependency_ids is not None:
            task.dependency_ids = payload.dependency_ids

        return await self._task_repo.update(task)

    async def delete_task(
        self,
        task_id: UUID,
        workspace_id: UUID,
    ) -> None:
        """Soft-delete a task."""
        task = await self._task_repo.get_by_id(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")
        if task.workspace_id != workspace_id:
            raise ValueError("Task does not belong to workspace")

        await self._task_repo.delete(task)
        logger.info("Task deleted", extra={"task_id": str(task_id)})

    async def update_status(
        self,
        task_id: UUID,
        workspace_id: UUID,
        new_status: str,
    ) -> Task:
        """Update task status."""
        task = await self._task_repo.get_by_id(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")
        if task.workspace_id != workspace_id:
            raise ValueError("Task does not belong to workspace")

        try:
            task.status = TaskStatus(new_status)
        except ValueError as e:
            raise ValueError(f"Invalid status: {new_status}") from e

        task = await self._task_repo.update(task)
        logger.info(
            "Task status updated",
            extra={"task_id": str(task_id), "status": new_status},
        )
        return task

    async def reorder_tasks(
        self,
        issue_id: UUID,
        workspace_id: UUID,
        task_ids: list[UUID],
    ) -> list[Task]:
        """Reorder tasks for an issue."""
        # Validate all tasks belong to this issue
        existing = await self._task_repo.list_by_issue(issue_id)
        existing_ids = {t.id for t in existing}

        for tid in task_ids:
            if tid not in existing_ids:
                raise ValueError(f"Task {tid} not found for issue {issue_id}")

        await self._task_repo.bulk_update_order(issue_id, task_ids)

        # Re-fetch to get fresh updated_at timestamps and sort_order
        return list(await self._task_repo.list_by_issue(issue_id))

    async def export_context(
        self,
        issue_id: UUID,
        workspace_id: UUID,
        export_format: str = "markdown",
    ) -> dict[str, Any]:
        """Export issue context with tasks as markdown."""
        issue = await self._issue_repo.get_by_id(issue_id)
        if not issue:
            raise ValueError(f"Issue {issue_id} not found")
        if issue.workspace_id != workspace_id:
            raise ValueError("Issue does not belong to workspace")

        tasks = await self._task_repo.list_by_issue(issue_id)

        if export_format == "claude_code":
            markdown = self._format_claude_code(issue, tasks)
        elif export_format == "task_list":
            markdown = self._format_task_list(issue, tasks)
        else:
            markdown = self._format_markdown(issue, tasks)

        stats: dict[str, int] = {
            "tasks": len(tasks),
            "completed": sum(1 for t in tasks if t.status == TaskStatus.DONE),
        }

        return {
            "content": markdown,
            "format": export_format,
            "generated_at": datetime.now(tz=UTC),
            "stats": stats,
        }

    def _format_markdown(self, issue: Any, tasks: Sequence[Task]) -> str:
        """Full markdown context export."""
        lines = [
            f"# {issue.identifier}: {issue.name}",
            "",
        ]

        if issue.description:
            lines.extend(["## Description", "", issue.description, ""])

        if hasattr(issue, "acceptance_criteria") and issue.acceptance_criteria:
            lines.append("## Acceptance Criteria")
            lines.append("")
            for ac in issue.acceptance_criteria:
                text = ac.get("text", "") if isinstance(ac, dict) else str(ac)
                done = ac.get("done", False) if isinstance(ac, dict) else False
                check = "x" if done else " "
                lines.append(f"- [{check}] {text}")
            lines.append("")

        if hasattr(issue, "technical_requirements") and issue.technical_requirements:
            lines.extend(["## Technical Requirements", "", issue.technical_requirements, ""])

        if tasks:
            lines.append("## Tasks")
            lines.append("")
            for i, task in enumerate(tasks, 1):
                status_mark = "x" if task.status == TaskStatus.DONE else " "
                lines.append(f"- [{status_mark}] **Task {i}**: {task.title}")
                if task.description:
                    lines.append(f"  {task.description}")
                if task.estimated_hours:
                    lines.append(f"  *Estimated: {task.estimated_hours}h*")
            lines.append("")

        return "\n".join(lines)

    def _format_claude_code(self, issue: Any, tasks: Sequence[Task]) -> str:
        """Claude Code optimized prompt format."""
        lines = [
            "## Context",
            f"Issue: {issue.identifier} - {issue.name}",
        ]
        if issue.description:
            lines.extend(["", issue.description])

        if tasks:
            lines.extend(["", "## Tasks"])
            for i, task in enumerate(tasks, 1):
                status = "DONE" if task.status == TaskStatus.DONE else "TODO"
                lines.append(f"{i}. [{status}] {task.title}")
                if task.ai_prompt:
                    lines.append(f"   Prompt: {task.ai_prompt}")

        if hasattr(issue, "technical_requirements") and issue.technical_requirements:
            lines.extend(["", "## Constraints"])
            for line in issue.technical_requirements.strip().splitlines():
                stripped = line.strip()
                if stripped:
                    prefix = "" if stripped.startswith("-") else "- "
                    lines.append(f"{prefix}{stripped}")
        else:
            lines.extend(
                [
                    "",
                    "## Constraints",
                    "- Follow existing code patterns and conventions",
                    "- Write tests for all changes (>80% coverage)",
                ]
            )

        if hasattr(issue, "acceptance_criteria") and issue.acceptance_criteria:
            lines.extend(["", "## Acceptance Criteria"])
            for ac in issue.acceptance_criteria:
                text = ac.get("text", "") if isinstance(ac, dict) else str(ac)
                lines.append(f"- [ ] {text}")

        return "\n".join(lines)

    def _format_task_list(self, issue: Any, tasks: Sequence[Task]) -> str:
        """Ordered task list with prompts."""
        lines = [f"# Task List: {issue.identifier}", ""]

        for i, task in enumerate(tasks, 1):
            lines.append(f"## Task {i}: {task.title}")
            if task.description:
                lines.append("")
                lines.append(task.description)
            if task.ai_prompt:
                lines.append("")
                lines.append(f"**Prompt**: {task.ai_prompt}")
            if task.code_references:
                lines.append("")
                lines.append("**Files**:")
                for ref in task.code_references:
                    file_path = ref.get("file", "") if ref else ""
                    lines.append(f"- `{file_path}`")
            lines.append("")

        return "\n".join(lines)

    def _generate_ai_prompt(
        self,
        task_title: str,
        task_description: str | None,
        acceptance_criteria: list[dict[str, Any]] | None,
        code_references: list[dict[str, Any]] | None,
        issue: Any,
    ) -> str:
        """Generate Claude Code ready-to-use prompt for a task."""
        lines = [
            task_title,
            "",
            "## Context",
            f"Issue: {issue.identifier} - {issue.name}",
        ]

        if issue.description:
            desc_preview = (
                issue.description[:200] + "..."
                if len(issue.description) > 200
                else issue.description
            )
            lines.extend(["", desc_preview])

        if task_description:
            lines.extend(["", "## Requirements", "", task_description])

        if acceptance_criteria:
            lines.extend(["", "## Acceptance Criteria", ""])
            for ac in acceptance_criteria:
                text = ac.get("text", "")
                done = ac.get("done", False)
                check = "x" if done else " "
                lines.append(f"- [{check}] {text}")

        if code_references:
            lines.extend(["", "## Files to Reference", ""])
            for ref in code_references:
                file_path = ref.get("file", "")
                line_range = ref.get("lines", "")
                description = ref.get("description", "")
                badge = ref.get("badge", "")

                ref_line = f"- `{file_path}`"
                if line_range:
                    ref_line += f" (lines {line_range})"
                if badge:
                    ref_line += f" [{badge}]"
                lines.append(ref_line)
                if description:
                    lines.append(f"  {description}")

        if hasattr(issue, "technical_requirements") and issue.technical_requirements:
            lines.extend(["", "## Technical Constraints", "", issue.technical_requirements])

        return "\n".join(lines)

    async def create_tasks_from_decomposition(
        self,
        issue_id: UUID,
        workspace_id: UUID,
        subtasks: list[dict[str, Any]],
    ) -> list[Task]:
        """Create tasks from AI decomposition skill output.

        Uses a single bulk_create call instead of N individual create_task calls,
        reducing DB round-trips from 2N to 2 (one list_by_issue + one bulk_create).

        Args:
            issue_id: Parent issue UUID
            workspace_id: Workspace UUID for scoping
            subtasks: List of subtask dicts from decompose-tasks skill

        Returns:
            List of created Task entities

        Raises:
            ValueError: If issue not found or workspace mismatch
        """
        # Validate issue exists and belongs to workspace (single query with relationships)
        issue = await self._issue_repo.get_by_id(issue_id)
        if not issue:
            raise ValueError(f"Issue {issue_id} not found")
        if issue.workspace_id != workspace_id:
            raise ValueError("Issue does not belong to workspace")

        # Pre-fetch current task count once to determine starting sort_order
        existing = await self._task_repo.list_by_issue(issue_id)
        next_order = len(existing)

        tasks_to_create: list[Task] = []

        for idx, subtask_data in enumerate(subtasks):
            # _generate_ai_prompt is pure computation — no DB access
            ai_prompt = self._generate_ai_prompt(
                task_title=subtask_data.get("name", ""),
                task_description=subtask_data.get("description"),
                acceptance_criteria=subtask_data.get("acceptance_criteria"),
                code_references=subtask_data.get("code_references"),
                issue=issue,
            )

            estimated_hours: float | None = None
            if "estimated_days" in subtask_data:
                estimated_hours = subtask_data.get("estimated_days", 0) * 8

            task = Task(
                workspace_id=workspace_id,
                issue_id=issue_id,
                title=subtask_data.get("name", "").strip(),
                description=subtask_data.get("description"),
                acceptance_criteria=subtask_data.get("acceptance_criteria"),
                status=TaskStatus.TODO,
                sort_order=next_order + idx,
                estimated_hours=estimated_hours,
                code_references=subtask_data.get("code_references"),
                dependency_ids=subtask_data.get("dependencies"),
                ai_prompt=ai_prompt,
                ai_generated=True,
            )
            tasks_to_create.append(task)

        created_tasks = await self._task_repo.bulk_create(tasks_to_create)

        logger.info(
            "Tasks created from AI decomposition",
            extra={
                "issue_id": str(issue_id),
                "task_count": len(created_tasks),
            },
        )

        return created_tasks
