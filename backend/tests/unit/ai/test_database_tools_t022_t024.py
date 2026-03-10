"""Unit tests for database tools T022-T024.

Tests for:
- T022: get_workspace_members
- T024: get_cycle_context
"""

from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from pilot_space.ai.tools.database_tools import (
    get_cycle_context,
    get_workspace_members,
)
from pilot_space.ai.tools.mcp_server import ToolContext
from pilot_space.infrastructure.database.models.cycle import Cycle, CycleStatus
from pilot_space.infrastructure.database.models.issue import IssuePriority
from pilot_space.infrastructure.database.models.state import State, StateGroup
from pilot_space.infrastructure.database.models.user import User
from pilot_space.infrastructure.database.models.workspace_member import (
    WorkspaceMember,
    WorkspaceRole,
)


@pytest.fixture
def workspace_id() -> str:
    """Workspace ID for testing."""
    return str(uuid4())


@pytest.fixture
def user_id() -> str:
    """User ID for testing."""
    return str(uuid4())


@pytest.fixture
def tool_context(workspace_id: str, user_id: str) -> ToolContext:
    """Create a tool context for testing."""
    return ToolContext(
        db_session=AsyncMock(spec=AsyncSession),
        workspace_id=workspace_id,
        user_id=user_id,
    )


class TestGetWorkspaceMembers:
    """Test suite for get_workspace_members tool."""

    @pytest.mark.asyncio
    async def test_get_workspace_members_basic(
        self,
        tool_context: ToolContext,
        workspace_id: str,
    ) -> None:
        """Test basic workspace members retrieval."""
        # Arrange
        user1 = User(
            id=uuid4(),
            email="user1@example.com",
            full_name="User One",
        )
        user2 = User(
            id=uuid4(),
            email="user2@example.com",
            full_name="User Two",
        )

        member1 = WorkspaceMember(
            id=uuid4(),
            user_id=user1.id,
            workspace_id=UUID(workspace_id),
            role=WorkspaceRole.ADMIN,
        )
        member1.user = user1

        member2 = WorkspaceMember(
            id=uuid4(),
            user_id=user2.id,
            workspace_id=UUID(workspace_id),
            role=WorkspaceRole.MEMBER,
        )
        member2.user = user2

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [member1, member2]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        tool_context.db_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await get_workspace_members(ctx=tool_context)

        # Assert
        assert result["count"] == 2
        assert len(result["members"]) == 2
        assert result["members"][0]["email"] == "user1@example.com"
        assert result["members"][0]["role"] == "ADMIN"
        assert result["members"][1]["email"] == "user2@example.com"
        assert result["members"][1]["role"] == "MEMBER"

    @pytest.mark.asyncio
    async def test_get_workspace_members_empty(
        self,
        tool_context: ToolContext,
    ) -> None:
        """Test workspace members retrieval with no members."""
        # Arrange
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        tool_context.db_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await get_workspace_members(ctx=tool_context)

        # Assert
        assert result["count"] == 0
        assert result["members"] == []

    @pytest.mark.asyncio
    async def test_get_workspace_members_with_skills(
        self,
        tool_context: ToolContext,
        workspace_id: str,
    ) -> None:
        """Test workspace members retrieval with skills included."""
        # Arrange
        user1 = User(
            id=uuid4(),
            email="user1@example.com",
            full_name="User One",
        )
        user1.skills = ["Python", "FastAPI"]  # type: ignore[attr-defined]

        member1 = WorkspaceMember(
            id=uuid4(),
            user_id=user1.id,
            workspace_id=UUID(workspace_id),
            role=WorkspaceRole.ADMIN,
        )
        member1.user = user1

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [member1]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        tool_context.db_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await get_workspace_members(ctx=tool_context, include_skills=True)

        # Assert
        assert result["count"] == 1
        assert result["members"][0]["skills"] == ["Python", "FastAPI"]


class TestGetCycleContext:
    """Test suite for get_cycle_context tool."""

    @pytest.mark.asyncio
    async def test_get_cycle_context_basic(
        self,
        tool_context: ToolContext,
        workspace_id: str,
    ) -> None:
        """Test basic cycle context retrieval."""
        # Arrange
        cycle_id = uuid4()
        cycle = Cycle(
            id=cycle_id,
            workspace_id=UUID(workspace_id),
            project_id=uuid4(),
            name="Sprint 1",
            description="First sprint",
            status=CycleStatus.ACTIVE,
            start_date=date(2026, 1, 20),
            end_date=date(2026, 2, 3),
            sequence=1,
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = cycle
        tool_context.db_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await get_cycle_context(
            cycle_id=str(cycle_id),
            ctx=tool_context,
        )

        # Assert
        assert result["found"] is True
        assert result["cycle"]["name"] == "Sprint 1"
        assert result["cycle"]["description"] == "First sprint"
        assert result["cycle"]["status"] == "active"
        assert result["cycle"]["start_date"] == "2026-01-20"
        assert result["cycle"]["end_date"] == "2026-02-03"

    @pytest.mark.asyncio
    async def test_get_cycle_context_with_issues(
        self,
        tool_context: ToolContext,
        workspace_id: str,
    ) -> None:
        """Test cycle context with issues and metrics."""
        # Arrange
        cycle_id = uuid4()
        project_id = uuid4()

        # Create states
        completed_state = State(
            id=uuid4(),
            workspace_id=UUID(workspace_id),
            name="Done",
            group=StateGroup.COMPLETED,
            sequence=3,
        )
        in_progress_state = State(
            id=uuid4(),
            workspace_id=UUID(workspace_id),
            name="In Progress",
            group=StateGroup.STARTED,
            sequence=2,
        )

        # Create mock issues (using MagicMock to avoid Issue model constraints)
        issue1 = MagicMock()
        issue1.id = uuid4()
        issue1.identifier = "PILOT-1"
        issue1.name = "Issue 1"
        issue1.state = completed_state
        issue1.state_id = completed_state.id
        issue1.priority = IssuePriority.HIGH

        issue2 = MagicMock()
        issue2.id = uuid4()
        issue2.identifier = "PILOT-2"
        issue2.name = "Issue 2"
        issue2.state = in_progress_state
        issue2.state_id = in_progress_state.id
        issue2.priority = IssuePriority.MEDIUM

        cycle = Cycle(
            id=cycle_id,
            workspace_id=UUID(workspace_id),
            project_id=project_id,
            name="Sprint 1",
            description="First sprint",
            status=CycleStatus.ACTIVE,
            start_date=date(2026, 1, 20),
            end_date=date(2026, 2, 3),
            sequence=1,
        )
        cycle.issues = [issue1, issue2]

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = cycle
        tool_context.db_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await get_cycle_context(
            cycle_id=str(cycle_id),
            ctx=tool_context,
            include_issues=True,
        )

        # Assert
        assert result["found"] is True
        assert result["cycle"]["name"] == "Sprint 1"

        # Check metrics
        assert result["metrics"]["total_issues"] == 2
        assert result["metrics"]["completed_issues"] == 1
        assert result["metrics"]["progress_percent"] == 50.0

        # Check issues
        assert len(result["issues"]) == 2
        assert result["issues"][0]["identifier"] == "PILOT-1"
        assert result["issues"][0]["state"] == "Done"
        assert result["issues"][1]["identifier"] == "PILOT-2"
        assert result["issues"][1]["state"] == "In Progress"

    @pytest.mark.asyncio
    async def test_get_cycle_context_not_found(
        self,
        tool_context: ToolContext,
    ) -> None:
        """Test cycle context when cycle does not exist."""
        # Arrange
        cycle_id = uuid4()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        tool_context.db_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await get_cycle_context(
            cycle_id=str(cycle_id),
            ctx=tool_context,
        )

        # Assert
        assert result["found"] is False
        assert f"Cycle {cycle_id} not found" in result["error"]

    @pytest.mark.asyncio
    async def test_get_cycle_context_empty_issues(
        self,
        tool_context: ToolContext,
        workspace_id: str,
    ) -> None:
        """Test cycle context with no issues."""
        # Arrange
        cycle_id = uuid4()
        cycle = Cycle(
            id=cycle_id,
            workspace_id=UUID(workspace_id),
            project_id=uuid4(),
            name="Sprint 1",
            description="First sprint",
            status=CycleStatus.PLANNED,
            start_date=date(2026, 1, 20),
            end_date=date(2026, 2, 3),
            sequence=1,
        )
        cycle.issues = []

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = cycle
        tool_context.db_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await get_cycle_context(
            cycle_id=str(cycle_id),
            ctx=tool_context,
            include_issues=True,
        )

        # Assert
        assert result["found"] is True
        assert result["metrics"]["total_issues"] == 0
        assert result["metrics"]["completed_issues"] == 0
        assert result["metrics"]["progress_percent"] == 0
        assert result["issues"] == []
