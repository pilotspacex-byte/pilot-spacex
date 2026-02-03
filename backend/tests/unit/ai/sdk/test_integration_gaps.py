"""Tests for SDK integration gap implementations.

Tests for:
- tool_result emission for non-content tools (G8)
- Enriched approval_request with all 9 fields (G9)
- parentToolUseId in content_block_start (G10)
- model in message_start (G11)
- system_prompt_base passed to configure_sdk_for_space (G7 integration)
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock
from uuid import UUID, uuid4

from pilot_space.ai.agents.pilotspace_agent_helpers import (
    transform_sdk_message,
    transform_tool_result,
)
from pilot_space.ai.sdk.hooks import (
    PermissionCheckHook,
    _build_affected_entities,
    _build_approval_sse_event,
    _classify_urgency,
)
from pilot_space.ai.sdk.sandbox_config import (
    SandboxSettings,
    SDKConfiguration,
    configure_sdk_for_space,
)

# ========================================
# Helpers
# ========================================


def _make_tool_result_msg(
    result: Any = None,
    tool_name: str = "",
    tool_use_id: str = "",
) -> MagicMock:
    """Create mock ToolResultMessage."""
    msg = MagicMock()
    msg.__class__.__name__ = "ToolResultMessage"
    type(msg).__name__ = "ToolResultMessage"
    msg.result = result
    msg.tool_name = tool_name
    msg.tool_use_id = tool_use_id
    return msg


def _make_system_init_msg(
    session_id: str = "sess-1",
    model: str | None = None,
) -> MagicMock:
    """Create mock SystemMessage for init events."""
    msg = MagicMock()
    type(msg).__name__ = "SystemMessage"
    data: dict[str, Any] = {
        "type": "system",
        "subtype": "init",
        "session_id": session_id,
    }
    if model:
        data["model"] = model
    msg.data = data
    return msg


def _make_assistant_msg_with_parent(blocks: list[Any]) -> MagicMock:
    """Create mock AssistantMessage with content blocks."""
    msg = MagicMock()
    type(msg).__name__ = "AssistantMessage"
    msg.content = blocks
    return msg


def _make_sdk_config(**overrides: Any) -> SDKConfiguration:
    """Create SDKConfiguration with sensible test defaults."""
    defaults: dict[str, Any] = {
        "cwd": "/tmp/test",
        "setting_sources": ["project"],
        "sandbox": SandboxSettings(),
        "permission_mode": "default",
        "env": {},
        "allowed_tools": ["Read", "Write"],
    }
    defaults.update(overrides)
    return SDKConfiguration(**defaults)


def _make_space_context() -> MagicMock:
    """Create mock SpaceContext for configure_sdk_for_space()."""
    ctx = MagicMock()
    ctx.path = Path("/sandbox/user1/workspace1")
    ctx.to_sdk_env.return_value = {"PILOTSPACE_USER_ID": "user1"}
    ctx.hooks_file = Path("/sandbox/user1/workspace1/.claude/hooks.json")
    return ctx


def _parse_sse_event(sse_str: str) -> tuple[str, dict[str, Any]]:
    """Parse SSE string into (event_type, data_dict)."""
    lines = sse_str.strip().split("\n")
    event_type = ""
    data_str = ""
    for line in lines:
        if line.startswith("event: "):
            event_type = line[len("event: ") :]
        elif line.startswith("data: "):
            data_str = line[len("data: ") :]
    return event_type, json.loads(data_str) if data_str else {}


# ========================================
# G8: tool_result emission for non-content tools
# ========================================


class TestToolResultEmission:
    """Tests for transform_tool_result SSE event dispatch."""

    def test_pending_apply_emits_content_update(self) -> None:
        """Tool results with pending_apply + note operation emit content_update."""
        result_data = {
            "status": "pending_apply",
            "operation": "replace_block",
            "note_id": "note-123",
            "block_id": "block-1",
            "markdown": "Updated text",
        }
        msg = _make_tool_result_msg(
            result=result_data,
            tool_name="update_note_block",
            tool_use_id="tc-1",
        )
        sse = transform_tool_result(msg)
        assert sse is not None
        event_type, data = _parse_sse_event(sse)
        assert event_type == "content_update"
        assert data["noteId"] == "note-123"
        assert data["operation"] == "replace_block"

    def test_non_content_tool_emits_tool_result(self) -> None:
        """Tool results WITHOUT pending_apply emit event: tool_result."""
        result_data = {"summary": "Found 3 matches", "count": 3}
        msg = _make_tool_result_msg(
            result=result_data,
            tool_name="find_duplicates",
            tool_use_id="tc-42",
        )
        sse = transform_tool_result(msg)
        assert sse is not None
        event_type, data = _parse_sse_event(sse)
        assert event_type == "tool_result"
        assert data["toolCallId"] == "tc-42"
        assert data["status"] == "completed"
        assert data["output"] == result_data

    def test_error_tool_result_has_failed_status(self) -> None:
        """Error tool results have status 'failed' and errorMessage."""
        result_data = {
            "is_error": True,
            "error": "Permission denied for workspace",
        }
        msg = _make_tool_result_msg(
            result=result_data,
            tool_name="create_issue_in_db",
            tool_use_id="tc-err",
        )
        sse = transform_tool_result(msg)
        assert sse is not None
        event_type, data = _parse_sse_event(sse)
        assert event_type == "tool_result"
        assert data["status"] == "failed"
        assert data["errorMessage"] == "Permission denied for workspace"
        assert "output" not in data

    def test_string_error_result_detected(self) -> None:
        """Tool results with string starting with 'Error' are detected as errors."""
        msg = _make_tool_result_msg(
            result="Error: file not found",
            tool_name="Read",
            tool_use_id="tc-str-err",
        )
        sse = transform_tool_result(msg)
        assert sse is not None
        event_type, data = _parse_sse_event(sse)
        assert event_type == "tool_result"
        assert data["status"] == "failed"
        assert data["errorMessage"] == "Error: file not found"

    def test_tool_result_generates_uuid_when_no_id(self) -> None:
        """Missing tool_use_id generates a UUID for toolCallId."""
        msg = _make_tool_result_msg(
            result={"ok": True},
            tool_name="some_tool",
            tool_use_id="",
        )
        sse = transform_tool_result(msg)
        assert sse is not None
        _, data = _parse_sse_event(sse)
        # Should be a valid UUID string
        UUID(data["toolCallId"])

    def test_completed_result_includes_output(self) -> None:
        """Non-error results include the output field."""
        result_data = {"items": [1, 2, 3]}
        msg = _make_tool_result_msg(
            result=result_data,
            tool_name="list_items",
            tool_use_id="tc-ok",
        )
        sse = transform_tool_result(msg)
        assert sse is not None
        _, data = _parse_sse_event(sse)
        assert data["status"] == "completed"
        assert data["output"] == {"items": [1, 2, 3]}


# ========================================
# G9: Enriched approval_request
# ========================================


class TestEnrichedApprovalRequest:
    """Tests for _build_approval_sse_event with all 9 fields."""

    def test_all_nine_fields_present(self) -> None:
        """Verify all 9 required fields are in the SSE event."""
        approval_id = uuid4()
        sse = _build_approval_sse_event(
            approval_id=approval_id,
            tool_name="delete_issue_from_db",
            tool_input={"issue_id": "ISS-1"},
            reason="Destructive action requires approval",
        )
        _, data = _parse_sse_event(sse)
        required_fields = {
            "requestId",
            "actionType",
            "description",
            "consequences",
            "affectedEntities",
            "urgency",
            "proposedContent",
            "expiresAt",
            "confidenceTag",
        }
        assert required_fields.issubset(data.keys())

    def test_destructive_tool_urgency_high(self) -> None:
        """Destructive tools (delete_issue_from_db) get urgency 'high'."""
        assert _classify_urgency("delete_issue_from_db") == "high"
        assert _classify_urgency("merge_pull_request") == "high"
        assert _classify_urgency("close_pull_request") == "high"

    def test_content_creation_tool_urgency_medium(self) -> None:
        """Content creation tools (create_issue_in_db) get urgency 'medium'."""
        assert _classify_urgency("create_issue_in_db") == "medium"
        assert _classify_urgency("create_subtasks") == "medium"

    def test_read_only_tool_urgency_low(self) -> None:
        """Read-only or unmapped tools get urgency 'low'."""
        assert _classify_urgency("summarize_note") == "low"
        assert _classify_urgency("Read") == "low"
        assert _classify_urgency("unknown_tool") == "low"

    def test_affected_entities_extracts_issue_id(self) -> None:
        """affectedEntities extracts issue_id from tool_input."""
        entities = _build_affected_entities(
            "delete_issue_from_db",
            {"issue_id": "ISS-99", "name": "Fix login bug"},
        )
        assert len(entities) == 1
        assert entities[0]["type"] == "issue"
        assert entities[0]["id"] == "ISS-99"
        assert entities[0]["name"] == "Fix login bug"

    def test_affected_entities_extracts_note_id(self) -> None:
        """affectedEntities extracts note_id from tool_input."""
        entities = _build_affected_entities(
            "update_note_block",
            {"note_id": "NOTE-5"},
        )
        assert len(entities) == 1
        assert entities[0]["type"] == "note"
        assert entities[0]["id"] == "NOTE-5"

    def test_affected_entities_extracts_pr_number(self) -> None:
        """affectedEntities extracts pr_number from tool_input."""
        entities = _build_affected_entities(
            "merge_pull_request",
            {"pr_number": 42},
        )
        assert len(entities) == 1
        assert entities[0]["type"] == "file"
        assert entities[0]["id"] == "42"
        assert entities[0]["name"] == "PR #42"

    def test_affected_entities_multiple_keys(self) -> None:
        """Multiple entity keys produce multiple affected entities."""
        entities = _build_affected_entities(
            "link_commit_to_issue",
            {"issue_id": "ISS-1", "note_id": "NOTE-1", "pr_number": 7},
        )
        assert len(entities) == 3
        types = {e["type"] for e in entities}
        assert types == {"issue", "note", "file"}

    def test_expires_at_approximately_24h_future(self) -> None:
        """expiresAt is approximately 24 hours in the future."""
        before = datetime.now(tz=UTC)
        sse = _build_approval_sse_event(
            approval_id=uuid4(),
            tool_name="create_issue_in_db",
            tool_input={},
            reason="test",
        )
        after = datetime.now(tz=UTC)
        _, data = _parse_sse_event(sse)
        expires = datetime.fromisoformat(data["expiresAt"])
        # expiresAt should be between before+23h and after+25h
        delta_min = (expires - after).total_seconds() / 3600
        delta_max = (expires - before).total_seconds() / 3600
        assert delta_min >= 23.0
        assert delta_max <= 25.0

    def test_action_type_uses_tool_action_mapping(self) -> None:
        """actionType maps through TOOL_ACTION_MAPPING."""
        sse = _build_approval_sse_event(
            approval_id=uuid4(),
            tool_name="delete_issue_from_db",
            tool_input={},
            reason="test",
        )
        _, data = _parse_sse_event(sse)
        expected = PermissionCheckHook.TOOL_ACTION_MAPPING["delete_issue_from_db"]
        assert data["actionType"] == expected

    def test_unmapped_tool_uses_tool_name_as_action(self) -> None:
        """Tools not in TOOL_ACTION_MAPPING use tool_name directly."""
        sse = _build_approval_sse_event(
            approval_id=uuid4(),
            tool_name="custom_new_tool",
            tool_input={},
            reason="test",
        )
        _, data = _parse_sse_event(sse)
        assert data["actionType"] == "custom_new_tool"


# ========================================
# G10: parentToolUseId in content_block_start
# ========================================


class TestParentToolUseId:
    """Tests for parentToolUseId in content_block_start events."""

    def test_dict_block_with_parent_tool_use_id(self) -> None:
        """Dict blocks with parent_tool_use_id emit parentToolUseId."""
        block = {
            "type": "text",
            "text": "Subagent output",
            "parent_tool_use_id": "tool-abc-123",
        }
        msg = _make_assistant_msg_with_parent([block])
        holder: dict[str, str | None] = {"_current_message_id": "msg-1"}
        sse = transform_sdk_message(msg, holder)
        assert sse is not None
        # Find the content_block_start event
        events = sse.split("\n\n")
        block_start = None
        for evt in events:
            if "content_block_start" in evt:
                block_start = evt
                break
        assert block_start is not None
        _, data = _parse_sse_event(block_start + "\n\n")
        assert data["parentToolUseId"] == "tool-abc-123"

    def test_object_block_with_parent_tool_use_id(self) -> None:
        """Object blocks with parent_tool_use_id attr emit parentToolUseId."""
        block = MagicMock()
        block.type = "text"
        block.text = "Output from subagent"
        block.parent_tool_use_id = "tool-xyz-789"
        msg = _make_assistant_msg_with_parent([block])
        holder: dict[str, str | None] = {"_current_message_id": "msg-2"}
        sse = transform_sdk_message(msg, holder)
        assert sse is not None
        events = sse.split("\n\n")
        block_start = None
        for evt in events:
            if "content_block_start" in evt:
                block_start = evt
                break
        assert block_start is not None
        _, data = _parse_sse_event(block_start + "\n\n")
        assert data["parentToolUseId"] == "tool-xyz-789"

    def test_block_without_parent_id_omits_field(self) -> None:
        """Blocks without parent_tool_use_id don't include parentToolUseId."""
        block = {"type": "text", "text": "Regular text"}
        msg = _make_assistant_msg_with_parent([block])
        holder: dict[str, str | None] = {"_current_message_id": "msg-3"}
        sse = transform_sdk_message(msg, holder)
        assert sse is not None
        events = sse.split("\n\n")
        block_start = None
        for evt in events:
            if "content_block_start" in evt:
                block_start = evt
                break
        assert block_start is not None
        _, data = _parse_sse_event(block_start + "\n\n")
        assert "parentToolUseId" not in data


# ========================================
# G11: model in message_start
# ========================================


class TestModelInMessageStart:
    """Tests for model field in message_start SSE events."""

    def test_init_with_model_includes_field(self) -> None:
        """Init message with model field includes it in SSE."""
        msg = _make_system_init_msg(session_id="s1", model="claude-sonnet-4-20250514")
        holder: dict[str, str | None] = {"_current_message_id": None}
        sse = transform_sdk_message(msg, holder)
        assert sse is not None
        event_type, data = _parse_sse_event(sse)
        assert event_type == "message_start"
        assert data["model"] == "claude-sonnet-4-20250514"
        assert data["sessionId"] == "s1"

    def test_init_without_model_omits_field(self) -> None:
        """Init message without model field doesn't include it."""
        msg = _make_system_init_msg(session_id="s2", model=None)
        holder: dict[str, str | None] = {"_current_message_id": None}
        sse = transform_sdk_message(msg, holder)
        assert sse is not None
        event_type, data = _parse_sse_event(sse)
        assert event_type == "message_start"
        assert "model" not in data


# ========================================
# G7 Integration: system_prompt_base via configure_sdk_for_space
# ========================================


class TestSystemPromptBaseIntegration:
    """Tests for system_prompt_base in SDKConfiguration and configure_sdk_for_space."""

    def test_to_sdk_params_includes_system_prompt_with_cache(self) -> None:
        """system_prompt with cache_control: ephemeral when base is set."""
        config = _make_sdk_config(system_prompt_base="You are PilotSpace Agent.")
        params = config.to_sdk_params()
        assert "system_prompt" in params
        assert params["system_prompt"]["content"] == "You are PilotSpace Agent."
        assert params["system_prompt"]["cache_control"] == "ephemeral"

    def test_to_sdk_params_omits_system_prompt_when_none(self) -> None:
        """system_prompt is not included when system_prompt_base is None."""
        config = _make_sdk_config(system_prompt_base=None)
        params = config.to_sdk_params()
        assert "system_prompt" not in params

    def test_configure_sdk_passes_system_prompt_base(self) -> None:
        """configure_sdk_for_space forwards system_prompt_base to config."""
        ctx = _make_space_context()
        config = configure_sdk_for_space(
            ctx,
            system_prompt_base="PilotSpace orchestrator prompt",
        )
        params = config.to_sdk_params()
        assert params["system_prompt"]["content"] == "PilotSpace orchestrator prompt"
        assert params["system_prompt"]["cache_control"] == "ephemeral"

    def test_configure_sdk_default_no_system_prompt(self) -> None:
        """Default configure_sdk_for_space has no system_prompt."""
        ctx = _make_space_context()
        config = configure_sdk_for_space(ctx)
        params = config.to_sdk_params()
        assert "system_prompt" not in params
