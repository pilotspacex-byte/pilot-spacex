"""Unit tests for project MCP tools.

Tests for 5 project tools (PR-001 to PR-005) that AI agents use
to query and manipulate projects during conversations.

Uses mock-based patterns (MagicMock/AsyncMock for db_session
and ToolContext). _capture_project_tools intercepts SDK tool
closures from the server factory for handler execution tests.
"""

from __future__ import annotations

import asyncio
import json
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

if TYPE_CHECKING:
    from pilot_space.ai.tools.mcp_server import ToolContext


# Fixtures


@pytest.fixture
def workspace_id() -> str:
    """Workspace UUID string."""
    return str(uuid4())


@pytest.fixture
def user_id() -> str:
    """User UUID string."""
    return str(uuid4())


@pytest.fixture
def mock_tool_context(workspace_id: str, user_id: str) -> ToolContext:
    """Mock ToolContext with session and IDs."""
    from pilot_space.ai.tools.mcp_server import ToolContext

    mock_session = MagicMock()
    mock_session.execute = AsyncMock()
    return ToolContext(
        db_session=mock_session,
        workspace_id=workspace_id,
        user_id=user_id,
    )


def _capture_project_tools(
    event_queue: asyncio.Queue[str],
    tool_context: ToolContext | None = None,
) -> dict[str, object]:
    """Create project server and capture SdkMcpTool objects by name."""
    from pilot_space.ai.mcp import project_server as module

    captured: dict[str, object] = {}
    original_create = module.create_sdk_mcp_server

    def _intercept_create(*, name: str, version: str, tools: list[object]):
        captured["tools"] = {t.name: t for t in tools}  # type: ignore[attr-defined]
        return original_create(name=name, version=version, tools=tools)

    with patch.object(module, "create_sdk_mcp_server", side_effect=_intercept_create):
        module.create_project_tools_server(event_queue=event_queue, tool_context=tool_context)

    return captured["tools"]  # type: ignore[return-value]


# Test Classes


class TestServerConfiguration:
    """Test suite for server configuration and tool registration."""

    def test_server_name_constant(self) -> None:
        """Verify SERVER_NAME is correct."""
        from pilot_space.ai.mcp.project_server import SERVER_NAME

        assert SERVER_NAME == "pilot-projects"

    def test_tool_names_list(self) -> None:
        """Verify TOOL_NAMES contains all 5 tools."""
        from pilot_space.ai.mcp.project_server import TOOL_NAMES

        assert len(TOOL_NAMES) == 5

        expected_tools = [
            "mcp__pilot-projects__get_project",
            "mcp__pilot-projects__search_projects",
            "mcp__pilot-projects__create_project",
            "mcp__pilot-projects__update_project",
            "mcp__pilot-projects__update_project_settings",
        ]
        for tool_name in expected_tools:
            assert tool_name in TOOL_NAMES, f"{tool_name} not in TOOL_NAMES"

    def test_server_requires_tool_context(self) -> None:
        """Verify server raises error without tool_context."""
        from pilot_space.ai.mcp.project_server import create_project_tools_server

        event_queue = asyncio.Queue()

        with pytest.raises(ValueError, match="ToolContext is required"):
            create_project_tools_server(event_queue=event_queue, tool_context=None)

    def test_server_creation_success(
        self,
        mock_tool_context: ToolContext,
    ) -> None:
        """Verify server can be created with valid tool_context."""
        from pilot_space.ai.mcp.project_server import create_project_tools_server

        event_queue = asyncio.Queue()
        server = create_project_tools_server(
            event_queue=event_queue,
            tool_context=mock_tool_context,
        )

        # Server should be a dict with type, name, and instance
        assert isinstance(server, dict)
        assert server["type"] == "sdk"
        assert server["name"] == "pilot-projects"
        assert "instance" in server

    def test_identifier_pattern_validation(self) -> None:
        """Verify identifier pattern regex is correct."""
        from pilot_space.ai.mcp.project_server import _IDENTIFIER_PATTERN

        # Valid identifiers
        assert _IDENTIFIER_PATTERN.match("AB")
        assert _IDENTIFIER_PATTERN.match("PILOT")
        assert _IDENTIFIER_PATTERN.match("ABCDEFGHIJ")

        # Invalid identifiers
        assert not _IDENTIFIER_PATTERN.match("A")  # Too short
        assert not _IDENTIFIER_PATTERN.match("ABCDEFGHIJK")  # Too long
        assert not _IDENTIFIER_PATTERN.match("abc")  # Lowercase
        assert not _IDENTIFIER_PATTERN.match("AB1")  # Contains number
        assert not _IDENTIFIER_PATTERN.match("AB-CD")  # Contains hyphen


class TestGetProject:
    """Test suite for get_project tool (PR-001)."""

    def test_tool_registered_in_approval_map(self) -> None:
        """Verify get_project is in approval map as AUTO_EXECUTE."""
        from pilot_space.ai.tools.mcp_server import TOOL_APPROVAL_MAP, ToolApprovalLevel

        assert "get_project" in TOOL_APPROVAL_MAP
        assert TOOL_APPROVAL_MAP["get_project"] == ToolApprovalLevel.AUTO_EXECUTE


# ---------------------------------------------------------------------------
# Handler execution tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestGetProjectHandler:
    """Test get_project handler execution."""

    async def test_get_project_not_found(
        self,
        mock_tool_context: ToolContext,
    ) -> None:
        """get_project returns error for invalid UUID."""
        queue: asyncio.Queue[str] = asyncio.Queue()
        tools = _capture_project_tools(queue, tool_context=mock_tool_context)
        tool = tools["get_project"]

        result = await tool.handler({"project_id": "not-a-uuid"})  # type: ignore[attr-defined]

        text = result["content"][0]["text"]
        assert "Error" in text

    async def test_get_project_invalid_identifier(
        self,
        mock_tool_context: ToolContext,
    ) -> None:
        """get_project returns error for invalid identifier format."""
        queue: asyncio.Queue[str] = asyncio.Queue()
        tools = _capture_project_tools(queue, tool_context=mock_tool_context)
        tool = tools["get_project"]

        result = await tool.handler({"project_id": "ab"})  # type: ignore[attr-defined]

        text = result["content"][0]["text"]
        assert "Error" in text


@pytest.mark.asyncio
class TestCreateProjectHandler:
    """Test create_project handler execution."""

    async def test_create_project_missing_name(
        self,
        mock_tool_context: ToolContext,
    ) -> None:
        """create_project rejects empty name."""
        queue: asyncio.Queue[str] = asyncio.Queue()
        tools = _capture_project_tools(queue, tool_context=mock_tool_context)
        tool = tools["create_project"]

        result = await tool.handler(  # type: ignore[attr-defined]
            {"name": "   ", "identifier": "TEST"}
        )

        text = result["content"][0]["text"]
        assert "cannot be empty" in text.lower() or "Error" in text

    async def test_create_project_invalid_identifier(
        self,
        mock_tool_context: ToolContext,
    ) -> None:
        """create_project rejects invalid identifier format."""
        queue: asyncio.Queue[str] = asyncio.Queue()
        tools = _capture_project_tools(queue, tool_context=mock_tool_context)
        tool = tools["create_project"]

        result = await tool.handler(  # type: ignore[attr-defined]
            {"name": "My Project", "identifier": "a"}
        )

        text = result["content"][0]["text"]
        assert "Error" in text or "invalid" in text.lower()

    async def test_create_project_emits_approval_event(
        self,
        mock_tool_context: ToolContext,
    ) -> None:
        """create_project pushes approval_request SSE event when identifier valid."""
        queue: asyncio.Queue[str] = asyncio.Queue()
        tools = _capture_project_tools(queue, tool_context=mock_tool_context)
        tool = tools["create_project"]

        # Mock identifier_exists to return False (available)
        mock_repo = MagicMock()
        mock_repo.identifier_exists = AsyncMock(return_value=False)

        with patch(
            "pilot_space.infrastructure.database.repositories.project_repository.ProjectRepository",
            return_value=mock_repo,
        ):
            result = await tool.handler(  # type: ignore[attr-defined]
                {"name": "New Project", "identifier": "NEWPROJ"}
            )

        text = result["content"][0]["text"]
        assert "Approval required" in text

        # Verify SSE event
        assert not queue.empty()
        event = await queue.get()
        event_data = json.loads(event.split("data: ")[1].strip())
        assert event_data["operation"] == "create_project"
        assert event_data["approval_level"] == "require_approval"


class TestSearchProjects:
    """Test suite for search_projects tool (PR-002)."""

    def test_tool_registered_in_approval_map(self) -> None:
        """Verify search_projects is in approval map as AUTO_EXECUTE."""
        from pilot_space.ai.tools.mcp_server import TOOL_APPROVAL_MAP, ToolApprovalLevel

        assert "search_projects" in TOOL_APPROVAL_MAP
        assert TOOL_APPROVAL_MAP["search_projects"] == ToolApprovalLevel.AUTO_EXECUTE


class TestCreateProject:
    """Test suite for create_project tool (PR-003)."""

    def test_tool_registered_in_approval_map(self) -> None:
        """Verify create_project is in approval map as REQUIRE_APPROVAL."""
        from pilot_space.ai.tools.mcp_server import TOOL_APPROVAL_MAP, ToolApprovalLevel

        assert "create_project" in TOOL_APPROVAL_MAP
        assert TOOL_APPROVAL_MAP["create_project"] == ToolApprovalLevel.REQUIRE_APPROVAL


class TestUpdateProject:
    """Test suite for update_project tool (PR-004)."""

    def test_tool_registered_in_approval_map(self) -> None:
        """Verify update_project is in approval map as REQUIRE_APPROVAL."""
        from pilot_space.ai.tools.mcp_server import TOOL_APPROVAL_MAP, ToolApprovalLevel

        assert "update_project" in TOOL_APPROVAL_MAP
        assert TOOL_APPROVAL_MAP["update_project"] == ToolApprovalLevel.REQUIRE_APPROVAL


class TestUpdateProjectSettings:
    """Test suite for update_project_settings tool (PR-005)."""

    def test_tool_registered_in_approval_map(self) -> None:
        """Verify update_project_settings is in approval map as REQUIRE_APPROVAL."""
        from pilot_space.ai.tools.mcp_server import TOOL_APPROVAL_MAP, ToolApprovalLevel

        assert "update_project_settings" in TOOL_APPROVAL_MAP
        assert TOOL_APPROVAL_MAP["update_project_settings"] == ToolApprovalLevel.REQUIRE_APPROVAL


class TestToolCategoryRegistration:
    """Test suite for verifying all tools are registered in correct approval map."""

    def test_all_project_tools_in_approval_map(self) -> None:
        """Verify all 5 project tools are registered with correct approval levels."""
        from pilot_space.ai.tools.mcp_server import TOOL_APPROVAL_MAP, ToolApprovalLevel

        # Read-only tools (AUTO_EXECUTE)
        auto_execute_tools = ["get_project", "search_projects"]
        for tool_name in auto_execute_tools:
            assert tool_name in TOOL_APPROVAL_MAP
            assert TOOL_APPROVAL_MAP[tool_name] == ToolApprovalLevel.AUTO_EXECUTE

        # Mutation tools (REQUIRE_APPROVAL)
        require_approval_tools = [
            "create_project",
            "update_project",
            "update_project_settings",
        ]
        for tool_name in require_approval_tools:
            assert tool_name in TOOL_APPROVAL_MAP
            assert TOOL_APPROVAL_MAP[tool_name] == ToolApprovalLevel.REQUIRE_APPROVAL
