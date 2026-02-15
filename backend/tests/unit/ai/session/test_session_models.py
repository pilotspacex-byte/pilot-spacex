"""Unit tests for AI session data models."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pilot_space.ai.session.session_models import AIMessage


class TestAIMessageToolCalls:
    """Test AIMessage tool_calls serialization round-trip."""

    def test_tool_calls_none_by_default(self) -> None:
        msg = AIMessage(role="assistant", content="hello")
        assert msg.tool_calls is None

    def test_to_dict_excludes_tool_calls_when_none(self) -> None:
        msg = AIMessage(role="assistant", content="hello")
        d = msg.to_dict()
        assert "tool_calls" not in d

    def test_to_dict_includes_tool_calls_when_set(self) -> None:
        tc: list[dict[str, Any]] = [
            {"id": "call_1", "name": "get_issue", "input": {}, "status": "completed"}
        ]
        msg = AIMessage(role="assistant", content="hello", tool_calls=tc)
        d = msg.to_dict()
        assert d["tool_calls"] == tc

    def test_from_dict_restores_tool_calls(self) -> None:
        tc: list[dict[str, Any]] = [
            {
                "id": "call_1",
                "name": "get_issue",
                "input": {"issue_id": "123"},
                "output": {"title": "Bug"},
                "status": "completed",
            }
        ]
        data = {
            "role": "assistant",
            "content": "text",
            "timestamp": datetime.now(UTC).isoformat(),
            "tool_calls": tc,
        }
        msg = AIMessage.from_dict(data)
        assert msg.tool_calls is not None
        assert len(msg.tool_calls) == 1
        assert msg.tool_calls[0]["name"] == "get_issue"

    def test_from_dict_without_tool_calls_is_none(self) -> None:
        data = {
            "role": "user",
            "content": "hello",
            "timestamp": datetime.now(UTC).isoformat(),
        }
        msg = AIMessage.from_dict(data)
        assert msg.tool_calls is None

    def test_round_trip_preserves_tool_calls(self) -> None:
        tc: list[dict[str, Any]] = [
            {"id": "tc1", "name": "search", "input": {"q": "test"}, "status": "pending"},
            {
                "id": "tc2",
                "name": "create_issue",
                "input": {"title": "new"},
                "output": {"id": "456"},
                "status": "completed",
            },
        ]
        original = AIMessage(role="assistant", content="ok", tool_calls=tc)
        restored = AIMessage.from_dict(original.to_dict())
        assert restored.tool_calls == original.tool_calls
