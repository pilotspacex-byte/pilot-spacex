"""Unit tests for TaskService (CRUD operations).

Tests CRUD operations: list, create, update, delete.
Uses mock repositories for service-layer isolation.

Source: 013-task-management, Phase 1.8
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest

from pilot_space.application.services.task_service import (
    CreateTaskPayload,
    TaskService,
    UpdateTaskPayload,
)
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
# list_tasks Tests
# ============================================================================


class TestListTasks:
    """Tests for list_tasks()."""

    async def test_list_tasks_returns_tasks_and_stats(
        self,
        task_service: TaskService,
        mock_task_repo: AsyncMock,
        mock_issue_repo: AsyncMock,
        workspace_id: UUID,
        issue_id: UUID,
        mock_task: Task,
        mock_issue: Issue,
    ) -> None:
        """Returns tasks with progress statistics."""
        mock_issue_repo.get_by_id_scalar.return_value = mock_issue
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

        result = await task_service.list_tasks(issue_id, workspace_id)

        assert len(result["tasks"]) == 2
        assert result["total"] == 2
        assert result["completed"] == 1
        assert result["completion_percent"] == 50.0

    async def test_list_tasks_empty_result(
        self,
        task_service: TaskService,
        mock_task_repo: AsyncMock,
        mock_issue_repo: AsyncMock,
        workspace_id: UUID,
        issue_id: UUID,
        mock_issue: Issue,
    ) -> None:
        """Returns empty list for issue with no tasks."""
        mock_issue_repo.get_by_id_scalar.return_value = mock_issue
        mock_task_repo.list_by_issue.return_value = []

        result = await task_service.list_tasks(issue_id, workspace_id)

        assert result["tasks"] == []
        assert result["total"] == 0
        assert result["completed"] == 0
        assert result["completion_percent"] == 0.0

    async def test_list_tasks_calculates_completion_percent(
        self,
        task_service: TaskService,
        mock_task_repo: AsyncMock,
        mock_issue_repo: AsyncMock,
        workspace_id: UUID,
        issue_id: UUID,
        mock_issue: Issue,
    ) -> None:
        """Calculates completion percentage correctly."""
        mock_issue_repo.get_by_id_scalar.return_value = mock_issue
        tasks = [
            Task(
                id=uuid4(),
                workspace_id=workspace_id,
                issue_id=issue_id,
                title="T1",
                status=TaskStatus.DONE,
                sort_order=0,
                ai_generated=False,
            ),
            Task(
                id=uuid4(),
                workspace_id=workspace_id,
                issue_id=issue_id,
                title="T2",
                status=TaskStatus.DONE,
                sort_order=1,
                ai_generated=False,
            ),
            Task(
                id=uuid4(),
                workspace_id=workspace_id,
                issue_id=issue_id,
                title="T3",
                status=TaskStatus.TODO,
                sort_order=2,
                ai_generated=False,
            ),
        ]
        mock_task_repo.list_by_issue.return_value = tasks

        result = await task_service.list_tasks(issue_id, workspace_id)

        assert result["completion_percent"] == 66.7


# ============================================================================
# create_task Tests
# ============================================================================


class TestCreateTask:
    """Tests for create_task()."""

    async def test_create_task_success_with_all_fields(
        self,
        task_service: TaskService,
        mock_task_repo: AsyncMock,
        mock_issue_repo: AsyncMock,
        workspace_id: UUID,
        issue_id: UUID,
        mock_issue: Issue,
    ) -> None:
        """Creates task with all fields populated."""
        mock_issue_repo.get_by_id_scalar.return_value = mock_issue
        mock_task_repo.list_by_issue.return_value = []

        async def create_side_effect(task: Task) -> Task:
            task.id = uuid4()
            task.created_at = datetime.now(tz=UTC)
            task.updated_at = datetime.now(tz=UTC)
            return task

        mock_task_repo.create.side_effect = create_side_effect

        payload = CreateTaskPayload(
            workspace_id=workspace_id,
            issue_id=issue_id,
            title="New Task",
            description="Task description",
            acceptance_criteria=[{"text": "AC1", "done": False}],
            estimated_hours=5.0,
            code_references=[{"file": "main.py", "lines": "10-20"}],
            dependency_ids=["dep1"],
            ai_prompt="Implement feature X",
            ai_generated=True,
        )

        result = await task_service.create_task(payload)

        assert result.title == "New Task"
        assert result.description == "Task description"
        assert result.estimated_hours == 5.0
        assert result.ai_generated is True
        mock_task_repo.create.assert_awaited_once()

    async def test_create_task_minimal_fields(
        self,
        task_service: TaskService,
        mock_task_repo: AsyncMock,
        mock_issue_repo: AsyncMock,
        workspace_id: UUID,
        issue_id: UUID,
        mock_issue: Issue,
    ) -> None:
        """Creates task with minimal required fields."""
        mock_issue_repo.get_by_id_scalar.return_value = mock_issue
        mock_task_repo.list_by_issue.return_value = []

        async def create_side_effect(task: Task) -> Task:
            task.id = uuid4()
            return task

        mock_task_repo.create.side_effect = create_side_effect

        payload = CreateTaskPayload(
            workspace_id=workspace_id,
            issue_id=issue_id,
            title="Minimal Task",
        )

        result = await task_service.create_task(payload)

        assert result.title == "Minimal Task"
        assert result.description is None
        assert result.estimated_hours is None
        assert result.ai_generated is False

    async def test_create_task_validates_issue_exists(
        self,
        task_service: TaskService,
        mock_issue_repo: AsyncMock,
        workspace_id: UUID,
        issue_id: UUID,
    ) -> None:
        """Raises ValueError if issue does not exist."""
        mock_issue_repo.get_by_id_scalar.return_value = None

        payload = CreateTaskPayload(
            workspace_id=workspace_id,
            issue_id=issue_id,
            title="Task",
        )

        with pytest.raises(ValueError, match="not found"):
            await task_service.create_task(payload)

    async def test_create_task_validates_workspace_match(
        self,
        task_service: TaskService,
        mock_issue_repo: AsyncMock,
        workspace_id: UUID,
        issue_id: UUID,
        mock_issue: Issue,
    ) -> None:
        """Raises ValueError if issue workspace mismatch."""
        mock_issue.workspace_id = uuid4()
        mock_issue_repo.get_by_id_scalar.return_value = mock_issue

        payload = CreateTaskPayload(
            workspace_id=workspace_id,
            issue_id=issue_id,
            title="Task",
        )

        with pytest.raises(ValueError, match="does not belong to workspace"):
            await task_service.create_task(payload)

    async def test_create_task_assigns_next_sort_order(
        self,
        task_service: TaskService,
        mock_task_repo: AsyncMock,
        mock_issue_repo: AsyncMock,
        workspace_id: UUID,
        issue_id: UUID,
        mock_issue: Issue,
        mock_task: Task,
    ) -> None:
        """Assigns sort_order based on existing task count."""
        mock_issue_repo.get_by_id_scalar.return_value = mock_issue
        existing_tasks = [mock_task, mock_task, mock_task]
        mock_task_repo.list_by_issue.return_value = existing_tasks

        created_task: Task | None = None

        async def create_side_effect(task: Task) -> Task:
            nonlocal created_task
            created_task = task
            task.id = uuid4()
            return task

        mock_task_repo.create.side_effect = create_side_effect

        payload = CreateTaskPayload(
            workspace_id=workspace_id,
            issue_id=issue_id,
            title="Task",
        )

        await task_service.create_task(payload)

        assert created_task is not None
        assert created_task.sort_order == 3

    async def test_create_task_trims_title(
        self,
        task_service: TaskService,
        mock_task_repo: AsyncMock,
        mock_issue_repo: AsyncMock,
        workspace_id: UUID,
        issue_id: UUID,
        mock_issue: Issue,
    ) -> None:
        """Strips whitespace from title."""
        mock_issue_repo.get_by_id_scalar.return_value = mock_issue
        mock_task_repo.list_by_issue.return_value = []

        created_task: Task | None = None

        async def create_side_effect(task: Task) -> Task:
            nonlocal created_task
            created_task = task
            task.id = uuid4()
            return task

        mock_task_repo.create.side_effect = create_side_effect

        payload = CreateTaskPayload(
            workspace_id=workspace_id,
            issue_id=issue_id,
            title="  Whitespace Task  ",
        )

        await task_service.create_task(payload)

        assert created_task is not None
        assert created_task.title == "Whitespace Task"


# ============================================================================
# update_task Tests
# ============================================================================


class TestUpdateTask:
    """Tests for update_task()."""

    async def test_update_task_success(
        self,
        task_service: TaskService,
        mock_task_repo: AsyncMock,
        workspace_id: UUID,
        mock_task: Task,
    ) -> None:
        """Updates task fields successfully."""
        mock_task_repo.get_by_id.return_value = mock_task
        mock_task_repo.update.return_value = mock_task

        payload = UpdateTaskPayload(
            task_id=mock_task.id,
            workspace_id=workspace_id,
            title="Updated Title",
            description="Updated description",
        )

        result = await task_service.update_task(payload)

        assert result.title == "Updated Title"
        assert result.description == "Updated description"
        mock_task_repo.update.assert_awaited_once()

    async def test_update_task_not_found(
        self,
        task_service: TaskService,
        mock_task_repo: AsyncMock,
        workspace_id: UUID,
    ) -> None:
        """Raises ValueError if task not found."""
        mock_task_repo.get_by_id.return_value = None

        payload = UpdateTaskPayload(
            task_id=uuid4(),
            workspace_id=workspace_id,
        )

        with pytest.raises(ValueError, match="not found"):
            await task_service.update_task(payload)

    async def test_update_task_validates_workspace(
        self,
        task_service: TaskService,
        mock_task_repo: AsyncMock,
        workspace_id: UUID,
        mock_task: Task,
    ) -> None:
        """Raises ValueError if workspace mismatch."""
        mock_task.workspace_id = uuid4()
        mock_task_repo.get_by_id.return_value = mock_task

        payload = UpdateTaskPayload(
            task_id=mock_task.id,
            workspace_id=workspace_id,
        )

        with pytest.raises(ValueError, match="does not belong to workspace"):
            await task_service.update_task(payload)

    async def test_update_task_clears_description(
        self,
        task_service: TaskService,
        mock_task_repo: AsyncMock,
        workspace_id: UUID,
        mock_task: Task,
    ) -> None:
        """Clears description when clear_description=True."""
        mock_task.description = "Original description"
        mock_task_repo.get_by_id.return_value = mock_task
        mock_task_repo.update.return_value = mock_task

        payload = UpdateTaskPayload(
            task_id=mock_task.id,
            workspace_id=workspace_id,
            clear_description=True,
        )

        result = await task_service.update_task(payload)

        assert result.description is None

    async def test_update_task_clears_estimated_hours(
        self,
        task_service: TaskService,
        mock_task_repo: AsyncMock,
        workspace_id: UUID,
        mock_task: Task,
    ) -> None:
        """Clears estimated_hours when clear_estimated_hours=True."""
        mock_task.estimated_hours = 5.0
        mock_task_repo.get_by_id.return_value = mock_task
        mock_task_repo.update.return_value = mock_task

        payload = UpdateTaskPayload(
            task_id=mock_task.id,
            workspace_id=workspace_id,
            clear_estimated_hours=True,
        )

        result = await task_service.update_task(payload)

        assert result.estimated_hours is None

    async def test_update_task_clears_code_references(
        self,
        task_service: TaskService,
        mock_task_repo: AsyncMock,
        workspace_id: UUID,
        mock_task: Task,
    ) -> None:
        """Clears code_references when clear_code_references=True."""
        mock_task.code_references = [{"file": "test.py"}]
        mock_task_repo.get_by_id.return_value = mock_task
        mock_task_repo.update.return_value = mock_task

        payload = UpdateTaskPayload(
            task_id=mock_task.id,
            workspace_id=workspace_id,
            clear_code_references=True,
        )

        result = await task_service.update_task(payload)

        assert result.code_references is None

    async def test_update_task_partial_fields(
        self,
        task_service: TaskService,
        mock_task_repo: AsyncMock,
        workspace_id: UUID,
        mock_task: Task,
    ) -> None:
        """Updates only specified fields."""
        original_title = mock_task.title
        mock_task_repo.get_by_id.return_value = mock_task
        mock_task_repo.update.return_value = mock_task

        payload = UpdateTaskPayload(
            task_id=mock_task.id,
            workspace_id=workspace_id,
            estimated_hours=3.5,
        )

        result = await task_service.update_task(payload)

        assert result.title == original_title
        assert result.estimated_hours == 3.5


# ============================================================================
# delete_task Tests
# ============================================================================


class TestDeleteTask:
    """Tests for delete_task()."""

    async def test_delete_task_success(
        self,
        task_service: TaskService,
        mock_task_repo: AsyncMock,
        workspace_id: UUID,
        mock_task: Task,
    ) -> None:
        """Soft deletes task successfully."""
        mock_task_repo.get_by_id.return_value = mock_task

        await task_service.delete_task(mock_task.id, workspace_id)

        mock_task_repo.delete.assert_awaited_once_with(mock_task)

    async def test_delete_task_not_found(
        self,
        task_service: TaskService,
        mock_task_repo: AsyncMock,
        workspace_id: UUID,
    ) -> None:
        """Raises ValueError if task not found."""
        mock_task_repo.get_by_id.return_value = None

        with pytest.raises(ValueError, match="not found"):
            await task_service.delete_task(uuid4(), workspace_id)

    async def test_delete_task_validates_workspace(
        self,
        task_service: TaskService,
        mock_task_repo: AsyncMock,
        workspace_id: UUID,
        mock_task: Task,
    ) -> None:
        """Raises ValueError if workspace mismatch."""
        mock_task.workspace_id = uuid4()
        mock_task_repo.get_by_id.return_value = mock_task

        with pytest.raises(ValueError, match="does not belong to workspace"):
            await task_service.delete_task(mock_task.id, workspace_id)
