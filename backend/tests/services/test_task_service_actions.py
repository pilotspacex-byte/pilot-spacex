"""Unit tests for TaskService (Action operations).

Tests action operations: status update, reorder, decompose, export.
Uses mock repositories for service-layer isolation.

Source: 013-task-management, Phase 1.8
"""

from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest

from pilot_space.application.services.task_service import TaskService
from pilot_space.infrastructure.database.models import Issue
from pilot_space.infrastructure.database.models.task import Task, TaskStatus

pytestmark = pytest.mark.asyncio


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def workspace_id() -> UUID:
    """Workspace ID for tests."""
    return uuid4()


@pytest.fixture
def issue_id() -> UUID:
    """Issue ID for tests."""
    return uuid4()


@pytest.fixture
def mock_issue(workspace_id: UUID, issue_id: UUID) -> Issue:
    """Mock Issue for validation."""
    from pilot_space.infrastructure.database.models import Project

    # Create a real Project instance instead of MagicMock to avoid SQLAlchemy descriptor issues
    project = Project(
        id=uuid4(),
        workspace_id=workspace_id,
        name="Test Project",
        identifier="PS",
    )

    issue = Issue(
        id=issue_id,
        workspace_id=workspace_id,
        project_id=project.id,
        sequence_id=42,
        name="Test Issue",
        state_id=uuid4(),
        reporter_id=uuid4(),
    )
    # Use object.__setattr__ to bypass SQLAlchemy descriptor and avoid _sa_instance_state errors
    object.__setattr__(issue, "project", project)
    issue.description = "Test description"
    return issue


@pytest.fixture
def mock_task(workspace_id: UUID, issue_id: UUID) -> Task:
    """Mock Task for tests."""
    return Task(
        id=uuid4(),
        workspace_id=workspace_id,
        issue_id=issue_id,
        title="Test Task",
        description="Task description",
        status=TaskStatus.TODO,
        sort_order=0,
        ai_generated=False,
    )


@pytest.fixture
def mock_session() -> AsyncMock:
    """Mock AsyncSession."""
    return AsyncMock()


@pytest.fixture
def mock_task_repo() -> AsyncMock:
    """Mock TaskRepository."""
    return AsyncMock()


@pytest.fixture
def mock_issue_repo() -> AsyncMock:
    """Mock IssueRepository."""
    return AsyncMock()


@pytest.fixture
def task_service(
    mock_session: AsyncMock,
    mock_task_repo: AsyncMock,
    mock_issue_repo: AsyncMock,
) -> TaskService:
    """TaskService with mocked dependencies."""
    return TaskService(
        session=mock_session,
        task_repository=mock_task_repo,
        issue_repository=mock_issue_repo,
    )


# ============================================================================
# update_status Tests
# ============================================================================


class TestUpdateStatus:
    """Tests for update_status()."""

    async def test_update_status_todo_to_in_progress(
        self,
        task_service: TaskService,
        mock_task_repo: AsyncMock,
        workspace_id: UUID,
        mock_task: Task,
    ) -> None:
        """Updates status from todo to in_progress."""
        mock_task.status = TaskStatus.TODO
        mock_task_repo.get_by_id.return_value = mock_task
        mock_task_repo.update.return_value = mock_task

        result = await task_service.update_status(mock_task.id, workspace_id, "in_progress")

        assert result.status == TaskStatus.IN_PROGRESS

    async def test_update_status_in_progress_to_done(
        self,
        task_service: TaskService,
        mock_task_repo: AsyncMock,
        workspace_id: UUID,
        mock_task: Task,
    ) -> None:
        """Updates status from in_progress to done."""
        mock_task.status = TaskStatus.IN_PROGRESS
        mock_task_repo.get_by_id.return_value = mock_task
        mock_task_repo.update.return_value = mock_task

        result = await task_service.update_status(mock_task.id, workspace_id, "done")

        assert result.status == TaskStatus.DONE

    async def test_update_status_done_to_todo_reopen(
        self,
        task_service: TaskService,
        mock_task_repo: AsyncMock,
        workspace_id: UUID,
        mock_task: Task,
    ) -> None:
        """Reopens completed task by changing done to todo."""
        mock_task.status = TaskStatus.DONE
        mock_task_repo.get_by_id.return_value = mock_task
        mock_task_repo.update.return_value = mock_task

        result = await task_service.update_status(mock_task.id, workspace_id, "todo")

        assert result.status == TaskStatus.TODO

    async def test_update_status_invalid_status(
        self,
        task_service: TaskService,
        mock_task_repo: AsyncMock,
        workspace_id: UUID,
        mock_task: Task,
    ) -> None:
        """Raises ValueError for invalid status."""
        mock_task_repo.get_by_id.return_value = mock_task

        with pytest.raises(ValueError, match="Invalid status"):
            await task_service.update_status(mock_task.id, workspace_id, "invalid_status")

    async def test_update_status_task_not_found(
        self,
        task_service: TaskService,
        mock_task_repo: AsyncMock,
        workspace_id: UUID,
    ) -> None:
        """Raises ValueError if task not found."""
        mock_task_repo.get_by_id.return_value = None

        with pytest.raises(ValueError, match="not found"):
            await task_service.update_status(uuid4(), workspace_id, "done")


# ============================================================================
# reorder_tasks Tests
# ============================================================================


class TestReorderTasks:
    """Tests for reorder_tasks()."""

    async def test_reorder_tasks_valid_order(
        self,
        task_service: TaskService,
        mock_task_repo: AsyncMock,
        workspace_id: UUID,
        issue_id: UUID,
    ) -> None:
        """Reorders tasks successfully."""
        task1_id = uuid4()
        task2_id = uuid4()
        task3_id = uuid4()

        existing_tasks = [
            Task(
                id=task1_id,
                issue_id=issue_id,
                workspace_id=workspace_id,
                title="T1",
                status=TaskStatus.TODO,
                sort_order=0,
                ai_generated=False,
            ),
            Task(
                id=task2_id,
                issue_id=issue_id,
                workspace_id=workspace_id,
                title="T2",
                status=TaskStatus.TODO,
                sort_order=1,
                ai_generated=False,
            ),
            Task(
                id=task3_id,
                issue_id=issue_id,
                workspace_id=workspace_id,
                title="T3",
                status=TaskStatus.TODO,
                sort_order=2,
                ai_generated=False,
            ),
        ]

        reordered_tasks = [
            existing_tasks[2],
            existing_tasks[0],
            existing_tasks[1],
        ]

        mock_task_repo.list_by_issue.side_effect = [
            existing_tasks,
            reordered_tasks,
        ]

        new_order = [task3_id, task1_id, task2_id]
        result = await task_service.reorder_tasks(issue_id, workspace_id, new_order)

        assert len(result) == 3
        mock_task_repo.bulk_update_order.assert_awaited_once_with(issue_id, new_order)

    async def test_reorder_tasks_invalid_task_id(
        self,
        task_service: TaskService,
        mock_task_repo: AsyncMock,
        workspace_id: UUID,
        issue_id: UUID,
    ) -> None:
        """Raises ValueError if task ID not in issue."""
        task1_id = uuid4()
        existing_tasks = [
            Task(
                id=task1_id,
                issue_id=issue_id,
                workspace_id=workspace_id,
                title="T1",
                status=TaskStatus.TODO,
                sort_order=0,
                ai_generated=False,
            ),
        ]

        mock_task_repo.list_by_issue.return_value = existing_tasks

        invalid_id = uuid4()
        with pytest.raises(ValueError, match="not found for issue"):
            await task_service.reorder_tasks(issue_id, workspace_id, [task1_id, invalid_id])


# ============================================================================
# export_context Tests
# ============================================================================


class TestExportContext:
    """Tests for export_context()."""

    async def test_export_context_markdown_format(
        self,
        task_service: TaskService,
        mock_task_repo: AsyncMock,
        mock_issue_repo: AsyncMock,
        workspace_id: UUID,
        issue_id: UUID,
        mock_issue: Issue,
        mock_task: Task,
    ) -> None:
        """Exports context in markdown format."""
        mock_issue_repo.get_by_id.return_value = mock_issue

        task2 = Task(
            id=uuid4(),
            workspace_id=workspace_id,
            issue_id=issue_id,
            title="Task 2",
            status=TaskStatus.DONE,
            sort_order=1,
            ai_generated=False,
        )
        mock_task_repo.list_by_issue.return_value = [mock_task, task2]

        result = await task_service.export_context(issue_id, workspace_id, "markdown")

        assert result["format"] == "markdown"
        assert "PS-42" in result["content"]
        assert "Test Issue" in result["content"]
        assert result["stats"]["tasks"] == 2
        assert result["stats"]["completed"] == 1

    async def test_export_context_claude_code_format(
        self,
        task_service: TaskService,
        mock_task_repo: AsyncMock,
        mock_issue_repo: AsyncMock,
        workspace_id: UUID,
        issue_id: UUID,
        mock_issue: Issue,
        mock_task: Task,
    ) -> None:
        """Exports context in claude_code format."""
        # identifier is a computed property, already set by fixture (PS-42)
        mock_issue.name = "Test Issue"
        mock_issue.description = "Issue description"
        mock_issue_repo.get_by_id.return_value = mock_issue
        mock_task.ai_prompt = "Implement X"
        mock_task_repo.list_by_issue.return_value = [mock_task]

        result = await task_service.export_context(issue_id, workspace_id, "claude_code")

        assert result["format"] == "claude_code"
        assert "## Context" in result["content"]
        assert "## Constraints" in result["content"]

    async def test_export_context_task_list_format(
        self,
        task_service: TaskService,
        mock_task_repo: AsyncMock,
        mock_issue_repo: AsyncMock,
        workspace_id: UUID,
        issue_id: UUID,
        mock_issue: Issue,
        mock_task: Task,
    ) -> None:
        """Exports context in task_list format."""
        # identifier is a computed property, already set by fixture (PS-42)
        mock_issue_repo.get_by_id.return_value = mock_issue
        mock_task.code_references = [{"file": "main.py"}]
        mock_task_repo.list_by_issue.return_value = [mock_task]

        result = await task_service.export_context(issue_id, workspace_id, "task_list")

        assert result["format"] == "task_list"
        assert "# Task List:" in result["content"]
        assert "main.py" in result["content"]

    async def test_export_context_issue_not_found(
        self,
        task_service: TaskService,
        mock_issue_repo: AsyncMock,
        workspace_id: UUID,
        issue_id: UUID,
    ) -> None:
        """Raises ValueError if issue not found."""
        mock_issue_repo.get_by_id.return_value = None

        with pytest.raises(ValueError, match="not found"):
            await task_service.export_context(issue_id, workspace_id, "markdown")

    async def test_export_context_validates_workspace(
        self,
        task_service: TaskService,
        mock_issue_repo: AsyncMock,
        workspace_id: UUID,
        issue_id: UUID,
        mock_issue: Issue,
    ) -> None:
        """Raises ValueError if workspace mismatch."""
        mock_issue.workspace_id = uuid4()
        mock_issue_repo.get_by_id.return_value = mock_issue

        with pytest.raises(ValueError, match="does not belong to workspace"):
            await task_service.export_context(issue_id, workspace_id, "markdown")
