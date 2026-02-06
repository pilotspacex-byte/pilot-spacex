"""Unit tests for issue relation MCP tools (T010).

Tests for 6 relationship tools (IS-005 to IS-010) in issue_relation_server:
link_issue_to_note, unlink_issue_from_note, link_issues, unlink_issues,
add_sub_issue, transition_issue_state.

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


def _capture_relation_tools(
    queue: asyncio.Queue[str],
    ctx: ToolContext | None = None,
) -> dict[str, Any]:
    from pilot_space.ai.mcp import issue_relation_server as mod

    captured: dict[str, object] = {}
    orig = mod.create_sdk_mcp_server

    def intercept(*, name: str, version: str, tools: list[Any]) -> Any:
        captured["tools"] = {t.name: t for t in tools}
        return orig(name=name, version=version, tools=tools)

    with patch.object(mod, "create_sdk_mcp_server", side_effect=intercept):
        mod.create_issue_relation_tools_server(queue, tool_context=ctx)
    return captured["tools"]


class TestIssueRelationServerConfiguration:
    def test_server_name(self) -> None:
        from pilot_space.ai.mcp.issue_relation_server import SERVER_NAME

        assert SERVER_NAME == "pilot-issue-relations"

    def test_tool_names(self) -> None:
        from pilot_space.ai.mcp.issue_relation_server import TOOL_NAMES

        assert len(TOOL_NAMES) == 6
        expected = [
            "mcp__pilot-issue-relations__link_issue_to_note",
            "mcp__pilot-issue-relations__unlink_issue_from_note",
            "mcp__pilot-issue-relations__link_issues",
            "mcp__pilot-issue-relations__unlink_issues",
            "mcp__pilot-issue-relations__add_sub_issue",
            "mcp__pilot-issue-relations__transition_issue_state",
        ]
        for name in expected:
            assert name in TOOL_NAMES

    def test_server_creation(self, mock_tool_context: ToolContext) -> None:
        from pilot_space.ai.mcp.issue_relation_server import create_issue_relation_tools_server

        server = create_issue_relation_tools_server(asyncio.Queue(), tool_context=mock_tool_context)
        assert server["type"] == "sdk"
        assert server["name"] == "pilot-issue-relations"

    def test_captured_tools(self, mock_tool_context: ToolContext) -> None:
        tools = _capture_relation_tools(asyncio.Queue(), mock_tool_context)
        expected = {
            "link_issue_to_note",
            "unlink_issue_from_note",
            "link_issues",
            "unlink_issues",
            "add_sub_issue",
            "transition_issue_state",
        }
        assert set(tools.keys()) == expected


class TestLinkIssueToNote:
    def test_approval_level(self) -> None:
        from pilot_space.ai.tools.mcp_server import TOOL_APPROVAL_MAP, ToolApprovalLevel

        assert TOOL_APPROVAL_MAP["link_issue_to_note"] == ToolApprovalLevel.REQUIRE_APPROVAL

    @pytest.mark.asyncio
    async def test_returns_payload(self, mock_tool_context: ToolContext) -> None:
        tools = _capture_relation_tools(asyncio.Queue(), mock_tool_context)
        issue_uuid, note_uuid = uuid4(), uuid4()

        with (
            patch(
                "pilot_space.ai.mcp.issue_relation_server.resolve_entity_id",
                side_effect=[(issue_uuid, None), (note_uuid, None)],
            ),
            patch(
                "pilot_space.ai.mcp.issue_relation_server._verify_issue_workspace",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "pilot_space.ai.mcp.issue_relation_server._verify_note_workspace",
                new_callable=AsyncMock,
                return_value=None,
            ),
        ):
            result = await tools["link_issue_to_note"].handler(
                {
                    "issue_id": str(issue_uuid),
                    "note_id": str(note_uuid),
                    "link_type": "referenced",
                    "block_id": "block123",
                }
            )

        data = json.loads(result["content"][0]["text"])
        assert data["status"] == "approval_required"
        assert data["operation"] == "link_issue_to_note"
        assert data["payload"]["issue_id"] == str(issue_uuid)
        assert data["payload"]["note_id"] == str(note_uuid)


class TestUnlinkIssueFromNote:
    def test_approval_level(self) -> None:
        from pilot_space.ai.tools.mcp_server import TOOL_APPROVAL_MAP, ToolApprovalLevel

        assert TOOL_APPROVAL_MAP["unlink_issue_from_note"] == ToolApprovalLevel.ALWAYS_REQUIRE

    @pytest.mark.asyncio
    async def test_returns_approval_payload(self, mock_tool_context: ToolContext) -> None:
        queue: asyncio.Queue[str] = asyncio.Queue()
        tools = _capture_relation_tools(queue, mock_tool_context)
        issue_uuid, note_uuid = uuid4(), uuid4()

        with (
            patch(
                "pilot_space.ai.mcp.issue_relation_server.resolve_entity_id",
                side_effect=[(issue_uuid, None), (note_uuid, None)],
            ),
            patch(
                "pilot_space.ai.mcp.issue_relation_server._verify_issue_workspace",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "pilot_space.ai.mcp.issue_relation_server._verify_note_workspace",
                new_callable=AsyncMock,
                return_value=None,
            ),
        ):
            result = await tools["unlink_issue_from_note"].handler(
                {
                    "issue_id": str(issue_uuid),
                    "note_id": str(note_uuid),
                }
            )

        data = json.loads(result["content"][0]["text"])
        assert data["status"] == "approval_required"
        assert data["operation"] == "unlink_issue_from_note"
        # No duplicate SSE event — approval conveyed via operation payload only
        assert queue.empty()


class TestLinkIssues:
    def test_approval_level(self) -> None:
        from pilot_space.ai.tools.mcp_server import TOOL_APPROVAL_MAP, ToolApprovalLevel

        assert TOOL_APPROVAL_MAP["link_issues"] == ToolApprovalLevel.REQUIRE_APPROVAL

    @pytest.mark.asyncio
    async def test_returns_payload_with_inverse_note(self, mock_tool_context: ToolContext) -> None:
        tools = _capture_relation_tools(asyncio.Queue(), mock_tool_context)
        src, tgt = uuid4(), uuid4()

        with (
            patch(
                "pilot_space.ai.mcp.issue_relation_server.resolve_entity_id",
                side_effect=[(src, None), (tgt, None)],
            ),
            patch(
                "pilot_space.ai.mcp.issue_relation_server._verify_issue_workspace",
                new_callable=AsyncMock,
                return_value=None,
            ),
        ):
            result = await tools["link_issues"].handler(
                {
                    "source_issue_id": str(src),
                    "target_issue_id": str(tgt),
                    "link_type": "blocks",
                }
            )

        data = json.loads(result["content"][0]["text"])
        assert data["status"] == "approval_required"
        assert data["payload"]["link_type"] == "blocks"
        assert "inverse" in data["preview"]["note"].lower()

    @pytest.mark.asyncio
    async def test_self_link_rejected(self, mock_tool_context: ToolContext) -> None:
        tools = _capture_relation_tools(asyncio.Queue(), mock_tool_context)
        same = uuid4()

        with (
            patch(
                "pilot_space.ai.mcp.issue_relation_server.resolve_entity_id",
                side_effect=[(same, None), (same, None)],
            ),
            patch(
                "pilot_space.ai.mcp.issue_relation_server._verify_issue_workspace",
                new_callable=AsyncMock,
                return_value=None,
            ),
        ):
            result = await tools["link_issues"].handler(
                {
                    "source_issue_id": str(same),
                    "target_issue_id": str(same),
                    "link_type": "blocks",
                }
            )
        assert "cannot link an issue to itself" in result["content"][0]["text"].lower()

    @pytest.mark.asyncio
    async def test_invalid_link_type(self, mock_tool_context: ToolContext) -> None:
        tools = _capture_relation_tools(asyncio.Queue(), mock_tool_context)
        src, tgt = uuid4(), uuid4()

        with (
            patch(
                "pilot_space.ai.mcp.issue_relation_server.resolve_entity_id",
                side_effect=[(src, None), (tgt, None)],
            ),
            patch(
                "pilot_space.ai.mcp.issue_relation_server._verify_issue_workspace",
                new_callable=AsyncMock,
                return_value=None,
            ),
        ):
            result = await tools["link_issues"].handler(
                {
                    "source_issue_id": str(src),
                    "target_issue_id": str(tgt),
                    "link_type": "invalid_type",
                }
            )
        assert "invalid link_type" in result["content"][0]["text"].lower()


class TestUnlinkIssues:
    def test_approval_level(self) -> None:
        from pilot_space.ai.tools.mcp_server import TOOL_APPROVAL_MAP, ToolApprovalLevel

        assert TOOL_APPROVAL_MAP["unlink_issues"] == ToolApprovalLevel.ALWAYS_REQUIRE

    @pytest.mark.asyncio
    async def test_returns_approval_payload(self, mock_tool_context: ToolContext) -> None:
        queue: asyncio.Queue[str] = asyncio.Queue()
        tools = _capture_relation_tools(queue, mock_tool_context)
        src, tgt = uuid4(), uuid4()

        with (
            patch(
                "pilot_space.ai.mcp.issue_relation_server.resolve_entity_id",
                side_effect=[(src, None), (tgt, None)],
            ),
            patch(
                "pilot_space.ai.mcp.issue_relation_server._verify_issue_workspace",
                new_callable=AsyncMock,
                return_value=None,
            ),
        ):
            result = await tools["unlink_issues"].handler(
                {
                    "source_issue_id": str(src),
                    "target_issue_id": str(tgt),
                }
            )

        data = json.loads(result["content"][0]["text"])
        assert data["status"] == "approval_required"
        # No duplicate SSE event — approval conveyed via operation payload only
        assert queue.empty()


class TestAddSubIssue:
    def test_approval_level(self) -> None:
        from pilot_space.ai.tools.mcp_server import TOOL_APPROVAL_MAP, ToolApprovalLevel

        assert TOOL_APPROVAL_MAP["add_sub_issue"] == ToolApprovalLevel.REQUIRE_APPROVAL

    @pytest.mark.asyncio
    async def test_returns_payload(self, mock_tool_context: ToolContext) -> None:
        tools = _capture_relation_tools(asyncio.Queue(), mock_tool_context)
        parent, child = uuid4(), uuid4()

        repo = AsyncMock()
        repo.get_by_id.return_value = None  # no circular dependency

        with (
            patch(
                "pilot_space.ai.mcp.issue_relation_server.resolve_entity_id",
                side_effect=[(parent, None), (child, None)],
            ),
            patch("pilot_space.ai.mcp.issue_relation_server.IssueRepository", return_value=repo),
            patch(
                "pilot_space.ai.mcp.issue_relation_server._verify_issue_workspace",
                new_callable=AsyncMock,
                return_value=None,
            ),
        ):
            result = await tools["add_sub_issue"].handler(
                {
                    "parent_issue_id": str(parent),
                    "child_issue_id": str(child),
                }
            )

        data = json.loads(result["content"][0]["text"])
        assert data["status"] == "approval_required"
        assert data["operation"] == "add_sub_issue"
        assert data["payload"]["parent_issue_id"] == str(parent)
        assert data["payload"]["child_issue_id"] == str(child)

    @pytest.mark.asyncio
    async def test_circular_dependency_rejected(self, mock_tool_context: ToolContext) -> None:
        tools = _capture_relation_tools(asyncio.Queue(), mock_tool_context)
        parent, child = uuid4(), uuid4()

        mock_parent_issue = MagicMock()
        mock_parent_issue.parent_id = child  # circular: parent's parent is the child
        mock_parent_issue.workspace_id = UUID(mock_tool_context.workspace_id)

        repo = AsyncMock()
        repo.get_by_id.return_value = mock_parent_issue

        with (
            patch(
                "pilot_space.ai.mcp.issue_relation_server.resolve_entity_id",
                side_effect=[(parent, None), (child, None)],
            ),
            patch("pilot_space.ai.mcp.issue_relation_server.IssueRepository", return_value=repo),
        ):
            result = await tools["add_sub_issue"].handler(
                {
                    "parent_issue_id": str(parent),
                    "child_issue_id": str(child),
                }
            )
        assert "circular" in result["content"][0]["text"].lower()


class TestTransitionIssueState:
    def test_approval_level(self) -> None:
        from pilot_space.ai.tools.mcp_server import TOOL_APPROVAL_MAP, ToolApprovalLevel

        assert TOOL_APPROVAL_MAP["transition_issue_state"] == ToolApprovalLevel.REQUIRE_APPROVAL

    @pytest.mark.asyncio
    async def test_returns_payload_with_comment(self, mock_tool_context: ToolContext) -> None:
        tools = _capture_relation_tools(asyncio.Queue(), mock_tool_context)
        issue_uuid, state_id = uuid4(), str(uuid4())

        with (
            patch(
                "pilot_space.ai.mcp.issue_relation_server.resolve_entity_id",
                return_value=(issue_uuid, None),
            ),
            patch(
                "pilot_space.ai.mcp.issue_relation_server._verify_issue_workspace",
                new_callable=AsyncMock,
                return_value=None,
            ),
        ):
            result = await tools["transition_issue_state"].handler(
                {
                    "issue_id": str(issue_uuid),
                    "target_state_id": state_id,
                    "comment": "Moving to in progress",
                }
            )

        data = json.loads(result["content"][0]["text"])
        assert data["status"] == "approval_required"
        assert data["operation"] == "transition_issue_state"
        assert data["payload"]["target_state_id"] == state_id
        assert data["payload"]["comment"] == "Moving to in progress"

    @pytest.mark.asyncio
    async def test_without_comment(self, mock_tool_context: ToolContext) -> None:
        tools = _capture_relation_tools(asyncio.Queue(), mock_tool_context)
        issue_uuid, state_id = uuid4(), str(uuid4())

        with (
            patch(
                "pilot_space.ai.mcp.issue_relation_server.resolve_entity_id",
                return_value=(issue_uuid, None),
            ),
            patch(
                "pilot_space.ai.mcp.issue_relation_server._verify_issue_workspace",
                new_callable=AsyncMock,
                return_value=None,
            ),
        ):
            result = await tools["transition_issue_state"].handler(
                {
                    "issue_id": str(issue_uuid),
                    "target_state_id": state_id,
                }
            )

        data = json.loads(result["content"][0]["text"])
        assert "comment" not in data["payload"]
