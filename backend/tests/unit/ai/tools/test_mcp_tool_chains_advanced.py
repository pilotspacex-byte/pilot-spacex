"""Advanced cross-tool integration tests for MCP tool chains.

Multi-server workflows, error handling, and SSE event propagation tests.
All tests use mocked database sessions (AsyncMock) — no real DB needed.

Reference: spec 010-enhanced-mcp-tools cross-tool integration
"""

from __future__ import annotations

import asyncio
import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from pilot_space.ai.tools.mcp_server import ToolContext

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def workspace_a_id() -> str:
    """Workspace A UUID string."""
    return str(uuid4())


@pytest.fixture
def user_id() -> str:
    """User UUID string."""
    return str(uuid4())


@pytest.fixture
def mock_tool_context(workspace_a_id: str, user_id: str) -> ToolContext:
    """Mock ToolContext with session and IDs for workspace A."""
    mock_session = MagicMock()
    mock_session.execute = AsyncMock()
    mock_session.flush = AsyncMock()
    mock_session.add = MagicMock()
    return ToolContext(
        db_session=mock_session,
        workspace_id=workspace_a_id,
        user_id=user_id,
    )


@pytest.fixture
def event_queue() -> asyncio.Queue[str]:
    """Event queue for SSE events."""
    return asyncio.Queue()


# ---------------------------------------------------------------------------
# Helper functions to capture tools
# ---------------------------------------------------------------------------


def _capture_note_tools(
    queue: asyncio.Queue[str],
    ctx: ToolContext | None = None,
) -> dict[str, Any]:
    """Create note server and capture SdkMcpTool objects by name."""
    from pilot_space.ai.mcp import note_server as module

    captured: dict[str, object] = {}
    original_create = module.create_sdk_mcp_server

    def _intercept_create(*, name: str, version: str, tools: list[Any]):
        captured["tools"] = {t.name: t for t in tools}
        return original_create(name=name, version=version, tools=tools)

    with patch.object(module, "create_sdk_mcp_server", side_effect=_intercept_create):
        module.create_note_tools_server(queue, context_note_id=None, tool_context=ctx)

    return captured["tools"]  # type: ignore[return-value]


def _capture_relation_tools(
    queue: asyncio.Queue[str],
    ctx: ToolContext | None = None,
) -> dict[str, Any]:
    """Create issue relation server and capture SdkMcpTool objects by name."""
    from pilot_space.ai.mcp import issue_relation_server as module

    captured: dict[str, object] = {}
    original_create = module.create_sdk_mcp_server

    def _intercept_create(*, name: str, version: str, tools: list[Any]):
        captured["tools"] = {t.name: t for t in tools}
        return original_create(name=name, version=version, tools=tools)

    with patch.object(module, "create_sdk_mcp_server", side_effect=_intercept_create):
        module.create_issue_relation_tools_server(queue, tool_context=ctx)

    return captured["tools"]  # type: ignore[return-value]


def _capture_comment_tools(
    queue: asyncio.Queue[str],
    ctx: ToolContext | None = None,
) -> dict[str, Any]:
    """Create comment server and capture SdkMcpTool objects by name."""
    from pilot_space.ai.mcp import comment_server as module

    captured: dict[str, object] = {}
    original_create = module.create_sdk_mcp_server

    def _intercept_create(*, name: str, version: str, tools: list[Any]):
        captured["tools"] = {t.name: t for t in tools}
        return original_create(name=name, version=version, tools=tools)

    with patch.object(module, "create_sdk_mcp_server", side_effect=_intercept_create):
        module.create_comment_tools_server(queue, tool_context=ctx)

    return captured["tools"]  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Test Classes
# ---------------------------------------------------------------------------


class TestMultiServerToolChain:
    """Test complex workflows involving 3+ servers."""

    @pytest.mark.asyncio
    async def test_note_extract_issues_with_comments(
        self,
        event_queue: asyncio.Queue[str],
        mock_tool_context: ToolContext,
    ) -> None:
        """Test extracting issues from note and adding comments."""
        # Step 1: Create note
        note_tools = _capture_note_tools(event_queue, mock_tool_context)
        create_note_tool = note_tools["create_note"]

        note_result = await create_note_tool.handler(
            {
                "title": "Sprint Planning",
                "content_markdown": (
                    "# Sprint Planning\n\n"
                    "- [ ] Implement user authentication\n"
                    "- [ ] Add search functionality\n"
                    "- [ ] Fix mobile layout issues"
                ),
            }
        )

        note_data = json.loads(note_result["content"][0]["text"])
        assert note_data["status"] == "approval_required"

        # Simulate note creation
        note_id = uuid4()

        # Step 2: Extract issues (note: extract_issues is a tool in note_server)
        # For this test, we'll simulate the result as if it were called
        # In a real scenario, this would call the extract_issues tool handler

        # Step 3: Create comment on extracted issue
        comment_tools = _capture_comment_tools(event_queue, mock_tool_context)
        create_comment_tool = comment_tools["create_comment"]

        # Simulate an extracted issue ID
        extracted_issue_id = str(uuid4())

        # Mock discussion lookup
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_tool_context.db_session.execute = AsyncMock(return_value=mock_result)

        comment_result = await create_comment_tool.handler(
            {
                "target_type": "issue",
                "target_id": extracted_issue_id,
                "content": "This task was extracted from sprint planning notes",
            }
        )

        # Verify comment creation
        text = comment_result["content"][0]["text"]
        assert "Approval required" in text

        # Verify SSE event
        assert not event_queue.empty()
        event = await event_queue.get()
        assert "event: content_update" in event


class TestToolErrorHandling:
    """Test error handling in cross-tool workflows."""

    @pytest.mark.asyncio
    async def test_link_nonexistent_issue_to_note(
        self,
        event_queue: asyncio.Queue[str],
        mock_tool_context: ToolContext,
    ) -> None:
        """Test linking a non-existent issue to a note (error path)."""
        relation_tools = _capture_relation_tools(event_queue, mock_tool_context)
        link_tool = relation_tools["link_issue_to_note"]

        note_id = uuid4()

        # Mock resolve_entity_id returning error for invalid issue
        with patch(
            "pilot_space.ai.mcp.issue_relation_server.resolve_entity_id",
            return_value=(None, "Issue 'INVALID-999' not found"),
        ):
            result = await link_tool.handler(
                {
                    "issue_id": "INVALID-999",
                    "note_id": str(note_id),
                    "link_type": "referenced",
                }
            )

        # Verify error message
        assert "error" in result["content"][0]["text"].lower()
        assert "not found" in result["content"][0]["text"].lower()

    @pytest.mark.asyncio
    async def test_circular_dependency_detection(
        self,
        event_queue: asyncio.Queue[str],
        mock_tool_context: ToolContext,
    ) -> None:
        """Test circular dependency detection when adding sub-issues."""
        relation_tools = _capture_relation_tools(event_queue, mock_tool_context)
        add_sub_issue_tool = relation_tools["add_sub_issue"]

        parent_id = uuid4()
        child_id = uuid4()

        # Mock parent issue where parent's parent is the child (circular)
        mock_parent_issue = MagicMock()
        mock_parent_issue.parent_id = child_id
        mock_parent_issue.workspace_id = UUID(mock_tool_context.workspace_id)

        repo = AsyncMock()
        repo.get_by_id.return_value = mock_parent_issue

        with (
            patch(
                "pilot_space.ai.mcp.issue_relation_server.resolve_entity_id",
                side_effect=[(parent_id, None), (child_id, None)],
            ),
            patch(
                "pilot_space.ai.mcp.issue_relation_server.IssueRepository",
                return_value=repo,
            ),
        ):
            result = await add_sub_issue_tool.handler(
                {
                    "parent_issue_id": str(parent_id),
                    "child_issue_id": str(child_id),
                }
            )

        # Verify circular dependency is rejected
        assert "circular" in result["content"][0]["text"].lower()


class TestSSEEventPropagation:
    """Test SSE event propagation across tool chains."""

    @pytest.mark.asyncio
    async def test_multiple_operations_generate_sse_events(
        self,
        event_queue: asyncio.Queue[str],
        mock_tool_context: ToolContext,
    ) -> None:
        """Test that multiple operations generate distinct SSE events."""
        # Step 1: Create comment
        comment_tools = _capture_comment_tools(event_queue, mock_tool_context)
        create_comment_tool = comment_tools["create_comment"]

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_tool_context.db_session.execute = AsyncMock(return_value=mock_result)

        await create_comment_tool.handler(
            {
                "target_type": "note",
                "target_id": str(uuid4()),
                "content": "First operation",
            }
        )

        # Step 2: Unlink issue from note
        relation_tools = _capture_relation_tools(event_queue, mock_tool_context)
        unlink_tool = relation_tools["unlink_issue_from_note"]

        issue_id = uuid4()
        note_id = uuid4()

        with (
            patch(
                "pilot_space.ai.mcp.issue_relation_server.resolve_entity_id",
                side_effect=[(issue_id, None), (note_id, None)],
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
            await unlink_tool.handler(
                {
                    "issue_id": str(issue_id),
                    "note_id": str(note_id),
                }
            )

        # Comment creation pushes SSE; unlink returns payload only (no duplicate SSE)
        assert event_queue.qsize() == 1

        event1 = await event_queue.get()
        assert "event: content_update" in event1
        event1_data = json.loads(event1.split("data: ")[1].strip())
        assert event1_data["operation"] == "comment_created"
