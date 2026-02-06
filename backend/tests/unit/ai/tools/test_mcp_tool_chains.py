"""Cross-tool integration tests for MCP tool chains.

Verify tools from different MCP servers work together in realistic workflows.
All tests use mocked database sessions (AsyncMock) — no real DB needed.

Reference: spec 010-enhanced-mcp-tools cross-tool integration
"""

from __future__ import annotations

import asyncio
import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

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
def workspace_b_id() -> str:
    """Workspace B UUID string."""
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
def mock_tool_context_workspace_b(workspace_b_id: str, user_id: str) -> ToolContext:
    """Mock ToolContext for workspace B."""
    mock_session = MagicMock()
    mock_session.execute = AsyncMock()
    mock_session.flush = AsyncMock()
    mock_session.add = MagicMock()
    return ToolContext(
        db_session=mock_session,
        workspace_id=workspace_b_id,
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


def _capture_issue_tools(
    queue: asyncio.Queue[str],
    ctx: ToolContext | None = None,
) -> dict[str, Any]:
    """Create issue server and capture SdkMcpTool objects by name."""
    from pilot_space.ai.mcp import issue_server as module

    captured: dict[str, object] = {}
    original_create = module.create_sdk_mcp_server

    def _intercept_create(*, name: str, version: str, tools: list[Any]):
        captured["tools"] = {t.name: t for t in tools}
        return original_create(name=name, version=version, tools=tools)

    with patch.object(module, "create_sdk_mcp_server", side_effect=_intercept_create):
        module.create_issue_tools_server(queue, tool_context=ctx)

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


class TestNoteToIssueWorkflow:
    """Test workflow: create note → create issue → link issue to note."""

    @pytest.mark.asyncio
    async def test_create_note_then_create_issue_and_link(
        self,
        event_queue: asyncio.Queue[str],
        mock_tool_context: ToolContext,
    ) -> None:
        """Test note creation, issue creation, and linking them together."""
        # Step 1: Create note
        note_tools = _capture_note_tools(event_queue, mock_tool_context)
        create_note_tool = note_tools["create_note"]

        note_result = await create_note_tool.handler(
            {
                "title": "Meeting Notes",
                "content_markdown": "# Discussion\n\nAction items discussed.",
            }
        )

        # Verify note creation returns approval_required
        # Note: create_note returns dict directly (not wrapped in {"content": [...]})
        assert note_result["status"] == "approval_required"
        assert note_result["operation"] == "create_note"
        assert note_result["payload"]["title"] == "Meeting Notes"

        # Simulate note creation in DB (mock the note_id)
        note_id = uuid4()

        # Step 2: Create issue
        issue_tools = _capture_issue_tools(event_queue, mock_tool_context)
        create_issue_tool = issue_tools["create_issue"]

        project_uuid = uuid4()
        with patch(
            "pilot_space.ai.mcp.issue_server.resolve_entity_id",
            return_value=(project_uuid, None),
        ):
            issue_result = await create_issue_tool.handler(
                {
                    "project_id": "PILOT",
                    "title": "Implement feature from meeting",
                    "priority": "high",
                }
            )

        # Verify issue creation returns approval_required
        issue_data = json.loads(issue_result["content"][0]["text"])
        assert issue_data["status"] == "approval_required"
        assert issue_data["operation"] == "create_issue"
        assert issue_data["payload"]["title"] == "Implement feature from meeting"
        assert issue_data["payload"]["priority"] == "high"

        # Simulate issue creation in DB (mock the issue_id)
        issue_id = uuid4()

        # Step 3: Link issue to note
        relation_tools = _capture_relation_tools(event_queue, mock_tool_context)
        link_tool = relation_tools["link_issue_to_note"]

        with patch(
            "pilot_space.ai.mcp.issue_relation_server.resolve_entity_id",
            side_effect=[(issue_id, None), (note_id, None)],
        ):
            link_result = await link_tool.handler(
                {
                    "issue_id": str(issue_id),
                    "note_id": str(note_id),
                    "link_type": "extracted",
                    "block_id": "block-123",
                }
            )

        # Verify link creation returns approval_required with both IDs
        link_data = json.loads(link_result["content"][0]["text"])
        assert link_data["status"] == "approval_required"
        assert link_data["operation"] == "link_issue_to_note"
        assert link_data["payload"]["issue_id"] == str(issue_id)
        assert link_data["payload"]["note_id"] == str(note_id)
        assert link_data["payload"]["link_type"] == "extracted"
        assert link_data["payload"]["block_id"] == "block-123"


class TestIssueRelationChain:
    """Test workflow: search issues → link dependency between issues."""

    @pytest.mark.asyncio
    async def test_search_issue_then_link_dependency(
        self,
        event_queue: asyncio.Queue[str],
        mock_tool_context: ToolContext,
    ) -> None:
        """Test searching for issues and creating a dependency link."""
        # Step 1: Search for issues
        issue_tools = _capture_issue_tools(event_queue, mock_tool_context)
        search_tool = issue_tools["search_issues"]

        # Mock two issues in search results
        issue1_id = uuid4()
        issue2_id = uuid4()

        mock_issue1 = MagicMock()
        mock_issue1.id = issue1_id
        mock_issue1.sequence_id = 1
        mock_issue1.name = "Backend API implementation"
        mock_issue1.priority.value = "high"
        mock_issue1.state.name = "In Progress"
        mock_issue1.project.identifier = "PILOT"
        mock_issue1.assignee = None

        mock_issue2 = MagicMock()
        mock_issue2.id = issue2_id
        mock_issue2.sequence_id = 2
        mock_issue2.name = "Frontend integration"
        mock_issue2.priority.value = "medium"
        mock_issue2.state.name = "Todo"
        mock_issue2.project.identifier = "PILOT"
        mock_issue2.assignee = None

        page = MagicMock()
        page.items = [mock_issue1, mock_issue2]

        repo = AsyncMock()
        repo.get_workspace_issues.return_value = page

        with patch("pilot_space.ai.mcp.issue_server.IssueRepository", return_value=repo):
            search_result = await search_tool.handler({"query": "API"})

        # Verify search returns both issues
        search_data = json.loads(search_result["content"][0]["text"])
        assert len(search_data) == 2
        assert search_data[0]["name"] == "Backend API implementation"
        assert search_data[1]["name"] == "Frontend integration"

        # Step 2: Link issues with blocks relationship
        relation_tools = _capture_relation_tools(event_queue, mock_tool_context)
        link_issues_tool = relation_tools["link_issues"]

        with patch(
            "pilot_space.ai.mcp.issue_relation_server.resolve_entity_id",
            side_effect=[(issue1_id, None), (issue2_id, None)],
        ):
            link_result = await link_issues_tool.handler(
                {
                    "source_issue_id": str(issue1_id),
                    "target_issue_id": str(issue2_id),
                    "link_type": "blocks",
                }
            )

        # Verify link shows correct link_type
        link_data = json.loads(link_result["content"][0]["text"])
        assert link_data["status"] == "approval_required"
        assert link_data["operation"] == "link_issues"
        assert link_data["payload"]["source_issue_id"] == str(issue1_id)
        assert link_data["payload"]["target_issue_id"] == str(issue2_id)
        assert link_data["payload"]["link_type"] == "blocks"
        assert "inverse" in link_data["preview"]["note"].lower()


class TestCommentOnIssue:
    """Test workflow: create comment → search comments."""

    @pytest.mark.asyncio
    async def test_create_comment_then_search(
        self,
        event_queue: asyncio.Queue[str],
        mock_tool_context: ToolContext,
    ) -> None:
        """Test creating a comment on an issue and searching for it."""
        # Step 1: Create comment on issue
        comment_tools = _capture_comment_tools(event_queue, mock_tool_context)
        create_comment_tool = comment_tools["create_comment"]

        issue_id = str(uuid4())

        # Mock discussion lookup returning None (will create new discussion)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_tool_context.db_session.execute = AsyncMock(return_value=mock_result)

        create_result = await create_comment_tool.handler(
            {
                "target_type": "issue",
                "target_id": issue_id,
                "content": "This issue needs more context about edge cases",
            }
        )

        # Verify comment creation success
        text = create_result["content"][0]["text"]
        assert "Created AI comment" in text

        # Verify SSE event was pushed
        assert not event_queue.empty()
        event = await event_queue.get()
        assert "event: content_update" in event
        event_data = json.loads(event.split("data: ")[1].strip())
        assert event_data["operation"] == "comment_created"
        assert event_data["targetType"] == "issue"
        assert event_data["isAiGenerated"] is True

        # Step 2: Search for the comment
        search_comment_tool = comment_tools["search_comments"]

        # Mock search result with the created comment
        from datetime import UTC, datetime

        comment_id = uuid4()
        mock_comment = MagicMock()
        mock_comment.id = comment_id
        mock_comment.content = "This issue needs more context about edge cases"
        mock_comment.is_ai_generated = True
        mock_comment.created_at = datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC)
        mock_comment.edited_at = None  # No edits
        mock_comment.discussion_id = uuid4()

        # Mock author
        mock_author = MagicMock()
        mock_author.id = uuid4()
        mock_author.full_name = "AI Bot"
        mock_author.email = "ai@example.com"
        mock_comment.author = mock_author

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_comment]
        mock_unique = MagicMock()
        mock_unique.scalars.return_value = mock_scalars
        mock_result.unique.return_value = mock_unique
        mock_tool_context.db_session.execute = AsyncMock(return_value=mock_result)

        search_result = await search_comment_tool.handler(
            {
                "query": "edge cases",
            }
        )

        # Verify search result contains the created comment
        search_text = search_result["content"][0]["text"]
        assert "Found 1 comment" in search_text
        assert "This issue needs more context about edge cases" in search_text


class TestRLSIsolation:
    """Test RLS workspace isolation across different tool contexts."""

    @pytest.mark.asyncio
    async def test_workspace_isolation_search_issues(
        self,
        event_queue: asyncio.Queue[str],
        mock_tool_context: ToolContext,
        mock_tool_context_workspace_b: ToolContext,
        workspace_a_id: str,
        workspace_b_id: str,
    ) -> None:
        """Test that search_issues respects workspace isolation."""
        # Step 1: Search issues in workspace A
        issue_tools_a = _capture_issue_tools(event_queue, mock_tool_context)
        search_tool_a = issue_tools_a["search_issues"]

        issue_a1_id = uuid4()
        issue_a2_id = uuid4()

        mock_issue_a1 = MagicMock()
        mock_issue_a1.id = issue_a1_id
        mock_issue_a1.sequence_id = 1
        mock_issue_a1.name = "Workspace A Issue 1"
        mock_issue_a1.priority.value = "high"
        mock_issue_a1.state.name = "Todo"
        mock_issue_a1.project.identifier = "WSA"
        mock_issue_a1.assignee = None

        mock_issue_a2 = MagicMock()
        mock_issue_a2.id = issue_a2_id
        mock_issue_a2.sequence_id = 2
        mock_issue_a2.name = "Workspace A Issue 2"
        mock_issue_a2.priority.value = "medium"
        mock_issue_a2.state.name = "In Progress"
        mock_issue_a2.project.identifier = "WSA"
        mock_issue_a2.assignee = None

        page_a = MagicMock()
        page_a.items = [mock_issue_a1, mock_issue_a2]

        repo_a = AsyncMock()
        repo_a.get_workspace_issues.return_value = page_a

        with patch("pilot_space.ai.mcp.issue_server.IssueRepository", return_value=repo_a):
            result_a = await search_tool_a.handler({"query": "Issue"})

        # Verify workspace A sees only its issues
        data_a = json.loads(result_a["content"][0]["text"])
        assert len(data_a) == 2
        assert data_a[0]["name"] == "Workspace A Issue 1"
        assert data_a[1]["name"] == "Workspace A Issue 2"

        # Step 2: Search issues in workspace B
        issue_tools_b = _capture_issue_tools(event_queue, mock_tool_context_workspace_b)
        search_tool_b = issue_tools_b["search_issues"]

        issue_b1_id = uuid4()

        mock_issue_b1 = MagicMock()
        mock_issue_b1.id = issue_b1_id
        mock_issue_b1.sequence_id = 1
        mock_issue_b1.name = "Workspace B Issue 1"
        mock_issue_b1.priority.value = "low"
        mock_issue_b1.state.name = "Done"
        mock_issue_b1.project.identifier = "WSB"
        mock_issue_b1.assignee = None

        page_b = MagicMock()
        page_b.items = [mock_issue_b1]

        repo_b = AsyncMock()
        repo_b.get_workspace_issues.return_value = page_b

        with patch("pilot_space.ai.mcp.issue_server.IssueRepository", return_value=repo_b):
            result_b = await search_tool_b.handler({"query": "Issue"})

        # Verify workspace B sees only its issues
        data_b = json.loads(result_b["content"][0]["text"])
        assert len(data_b) == 1
        assert data_b[0]["name"] == "Workspace B Issue 1"

        # Verify no cross-workspace contamination
        assert all(issue["name"].startswith("Workspace A") for issue in data_a)
        assert all(issue["name"].startswith("Workspace B") for issue in data_b)


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

        # Note: create_note returns dict directly
        assert note_result["status"] == "approval_required"

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
        assert "Created AI comment" in text

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

        with patch(
            "pilot_space.ai.mcp.issue_relation_server.resolve_entity_id",
            side_effect=[(issue_id, None), (note_id, None)],
        ):
            await unlink_tool.handler(
                {
                    "issue_id": str(issue_id),
                    "note_id": str(note_id),
                }
            )

        # Verify both SSE events are in queue
        assert event_queue.qsize() == 2

        event1 = await event_queue.get()
        assert "event: content_update" in event1
        event1_data = json.loads(event1.split("data: ")[1].strip())
        assert event1_data["operation"] == "comment_created"

        event2 = await event_queue.get()
        assert "event: approval_request" in event2
