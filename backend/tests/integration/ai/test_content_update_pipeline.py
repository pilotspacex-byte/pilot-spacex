"""Integration tests for the content_update SSE pipeline.

Tests the full pipeline from MCP tool result → _transform_tool_result() → SSE event string,
validating the entire agent method chain for all 3 operation types:
replace_block, append_blocks, and insert_inline_issue.

Unlike unit tests in tests/unit/ai/test_sse_transform.py which test individual methods,
these integration tests verify the complete transform_sdk_message → _transform_tool_result
→ emit_*_event chain, parsing and validating the final SSE output.

Reference: content_update SSE flow between backend and frontend.
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from pilot_space.ai.agents.agent_base import AgentContext
from pilot_space.ai.agents.pilotspace_agent import PilotSpaceAgent

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_deps() -> dict[str, Any]:
    """Create mock dependencies for PilotSpaceAgent."""
    return {
        "tool_registry": MagicMock(),
        "provider_selector": MagicMock(),
        "cost_tracker": MagicMock(),
        "resilient_executor": MagicMock(),
        "permission_handler": MagicMock(),
        "session_handler": None,
        "skill_registry": MagicMock(),
        "space_manager": None,
    }


@pytest.fixture
def agent(mock_deps: dict[str, Any]) -> PilotSpaceAgent:
    """Create PilotSpaceAgent instance with mock dependencies."""
    return PilotSpaceAgent(**mock_deps)


@pytest.fixture
def context() -> AgentContext:
    """Create test AgentContext."""
    return AgentContext(
        workspace_id=uuid4(),
        user_id=uuid4(),
        operation_id=uuid4(),
    )


class _MockToolResultMessage:
    """Simulate SDK ToolResultMessage with tool result payload.

    Mirrors the minimal interface of claude-agent-sdk ToolResultMessage
    that transform_sdk_message inspects.
    """

    def __init__(self, tool_name: str, result_data: dict[str, Any]) -> None:
        self.tool_name = tool_name
        self.result = result_data
        self.__class__.__name__ = "ToolResultMessage"


def _parse_sse_event(raw: str) -> tuple[str, dict[str, Any]]:
    """Parse a single SSE event string into (event_type, data_dict).

    Handles the ``event: <type>\ndata: <json>\n\n`` format.
    For multi-event strings (multiple issues), parses only the first event.

    Args:
        raw: Raw SSE-formatted string.

    Returns:
        Tuple of (event type, parsed JSON data).

    Raises:
        ValueError: When the SSE string is malformed.
    """
    lines = raw.strip().split("\n")
    event_type = ""
    data_str = ""
    for line in lines:
        if line.startswith("event: "):
            event_type = line[len("event: ") :]
        elif line.startswith("data: "):
            data_str = line[len("data: ") :]
            break  # take first data line

    if not event_type or not data_str:
        msg = f"Malformed SSE: {raw!r}"
        raise ValueError(msg)

    return event_type, json.loads(data_str)


def _parse_all_sse_events(raw: str) -> list[tuple[str, dict[str, Any]]]:
    """Parse a multi-event SSE string into a list of (event_type, data_dict).

    Events are separated by double newlines in SSE protocol.

    Args:
        raw: Raw SSE-formatted string (may contain multiple events).

    Returns:
        List of (event type, parsed JSON data) tuples.
    """
    results: list[tuple[str, dict[str, Any]]] = []
    # Split on double newline to get individual events
    segments = [s.strip() for s in raw.split("\n\n") if s.strip()]
    for segment in segments:
        event_type = ""
        data_str = ""
        for line in segment.split("\n"):
            if line.startswith("event: "):
                event_type = line[len("event: ") :]
            elif line.startswith("data: "):
                data_str = line[len("data: ") :]
        if event_type and data_str:
            results.append((event_type, json.loads(data_str)))
    return results


# ---------------------------------------------------------------------------
# Shared field validation helper
# ---------------------------------------------------------------------------

_REQUIRED_CONTENT_UPDATE_FIELDS = {
    "noteId",
    "operation",
    "blockId",
    "markdown",
    "content",
    "issueData",
    "afterBlockId",
}


def _assert_content_update_structure(data: dict[str, Any]) -> None:
    """Assert that content_update SSE data has all required fields.

    Frontend ContentUpdateData interface requires every field present
    (nullable fields must still appear as ``null``).

    Args:
        data: Parsed JSON data from SSE event.
    """
    missing = _REQUIRED_CONTENT_UPDATE_FIELDS - set(data.keys())
    assert not missing, f"Missing required fields: {missing}"


# ===========================================================================
# Test: replace_block full pipeline
# ===========================================================================


class TestReplaceBlockPipeline:
    """Integration tests for the replace_block operation pipeline.

    Verifies tool result → transform_sdk_message → _transform_tool_result
    → _emit_replace_block_event → SSE string.
    """

    def test_update_note_block_produces_valid_sse(
        self, agent: PilotSpaceAgent, context: AgentContext
    ) -> None:
        """Full pipeline: update_note_block with replace_block operation."""
        note_id = str(uuid4())
        block_id = "block-abc-123"
        markdown = "## Refactored heading\n\nParagraph text."

        tool_result = {
            "tool": "update_note_block",
            "note_id": note_id,
            "operation": "replace_block",
            "block_id": block_id,
            "markdown": markdown,
            "status": "pending_apply",
        }
        message = _MockToolResultMessage("update_note_block", tool_result)
        raw = agent.transform_sdk_message(message, context)

        assert raw is not None
        event_type, data = _parse_sse_event(raw)

        assert event_type == "content_update"
        _assert_content_update_structure(data)
        assert data["noteId"] == note_id
        assert data["operation"] == "replace_block"
        assert data["blockId"] == block_id
        assert data["markdown"] == markdown
        assert data["content"] is None
        assert data["issueData"] is None
        assert data["afterBlockId"] is None

    def test_enhance_text_produces_valid_sse(
        self, agent: PilotSpaceAgent, context: AgentContext
    ) -> None:
        """Full pipeline: enhance_text tool emits replace_block content_update."""
        note_id = str(uuid4())
        block_id = "block-enhance-1"
        markdown = "The quick **brown** fox jumped over the lazy dog."

        tool_result = {
            "tool": "enhance_text",
            "note_id": note_id,
            "operation": "replace_block",
            "block_id": block_id,
            "markdown": markdown,
            "status": "pending_apply",
        }
        message = _MockToolResultMessage("enhance_text", tool_result)
        raw = agent.transform_sdk_message(message, context)

        assert raw is not None
        event_type, data = _parse_sse_event(raw)

        assert event_type == "content_update"
        _assert_content_update_structure(data)
        assert data["operation"] == "replace_block"
        assert data["markdown"] == markdown
        assert data["blockId"] == block_id

    def test_replace_block_with_special_characters(
        self, agent: PilotSpaceAgent, context: AgentContext
    ) -> None:
        """Verify markdown with special JSON chars is properly escaped."""
        note_id = str(uuid4())
        markdown = 'Code: `const x = {"key": "value"}`\nNewline\tTab'

        tool_result = {
            "tool": "update_note_block",
            "note_id": note_id,
            "operation": "replace_block",
            "block_id": "block-special",
            "markdown": markdown,
            "status": "pending_apply",
        }
        message = _MockToolResultMessage("update_note_block", tool_result)
        raw = agent.transform_sdk_message(message, context)

        assert raw is not None
        _, data = _parse_sse_event(raw)

        # json.loads should round-trip correctly
        assert data["markdown"] == markdown


# ===========================================================================
# Test: append_blocks full pipeline
# ===========================================================================


class TestAppendBlocksPipeline:
    """Integration tests for the append_blocks operation pipeline."""

    def test_append_blocks_with_after_block_id(
        self, agent: PilotSpaceAgent, context: AgentContext
    ) -> None:
        """Full pipeline: append_blocks with afterBlockId."""
        note_id = str(uuid4())
        after_block_id = "block-anchor-99"
        markdown = "- New bullet point\n- Another item\n- Third item"

        tool_result = {
            "tool": "update_note_block",
            "note_id": note_id,
            "operation": "append_blocks",
            "block_id": "new-block-id",
            "markdown": markdown,
            "after_block_id": after_block_id,
            "status": "pending_apply",
        }
        message = _MockToolResultMessage("update_note_block", tool_result)
        raw = agent.transform_sdk_message(message, context)

        assert raw is not None
        event_type, data = _parse_sse_event(raw)

        assert event_type == "content_update"
        _assert_content_update_structure(data)
        assert data["noteId"] == note_id
        assert data["operation"] == "append_blocks"
        assert data["afterBlockId"] == after_block_id
        assert data["markdown"] == markdown
        assert data["content"] is None
        assert data["issueData"] is None

    def test_append_blocks_without_after_block_id(
        self, agent: PilotSpaceAgent, context: AgentContext
    ) -> None:
        """append_blocks with no after_block_id should still produce valid SSE."""
        note_id = str(uuid4())
        markdown = "Appended paragraph at end."

        tool_result = {
            "tool": "update_note_block",
            "note_id": note_id,
            "operation": "append_blocks",
            "block_id": "new-block-456",
            "markdown": markdown,
            "status": "pending_apply",
            # No after_block_id → frontend appends at end
        }
        message = _MockToolResultMessage("update_note_block", tool_result)
        raw = agent.transform_sdk_message(message, context)

        assert raw is not None
        _, data = _parse_sse_event(raw)

        assert data["operation"] == "append_blocks"
        assert data["afterBlockId"] is None
        _assert_content_update_structure(data)

    def test_append_blocks_multiline_markdown(
        self, agent: PilotSpaceAgent, context: AgentContext
    ) -> None:
        """Verify multiline markdown preserves all content."""
        note_id = str(uuid4())
        markdown = (
            "## Section Title\n\n"
            "Paragraph one with **bold** text.\n\n"
            "```python\ndef hello():\n    print('world')\n```\n\n"
            "Final paragraph."
        )

        tool_result = {
            "tool": "update_note_block",
            "note_id": note_id,
            "operation": "append_blocks",
            "block_id": "new-multi",
            "markdown": markdown,
            "after_block_id": "block-anchor",
            "status": "pending_apply",
        }
        message = _MockToolResultMessage("update_note_block", tool_result)
        raw = agent.transform_sdk_message(message, context)

        assert raw is not None
        _, data = _parse_sse_event(raw)

        assert data["markdown"] == markdown
        assert "```python" in data["markdown"]


# ===========================================================================
# Test: insert_inline_issue full pipeline
# ===========================================================================


class TestInsertInlineIssuePipeline:
    """Integration tests for the insert_inline_issue operation pipeline."""

    def test_single_issue_creation(self, agent: PilotSpaceAgent, context: AgentContext) -> None:
        """Full pipeline: create_single_issue → insert_inline_issue SSE."""
        note_id = str(uuid4())
        issue_data = {
            "title": "Refactor API layer",
            "description": "Simplify endpoint structure",
            "priority": "low",
            "type": "task",
        }

        tool_result = {
            "tool": "create_issue_from_note",
            "note_id": note_id,
            "operation": "create_single_issue",
            "block_id": "block-src-5",
            "issue": issue_data,
            "link_type": "extracted",
            "status": "pending_apply",
        }
        message = _MockToolResultMessage("create_issue_from_note", tool_result)
        raw = agent.transform_sdk_message(message, context)

        assert raw is not None
        event_type, data = _parse_sse_event(raw)

        assert event_type == "content_update"
        _assert_content_update_structure(data)
        assert data["noteId"] == note_id
        assert data["operation"] == "insert_inline_issue"
        assert data["blockId"] == "block-src-5"
        assert data["markdown"] is None
        assert data["content"] is None
        assert data["issueData"] == issue_data
        assert data["afterBlockId"] is None

    def test_multiple_issues_creates_multiple_events(
        self, agent: PilotSpaceAgent, context: AgentContext
    ) -> None:
        """Full pipeline: create_issues with multiple issues emits one event per issue."""
        note_id = str(uuid4())
        issues = [
            {
                "title": "Fix auth bug",
                "description": "Login fails",
                "priority": "high",
                "type": "bug",
            },
            {
                "title": "Add dark mode",
                "description": "Dark theme",
                "priority": "medium",
                "type": "feature",
            },
            {"title": "Update docs", "description": "API docs", "priority": "low", "type": "task"},
        ]
        block_ids = ["block-1", "block-2", "block-3"]

        tool_result = {
            "tool": "extract_issues",
            "note_id": note_id,
            "operation": "create_issues",
            "block_ids": block_ids,
            "issues": issues,
            "link_type": "extracted",
            "status": "pending_apply",
        }
        message = _MockToolResultMessage("extract_issues", tool_result)
        raw = agent.transform_sdk_message(message, context)

        assert raw is not None

        # Should produce 3 separate SSE events
        events = _parse_all_sse_events(raw)
        assert len(events) == 3

        for idx, (event_type, data) in enumerate(events):
            assert event_type == "content_update"
            _assert_content_update_structure(data)
            assert data["noteId"] == note_id
            assert data["operation"] == "insert_inline_issue"
            assert data["blockId"] == block_ids[idx]
            assert data["issueData"] == issues[idx]
            assert data["markdown"] is None
            assert data["content"] is None
            assert data["afterBlockId"] is None

    def test_multiple_issues_with_fewer_block_ids(
        self, agent: PilotSpaceAgent, context: AgentContext
    ) -> None:
        """When block_ids < issues count, extra issues get null blockId."""
        note_id = str(uuid4())
        issues = [
            {"title": "Issue A", "priority": "high", "type": "bug"},
            {"title": "Issue B", "priority": "low", "type": "task"},
        ]
        block_ids = ["block-only-1"]

        tool_result = {
            "tool": "extract_issues",
            "note_id": note_id,
            "operation": "create_issues",
            "block_ids": block_ids,
            "issues": issues,
            "link_type": "extracted",
            "status": "pending_apply",
        }
        message = _MockToolResultMessage("extract_issues", tool_result)
        raw = agent.transform_sdk_message(message, context)

        assert raw is not None
        events = _parse_all_sse_events(raw)
        assert len(events) == 2

        # First issue has block_id, second gets None
        assert events[0][1]["blockId"] == "block-only-1"
        assert events[1][1]["blockId"] is None

    def test_empty_issues_list_returns_empty(
        self, agent: PilotSpaceAgent, context: AgentContext
    ) -> None:
        """create_issues with empty issues list returns empty string."""
        note_id = str(uuid4())

        tool_result = {
            "tool": "extract_issues",
            "note_id": note_id,
            "operation": "create_issues",
            "block_ids": [],
            "issues": [],
            "link_type": "extracted",
            "status": "pending_apply",
        }
        message = _MockToolResultMessage("extract_issues", tool_result)
        raw = agent.transform_sdk_message(message, context)

        # Empty issues → empty string
        assert raw == ""


# ===========================================================================
# Test: non-content operations pass through unchanged
# ===========================================================================


class TestNonContentOperationsPassThrough:
    """Verify non-note-tool results and non-content operations do not emit content_update."""

    def test_read_content_operation_does_not_emit_content_update(
        self, agent: PilotSpaceAgent, context: AgentContext
    ) -> None:
        """summarize_note (read_content) should not produce content_update."""
        tool_result = {
            "tool": "summarize_note",
            "note_id": str(uuid4()),
            "operation": "read_content",
            "status": "pending_apply",
        }
        message = _MockToolResultMessage("summarize_note", tool_result)
        raw = agent.transform_sdk_message(message, context)

        assert raw is None or "event: content_update" not in raw

    def test_search_issues_does_not_emit_content_update(
        self, agent: PilotSpaceAgent, context: AgentContext
    ) -> None:
        """link_existing_issues (search_issues) should not produce content_update."""
        tool_result = {
            "tool": "link_existing_issues",
            "note_id": str(uuid4()),
            "operation": "search_issues",
            "search_query": "authentication",
            "workspace_id": str(uuid4()),
            "status": "pending_apply",
        }
        message = _MockToolResultMessage("link_existing_issues", tool_result)
        raw = agent.transform_sdk_message(message, context)

        assert raw is None or "event: content_update" not in raw

    def test_system_message_not_intercepted_as_content_update(
        self, agent: PilotSpaceAgent, context: AgentContext
    ) -> None:
        """SystemMessage should emit message_start, not content_update."""
        system_msg = MagicMock()
        system_msg.__class__.__name__ = "SystemMessage"
        system_msg.data = {
            "type": "system",
            "subtype": "init",
            "session_id": "sess-abc",
        }

        raw = agent.transform_sdk_message(system_msg, context)

        assert raw is not None
        assert "event: message_start" in raw
        assert "event: content_update" not in raw

    def test_assistant_message_not_intercepted_as_content_update(
        self, agent: PilotSpaceAgent, context: AgentContext
    ) -> None:
        """AssistantMessage should emit text_delta, not content_update."""
        assistant_msg = MagicMock()
        assistant_msg.__class__.__name__ = "AssistantMessage"
        assistant_msg.content = [MagicMock(text="Some AI response text")]

        raw = agent.transform_sdk_message(assistant_msg, context)

        assert raw is not None
        assert "event: text_delta" in raw
        assert "event: content_update" not in raw

    def test_result_message_not_intercepted_as_content_update(
        self, agent: PilotSpaceAgent, context: AgentContext
    ) -> None:
        """ResultMessage should emit message_stop, not content_update."""
        result_msg = MagicMock()
        result_msg.__class__.__name__ = "ResultMessage"
        result_msg.session_id = "sess-xyz"
        result_msg.is_error = False
        result_msg.usage = MagicMock()
        result_msg.usage.input_tokens = 200
        result_msg.usage.output_tokens = 80
        result_msg.usage.total_cost_usd = None

        raw = agent.transform_sdk_message(result_msg, context)

        assert raw is not None
        assert "event: message_stop" in raw
        assert "event: content_update" not in raw


# ===========================================================================
# Test: error/edge cases in the pipeline
# ===========================================================================


class TestPipelineEdgeCases:
    """Edge cases and error conditions in the content_update pipeline."""

    def test_missing_status_field_returns_none(
        self, agent: PilotSpaceAgent, context: AgentContext
    ) -> None:
        """Tool result without status='pending_apply' should return None."""
        tool_result = {
            "tool": "update_note_block",
            "note_id": str(uuid4()),
            "operation": "replace_block",
            "block_id": "block-123",
            "markdown": "Content",
        }
        message = _MockToolResultMessage("update_note_block", tool_result)
        raw = agent.transform_sdk_message(message, context)

        assert raw is None

    def test_error_status_returns_none(self, agent: PilotSpaceAgent, context: AgentContext) -> None:
        """Tool result with status='error' should not produce content_update."""
        tool_result = {
            "tool": "update_note_block",
            "error": "Something failed",
            "status": "error",
        }
        message = _MockToolResultMessage("update_note_block", tool_result)
        raw = agent.transform_sdk_message(message, context)

        assert raw is None

    def test_missing_note_id_returns_none(
        self, agent: PilotSpaceAgent, context: AgentContext
    ) -> None:
        """Tool result without note_id should return None."""
        tool_result = {
            "tool": "update_note_block",
            "operation": "replace_block",
            "block_id": "block-123",
            "markdown": "Content",
            "status": "pending_apply",
            # Missing note_id
        }
        message = _MockToolResultMessage("update_note_block", tool_result)
        raw = agent.transform_sdk_message(message, context)

        assert raw is None

    def test_malformed_result_data_returns_none(
        self, agent: PilotSpaceAgent, context: AgentContext
    ) -> None:
        """Completely malformed result dict should not crash."""
        tool_result = {"random_key": 42}
        message = _MockToolResultMessage("unknown_tool", tool_result)
        raw = agent.transform_sdk_message(message, context)

        assert raw is None

    def test_non_dict_result_returns_none(
        self, agent: PilotSpaceAgent, context: AgentContext
    ) -> None:
        """Non-dict result attribute should be handled gracefully."""
        message = _MockToolResultMessage("some_tool", {})
        # Override result to be non-dict
        message.result = "string_result"  # type: ignore[assignment]
        raw = agent.transform_sdk_message(message, context)

        assert raw is None

    def test_unknown_operation_returns_none(
        self, agent: PilotSpaceAgent, context: AgentContext
    ) -> None:
        """Known tool with unknown operation should return None."""
        tool_result = {
            "tool": "update_note_block",
            "note_id": str(uuid4()),
            "operation": "unknown_operation",
            "block_id": "block-1",
            "markdown": "Content",
            "status": "pending_apply",
        }
        message = _MockToolResultMessage("update_note_block", tool_result)
        raw = agent.transform_sdk_message(message, context)

        assert raw is None


# ===========================================================================
# Test: SSE format compliance
# ===========================================================================


class TestSSEFormatCompliance:
    """Verify SSE output strictly matches the protocol format expected by the frontend.

    Frontend SSEClient expects: ``event: <type>\\ndata: <json>\\n\\n``
    """

    def test_sse_event_ends_with_double_newline(
        self, agent: PilotSpaceAgent, context: AgentContext
    ) -> None:
        """SSE events must end with \\n\\n per SSE protocol."""
        note_id = str(uuid4())
        tool_result = {
            "tool": "update_note_block",
            "note_id": note_id,
            "operation": "replace_block",
            "block_id": "block-1",
            "markdown": "text",
            "status": "pending_apply",
        }
        message = _MockToolResultMessage("update_note_block", tool_result)
        raw = agent.transform_sdk_message(message, context)

        assert raw is not None
        assert raw.endswith("\n\n"), f"SSE must end with \\n\\n, got: {raw[-10:]!r}"

    def test_sse_data_is_valid_json(self, agent: PilotSpaceAgent, context: AgentContext) -> None:
        """SSE data line must contain valid JSON parseable by frontend."""
        note_id = str(uuid4())
        tool_result = {
            "tool": "update_note_block",
            "note_id": note_id,
            "operation": "replace_block",
            "block_id": "block-json",
            "markdown": "test",
            "status": "pending_apply",
        }
        message = _MockToolResultMessage("update_note_block", tool_result)
        raw = agent.transform_sdk_message(message, context)

        assert raw is not None
        # Extract data line
        for line in raw.split("\n"):
            if line.startswith("data: "):
                data_str = line[len("data: ") :]
                parsed = json.loads(data_str)
                assert isinstance(parsed, dict)
                break
        else:
            pytest.fail("No data: line found in SSE event")

    def test_sse_uses_camel_case_fields(
        self, agent: PilotSpaceAgent, context: AgentContext
    ) -> None:
        """SSE data must use camelCase matching frontend ContentUpdateData interface."""
        note_id = str(uuid4())
        tool_result = {
            "tool": "update_note_block",
            "note_id": note_id,
            "operation": "append_blocks",
            "block_id": "new-b",
            "markdown": "content",
            "after_block_id": "block-anchor",
            "status": "pending_apply",
        }
        message = _MockToolResultMessage("update_note_block", tool_result)
        raw = agent.transform_sdk_message(message, context)

        assert raw is not None
        _, data = _parse_sse_event(raw)

        # Must use camelCase, not snake_case
        assert "noteId" in data
        assert "blockId" in data
        assert "afterBlockId" in data
        assert "issueData" in data
        assert "note_id" not in data
        assert "block_id" not in data
        assert "after_block_id" not in data
        assert "issue_data" not in data

    def test_multi_event_sse_each_has_correct_format(
        self, agent: PilotSpaceAgent, context: AgentContext
    ) -> None:
        """Multi-issue SSE should produce individually parseable events."""
        note_id = str(uuid4())
        issues = [
            {"title": "Issue 1", "type": "bug"},
            {"title": "Issue 2", "type": "task"},
        ]

        tool_result = {
            "tool": "extract_issues",
            "note_id": note_id,
            "operation": "create_issues",
            "block_ids": ["b1", "b2"],
            "issues": issues,
            "link_type": "extracted",
            "status": "pending_apply",
        }
        message = _MockToolResultMessage("extract_issues", tool_result)
        raw = agent.transform_sdk_message(message, context)

        assert raw is not None

        events = _parse_all_sse_events(raw)
        assert len(events) == 2

        for event_type, data in events:
            assert event_type == "content_update"
            _assert_content_update_structure(data)
