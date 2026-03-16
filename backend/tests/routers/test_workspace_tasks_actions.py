"""Unit tests for workspace task management API router (Action operations).

Tests action endpoints: status update, reorder, export tests.
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
# PATCH /workspaces/{workspace_id}/tasks/{task_id}/status
# ============================================================================


class TestUpdateTaskStatus:
    """Tests for update task status endpoint."""

    async def test_update_status_success(
        self,
        task_client: AsyncClient,
        workspace_id: str,
        task_id: str,
        mock_service: AsyncMock,
        mock_task: Task,
        mock_workspace: MagicMock,
    ) -> None:
        """Updates task status successfully."""
        mock_task.status = TaskStatus.IN_PROGRESS
        mock_service.update_status.return_value = mock_task

        with patch(_RESOLVE_WORKSPACE_PATH, return_value=mock_workspace):
            response = await task_client.patch(
                f"/api/v1/workspaces/{workspace_id}/tasks/{task_id}/status",
                json={"status": "in_progress"},
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "in_progress"

    async def test_update_status_task_not_found(
        self,
        task_client: AsyncClient,
        workspace_id: str,
        task_id: str,
        mock_service: AsyncMock,
        mock_workspace: MagicMock,
    ) -> None:
        """Returns 400 if task not found (status endpoint uses 400 for ValueError)."""
        mock_service.update_status.side_effect = ValueError("Task not found")

        with patch(_RESOLVE_WORKSPACE_PATH, return_value=mock_workspace):
            response = await task_client.patch(
                f"/api/v1/workspaces/{workspace_id}/tasks/{task_id}/status",
                json={"status": "in_progress"},
            )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    async def test_update_status_validation_error(
        self,
        task_client: AsyncClient,
        workspace_id: str,
        task_id: str,
    ) -> None:
        """Returns 422 for invalid status value."""
        response = await task_client.patch(
            f"/api/v1/workspaces/{workspace_id}/tasks/{task_id}/status",
            json={"status": "not_a_valid_status"},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ============================================================================
# PUT /workspaces/{workspace_id}/issues/{issue_id}/tasks/reorder
# ============================================================================


class TestReorderTasks:
    """Tests for reorder tasks endpoint."""

    async def test_reorder_tasks_success(
        self,
        task_client: AsyncClient,
        workspace_id: str,
        issue_id: str,
        mock_service: AsyncMock,
        mock_task: Task,
        mock_workspace: MagicMock,
    ) -> None:
        """Reorders tasks successfully."""
        task2 = Task(
            id=uuid4(),
            workspace_id=mock_task.workspace_id,
            issue_id=mock_task.issue_id,
            title="Task 2",
            status=TaskStatus.TODO,
            sort_order=1,
            ai_generated=False,
            created_at=datetime.now(tz=UTC),
            updated_at=datetime.now(tz=UTC),
        )
        mock_service.reorder_tasks.return_value = [task2, mock_task]

        task1_id = str(uuid4())
        task2_id = str(uuid4())

        with patch(_RESOLVE_WORKSPACE_PATH, return_value=mock_workspace):
            response = await task_client.put(
                f"/api/v1/workspaces/{workspace_id}/issues/{issue_id}/tasks/reorder",
                json={"taskIds": [task2_id, task1_id]},
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["tasks"]) == 2
        assert "completionPercent" in data

    async def test_reorder_tasks_invalid_task_id(
        self,
        task_client: AsyncClient,
        workspace_id: str,
        issue_id: str,
        mock_service: AsyncMock,
        mock_workspace: MagicMock,
    ) -> None:
        """Returns 400 if task ID not in issue."""
        mock_service.reorder_tasks.side_effect = ValueError("Task not found for issue")

        with patch(_RESOLVE_WORKSPACE_PATH, return_value=mock_workspace):
            response = await task_client.put(
                f"/api/v1/workspaces/{workspace_id}/issues/{issue_id}/tasks/reorder",
                json={"taskIds": [str(uuid4())]},
            )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    async def test_reorder_tasks_empty_list(
        self,
        task_client: AsyncClient,
        workspace_id: str,
        issue_id: str,
    ) -> None:
        """Returns 422 for empty task list."""
        response = await task_client.put(
            f"/api/v1/workspaces/{workspace_id}/issues/{issue_id}/tasks/reorder",
            json={"taskIds": []},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ============================================================================
# GET /workspaces/{workspace_id}/issues/{issue_id}/context/export
# ============================================================================


class TestExportContext:
    """Tests for export context endpoint."""

    async def test_export_context_markdown_format(
        self,
        task_client: AsyncClient,
        workspace_id: str,
        issue_id: str,
        mock_service: AsyncMock,
        mock_workspace: MagicMock,
    ) -> None:
        """Exports context in markdown format."""
        mock_service.export_context.return_value = {
            "content": "# Issue Context\n\nContent here",
            "format": "markdown",
            "generated_at": datetime.now(tz=UTC),
            "stats": {"tasks": 3, "completed": 1},
        }

        with patch(_RESOLVE_WORKSPACE_PATH, return_value=mock_workspace):
            response = await task_client.get(
                f"/api/v1/workspaces/{workspace_id}/issues/{issue_id}/context/export"
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["format"] == "markdown"
        assert "# Issue Context" in data["content"]
        assert data["stats"]["tasks"] == 3

    async def test_export_context_claude_code_format(
        self,
        task_client: AsyncClient,
        workspace_id: str,
        issue_id: str,
        mock_service: AsyncMock,
        mock_workspace: MagicMock,
    ) -> None:
        """Exports context in claude_code format."""
        mock_service.export_context.return_value = {
            "content": "## Context\n\nClaude-optimized content",
            "format": "claude_code",
            "generated_at": datetime.now(tz=UTC),
            "stats": {"tasks": 2, "completed": 0},
        }

        with patch(_RESOLVE_WORKSPACE_PATH, return_value=mock_workspace):
            response = await task_client.get(
                f"/api/v1/workspaces/{workspace_id}/issues/{issue_id}/context/export?format=claude_code"
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["format"] == "claude_code"

    async def test_export_context_task_list_format(
        self,
        task_client: AsyncClient,
        workspace_id: str,
        issue_id: str,
        mock_service: AsyncMock,
        mock_workspace: MagicMock,
    ) -> None:
        """Exports context in task_list format."""
        mock_service.export_context.return_value = {
            "content": "# Task List\n\n## Task 1",
            "format": "task_list",
            "generated_at": datetime.now(tz=UTC),
            "stats": {"tasks": 1, "completed": 0},
        }

        with patch(_RESOLVE_WORKSPACE_PATH, return_value=mock_workspace):
            response = await task_client.get(
                f"/api/v1/workspaces/{workspace_id}/issues/{issue_id}/context/export?format=task_list"
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["format"] == "task_list"

    async def test_export_context_issue_not_found(
        self,
        task_client: AsyncClient,
        workspace_id: str,
        issue_id: str,
        mock_service: AsyncMock,
        mock_workspace: MagicMock,
    ) -> None:
        """Returns 404 if issue not found."""
        mock_service.export_context.side_effect = ValueError("Issue not found")

        with patch(_RESOLVE_WORKSPACE_PATH, return_value=mock_workspace):
            response = await task_client.get(
                f"/api/v1/workspaces/{workspace_id}/issues/{issue_id}/context/export"
            )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_export_context_invalid_format(
        self,
        task_client: AsyncClient,
        workspace_id: str,
        issue_id: str,
    ) -> None:
        """Returns 422 for invalid format parameter."""
        response = await task_client.get(
            f"/api/v1/workspaces/{workspace_id}/issues/{issue_id}/context/export?format=invalid"
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
