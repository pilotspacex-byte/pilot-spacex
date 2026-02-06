"""Unit tests for comment MCP read tools (search_comments, get_comments).

Split from test_comment_tools.py to stay under the 700-line file limit.
Uses the same mock-based patterns for db_session and ToolContext.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from pilot_space.ai.tools.mcp_server import ToolContext

# ---------------------------------------------------------------------------
# Helpers (shared patterns from test_comment_tools.py)
# ---------------------------------------------------------------------------


def _make_mock_context(
    workspace_id: str | None = None,
    user_id: str | None = None,
) -> ToolContext:
    """Build a ToolContext backed by a fully-mocked AsyncSession."""
    mock_session = MagicMock()
    mock_session.execute = AsyncMock()
    mock_session.flush = AsyncMock()
    mock_session.add = MagicMock()
    return ToolContext(
        db_session=mock_session,
        workspace_id=workspace_id or str(uuid4()),
        user_id=user_id or str(uuid4()),
    )


def _capture_comment_tools(
    event_queue: asyncio.Queue[str],
    tool_context: ToolContext | None = None,
) -> dict[str, object]:
    """Create comment server and capture SdkMcpTool objects by name."""
    from pilot_space.ai.mcp import comment_server as module

    captured: dict[str, object] = {}
    original_create = module.create_sdk_mcp_server

    def _intercept_create(*, name: str, version: str, tools: list[object]):
        captured["tools"] = {t.name: t for t in tools}  # type: ignore[attr-defined]
        return original_create(name=name, version=version, tools=tools)

    with patch.object(module, "create_sdk_mcp_server", side_effect=_intercept_create):
        module.create_comment_tools_server(event_queue, tool_context=tool_context)

    return captured["tools"]  # type: ignore[return-value]


def _mock_discussion(
    *,
    discussion_id: str | None = None,
    workspace_id: str | None = None,
    target_type: str = "note",
    target_id: str | None = None,
    note_id: str | None = None,
) -> MagicMock:
    """Build a mock ThreadedDiscussion row."""
    d = MagicMock()
    d.id = uuid4() if discussion_id is None else discussion_id
    d.workspace_id = uuid4() if workspace_id is None else workspace_id
    d.target_type = target_type
    d.target_id = uuid4() if target_id is None else target_id
    d.note_id = note_id or d.target_id
    d.is_deleted = False
    return d


def _mock_comment(
    *,
    comment_id: str | None = None,
    discussion_id: str | None = None,
    content: str = "mock comment",
    is_ai_generated: bool = True,
    author_display_name: str = "AI Bot",
    author_email: str = "ai@example.com",
    edited_at: datetime | None = None,
) -> MagicMock:
    """Build a mock DiscussionComment row with nested author."""
    c = MagicMock()
    c.id = uuid4() if comment_id is None else comment_id
    c.discussion_id = uuid4() if discussion_id is None else discussion_id
    c.content = content
    c.is_ai_generated = is_ai_generated
    c.edited_at = edited_at
    c.created_at = datetime.now(UTC)
    c.workspace_id = uuid4()

    author = MagicMock()
    author.id = uuid4()
    author.full_name = author_display_name
    author.email = author_email
    c.author = author
    return c


# ---------------------------------------------------------------------------
# search_comments
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestSearchComments:
    """Test search_comments tool handler."""

    async def test_search_returns_results(self) -> None:
        """Search matching comments are formatted and returned."""
        ctx = _make_mock_context()
        queue: asyncio.Queue[str] = asyncio.Queue()
        tools = _capture_comment_tools(queue, tool_context=ctx)
        tool = tools["search_comments"]

        comment = _mock_comment(content="Python best practices")

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [comment]
        mock_unique = MagicMock()
        mock_unique.scalars.return_value = mock_scalars
        mock_result.unique.return_value = mock_unique
        ctx.db_session.execute = AsyncMock(return_value=mock_result)

        result = await tool.handler({"query": "Python"})  # type: ignore[attr-defined]

        text = result["content"][0]["text"]
        assert "Found 1 comment" in text
        assert "Python best practices" in text

    async def test_search_no_results(self) -> None:
        """Empty result set returns informative message."""
        ctx = _make_mock_context()
        queue: asyncio.Queue[str] = asyncio.Queue()
        tools = _capture_comment_tools(queue, tool_context=ctx)
        tool = tools["search_comments"]

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_unique = MagicMock()
        mock_unique.scalars.return_value = mock_scalars
        mock_result.unique.return_value = mock_unique
        ctx.db_session.execute = AsyncMock(return_value=mock_result)

        result = await tool.handler({"query": "NonExistentTerm"})  # type: ignore[attr-defined]

        text = result["content"][0]["text"]
        assert "No comments found" in text

    async def test_search_invalid_target_id(self) -> None:
        """Invalid target_id UUID should be rejected."""
        ctx = _make_mock_context()
        queue: asyncio.Queue[str] = asyncio.Queue()
        tools = _capture_comment_tools(queue, tool_context=ctx)
        tool = tools["search_comments"]

        result = await tool.handler(
            {  # type: ignore[attr-defined]
                "query": "test",
                "target_id": "not-a-uuid",
            }
        )

        text = result["content"][0]["text"]
        assert "invalid target_id UUID" in text


# ---------------------------------------------------------------------------
# get_comments
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestGetComments:
    """Test get_comments tool handler."""

    async def test_get_returns_comments(self) -> None:
        """Comments for a known target are returned with structure."""
        ctx = _make_mock_context()
        queue: asyncio.Queue[str] = asyncio.Queue()
        tools = _capture_comment_tools(queue, tool_context=ctx)
        tool = tools["get_comments"]

        discussion = _mock_discussion()
        comment = _mock_comment(
            discussion_id=str(discussion.id),
            content="Architecture review note",
        )

        disc_result = MagicMock()
        disc_scalars = MagicMock()
        disc_scalars.all.return_value = [discussion]
        disc_result.scalars.return_value = disc_scalars

        comment_result = MagicMock()
        comment_scalars = MagicMock()
        comment_scalars.all.return_value = [comment]
        comment_unique = MagicMock()
        comment_unique.scalars.return_value = comment_scalars
        comment_result.unique.return_value = comment_unique

        ctx.db_session.execute = AsyncMock(side_effect=[disc_result, comment_result])

        result = await tool.handler(
            {  # type: ignore[attr-defined]
                "target_type": "note",
                "target_id": str(discussion.target_id),
            }
        )

        text = result["content"][0]["text"]
        assert "Found 1 comment" in text
        assert "Architecture review note" in text

    async def test_get_no_discussions(self) -> None:
        """No discussions for target returns informative message."""
        ctx = _make_mock_context()
        queue: asyncio.Queue[str] = asyncio.Queue()
        tools = _capture_comment_tools(queue, tool_context=ctx)
        tool = tools["get_comments"]

        disc_result = MagicMock()
        disc_scalars = MagicMock()
        disc_scalars.all.return_value = []
        disc_result.scalars.return_value = disc_scalars
        ctx.db_session.execute = AsyncMock(return_value=disc_result)

        result = await tool.handler(
            {  # type: ignore[attr-defined]
                "target_type": "note",
                "target_id": str(uuid4()),
            }
        )

        text = result["content"][0]["text"]
        assert "No discussions found" in text

    async def test_get_invalid_target_type(self) -> None:
        """Unsupported target_type should be rejected."""
        ctx = _make_mock_context()
        queue: asyncio.Queue[str] = asyncio.Queue()
        tools = _capture_comment_tools(queue, tool_context=ctx)
        tool = tools["get_comments"]

        result = await tool.handler(
            {  # type: ignore[attr-defined]
                "target_type": "workspace",
                "target_id": str(uuid4()),
            }
        )

        text = result["content"][0]["text"]
        assert "unsupported target_type" in text

    async def test_get_invalid_target_id(self) -> None:
        """Invalid UUID for target_id should be rejected."""
        ctx = _make_mock_context()
        queue: asyncio.Queue[str] = asyncio.Queue()
        tools = _capture_comment_tools(queue, tool_context=ctx)
        tool = tools["get_comments"]

        result = await tool.handler(
            {  # type: ignore[attr-defined]
                "target_type": "note",
                "target_id": "bad-uuid",
            }
        )

        text = result["content"][0]["text"]
        assert "invalid target_id UUID" in text

    async def test_get_discussions_but_no_comments(self) -> None:
        """Discussion exists but has zero comments."""
        ctx = _make_mock_context()
        queue: asyncio.Queue[str] = asyncio.Queue()
        tools = _capture_comment_tools(queue, tool_context=ctx)
        tool = tools["get_comments"]

        discussion = _mock_discussion()

        disc_result = MagicMock()
        disc_scalars = MagicMock()
        disc_scalars.all.return_value = [discussion]
        disc_result.scalars.return_value = disc_scalars

        comment_result = MagicMock()
        comment_scalars = MagicMock()
        comment_scalars.all.return_value = []
        comment_unique = MagicMock()
        comment_unique.scalars.return_value = comment_scalars
        comment_result.unique.return_value = comment_unique

        ctx.db_session.execute = AsyncMock(side_effect=[disc_result, comment_result])

        result = await tool.handler(
            {  # type: ignore[attr-defined]
                "target_type": "note",
                "target_id": str(discussion.target_id),
            }
        )

        text = result["content"][0]["text"]
        assert "No comments found" in text


# ---------------------------------------------------------------------------
# All tools registered
# ---------------------------------------------------------------------------


class TestToolCategoryRegistration:
    """Verify all 4 comment tools are registered with correct approval levels."""

    def test_all_comment_tools_in_approval_map(self) -> None:
        from pilot_space.ai.tools.mcp_server import TOOL_APPROVAL_MAP, ToolApprovalLevel

        # CM-001: create_comment is AUTO_EXECUTE (non-destructive addition)
        auto_execute_tools = ["search_comments", "get_comments", "create_comment"]
        for tool_name in auto_execute_tools:
            assert tool_name in TOOL_APPROVAL_MAP
            assert TOOL_APPROVAL_MAP[tool_name] == ToolApprovalLevel.AUTO_EXECUTE

        require_approval_tools = ["update_comment"]
        for tool_name in require_approval_tools:
            assert tool_name in TOOL_APPROVAL_MAP
            assert TOOL_APPROVAL_MAP[tool_name] == ToolApprovalLevel.REQUIRE_APPROVAL
