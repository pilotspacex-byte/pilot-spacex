"""Tests for generate_issues_from_description MCP tool in issue_server.py.

Phase 75, Plan 01 — CIP-01, CIP-02, CIP-05.

Tests:
  1. Tool returns text_result with count of proposed issues.
  2. Tool emits issue_batch_proposal SSE event via publisher.publish.
  3. SSE event contains issues array with required fields.
  4. source_note_id from tool_context.extra["note_id"] included as sourceNoteId.
  5. When no note_id in extra, sourceNoteId is null (no error).
  6. Each proposed issue has acceptance_criteria as list of {criterion, met} dicts.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from pilot_space.ai.mcp.event_publisher import EventPublisher
from pilot_space.ai.mcp.issue_server import create_issue_tools_server
from pilot_space.ai.tools.mcp_server import ToolContext


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_publisher() -> tuple[EventPublisher, asyncio.Queue[str]]:
    """Create a publisher backed by a real asyncio Queue."""
    q: asyncio.Queue[str] = asyncio.Queue()
    return EventPublisher(q), q


def _make_tool_context(*, note_id: str | None = None) -> ToolContext:
    """Build a minimal ToolContext mock."""
    ctx = MagicMock(spec=ToolContext)
    ctx.workspace_id = str(uuid4())
    ctx.user_id = str(uuid4())
    ctx.message_id = "msg-test-123"
    ctx.extra = {}
    if note_id is not None:
        ctx.extra["note_id"] = note_id
    ctx.db_session = AsyncMock()
    return ctx


# Mock LLM response with 2 structured issues
_MOCK_LLM_ISSUES = [
    {
        "title": "Set up authentication",
        "description": "Implement JWT-based auth with refresh token rotation.",
        "acceptance_criteria": [
            {"criterion": "User can log in with email/password", "met": False},
            {"criterion": "Access token expires in 15 minutes", "met": False},
        ],
        "priority": "high",
    },
    {
        "title": "Create user profile endpoint",
        "description": "REST endpoint to fetch and update user profile data.",
        "acceptance_criteria": [
            {"criterion": "GET /users/me returns profile", "met": False},
            {"criterion": "PATCH /users/me updates profile", "met": False},
        ],
        "priority": "medium",
    },
]

_MOCK_LLM_JSON = json.dumps(_MOCK_LLM_ISSUES)


async def _call_generate_tool(
    server_config: Any,
    args: dict[str, Any],
) -> dict[str, Any]:
    """Invoke generate_issues_from_description tool on the server config.

    McpSdkServerConfig is a TypedDict with keys: 'type', 'name', 'instance'.
    The 'instance' is a mcp.server.lowlevel.server.Server. Tools are registered
    as CallToolRequest handlers. We call the handler directly with a request object.
    """
    import mcp.types as mcp_types

    instance = server_config["instance"]

    # Build a CallToolRequest targeting our tool
    request = mcp_types.CallToolRequest(
        method="tools/call",
        params=mcp_types.CallToolRequestParams(
            name="generate_issues_from_description",
            arguments=args,
        ),
    )

    # Invoke the registered handler directly
    handler = instance.request_handlers[mcp_types.CallToolRequest]
    server_result = await handler(request)

    # server_result is a ServerResult wrapping CallToolResult
    inner = server_result.root  # type: ignore[attr-defined]
    return {
        "content": [
            {"type": c.type, "text": getattr(c, "text", "")}
            for c in inner.content
        ]
    }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def publisher_and_queue() -> tuple[EventPublisher, asyncio.Queue[str]]:
    return _make_publisher()


@pytest.fixture()
def tool_context_with_note() -> ToolContext:
    return _make_tool_context(note_id=str(uuid4()))


@pytest.fixture()
def tool_context_no_note() -> ToolContext:
    return _make_tool_context(note_id=None)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_issues_returns_text_result_with_count(
    publisher_and_queue: tuple[EventPublisher, asyncio.Queue[str]],
    tool_context_with_note: ToolContext,
) -> None:
    """Test 1: Tool returns text_result with count of proposed issues."""
    publisher, _ = publisher_and_queue

    with patch(
        "pilot_space.ai.mcp.issue_server._call_llm_for_issues",
        new=AsyncMock(return_value=_MOCK_LLM_ISSUES),
    ):
        server_config = create_issue_tools_server(publisher, tool_context=tool_context_with_note)
        result = await _call_generate_tool(
            server_config,
            {"description": "Build an auth system", "project_id": str(uuid4())},
        )

    assert "content" in result
    content_list = result["content"]
    assert len(content_list) >= 1
    text = content_list[0]["text"]
    assert "2" in text  # count of proposed issues
    assert "roposed" in text  # "Proposed X issues" text


@pytest.mark.asyncio
async def test_generate_issues_emits_batch_proposal_sse_event(
    publisher_and_queue: tuple[EventPublisher, asyncio.Queue[str]],
    tool_context_with_note: ToolContext,
) -> None:
    """Test 2: Tool emits issue_batch_proposal SSE event via publisher.publish."""
    publisher, queue = publisher_and_queue

    with patch(
        "pilot_space.ai.mcp.issue_server._call_llm_for_issues",
        new=AsyncMock(return_value=_MOCK_LLM_ISSUES),
    ):
        server_config = create_issue_tools_server(publisher, tool_context=tool_context_with_note)
        await _call_generate_tool(
            server_config,
            {"description": "Build an auth system", "project_id": str(uuid4())},
        )

    # Check SSE was emitted
    assert not queue.empty(), "Expected SSE event in queue"
    sse_raw = await queue.get()
    assert "event: issue_batch_proposal" in sse_raw
    assert "data: " in sse_raw


@pytest.mark.asyncio
async def test_generate_issues_sse_contains_required_fields(
    publisher_and_queue: tuple[EventPublisher, asyncio.Queue[str]],
    tool_context_with_note: ToolContext,
) -> None:
    """Test 3: SSE event contains issues array with title, description, acceptance_criteria, priority."""
    publisher, queue = publisher_and_queue
    project_id = str(uuid4())

    with patch(
        "pilot_space.ai.mcp.issue_server._call_llm_for_issues",
        new=AsyncMock(return_value=_MOCK_LLM_ISSUES),
    ):
        server_config = create_issue_tools_server(publisher, tool_context=tool_context_with_note)
        await _call_generate_tool(
            server_config,
            {"description": "Build an auth system", "project_id": project_id},
        )

    sse_raw = await queue.get()
    # Parse data portion
    data_line = next(line for line in sse_raw.split("\n") if line.startswith("data: "))
    data = json.loads(data_line[len("data: "):])

    assert "issues" in data
    assert len(data["issues"]) == 2

    first_issue = data["issues"][0]
    assert "title" in first_issue
    assert "description" in first_issue
    assert "acceptance_criteria" in first_issue
    assert "priority" in first_issue

    assert data["projectId"] == project_id
    assert "messageId" in data


@pytest.mark.asyncio
async def test_generate_issues_includes_source_note_id(
    publisher_and_queue: tuple[EventPublisher, asyncio.Queue[str]],
) -> None:
    """Test 4: source_note_id from tool_context.extra["note_id"] is included as sourceNoteId."""
    publisher, queue = publisher_and_queue
    note_id = str(uuid4())
    ctx = _make_tool_context(note_id=note_id)

    with patch(
        "pilot_space.ai.mcp.issue_server._call_llm_for_issues",
        new=AsyncMock(return_value=_MOCK_LLM_ISSUES),
    ):
        server_config = create_issue_tools_server(publisher, tool_context=ctx)
        await _call_generate_tool(
            server_config,
            {"description": "Build an auth system", "project_id": str(uuid4())},
        )

    sse_raw = await queue.get()
    data_line = next(line for line in sse_raw.split("\n") if line.startswith("data: "))
    data = json.loads(data_line[len("data: "):])

    assert data["sourceNoteId"] == note_id


@pytest.mark.asyncio
async def test_generate_issues_source_note_id_null_when_no_note(
    publisher_and_queue: tuple[EventPublisher, asyncio.Queue[str]],
) -> None:
    """Test 5: When tool_context.extra has no note_id, sourceNoteId is null (no error)."""
    publisher, queue = publisher_and_queue
    ctx = _make_tool_context(note_id=None)

    with patch(
        "pilot_space.ai.mcp.issue_server._call_llm_for_issues",
        new=AsyncMock(return_value=_MOCK_LLM_ISSUES),
    ):
        server_config = create_issue_tools_server(publisher, tool_context=ctx)
        result = await _call_generate_tool(
            server_config,
            {"description": "Build an auth system", "project_id": str(uuid4())},
        )

    # Should not error
    assert "content" in result

    sse_raw = await queue.get()
    data_line = next(line for line in sse_raw.split("\n") if line.startswith("data: "))
    data = json.loads(data_line[len("data: "):])

    assert data["sourceNoteId"] is None


@pytest.mark.asyncio
async def test_generate_issues_acceptance_criteria_structure(
    publisher_and_queue: tuple[EventPublisher, asyncio.Queue[str]],
    tool_context_with_note: ToolContext,
) -> None:
    """Test 6: Each proposed issue has acceptance_criteria as list of {criterion, met} dicts."""
    publisher, queue = publisher_and_queue

    with patch(
        "pilot_space.ai.mcp.issue_server._call_llm_for_issues",
        new=AsyncMock(return_value=_MOCK_LLM_ISSUES),
    ):
        server_config = create_issue_tools_server(publisher, tool_context=tool_context_with_note)
        await _call_generate_tool(
            server_config,
            {"description": "Build an auth system", "project_id": str(uuid4())},
        )

    sse_raw = await queue.get()
    data_line = next(line for line in sse_raw.split("\n") if line.startswith("data: "))
    data = json.loads(data_line[len("data: "):])

    for issue in data["issues"]:
        assert isinstance(issue["acceptance_criteria"], list)
        for ac in issue["acceptance_criteria"]:
            assert "criterion" in ac
            assert "met" in ac
            assert isinstance(ac["criterion"], str)
            assert isinstance(ac["met"], bool)
