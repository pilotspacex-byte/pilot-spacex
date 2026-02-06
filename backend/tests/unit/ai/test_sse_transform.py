"""Unit tests for SSE transform in PilotSpaceAgent.

Tests the transform_sdk_message() method's ability to intercept MCP tool results
and emit content_update SSE events for note content operations.

Reference: Task 5 - Add content_update SSE event in backend transform
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from pilot_space.ai.agents.agent_base import AgentContext
from pilot_space.ai.agents.pilotspace_agent import PilotSpaceAgent


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
    """Create PilotSpaceAgent instance."""
    return PilotSpaceAgent(**mock_deps)


@pytest.fixture
def context() -> AgentContext:
    """Create test AgentContext."""
    return AgentContext(
        workspace_id=uuid4(),
        user_id=uuid4(),
        operation_id=uuid4(),
    )


class MockToolResultMessage:
    """Mock SDK ToolResult message with tool result payload."""

    def __init__(self, tool_name: str, result_data: dict[str, Any]) -> None:
        """Initialize mock tool result message.

        Args:
            tool_name: Name of the tool that returned the result
            result_data: Tool result data
        """
        self.tool_name = tool_name
        self.result = result_data
        # Set the __name__ to match SDK message types
        self.__class__.__name__ = "ToolResultMessage"


class TestTransformToolResults:
    """Test transform_sdk_message() handling of MCP tool results."""

    def test_detects_note_tool_result_with_pending_status(
        self, agent: PilotSpaceAgent, context: AgentContext
    ) -> None:
        """Verify detection of note tool results with pending_apply status."""
        # Arrange - create tool result from update_note_block
        tool_result = {
            "tool": "update_note_block",
            "note_id": str(uuid4()),
            "operation": "replace_block",
            "block_id": "block-123",
            "markdown": "# Updated content",
            "status": "pending_apply",
        }
        message = MockToolResultMessage("update_note_block", tool_result)

        # Act
        result = agent.transform_sdk_message(message, context)

        # Assert - should emit content_update SSE event
        assert result is not None
        assert "event: content_update" in result
        assert "data: " in result


class TestReplaceBlockTransform:
    """Test transform for replace_block operations."""

    def test_emits_content_update_for_replace_block(
        self, agent: PilotSpaceAgent, context: AgentContext
    ) -> None:
        """Verify replace_block emits content_update SSE with correct data."""
        # Arrange
        note_id = str(uuid4())
        tool_result = {
            "tool": "update_note_block",
            "note_id": note_id,
            "operation": "replace_block",
            "block_id": "block-456",
            "markdown": "## Updated heading",
            "status": "pending_apply",
        }
        message = MockToolResultMessage("update_note_block", tool_result)

        # Act
        result = agent.transform_sdk_message(message, context)

        # Assert
        assert result is not None
        assert "event: content_update" in result
        assert f'"noteId": "{note_id}"' in result
        assert '"operation": "replace_block"' in result
        assert '"blockId": "block-456"' in result
        assert '"markdown": "## Updated heading"' in result

    def test_enhance_text_emits_replace_block_event(
        self, agent: PilotSpaceAgent, context: AgentContext
    ) -> None:
        """Verify enhance_text tool emits replace_block event."""
        # Arrange
        note_id = str(uuid4())
        tool_result = {
            "tool": "enhance_text",
            "note_id": note_id,
            "operation": "replace_block",
            "block_id": "block-789",
            "markdown": "Enhanced content with better wording.",
            "status": "pending_apply",
        }
        message = MockToolResultMessage("enhance_text", tool_result)

        # Act
        result = agent.transform_sdk_message(message, context)

        # Assert
        assert result is not None
        assert "event: content_update" in result
        assert '"operation": "replace_block"' in result
        assert '"markdown": "Enhanced content with better wording."' in result


class TestAppendBlocksTransform:
    """Test transform for append_blocks operations."""

    def test_emits_content_update_for_append_blocks(
        self, agent: PilotSpaceAgent, context: AgentContext
    ) -> None:
        """Verify append_blocks emits content_update SSE with afterBlockId."""
        # Arrange
        note_id = str(uuid4())
        tool_result = {
            "tool": "update_note_block",
            "note_id": note_id,
            "operation": "append_blocks",
            "block_id": "new-block-123",
            "markdown": "- New bullet point\n- Another item",
            "after_block_id": "block-100",
            "status": "pending_apply",
        }
        message = MockToolResultMessage("update_note_block", tool_result)

        # Act
        result = agent.transform_sdk_message(message, context)

        # Assert
        assert result is not None
        assert "event: content_update" in result
        assert '"operation": "append_blocks"' in result
        assert '"afterBlockId": "block-100"' in result
        assert '"markdown": "- New bullet point' in result


class TestIssueOperationsTransform:
    """Test transform for issue creation/extraction operations."""

    def test_emits_content_update_for_create_issues(
        self, agent: PilotSpaceAgent, context: AgentContext
    ) -> None:
        """Verify extract_issues emits content_update with issue data."""
        # Arrange
        note_id = str(uuid4())
        tool_result = {
            "tool": "extract_issues",
            "note_id": note_id,
            "operation": "create_issues",
            "block_ids": ["block-1", "block-2"],
            "issues": [
                {
                    "title": "Fix authentication bug",
                    "description": "Users cannot log in",
                    "priority": "high",
                    "type": "bug",
                },
                {
                    "title": "Add dark mode",
                    "description": "Implement dark theme",
                    "priority": "medium",
                    "type": "feature",
                },
            ],
            "link_type": "extracted",
            "status": "pending_apply",
        }
        message = MockToolResultMessage("extract_issues", tool_result)

        # Act
        result = agent.transform_sdk_message(message, context)

        # Assert
        assert result is not None
        assert "event: content_update" in result
        assert '"operation": "insert_inline_issue"' in result
        assert '"title": "Fix authentication bug"' in result
        assert '"title": "Add dark mode"' in result

    def test_emits_content_update_for_single_issue(
        self, agent: PilotSpaceAgent, context: AgentContext
    ) -> None:
        """Verify create_issue_from_note emits content_update for single issue."""
        # Arrange
        note_id = str(uuid4())
        tool_result = {
            "tool": "create_issue_from_note",
            "note_id": note_id,
            "operation": "create_single_issue",
            "block_id": "block-5",
            "issue": {
                "title": "Refactor API layer",
                "description": "Simplify endpoint structure",
                "priority": "low",
                "type": "task",
            },
            "link_type": "extracted",
            "status": "pending_apply",
        }
        message = MockToolResultMessage("create_issue_from_note", tool_result)

        # Act
        result = agent.transform_sdk_message(message, context)

        # Assert
        assert result is not None
        assert "event: content_update" in result
        assert '"operation": "insert_inline_issue"' in result
        assert '"title": "Refactor API layer"' in result


class TestNonContentUpdateOperations:
    """Test operations that should NOT emit content_update events."""

    def test_search_notes_does_not_emit_content_update(
        self, agent: PilotSpaceAgent, context: AgentContext
    ) -> None:
        """Verify search_notes (read operation) does not emit content_update."""
        # Arrange
        tool_result = {
            "tool": "search_notes",
            "query": "test",
            "operation": "search",
            "status": "executed",
        }
        message = MockToolResultMessage("search_notes", tool_result)

        # Act
        result = agent.transform_sdk_message(message, context)

        # Assert - should pass through as assistant text, not content_update
        # The actual content will be provided by the transform layer
        # For now, it should not emit content_update event
        assert result is None or "event: content_update" not in result

    def test_search_issues_does_not_emit_content_update(
        self, agent: PilotSpaceAgent, context: AgentContext
    ) -> None:
        """Verify link_existing_issues (search_issues) does not emit content_update."""
        # Arrange
        tool_result = {
            "tool": "link_existing_issues",
            "note_id": str(uuid4()),
            "operation": "search_issues",
            "search_query": "authentication",
            "workspace_id": str(uuid4()),
            "status": "pending_apply",
        }
        message = MockToolResultMessage("link_existing_issues", tool_result)

        # Act
        result = agent.transform_sdk_message(message, context)

        # Assert - search results should be returned as text, not content_update
        assert result is None or "event: content_update" not in result


class TestNonToolMessages:
    """Test that non-tool messages pass through unchanged."""

    def test_system_message_passes_through(
        self, agent: PilotSpaceAgent, context: AgentContext
    ) -> None:
        """Verify SystemMessage is processed normally."""
        # Arrange
        system_msg = MagicMock()
        system_msg.__class__.__name__ = "SystemMessage"
        system_msg.data = {
            "type": "system",
            "subtype": "init",
            "session_id": "test-session",
        }

        # Act
        result = agent.transform_sdk_message(system_msg, context)

        # Assert
        assert result is not None
        assert "event: message_start" in result

    def test_assistant_message_passes_through(
        self, agent: PilotSpaceAgent, context: AgentContext
    ) -> None:
        """Verify AssistantMessage is processed normally."""
        # Arrange
        assistant_msg = MagicMock()
        assistant_msg.__class__.__name__ = "AssistantMessage"
        assistant_msg.content = [MagicMock(text="Hello, this is a response")]

        # Act
        result = agent.transform_sdk_message(assistant_msg, context)

        # Assert
        assert result is not None
        assert "event: text_delta" in result

    def test_result_message_passes_through(
        self, agent: PilotSpaceAgent, context: AgentContext
    ) -> None:
        """Verify ResultMessage is processed normally."""
        # Arrange
        result_msg = MagicMock()
        result_msg.__class__.__name__ = "ResultMessage"
        result_msg.session_id = "test-session"
        result_msg.is_error = False
        result_msg.result = None
        result_msg.usage = MagicMock()
        result_msg.usage.input_tokens = 100
        result_msg.usage.output_tokens = 50
        result_msg.usage.cached_read_input_tokens = 0
        result_msg.usage.cached_creation_input_tokens = 0
        result_msg.usage.total_cost_usd = None

        # Act
        result = agent.transform_sdk_message(result_msg, context)

        # Assert
        assert result is not None
        assert "event: message_stop" in result


class TestErrorHandling:
    """Test error handling in transform logic."""

    def test_handles_tool_result_with_missing_status(
        self, agent: PilotSpaceAgent, context: AgentContext
    ) -> None:
        """Verify graceful handling of tool result without status field."""
        # Arrange
        tool_result = {
            "tool": "update_note_block",
            "note_id": str(uuid4()),
            "operation": "replace_block",
            "block_id": "block-123",
            "markdown": "Content",
            # Missing "status": "pending_apply"
        }
        message = MockToolResultMessage("update_note_block", tool_result)

        # Act
        result = agent.transform_sdk_message(message, context)

        # Assert - should not emit content_update without pending_apply status
        assert result is None or "event: content_update" not in result

    def test_handles_tool_result_with_error_status(
        self, agent: PilotSpaceAgent, context: AgentContext
    ) -> None:
        """Verify handling of tool results with error status."""
        # Arrange
        tool_result = {
            "tool": "update_note_block",
            "error": "Invalid operation",
            "status": "error",
        }
        message = MockToolResultMessage("update_note_block", tool_result)

        # Act
        result = agent.transform_sdk_message(message, context)

        # Assert - errors should not emit content_update
        assert result is None or "event: content_update" not in result

    def test_handles_malformed_tool_result(
        self, agent: PilotSpaceAgent, context: AgentContext
    ) -> None:
        """Verify graceful handling of malformed tool result data."""
        # Arrange
        tool_result = {"invalid": "data"}
        message = MockToolResultMessage("unknown_tool", tool_result)

        # Act
        result = agent.transform_sdk_message(message, context)

        # Assert - should not crash, just return None or ignore
        assert result is None or "event: content_update" not in result
