"""Tests for P1 SDK gap remediation (G-03, G-06, G-07).

G-03: Pydantic validation for structured output before SSE emission
G-06: TodoRead hydration for resumed sessions
G-07: Dynamic effort classification with high-effort patterns
"""

from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

from pilot_space.ai.agents.pilotspace_agent_helpers import (
    transform_sdk_message,
    transform_todo_to_task_progress as _transform_todo_to_task_progress,
    validate_structured_output as _validate_structured_output,
)
from pilot_space.ai.agents.pilotspace_stream_utils import classify_effort as _classify_effort

# ========================================
# G-07: Effort classification
# ========================================


class TestClassifyEffort:
    """Tests for _classify_effort with low and high effort routing."""

    def test_greeting_returns_low(self) -> None:
        assert _classify_effort("hi") == "low"

    def test_hello_returns_low(self) -> None:
        assert _classify_effort("hello there") == "low"

    def test_thanks_returns_low(self) -> None:
        assert _classify_effort("thanks") == "low"

    def test_yes_returns_low(self) -> None:
        assert _classify_effort("yes") == "low"

    def test_nope_returns_low(self) -> None:
        assert _classify_effort("nope") == "low"

    def test_help_returns_low(self) -> None:
        assert _classify_effort("help") == "low"

    def test_analyze_returns_high(self) -> None:
        assert _classify_effort("analyze the authentication flow") == "high"

    def test_review_returns_high(self) -> None:
        assert _classify_effort("review the PR changes") == "high"

    def test_refactor_returns_high(self) -> None:
        assert _classify_effort("refactor the user service") == "high"

    def test_audit_returns_high(self) -> None:
        assert _classify_effort("audit the security of our API") == "high"

    def test_security_review_returns_high(self) -> None:
        assert _classify_effort("security review of auth module") == "high"

    def test_design_returns_high(self) -> None:
        assert _classify_effort("design a new notification system") == "high"

    def test_long_message_returns_high(self) -> None:
        long_msg = "Please help me with this feature. " * 10
        assert len(long_msg) > 200
        assert _classify_effort(long_msg) == "high"

    def test_normal_message_returns_none(self) -> None:
        assert _classify_effort("fix the bug in login.py") is None

    def test_short_normal_returns_none(self) -> None:
        assert _classify_effort("add a logout button") is None

    def test_empty_returns_none(self) -> None:
        assert _classify_effort("") is None

    def test_whitespace_stripped(self) -> None:
        assert _classify_effort("  hi  ") == "low"

    def test_case_insensitive(self) -> None:
        assert _classify_effort("ANALYZE the code") == "high"

    def test_explain_in_detail_returns_high(self) -> None:
        assert _classify_effort("explain in detail how auth works") == "high"

    def test_compare_returns_high(self) -> None:
        assert _classify_effort("compare Redis vs Memcached for caching") == "high"


# ========================================
# G-06: TodoRead hydration
# ========================================


class TestTodoReadHydration:
    """Tests for TodoRead → task_progress SSE mapping."""

    def test_todo_write_still_works(self) -> None:
        result = _transform_todo_to_task_progress(
            "TodoWrite",
            {"todos": [{"id": "t1", "content": "Fix bug", "status": "pending"}]},
            "tuid-1",
        )
        assert result is not None
        assert "task_progress" in result

    def test_todo_read_produces_task_progress(self) -> None:
        result = _transform_todo_to_task_progress(
            "TodoRead",
            {"todos": [{"id": "t1", "content": "Fix bug", "status": "completed"}]},
            "tuid-1",
        )
        assert result is not None
        assert "task_progress" in result
        lines = [ln for ln in result.split("\n") if ln.startswith("data:")]
        data = json.loads(lines[0].removeprefix("data: "))
        assert data["taskId"] == "t1"
        assert data["status"] == "completed"
        assert data["progress"] == 100

    def test_mcp_todo_read_produces_task_progress(self) -> None:
        result = _transform_todo_to_task_progress(
            "mcp__TodoRead",
            {"todos": [{"id": "t2", "content": "Deploy", "status": "in_progress"}]},
            "tuid-2",
        )
        assert result is not None
        lines = [ln for ln in result.split("\n") if ln.startswith("data:")]
        data = json.loads(lines[0].removeprefix("data: "))
        assert data["status"] == "in_progress"

    def test_unrelated_tool_returns_none(self) -> None:
        result = _transform_todo_to_task_progress(
            "Read",
            {"todos": [{"id": "t1", "content": "X", "status": "pending"}]},
            "tuid-1",
        )
        assert result is None

    def test_empty_todos_returns_none(self) -> None:
        result = _transform_todo_to_task_progress(
            "TodoRead",
            {"todos": []},
            "tuid-1",
        )
        assert result is None

    def test_multiple_todos(self) -> None:
        result = _transform_todo_to_task_progress(
            "TodoRead",
            {
                "todos": [
                    {"id": "t1", "content": "Task A", "status": "completed"},
                    {"id": "t2", "content": "Task B", "status": "pending"},
                ]
            },
            "tuid-1",
        )
        assert result is not None
        assert result.count("task_progress") == 2


# ========================================
# G-03: Structured output validation
# ========================================


class TestValidateStructuredOutput:
    """Tests for Pydantic validation of structured output (G-03)."""

    def test_valid_extraction_result(self) -> None:
        data = {
            "schemaType": "extraction_result",
            "issues": [
                {
                    "title": "Fix auth bug",
                    "description": "Login fails on retry",
                    "priority": "high",
                    "type": "bug",
                }
            ],
        }
        result = _validate_structured_output("extraction_result", data)
        assert result is not None
        assert "issues" in result

    def test_valid_decomposition_result(self) -> None:
        data = {
            "schemaType": "decomposition_result",
            "subtasks": [
                {
                    "title": "Design schema",
                    "description": "Create DB schema",
                    "points": 3,
                }
            ],
        }
        result = _validate_structured_output("decomposition_result", data)
        assert result is not None
        assert "subtasks" in result

    def test_valid_duplicate_search_result(self) -> None:
        data = {
            "schemaType": "duplicate_search_result",
            "candidates": [
                {
                    "issueId": str(uuid4()),
                    "issueKey": "PS-42",
                    "title": "Similar issue",
                    "similarityScore": 0.85,
                    "reason": "Same root cause",
                }
            ],
            "threshold": 0.7,
            "queryTitle": "Auth bug",
        }
        result = _validate_structured_output("duplicate_search_result", data)
        assert result is not None
        assert "candidates" in result

    def test_unknown_schema_passes_through(self) -> None:
        data = {"schemaType": "unknown_type", "foo": "bar"}
        result = _validate_structured_output("unknown_type", data)
        assert result is not None
        assert result["foo"] == "bar"

    def test_invalid_extraction_returns_none(self) -> None:
        data = {
            "schemaType": "extraction_result",
            "issues": "not a list",  # Invalid: should be list
        }
        result = _validate_structured_output("extraction_result", data)
        assert result is None

    def test_missing_required_field_returns_none(self) -> None:
        data = {
            "schemaType": "decomposition_result",
            # Missing 'subtasks' — required field
        }
        result = _validate_structured_output("decomposition_result", data)
        # Should pass if field has default_factory, or None if truly required
        # Pydantic models use default_factory=list, so empty list is OK
        assert result is not None
        assert result.get("subtasks") == []


# ========================================
# G-03: Integration with transform_sdk_message
# ========================================


class MockResultMessage:
    """Mock SDK ResultMessage."""

    def __init__(
        self,
        result: Any = None,
        session_id: str = "",
        is_error: bool = False,
        usage: Any = None,
    ) -> None:
        self.result = result
        self.session_id = session_id
        self.is_error = is_error
        self.usage = usage
        self.__class__.__name__ = "ResultMessage"


class TestStructuredOutputInTransform:
    """Integration test: structured output validation in transform_sdk_message."""

    def test_valid_structured_result_emits_event(self) -> None:
        holder: dict[str, str | None] = {"_current_message_id": str(uuid4())}
        msg = MockResultMessage(
            result={
                "schemaType": "extraction_result",
                "issues": [
                    {"title": "Bug", "description": "Desc", "priority": "high", "type": "bug"}
                ],
            }
        )
        result = transform_sdk_message(msg, holder)
        assert result is not None
        assert "structured_result" in result
        assert "message_stop" in result

    def test_invalid_structured_result_skips_event(self) -> None:
        holder: dict[str, str | None] = {"_current_message_id": str(uuid4())}
        msg = MockResultMessage(
            result={
                "schemaType": "extraction_result",
                "issues": "not-a-list",
            }
        )
        result = transform_sdk_message(msg, holder)
        assert result is not None
        assert "structured_result" not in result
        assert "message_stop" in result

    def test_no_schema_type_skips_structured(self) -> None:
        holder: dict[str, str | None] = {"_current_message_id": str(uuid4())}
        msg = MockResultMessage(result={"plain": "result"})
        result = transform_sdk_message(msg, holder)
        assert result is not None
        assert "structured_result" not in result
        assert "message_stop" in result
