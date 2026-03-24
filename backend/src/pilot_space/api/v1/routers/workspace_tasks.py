"""Workspace-scoped Tasks API router.

Provides nested routes for tasks under workspace issues.
GET /workspaces/{workspace_id}/issues/{issue_id}/tasks
POST /workspaces/{workspace_id}/issues/{issue_id}/tasks
PATCH /workspaces/{workspace_id}/tasks/{task_id}
DELETE /workspaces/{workspace_id}/tasks/{task_id}
PATCH /workspaces/{workspace_id}/tasks/{task_id}/status
PUT /workspaces/{workspace_id}/issues/{issue_id}/tasks/reorder
GET /workspaces/{workspace_id}/issues/{issue_id}/context/export
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Path, Query, status

from pilot_space.api.v1.dependencies import TaskServiceDep, WorkspaceRepositoryDep
from pilot_space.api.v1.schemas.task import (
    ContextExportResponse,
    TaskCreateRequest,
    TaskListResponse,
    TaskReorderRequest,
    TaskResponse,
    TaskStatusUpdate,
    TaskUpdateRequest,
)
from pilot_space.dependencies import SyncedUserId
from pilot_space.dependencies.auth import SessionDep
from pilot_space.domain.exceptions import NotFoundError
from pilot_space.infrastructure.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()

# Path parameter types
WorkspaceIdOrSlug = Annotated[str, Path(description="Workspace ID (UUID) or slug")]
IssueIdPath = Annotated[UUID, Path(description="Issue ID")]
TaskIdPath = Annotated[UUID, Path(description="Task ID")]


def _is_valid_uuid(value: str) -> bool:
    """Check if a string is a valid UUID."""
    try:
        UUID(value)
        return True
    except ValueError:
        return False


async def _resolve_workspace(
    workspace_id_or_slug: str,
    workspace_repo: WorkspaceRepositoryDep,
):
    """Resolve workspace by UUID or slug (scalar-only, no relationships).

    Uses lazyload to prevent the Workspace model's 7 default selectin
    relationships from firing. Only scalar columns (id, slug, name, etc.)
    are loaded. Use this for validation/ownership checks.
    """
    if _is_valid_uuid(workspace_id_or_slug):
        workspace = await workspace_repo.get_by_id_scalar(UUID(workspace_id_or_slug))
    else:
        workspace = await workspace_repo.get_by_slug_scalar(workspace_id_or_slug)

    if not workspace:
        raise NotFoundError("Workspace not found")
    return workspace


# ============================================================================
# Task CRUD Endpoints
# ============================================================================


@router.get(
    "/{workspace_id}/issues/{issue_id}/tasks",
    response_model=TaskListResponse,
    tags=["workspace-tasks"],
    summary="List tasks for an issue",
)
async def list_tasks(
    workspace_id: WorkspaceIdOrSlug,
    issue_id: IssueIdPath,
    _session: SessionDep,
    current_user_id: SyncedUserId,
    workspace_repo: WorkspaceRepositoryDep,
    service: TaskServiceDep,
) -> TaskListResponse:
    """List all tasks for an issue with progress stats."""
    workspace = await _resolve_workspace(workspace_id, workspace_repo)

    result = await service.list_tasks(issue_id, workspace.id)

    return TaskListResponse(
        tasks=[TaskResponse.from_task(t) for t in result["tasks"]],
        total=result["total"],
        completed=result["completed"],
        completion_percent=result["completion_percent"],
    )


@router.post(
    "/{workspace_id}/issues/{issue_id}/tasks",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["workspace-tasks"],
    summary="Create a new task",
)
async def create_task(
    workspace_id: WorkspaceIdOrSlug,
    issue_id: IssueIdPath,
    request: TaskCreateRequest,
    _session: SessionDep,
    current_user_id: SyncedUserId,
    workspace_repo: WorkspaceRepositoryDep,
    service: TaskServiceDep,
) -> TaskResponse:
    """Create a new task for an issue."""
    from pilot_space.application.services.task_service import CreateTaskPayload

    workspace = await _resolve_workspace(workspace_id, workspace_repo)

    payload = CreateTaskPayload(
        workspace_id=workspace.id,
        issue_id=issue_id,
        title=request.title,
        description=request.description,
        acceptance_criteria=request.acceptance_criteria,
        estimated_hours=request.estimated_hours,
        code_references=[ref.model_dump() for ref in request.code_references]
        if request.code_references
        else None,
        dependency_ids=[str(d) for d in request.dependency_ids] if request.dependency_ids else None,
    )

    task = await service.create_task(payload)

    return TaskResponse.from_task(task)


@router.patch(
    "/{workspace_id}/tasks/{task_id}",
    response_model=TaskResponse,
    tags=["workspace-tasks"],
    summary="Update a task",
)
async def update_task(
    workspace_id: WorkspaceIdOrSlug,
    task_id: TaskIdPath,
    request: TaskUpdateRequest,
    _session: SessionDep,
    current_user_id: SyncedUserId,
    workspace_repo: WorkspaceRepositoryDep,
    service: TaskServiceDep,
) -> TaskResponse:
    """Update an existing task."""
    from pilot_space.application.services.task_service import UpdateTaskPayload

    workspace = await _resolve_workspace(workspace_id, workspace_repo)

    payload = UpdateTaskPayload(
        task_id=task_id,
        workspace_id=workspace.id,
        title=request.title,
        description=request.description,
        acceptance_criteria=request.acceptance_criteria,
        estimated_hours=request.estimated_hours,
        code_references=[ref.model_dump() for ref in request.code_references]
        if request.code_references
        else None,
        ai_prompt=request.ai_prompt,
        dependency_ids=[str(d) for d in request.dependency_ids] if request.dependency_ids else None,
        clear_description=request.clear_description,
        clear_estimated_hours=request.clear_estimated_hours,
        clear_code_references=request.clear_code_references,
    )

    task = await service.update_task(payload)

    return TaskResponse.from_task(task)


@router.delete(
    "/{workspace_id}/tasks/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["workspace-tasks"],
    summary="Delete a task",
)
async def delete_task(
    workspace_id: WorkspaceIdOrSlug,
    task_id: TaskIdPath,
    _session: SessionDep,
    current_user_id: SyncedUserId,
    workspace_repo: WorkspaceRepositoryDep,
    service: TaskServiceDep,
) -> None:
    """Soft-delete a task."""
    workspace = await _resolve_workspace(workspace_id, workspace_repo)

    await service.delete_task(task_id, workspace.id)


@router.patch(
    "/{workspace_id}/tasks/{task_id}/status",
    response_model=TaskResponse,
    tags=["workspace-tasks"],
    summary="Update task status",
)
async def update_task_status(
    workspace_id: WorkspaceIdOrSlug,
    task_id: TaskIdPath,
    request: TaskStatusUpdate,
    _session: SessionDep,
    current_user_id: SyncedUserId,
    workspace_repo: WorkspaceRepositoryDep,
    service: TaskServiceDep,
) -> TaskResponse:
    """Update task status (todo/in_progress/done)."""
    workspace = await _resolve_workspace(workspace_id, workspace_repo)

    task = await service.update_status(task_id, workspace.id, request.status)

    return TaskResponse.from_task(task)


@router.put(
    "/{workspace_id}/issues/{issue_id}/tasks/reorder",
    response_model=TaskListResponse,
    tags=["workspace-tasks"],
    summary="Reorder tasks",
)
async def reorder_tasks(
    workspace_id: WorkspaceIdOrSlug,
    issue_id: IssueIdPath,
    request: TaskReorderRequest,
    _session: SessionDep,
    current_user_id: SyncedUserId,
    workspace_repo: WorkspaceRepositoryDep,
    service: TaskServiceDep,
) -> TaskListResponse:
    """Reorder tasks for an issue."""
    workspace = await _resolve_workspace(workspace_id, workspace_repo)

    tasks = await service.reorder_tasks(issue_id, workspace.id, request.task_ids)

    total = len(tasks)
    completed = sum(1 for t in tasks if t.status.value == "done")

    return TaskListResponse(
        tasks=[TaskResponse.from_task(t) for t in tasks],
        total=total,
        completed=completed,
        completion_percent=round(completed / total * 100, 1) if total > 0 else 0.0,
    )


# ============================================================================
# Context Export Endpoint
# ============================================================================


@router.get(
    "/{workspace_id}/issues/{issue_id}/context/export",
    response_model=ContextExportResponse,
    tags=["workspace-tasks"],
    summary="Export issue context",
)
async def export_context(
    workspace_id: WorkspaceIdOrSlug,
    issue_id: IssueIdPath,
    _session: SessionDep,
    current_user_id: SyncedUserId,
    workspace_repo: WorkspaceRepositoryDep,
    service: TaskServiceDep,
    export_format: str = Query(
        default="markdown",
        alias="format",
        pattern="^(markdown|claude_code|task_list)$",
    ),
) -> ContextExportResponse:
    """Export issue context with tasks in various formats."""
    workspace = await _resolve_workspace(workspace_id, workspace_repo)

    result = await service.export_context(issue_id, workspace.id, export_format)

    return ContextExportResponse(
        content=result["content"],
        format=result["format"],
        generated_at=result["generated_at"],
        stats=result["stats"],
    )


# ============================================================================
# AI Decomposition Endpoint
# ============================================================================


@router.post(
    "/{workspace_id}/issues/{issue_id}/tasks/decompose",
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
    tags=["workspace-tasks"],
    summary="Decompose issue into subtasks (AI)",
)
async def decompose_issue(
    workspace_id: WorkspaceIdOrSlug,
    issue_id: IssueIdPath,
    _session: SessionDep,
    current_user_id: SyncedUserId,
) -> dict[str, str]:
    """Decompose issue into subtasks using AI.

    This endpoint delegates to the PilotSpace chat interface.
    Use the /decompose-tasks skill in chat for AI-powered decomposition.

    Example: "/decompose-tasks {issue_identifier}"
    """
    return {
        "message": "AI decomposition available via PilotSpace chat /decompose-tasks",
        "usage": f"Open chat and type: /decompose-tasks {issue_id}",
        "status": "not_implemented",
    }


__all__ = ["router"]
