"""Unit tests for issue CRUD MCP tools (T010).

Tests for 4 CRUD tools (IS-001 to IS-004) in issue_server:
get_issue, search_issues, create_issue, update_issue.

Uses mock-based patterns with _capture_tools to intercept SDK tool closures.

Reference: spec 010-enhanced-mcp-tools Phase 3
"""

from __future__ import annotations

import asyncio
import json
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from pilot_space.ai.tools.entity_resolver import EntityResolutionError

if TYPE_CHECKING:
    from pilot_space.ai.tools.mcp_server import ToolContext


@pytest.fixture
def workspace_id() -> str:
    return str(uuid4())


@pytest.fixture
def user_id() -> str:
    return str(uuid4())


@pytest.fixture
def mock_tool_context(workspace_id: str, user_id: str) -> ToolContext:
    from pilot_space.ai.tools.mcp_server import ToolContext

    return ToolContext(db_session=MagicMock(), workspace_id=workspace_id, user_id=user_id)


@pytest.fixture
def event_queue() -> asyncio.Queue[str]:
    return asyncio.Queue()


def _capture_issue_tools(
    queue: asyncio.Queue[str],
    ctx: ToolContext | None = None,
) -> dict[str, Any]:
    from pilot_space.ai.mcp import issue_server as mod

    captured: dict[str, object] = {}
    orig = mod.create_sdk_mcp_server

    def intercept(*, name: str, version: str, tools: list[Any]) -> Any:
        captured["tools"] = {t.name: t for t in tools}
        return orig(name=name, version=version, tools=tools)

    with patch.object(mod, "create_sdk_mcp_server", side_effect=intercept):
        mod.create_issue_tools_server(queue, tool_context=ctx)
    return captured["tools"]


class TestIssueServerConfiguration:
    def test_server_name(self) -> None:
        from pilot_space.ai.mcp.issue_server import SERVER_NAME

        assert SERVER_NAME == "pilot-issues"

    def test_tool_names(self) -> None:
        from pilot_space.ai.mcp.issue_server import TOOL_NAMES

        assert len(TOOL_NAMES) == 4
        expected = [
            "mcp__pilot-issues__get_issue",
            "mcp__pilot-issues__search_issues",
            "mcp__pilot-issues__create_issue",
            "mcp__pilot-issues__update_issue",
        ]
        for name in expected:
            assert name in TOOL_NAMES

    def test_server_creation(self, mock_tool_context: ToolContext) -> None:
        from pilot_space.ai.mcp.issue_server import create_issue_tools_server

        server = create_issue_tools_server(asyncio.Queue(), tool_context=mock_tool_context)
        assert server["type"] == "sdk"
        assert server["name"] == "pilot-issues"

    def test_captured_tools(self, mock_tool_context: ToolContext) -> None:
        tools = _capture_issue_tools(asyncio.Queue(), mock_tool_context)
        assert set(tools.keys()) == {"get_issue", "search_issues", "create_issue", "update_issue"}


class TestGetIssueTool:
    def test_approval_level(self) -> None:
        from pilot_space.ai.tools.mcp_server import TOOL_APPROVAL_MAP, ToolApprovalLevel

        assert TOOL_APPROVAL_MAP["get_issue"] == ToolApprovalLevel.AUTO_EXECUTE

    @pytest.mark.asyncio
    async def test_without_context_returns_error(self) -> None:
        tools = _capture_issue_tools(asyncio.Queue(), ctx=None)
        result = await tools["get_issue"].handler({"issue_id": str(uuid4())})
        assert "Tool context not available" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_returns_issue_data(self, mock_tool_context: ToolContext) -> None:
        tools = _capture_issue_tools(asyncio.Queue(), mock_tool_context)
        issue_id = uuid4()

        mock_issue = MagicMock()
        mock_issue.id = issue_id
        mock_issue.workspace_id = UUID(mock_tool_context.workspace_id)
        mock_issue.sequence_id = 1
        mock_issue.name = "Test Issue"
        mock_issue.description = "desc"
        mock_issue.priority.value = "medium"
        mock_issue.estimate_points = 3
        mock_issue.start_date = None
        mock_issue.target_date = None
        mock_issue.created_at.isoformat.return_value = "2025-01-01T00:00:00"
        mock_issue.updated_at.isoformat.return_value = "2025-01-02T00:00:00"
        mock_issue.project.identifier = "PILOT"
        mock_issue.project.id = uuid4()
        mock_issue.project.name = "Test Project"
        mock_issue.state.id = uuid4()
        mock_issue.state.name = "Todo"
        mock_issue.state.group.value = "unstarted"
        mock_issue.assignee = None
        mock_issue.reporter.id = uuid4()
        mock_issue.reporter.full_name = "Test User"
        mock_issue.reporter.email = "test@example.com"
        mock_issue.sub_issues = []
        mock_issue.note_links = []

        repo = AsyncMock()
        repo.get_by_id_with_relations.return_value = mock_issue

        with (
            patch(
                "pilot_space.ai.mcp.issue_server.resolve_entity_id_strict", return_value=issue_id
            ),
            patch("pilot_space.ai.mcp.issue_server.IssueRepository", return_value=repo),
        ):
            result = await tools["get_issue"].handler({"issue_id": str(issue_id)})

        data = json.loads(result["content"][0]["text"])
        assert data["id"] == str(issue_id)
        assert data["identifier"] == "PILOT-1"
        assert data["priority"] == "medium"

    @pytest.mark.asyncio
    async def test_not_found(self, mock_tool_context: ToolContext) -> None:
        tools = _capture_issue_tools(asyncio.Queue(), mock_tool_context)
        repo = AsyncMock()
        repo.get_by_id_with_relations.return_value = None

        with (
            patch("pilot_space.ai.mcp.issue_server.resolve_entity_id_strict", return_value=uuid4()),
            patch("pilot_space.ai.mcp.issue_server.IssueRepository", return_value=repo),
        ):
            result = await tools["get_issue"].handler({"issue_id": str(uuid4())})

        assert "not found" in result["content"][0]["text"].lower()

    @pytest.mark.asyncio
    async def test_invalid_identifier(self, mock_tool_context: ToolContext) -> None:
        tools = _capture_issue_tools(asyncio.Queue(), mock_tool_context)
        with patch(
            "pilot_space.ai.mcp.issue_server.resolve_entity_id_strict",
            side_effect=EntityResolutionError("Invalid issue identifier"),
        ):
            result = await tools["get_issue"].handler({"issue_id": "INVALID"})
        assert "error" in result["content"][0]["text"].lower()


class TestSearchIssuesTool:
    def test_approval_level(self) -> None:
        from pilot_space.ai.tools.mcp_server import TOOL_APPROVAL_MAP, ToolApprovalLevel

        assert TOOL_APPROVAL_MAP["search_issues"] == ToolApprovalLevel.AUTO_EXECUTE

    @pytest.mark.asyncio
    async def test_without_context_returns_error(self) -> None:
        tools = _capture_issue_tools(asyncio.Queue(), ctx=None)
        result = await tools["search_issues"].handler({})
        assert "Error" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_returns_results(self, mock_tool_context: ToolContext) -> None:
        tools = _capture_issue_tools(asyncio.Queue(), mock_tool_context)

        mock_issue = MagicMock()
        mock_issue.id = uuid4()
        mock_issue.sequence_id = 1
        mock_issue.name = "Found Issue"
        mock_issue.priority.value = "high"
        mock_issue.state.name = "Todo"
        mock_issue.project.identifier = "PILOT"
        mock_issue.assignee = None

        page = MagicMock()
        page.items = [mock_issue]
        repo = AsyncMock()
        repo.get_workspace_issues.return_value = page

        with patch("pilot_space.ai.mcp.issue_server.IssueRepository", return_value=repo):
            result = await tools["search_issues"].handler({"query": "Found"})

        data = json.loads(result["content"][0]["text"])
        assert len(data) == 1
        assert data[0]["name"] == "Found Issue"
        assert data[0]["identifier"] == "PILOT-1"


class TestCreateIssueTool:
    def test_approval_level(self) -> None:
        from pilot_space.ai.tools.mcp_server import TOOL_APPROVAL_MAP, ToolApprovalLevel

        assert TOOL_APPROVAL_MAP["create_issue"] == ToolApprovalLevel.REQUIRE_APPROVAL

    @pytest.mark.asyncio
    async def test_returns_operation_payload(self, mock_tool_context: ToolContext) -> None:
        tools = _capture_issue_tools(asyncio.Queue(), mock_tool_context)
        project_uuid = uuid4()

        with patch(
            "pilot_space.ai.mcp.issue_server.resolve_entity_id_strict",
            return_value=project_uuid,
        ):
            result = await tools["create_issue"].handler(
                {
                    "project_id": "PILOT",
                    "title": "New Bug",
                    "priority": "high",
                }
            )

        data = json.loads(result["content"][0]["text"])
        assert data["status"] == "approval_required"
        assert data["operation"] == "create_issue"
        assert data["payload"]["title"] == "New Bug"
        assert data["payload"]["project_id"] == str(project_uuid)
        assert data["payload"]["priority"] == "high"

    @pytest.mark.asyncio
    async def test_includes_optional_fields(self, mock_tool_context: ToolContext) -> None:
        tools = _capture_issue_tools(asyncio.Queue(), mock_tool_context)
        project_uuid = uuid4()

        with patch(
            "pilot_space.ai.mcp.issue_server.resolve_entity_id_strict",
            return_value=project_uuid,
        ):
            result = await tools["create_issue"].handler(
                {
                    "project_id": str(project_uuid),
                    "title": "Full Issue",
                    "description": "Detailed",
                    "estimate_points": 5,
                    "target_date": "2025-12-31",
                }
            )

        data = json.loads(result["content"][0]["text"])
        assert data["payload"]["estimate_points"] == 5
        assert data["payload"]["target_date"] == "2025-12-31"

    @pytest.mark.asyncio
    async def test_invalid_project(self, mock_tool_context: ToolContext) -> None:
        tools = _capture_issue_tools(asyncio.Queue(), mock_tool_context)
        with patch(
            "pilot_space.ai.mcp.issue_server.resolve_entity_id_strict",
            side_effect=EntityResolutionError("Project 'INVALID' not found"),
        ):
            result = await tools["create_issue"].handler({"project_id": "INVALID", "title": "X"})
        assert "error" in result["content"][0]["text"].lower()


class TestUpdateIssueTool:
    def test_approval_level(self) -> None:
        from pilot_space.ai.tools.mcp_server import TOOL_APPROVAL_MAP, ToolApprovalLevel

        assert TOOL_APPROVAL_MAP["update_issue"] == ToolApprovalLevel.REQUIRE_APPROVAL

    @pytest.mark.asyncio
    async def test_returns_operation_payload(self, mock_tool_context: ToolContext) -> None:
        tools = _capture_issue_tools(asyncio.Queue(), mock_tool_context)
        issue_uuid = uuid4()

        mock_issue = MagicMock()
        mock_issue.workspace_id = UUID(mock_tool_context.workspace_id)
        repo = AsyncMock()
        repo.get_by_id.return_value = mock_issue

        with (
            patch(
                "pilot_space.ai.mcp.issue_server.resolve_entity_id_strict",
                return_value=issue_uuid,
            ),
            patch("pilot_space.ai.mcp.issue_server.IssueRepository", return_value=repo),
        ):
            result = await tools["update_issue"].handler(
                {
                    "issue_id": "PILOT-1",
                    "title": "Updated Title",
                }
            )

        data = json.loads(result["content"][0]["text"])
        assert data["status"] == "approval_required"
        assert data["operation"] == "update_issue"
        assert data["payload"]["title"] == "Updated Title"
        assert data["payload"]["issue_id"] == str(issue_uuid)

    @pytest.mark.asyncio
    async def test_tracks_changes(self, mock_tool_context: ToolContext) -> None:
        tools = _capture_issue_tools(asyncio.Queue(), mock_tool_context)
        issue_uuid = uuid4()

        mock_issue = MagicMock()
        mock_issue.workspace_id = UUID(mock_tool_context.workspace_id)
        repo = AsyncMock()
        repo.get_by_id.return_value = mock_issue

        with (
            patch(
                "pilot_space.ai.mcp.issue_server.resolve_entity_id_strict",
                return_value=issue_uuid,
            ),
            patch("pilot_space.ai.mcp.issue_server.IssueRepository", return_value=repo),
        ):
            result = await tools["update_issue"].handler(
                {
                    "issue_id": str(issue_uuid),
                    "priority": "urgent",
                    "estimate_points": 8,
                    "target_date": "2025-12-31",
                }
            )

        data = json.loads(result["content"][0]["text"])
        assert len(data["preview"]["changes"]) == 3
        assert data["payload"]["priority"] == "urgent"
        assert data["payload"]["estimate_points"] == 8

    @pytest.mark.asyncio
    async def test_label_ids(self, mock_tool_context: ToolContext) -> None:
        tools = _capture_issue_tools(asyncio.Queue(), mock_tool_context)
        issue_uuid, label_id = uuid4(), str(uuid4())

        mock_issue = MagicMock()
        mock_issue.workspace_id = UUID(mock_tool_context.workspace_id)
        repo = AsyncMock()
        repo.get_by_id.return_value = mock_issue

        with (
            patch(
                "pilot_space.ai.mcp.issue_server.resolve_entity_id_strict",
                return_value=issue_uuid,
            ),
            patch("pilot_space.ai.mcp.issue_server.IssueRepository", return_value=repo),
        ):
            result = await tools["update_issue"].handler(
                {
                    "issue_id": str(issue_uuid),
                    "add_label_ids": [label_id],
                }
            )

        data = json.loads(result["content"][0]["text"])
        assert label_id in data["payload"]["add_label_ids"]
