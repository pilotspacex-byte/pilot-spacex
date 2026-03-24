"""Unit tests for workspace task management API router (CRUD operations).

Tests CRUD endpoints: list, create, update, delete tasks.
Uses mock service layer for router-level isolation.

Source: 013-task-management, Phase 1.8
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import status

from pilot_space.domain.exceptions import NotFoundError
from pilot_space.infrastructure.database.models.task import Task, TaskStatus

if TYPE_CHECKING:
    from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

_RESOLVE_WORKSPACE_PATH = "pilot_space.api.v1.routers.workspace_tasks._resolve_workspace"


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def workspace_id() -> str:
    """Workspace ID as string for URL path."""
    return str(uuid4())


@pytest.fixture
def issue_id() -> str:
    """Issue ID as string for URL path."""
    return str(uuid4())


@pytest.fixture
def task_id() -> str:
    """Task ID as string for URL path."""
    return str(uuid4())


@pytest.fixture
def mock_task() -> Task:
    """Mock Task for responses."""
    return Task(
        id=uuid4(),
        workspace_id=uuid4(),
        issue_id=uuid4(),
        title="Test Task",
        description="Task description",
        status=TaskStatus.TODO,
        sort_order=0,
        estimated_hours=5.0,
        code_references=[{"file": "main.py", "lines": "10-20"}],
        ai_prompt="Implement X",
        ai_generated=False,
        dependency_ids=None,
        created_at=datetime.now(tz=UTC),
        updated_at=datetime.now(tz=UTC),
    )


@pytest.fixture
def mock_service() -> AsyncMock:
    """Mock TaskService."""
    return AsyncMock()


@pytest.fixture
def mock_workspace() -> MagicMock:
    """Mock resolved workspace."""
    ws = MagicMock()
    ws.id = uuid4()
    return ws


@pytest.fixture
async def task_client(mock_service: AsyncMock) -> AsyncGenerator[AsyncClient, None]:
    """Authenticated client with dependency overrides for task router tests.

    Imports app directly (not via conftest's app fixture) to avoid a pre-existing
    circular import triggered by conftest's `from pilot_space.container import Container`.
    Uses app.dependency_overrides to bypass auth, session, workspace repo,
    and task service dependencies that FastAPI resolves before handler code runs.
    """
    from httpx import ASGITransport, AsyncClient

    from pilot_space.api.v1.dependencies import _get_task_service
    from pilot_space.api.v1.repository_deps import _get_workspace_repository
    from pilot_space.dependencies.auth import ensure_user_synced, get_session
    from pilot_space.main import app

    mock_session = AsyncMock()

    async def mock_session_gen() -> AsyncGenerator[Any, None]:
        yield mock_session

    app.dependency_overrides[get_session] = mock_session_gen
    app.dependency_overrides[ensure_user_synced] = lambda: uuid4()
    app.dependency_overrides[_get_workspace_repository] = lambda: AsyncMock()
    app.dependency_overrides[_get_task_service] = lambda: mock_service

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"Authorization": "Bearer test-token"},
    ) as ac:
        yield ac

    app.dependency_overrides.pop(get_session, None)
    app.dependency_overrides.pop(ensure_user_synced, None)
    app.dependency_overrides.pop(_get_workspace_repository, None)
    app.dependency_overrides.pop(_get_task_service, None)


# ============================================================================
# GET /workspaces/{workspace_id}/issues/{issue_id}/tasks
# ============================================================================


class TestListTasks:
    """Tests for list tasks endpoint."""

    async def test_list_tasks_success(
        self,
        task_client: AsyncClient,
        workspace_id: str,
        issue_id: str,
        mock_service: AsyncMock,
        mock_task: Task,
        mock_workspace: MagicMock,
    ) -> None:
        """Returns task list with progress stats."""
        mock_service.list_tasks.return_value = {
            "tasks": [mock_task],
            "total": 1,
            "completed": 0,
            "completion_percent": 0.0,
        }

        with patch(_RESOLVE_WORKSPACE_PATH, return_value=mock_workspace):
            response = await task_client.get(
                f"/api/v1/workspaces/{workspace_id}/issues/{issue_id}/tasks"
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["tasks"]) == 1
        assert data["total"] == 1
        assert data["completed"] == 0
        assert data["completionPercent"] == 0.0

    async def test_list_tasks_empty_result(
        self,
        task_client: AsyncClient,
        workspace_id: str,
        issue_id: str,
        mock_service: AsyncMock,
        mock_workspace: MagicMock,
    ) -> None:
        """Returns empty list for issue with no tasks."""
        mock_service.list_tasks.return_value = {
            "tasks": [],
            "total": 0,
            "completed": 0,
            "completion_percent": 0.0,
        }

        with patch(_RESOLVE_WORKSPACE_PATH, return_value=mock_workspace):
            response = await task_client.get(
                f"/api/v1/workspaces/{workspace_id}/issues/{issue_id}/tasks"
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["tasks"] == []


# ============================================================================
# POST /workspaces/{workspace_id}/issues/{issue_id}/tasks
# ============================================================================


class TestCreateTask:
    """Tests for create task endpoint."""

    async def test_create_task_success(
        self,
        task_client: AsyncClient,
        workspace_id: str,
        issue_id: str,
        mock_service: AsyncMock,
        mock_task: Task,
        mock_workspace: MagicMock,
    ) -> None:
        """Creates task successfully."""
        mock_service.create_task.return_value = mock_task

        with patch(_RESOLVE_WORKSPACE_PATH, return_value=mock_workspace):
            response = await task_client.post(
                f"/api/v1/workspaces/{workspace_id}/issues/{issue_id}/tasks",
                json={
                    "title": "New Task",
                    "description": "Task description",
                    "estimatedHours": 5.0,
                },
            )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["title"] == "Test Task"
        mock_service.create_task.assert_awaited_once()

    async def test_create_task_minimal_fields(
        self,
        task_client: AsyncClient,
        workspace_id: str,
        issue_id: str,
        mock_service: AsyncMock,
        mock_task: Task,
        mock_workspace: MagicMock,
    ) -> None:
        """Creates task with minimal fields."""
        mock_service.create_task.return_value = mock_task

        with patch(_RESOLVE_WORKSPACE_PATH, return_value=mock_workspace):
            response = await task_client.post(
                f"/api/v1/workspaces/{workspace_id}/issues/{issue_id}/tasks",
                json={"title": "Minimal Task"},
            )

        assert response.status_code == status.HTTP_201_CREATED

    async def test_create_task_validation_error(
        self,
        task_client: AsyncClient,
        workspace_id: str,
        issue_id: str,
        mock_workspace: MagicMock,
    ) -> None:
        """Returns 422 for missing required fields."""
        with patch(_RESOLVE_WORKSPACE_PATH, return_value=mock_workspace):
            response = await task_client.post(
                f"/api/v1/workspaces/{workspace_id}/issues/{issue_id}/tasks",
                json={},
            )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_create_task_issue_not_found(
        self,
        task_client: AsyncClient,
        workspace_id: str,
        issue_id: str,
        mock_service: AsyncMock,
        mock_workspace: MagicMock,
    ) -> None:
        """Returns 404 if issue not found."""
        mock_service.create_task.side_effect = NotFoundError("Issue not found")

        with patch(_RESOLVE_WORKSPACE_PATH, return_value=mock_workspace):
            response = await task_client.post(
                f"/api/v1/workspaces/{workspace_id}/issues/{issue_id}/tasks",
                json={"title": "Task"},
            )

        assert response.status_code == status.HTTP_404_NOT_FOUND


# ============================================================================
# PATCH /workspaces/{workspace_id}/tasks/{task_id}
# ============================================================================


class TestUpdateTask:
    """Tests for update task endpoint."""

    async def test_update_task_success(
        self,
        task_client: AsyncClient,
        workspace_id: str,
        task_id: str,
        mock_service: AsyncMock,
        mock_task: Task,
        mock_workspace: MagicMock,
    ) -> None:
        """Updates task successfully."""
        mock_task.title = "Updated Title"
        mock_service.update_task.return_value = mock_task

        with patch(_RESOLVE_WORKSPACE_PATH, return_value=mock_workspace):
            response = await task_client.patch(
                f"/api/v1/workspaces/{workspace_id}/tasks/{task_id}",
                json={"title": "Updated Title"},
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["title"] == "Updated Title"

    async def test_update_task_not_found(
        self,
        task_client: AsyncClient,
        workspace_id: str,
        task_id: str,
        mock_service: AsyncMock,
        mock_workspace: MagicMock,
    ) -> None:
        """Returns 404 if task not found."""
        mock_service.update_task.side_effect = NotFoundError("Task not found")

        with patch(_RESOLVE_WORKSPACE_PATH, return_value=mock_workspace):
            response = await task_client.patch(
                f"/api/v1/workspaces/{workspace_id}/tasks/{task_id}",
                json={"title": "Updated"},
            )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_update_task_clear_fields(
        self,
        task_client: AsyncClient,
        workspace_id: str,
        task_id: str,
        mock_service: AsyncMock,
        mock_task: Task,
        mock_workspace: MagicMock,
    ) -> None:
        """Clears fields when clear flags set."""
        mock_task.description = None
        mock_service.update_task.return_value = mock_task

        with patch(_RESOLVE_WORKSPACE_PATH, return_value=mock_workspace):
            response = await task_client.patch(
                f"/api/v1/workspaces/{workspace_id}/tasks/{task_id}",
                json={"clearDescription": True},
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["description"] is None


# ============================================================================
# DELETE /workspaces/{workspace_id}/tasks/{task_id}
# ============================================================================


class TestDeleteTask:
    """Tests for delete task endpoint."""

    async def test_delete_task_success(
        self,
        task_client: AsyncClient,
        workspace_id: str,
        task_id: str,
        mock_service: AsyncMock,
        mock_workspace: MagicMock,
    ) -> None:
        """Deletes task successfully."""
        mock_service.delete_task.return_value = None

        with patch(_RESOLVE_WORKSPACE_PATH, return_value=mock_workspace):
            response = await task_client.delete(
                f"/api/v1/workspaces/{workspace_id}/tasks/{task_id}"
            )

        assert response.status_code == status.HTTP_204_NO_CONTENT

    async def test_delete_task_not_found(
        self,
        task_client: AsyncClient,
        workspace_id: str,
        task_id: str,
        mock_service: AsyncMock,
        mock_workspace: MagicMock,
    ) -> None:
        """Returns 404 if task not found."""
        mock_service.delete_task.side_effect = NotFoundError("Task not found")

        with patch(_RESOLVE_WORKSPACE_PATH, return_value=mock_workspace):
            response = await task_client.delete(
                f"/api/v1/workspaces/{workspace_id}/tasks/{task_id}"
            )

        assert response.status_code == status.HTTP_404_NOT_FOUND
