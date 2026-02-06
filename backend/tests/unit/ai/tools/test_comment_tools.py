"""Unit tests for comment MCP mutation tools (create_comment, update_comment).

Read tool tests (search_comments, get_comments) are in test_comment_tools_read.py.
Uses mock-based patterns (MagicMock/AsyncMock for db_session and ToolContext)
instead of real database fixtures.

Pattern: _capture_comment_tools intercepts SDK tool closures from the server
factory so handlers can be called directly with args dicts.
"""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from pilot_space.ai.tools.mcp_server import ToolContext

# ---------------------------------------------------------------------------
# Helpers
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
    """Create comment server and capture SdkMcpTool objects by name.

    Intercepts ``create_sdk_mcp_server`` so that the tool list is stored
    before the real server is built.  Returns ``{tool_name: SdkMcpTool}``.
    """
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
# Server configuration
# ---------------------------------------------------------------------------


class TestServerConfiguration:
    """Verify SERVER_NAME, TOOL_NAMES, and server factory behaviour."""

    def test_server_name(self) -> None:
        from pilot_space.ai.mcp.comment_server import SERVER_NAME

        assert SERVER_NAME == "pilot-comments"

    def test_tool_names_list(self) -> None:
        from pilot_space.ai.mcp.comment_server import SERVER_NAME, TOOL_NAMES

        assert len(TOOL_NAMES) == 4

        expected = [
            f"mcp__{SERVER_NAME}__create_comment",
            f"mcp__{SERVER_NAME}__update_comment",
            f"mcp__{SERVER_NAME}__search_comments",
            f"mcp__{SERVER_NAME}__get_comments",
        ]
        for name in expected:
            assert name in TOOL_NAMES, f"{name} missing from TOOL_NAMES"

    def test_server_requires_tool_context(self) -> None:
        from pilot_space.ai.mcp.comment_server import create_comment_tools_server

        queue: asyncio.Queue[str] = asyncio.Queue()
        with pytest.raises(ValueError, match="tool_context is required"):
            create_comment_tools_server(queue, tool_context=None)

    def test_server_creation_success(self) -> None:
        from pilot_space.ai.mcp.comment_server import create_comment_tools_server

        ctx = _make_mock_context()
        queue: asyncio.Queue[str] = asyncio.Queue()
        server = create_comment_tools_server(queue, tool_context=ctx)

        assert isinstance(server, dict)
        assert server["type"] == "sdk"
        assert server["name"] == "pilot-comments"
        assert "instance" in server


# ---------------------------------------------------------------------------
# Approval map
# ---------------------------------------------------------------------------


class TestApprovalLevels:
    """Verify each tool is registered with the correct approval level."""

    def test_create_comment_approval(self) -> None:
        from pilot_space.ai.tools.mcp_server import TOOL_APPROVAL_MAP, ToolApprovalLevel

        assert TOOL_APPROVAL_MAP["create_comment"] == ToolApprovalLevel.REQUIRE_APPROVAL

    def test_update_comment_approval(self) -> None:
        from pilot_space.ai.tools.mcp_server import TOOL_APPROVAL_MAP, ToolApprovalLevel

        assert TOOL_APPROVAL_MAP["update_comment"] == ToolApprovalLevel.REQUIRE_APPROVAL

    def test_search_comments_approval(self) -> None:
        from pilot_space.ai.tools.mcp_server import TOOL_APPROVAL_MAP, ToolApprovalLevel

        assert TOOL_APPROVAL_MAP["search_comments"] == ToolApprovalLevel.AUTO_EXECUTE

    def test_get_comments_approval(self) -> None:
        from pilot_space.ai.tools.mcp_server import TOOL_APPROVAL_MAP, ToolApprovalLevel

        assert TOOL_APPROVAL_MAP["get_comments"] == ToolApprovalLevel.AUTO_EXECUTE


# ---------------------------------------------------------------------------
# create_comment
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestCreateComment:
    """Test create_comment tool handler."""

    async def test_create_on_note(self) -> None:
        """Create a comment targeting a note; expect discussion lookup + SSE event."""
        ctx = _make_mock_context()
        queue: asyncio.Queue[str] = asyncio.Queue()
        tools = _capture_comment_tools(queue, tool_context=ctx)
        tool = tools["create_comment"]

        note_id = str(uuid4())

        # First execute: discussion lookup -> returns None (will create)
        # Second execute: flush from session.add is a MagicMock, nothing to mock
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        ctx.db_session.execute = AsyncMock(return_value=mock_result)

        result = await tool.handler(
            {  # type: ignore[attr-defined]
                "target_type": "note",
                "target_id": note_id,
                "content": "Great observation about the architecture",
            }
        )

        assert "content" in result
        text = result["content"][0]["text"]
        assert "Approval required" in text

        # Verify SSE event was pushed
        assert not queue.empty()
        event = await queue.get()
        assert "event: content_update" in event
        event_data = json.loads(event.split("data: ")[1].strip())
        assert event_data["operation"] == "comment_created"
        assert event_data["status"] == "approval_required"
        assert event_data["approval_level"] == "require_approval"
        assert event_data["targetType"] == "note"
        assert event_data["isAiGenerated"] is True
        assert event_data["createDiscussion"] is True

    async def test_create_on_existing_discussion(self) -> None:
        """Create a comment when discussion already exists for target."""
        ctx = _make_mock_context()
        queue: asyncio.Queue[str] = asyncio.Queue()
        tools = _capture_comment_tools(queue, tool_context=ctx)
        tool = tools["create_comment"]

        discussion = _mock_discussion(target_type="issue")

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = discussion
        ctx.db_session.execute = AsyncMock(return_value=mock_result)

        result = await tool.handler(
            {  # type: ignore[attr-defined]
                "target_type": "issue",
                "target_id": str(discussion.target_id),
                "content": "Follow-up on this issue",
            }
        )

        text = result["content"][0]["text"]
        assert "Approval required" in text

        # Verify SSE event includes existing discussion ID
        event = await queue.get()
        event_data = json.loads(event.split("data: ")[1].strip())
        assert event_data["existingDiscussionId"] == str(discussion.id)
        assert event_data["createDiscussion"] is False

    async def test_create_missing_content(self) -> None:
        """Empty/whitespace content should be rejected."""
        ctx = _make_mock_context()
        queue: asyncio.Queue[str] = asyncio.Queue()
        tools = _capture_comment_tools(queue, tool_context=ctx)
        tool = tools["create_comment"]

        result = await tool.handler(
            {  # type: ignore[attr-defined]
                "target_type": "note",
                "target_id": str(uuid4()),
                "content": "   ",
            }
        )

        text = result["content"][0]["text"]
        assert "cannot be empty" in text

    async def test_create_invalid_target_type(self) -> None:
        """Unsupported target_type should be rejected."""
        ctx = _make_mock_context()
        queue: asyncio.Queue[str] = asyncio.Queue()
        tools = _capture_comment_tools(queue, tool_context=ctx)
        tool = tools["create_comment"]

        result = await tool.handler(
            {  # type: ignore[attr-defined]
                "target_type": "workspace",
                "target_id": str(uuid4()),
                "content": "some content",
            }
        )

        text = result["content"][0]["text"]
        assert "unsupported target_type" in text

    async def test_create_discussion_target_not_found(self) -> None:
        """When target_type is discussion and it doesn't exist, error."""
        ctx = _make_mock_context()
        queue: asyncio.Queue[str] = asyncio.Queue()
        tools = _capture_comment_tools(queue, tool_context=ctx)
        tool = tools["create_comment"]

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        ctx.db_session.execute = AsyncMock(return_value=mock_result)

        result = await tool.handler(
            {  # type: ignore[attr-defined]
                "target_type": "discussion",
                "target_id": str(uuid4()),
                "content": "Reply to discussion",
            }
        )

        text = result["content"][0]["text"]
        assert "not found" in text.lower()

    async def test_create_invalid_target_id_uuid(self) -> None:
        """Invalid UUID for target_id should be rejected."""
        ctx = _make_mock_context()
        queue: asyncio.Queue[str] = asyncio.Queue()
        tools = _capture_comment_tools(queue, tool_context=ctx)
        tool = tools["create_comment"]

        result = await tool.handler(
            {  # type: ignore[attr-defined]
                "target_type": "note",
                "target_id": "not-a-uuid",
                "content": "some content",
            }
        )

        text = result["content"][0]["text"]
        assert "invalid target_id UUID" in text


# ---------------------------------------------------------------------------
# update_comment
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestUpdateComment:
    """Test update_comment tool handler."""

    async def test_update_ai_comment(self) -> None:
        """Successfully update an AI-generated comment."""
        ctx = _make_mock_context()
        queue: asyncio.Queue[str] = asyncio.Queue()
        tools = _capture_comment_tools(queue, tool_context=ctx)
        tool = tools["update_comment"]

        comment = _mock_comment(
            content="Original AI text",
            is_ai_generated=True,
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = comment
        ctx.db_session.execute = AsyncMock(return_value=mock_result)

        result = await tool.handler(
            {  # type: ignore[attr-defined]
                "comment_id": str(comment.id),
                "content": "Revised AI text",
            }
        )

        text = result["content"][0]["text"]
        assert "update requested" in text
        assert "Approval required" in text

        # Verify SSE event
        assert not queue.empty()
        event = await queue.get()
        assert "event: content_update" in event
        event_data = json.loads(event.split("data: ")[1].strip())
        assert event_data["operation"] == "comment_updated"
        assert event_data["oldContent"] == "Original AI text"
        assert event_data["newContent"] == "Revised AI text"
        assert event_data["approval_level"] == "require_approval"

    async def test_update_user_comment_rejected(self) -> None:
        """AI cannot update a user-generated comment."""
        ctx = _make_mock_context()
        queue: asyncio.Queue[str] = asyncio.Queue()
        tools = _capture_comment_tools(queue, tool_context=ctx)
        tool = tools["update_comment"]

        comment = _mock_comment(
            content="User wrote this",
            is_ai_generated=False,
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = comment
        ctx.db_session.execute = AsyncMock(return_value=mock_result)

        result = await tool.handler(
            {  # type: ignore[attr-defined]
                "comment_id": str(comment.id),
                "content": "AI tries to change it",
            }
        )

        text = result["content"][0]["text"]
        assert "cannot update user-generated" in text.lower()

    async def test_update_not_found(self) -> None:
        """Non-existent comment should return not-found error."""
        ctx = _make_mock_context()
        queue: asyncio.Queue[str] = asyncio.Queue()
        tools = _capture_comment_tools(queue, tool_context=ctx)
        tool = tools["update_comment"]

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        ctx.db_session.execute = AsyncMock(return_value=mock_result)

        result = await tool.handler(
            {  # type: ignore[attr-defined]
                "comment_id": str(uuid4()),
                "content": "Updated content",
            }
        )

        text = result["content"][0]["text"]
        assert "not found" in text.lower()

    async def test_update_empty_content(self) -> None:
        """Empty content should be rejected."""
        ctx = _make_mock_context()
        queue: asyncio.Queue[str] = asyncio.Queue()
        tools = _capture_comment_tools(queue, tool_context=ctx)
        tool = tools["update_comment"]

        result = await tool.handler(
            {  # type: ignore[attr-defined]
                "comment_id": str(uuid4()),
                "content": "   ",
            }
        )

        text = result["content"][0]["text"]
        assert "cannot be empty" in text

    async def test_update_invalid_comment_id(self) -> None:
        """Invalid UUID for comment_id should be rejected."""
        ctx = _make_mock_context()
        queue: asyncio.Queue[str] = asyncio.Queue()
        tools = _capture_comment_tools(queue, tool_context=ctx)
        tool = tools["update_comment"]

        result = await tool.handler(
            {  # type: ignore[attr-defined]
                "comment_id": "bad-uuid",
                "content": "some content",
            }
        )

        text = result["content"][0]["text"]
        assert "invalid comment_id UUID" in text
