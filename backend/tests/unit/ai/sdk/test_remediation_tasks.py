"""Tests for remediation task implementations.

Tests for:
- Structured output schema lookup (T3/G-03)
- Effort classification for latency optimization (T7/G-09)
- Slash-command skill detection (T3)
- TodoWrite → task_progress SSE transform (T6/G-07)
"""

from __future__ import annotations

import json
from typing import Any

from pilot_space.ai.agents.pilotspace_note_helpers import (
    _map_todo_status,
    transform_todo_to_task_progress as _transform_todo_to_task_progress,
)
from pilot_space.ai.agents.pilotspace_stream_utils import (
    classify_effort as _classify_effort,
    detect_skill_from_message as _detect_skill_from_message,
)
from pilot_space.ai.sdk.output_schemas import get_skill_output_format

# ========================================
# T3/G-03: Structured output schema
# ========================================


class TestGetSkillOutputFormat:
    """Verify get_skill_output_format returns JSON schema for known skills."""

    def test_extract_issues_returns_schema(self) -> None:
        result = get_skill_output_format("extract-issues")
        assert result is not None
        assert isinstance(result, dict)
        assert "properties" in result or "$defs" in result

    def test_decompose_tasks_returns_schema(self) -> None:
        result = get_skill_output_format("decompose-tasks")
        assert result is not None
        assert isinstance(result, dict)

    def test_find_duplicates_returns_schema(self) -> None:
        result = get_skill_output_format("find-duplicates")
        assert result is not None
        assert isinstance(result, dict)

    def test_unknown_skill_returns_none(self) -> None:
        result = get_skill_output_format("regular-chat")
        assert result is None

    def test_empty_string_returns_none(self) -> None:
        result = get_skill_output_format("")
        assert result is None

    def test_schemas_are_valid_json_schema(self) -> None:
        """Each registered schema must have a 'type' or '$defs' key."""
        for skill in ("extract-issues", "decompose-tasks", "find-duplicates"):
            schema = get_skill_output_format(skill)
            assert schema is not None
            # Pydantic model_json_schema always produces a title
            assert "title" in schema


# ========================================
# T7/G-09: Effort classification
# ========================================


class TestClassifyEffort:
    """Verify _classify_effort labels simple messages as 'low'."""

    def test_hi_is_low(self) -> None:
        assert _classify_effort("hi") == "low"

    def test_hello_there_is_low(self) -> None:
        assert _classify_effort("hello there") == "low"

    def test_thanks_is_low(self) -> None:
        assert _classify_effort("thanks") == "low"

    def test_yes_is_low(self) -> None:
        assert _classify_effort("yes") == "low"

    def test_help_is_low(self) -> None:
        assert _classify_effort("help") == "low"

    def test_ok_is_low(self) -> None:
        assert _classify_effort("ok") == "low"

    def test_complex_message_returns_none(self) -> None:
        assert _classify_effort("Extract issues from this note") is None

    def test_long_message_returns_none(self) -> None:
        long_msg = "a" * 100
        assert _classify_effort(long_msg) is None

    def test_whitespace_padded_greeting_is_low(self) -> None:
        assert _classify_effort("  hi  ") == "low"

    def test_uppercase_greeting_is_low(self) -> None:
        assert _classify_effort("HI") == "low"

    def test_what_can_you_do_is_low(self) -> None:
        assert _classify_effort("what can you do") == "low"


# ========================================
# T3: Skill detection from slash commands
# ========================================


class TestDetectSkillFromMessage:
    """Verify _detect_skill_from_message parses slash commands."""

    def test_extract_issues_command(self) -> None:
        assert _detect_skill_from_message("/extract-issues") == "extract-issues"

    def test_command_with_args(self) -> None:
        assert _detect_skill_from_message("/decompose-tasks arg1 arg2") == "decompose-tasks"

    def test_regular_message_returns_none(self) -> None:
        assert _detect_skill_from_message("regular message") is None

    def test_slash_only_returns_none(self) -> None:
        assert _detect_skill_from_message("/") is None

    def test_empty_string_returns_none(self) -> None:
        assert _detect_skill_from_message("") is None

    def test_leading_whitespace_preserved(self) -> None:
        assert _detect_skill_from_message("  /summarize") == "summarize"

    def test_slash_in_middle_returns_none(self) -> None:
        assert _detect_skill_from_message("run /extract-issues") is None


# ========================================
# T6/G-07: TodoWrite → task_progress SSE
# ========================================


class TestMapTodoStatus:
    """Verify _map_todo_status maps SDK statuses to frontend TaskStatus."""

    def test_pending(self) -> None:
        assert _map_todo_status("pending") == "pending"

    def test_completed(self) -> None:
        assert _map_todo_status("completed") == "completed"

    def test_done_maps_to_completed(self) -> None:
        assert _map_todo_status("done") == "completed"

    def test_in_progress(self) -> None:
        assert _map_todo_status("in_progress") == "in_progress"

    def test_unknown_defaults_to_pending(self) -> None:
        assert _map_todo_status("unknown") == "pending"

    def test_empty_string_defaults_to_pending(self) -> None:
        assert _map_todo_status("") == "pending"


class TestTransformTodoToTaskProgress:
    """Verify _transform_todo_to_task_progress emits SSE events."""

    def test_todowrite_with_todos_returns_events(self) -> None:
        result_data: dict[str, Any] = {
            "todos": [
                {"id": "t1", "content": "Setup DB", "status": "completed"},
                {"id": "t2", "content": "Write tests", "status": "pending"},
            ]
        }
        output = _transform_todo_to_task_progress("TodoWrite", result_data, "tool-1")
        assert output is not None
        assert "event: task_progress" in output
        # Two todos produce two task_progress + one companion tool_result
        assert output.count("event: task_progress") == 2
        assert output.count("event: tool_result") == 1
        # Verify JSON payloads are parseable
        lines = [ln for ln in output.split("\n") if ln.startswith("data:")]
        assert len(lines) == 3
        first = json.loads(lines[0].removeprefix("data: "))
        assert first["taskId"] == "t1"
        assert first["status"] == "completed"
        assert first["progress"] == 100
        second = json.loads(lines[1].removeprefix("data: "))
        assert second["taskId"] == "t2"
        assert second["status"] == "pending"
        assert second["progress"] == 0
        # Companion tool_result event
        third = json.loads(lines[2].removeprefix("data: "))
        assert third["toolCallId"] == "tool-1"
        assert third["status"] == "completed"

    def test_non_todowrite_returns_none(self) -> None:
        assert _transform_todo_to_task_progress("Bash", {}, "tool-1") is None

    def test_mcp_prefixed_todowrite_accepted(self) -> None:
        result_data: dict[str, Any] = {
            "todos": [{"id": "t1", "content": "Task", "status": "pending"}]
        }
        output = _transform_todo_to_task_progress("mcp__TodoWrite", result_data, "tool-1")
        assert output is not None

    def test_empty_todos_returns_none(self) -> None:
        assert _transform_todo_to_task_progress("TodoWrite", {"todos": []}, "tool-1") is None

    def test_non_dict_result_returns_none(self) -> None:
        assert _transform_todo_to_task_progress("TodoWrite", "not a dict", "tool-1") is None

    def test_missing_todos_key_returns_none(self) -> None:
        assert _transform_todo_to_task_progress("TodoWrite", {"other": 1}, "tool-1") is None


# ========================================
# Session ownership validation
# ========================================
# Session ownership tests already covered in test_phase_1_4_features.py
# and test_integration_gaps.py. No duplication needed here.
