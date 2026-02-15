"""Unit tests for interaction_server (ask_user MCP tool).

Tests:
- handle_ask_user registers question in adapter and emits SSE
- handle_ask_user returns pending_answer status with questionId
- handle_ask_user rejects empty questions array
- handle_ask_user rejects non-list questions
- handle_ask_user normalizes messy AI-generated input
- create_interaction_server raises without user_id
- TOOL_NAMES contains expected tool name

Reference: Feature 014 (Approval Input UX)
"""

from __future__ import annotations

import asyncio
import json
from uuid import UUID, uuid4

import pytest

from pilot_space.ai.mcp.event_publisher import EventPublisher
from pilot_space.ai.mcp.interaction_server import (
    SERVER_NAME,
    TOOL_NAMES,
    create_interaction_server,
    handle_ask_user,
)


@pytest.fixture
def user_id() -> UUID:
    """Test user ID."""
    return uuid4()


@pytest.fixture
def event_queue() -> asyncio.Queue[str]:
    """Event queue for capturing SSE events."""
    return asyncio.Queue()


@pytest.fixture
def publisher(event_queue: asyncio.Queue[str]) -> EventPublisher:
    """EventPublisher backed by the test queue."""
    return EventPublisher(event_queue)


@pytest.fixture(autouse=True)
def _reset_adapter() -> None:  # type: ignore[misc]
    """Reset the singleton adapter to avoid leaking state across tests."""
    import pilot_space.ai.sdk.question_adapter as qa_mod

    qa_mod._default_adapter = None
    yield  # type: ignore[misc]
    qa_mod._default_adapter = None


class TestInteractionServerCreation:
    """Tests for create_interaction_server factory."""

    def test_raises_without_user_id(self, publisher: EventPublisher) -> None:
        """create_interaction_server raises ValueError without user_id."""
        with pytest.raises(ValueError, match="user_id is required"):
            create_interaction_server(publisher, user_id=None)

    def test_creates_server_with_valid_args(self, publisher: EventPublisher, user_id: UUID) -> None:
        """create_interaction_server returns McpSdkServerConfig."""
        server = create_interaction_server(publisher, user_id=user_id)
        assert server is not None

    def test_server_name_matches(self) -> None:
        """SERVER_NAME is pilot-interaction."""
        assert SERVER_NAME == "pilot-interaction"

    def test_tool_names_contains_ask_user(self) -> None:
        """TOOL_NAMES contains the expected ask_user tool name."""
        assert len(TOOL_NAMES) == 1
        assert TOOL_NAMES[0] == "mcp__pilot-interaction__ask_user"


class TestHandleAskUser:
    """Tests for the handle_ask_user core handler."""

    @pytest.mark.asyncio
    async def test_registers_question_and_emits_sse(
        self,
        event_queue: asyncio.Queue[str],
        publisher: EventPublisher,
        user_id: UUID,
    ) -> None:
        """handle_ask_user registers question in adapter and emits question_request SSE."""
        from pilot_space.ai.sdk.question_adapter import get_question_adapter

        result = await handle_ask_user(
            {
                "questions": [
                    {
                        "question": "Which approach?",
                        "header": "Approach",
                        "options": [
                            {"label": "Option A", "description": "Fast"},
                            {"label": "Option B", "description": "Comprehensive"},
                        ],
                        "multiSelect": False,
                    }
                ]
            },
            publisher,
            user_id,
        )

        # Verify SSE event was emitted
        assert not event_queue.empty()
        sse_event = await event_queue.get()
        assert "event: question_request" in sse_event
        assert "Which approach?" in sse_event

        # Verify result contains pending_answer status
        result_text = result["content"][0]["text"]
        result_data = json.loads(result_text)
        assert result_data["status"] == "pending_answer"
        assert "questionId" in result_data

        # Verify question registered in adapter
        adapter = get_question_adapter()
        assert adapter.get_pending_count() >= 1

    @pytest.mark.asyncio
    async def test_returns_valid_question_id(
        self,
        publisher: EventPublisher,
        user_id: UUID,
    ) -> None:
        """handle_ask_user returns a valid UUID as questionId."""
        result = await handle_ask_user(
            {
                "questions": [
                    {
                        "question": "Pick one",
                        "options": [{"label": "A"}, {"label": "B"}],
                    }
                ]
            },
            publisher,
            user_id,
        )

        result_text = result["content"][0]["text"]
        result_data = json.loads(result_text)
        # Verify questionId is a valid UUID
        UUID(result_data["questionId"])

    @pytest.mark.asyncio
    async def test_rejects_empty_questions(
        self,
        publisher: EventPublisher,
        user_id: UUID,
    ) -> None:
        """handle_ask_user returns error for empty questions array."""
        result = await handle_ask_user({"questions": []}, publisher, user_id)

        result_text = result["content"][0]["text"]
        assert "Error" in result_text
        assert "non-empty" in result_text

    @pytest.mark.asyncio
    async def test_rejects_non_list_questions(
        self,
        publisher: EventPublisher,
        user_id: UUID,
    ) -> None:
        """handle_ask_user returns error when questions is not a list."""
        result = await handle_ask_user({"questions": "not a list"}, publisher, user_id)

        result_text = result["content"][0]["text"]
        assert "Error" in result_text

    @pytest.mark.asyncio
    async def test_rejects_missing_questions_key(
        self,
        publisher: EventPublisher,
        user_id: UUID,
    ) -> None:
        """handle_ask_user returns error when questions key is missing."""
        result = await handle_ask_user({}, publisher, user_id)

        result_text = result["content"][0]["text"]
        assert "Error" in result_text

    @pytest.mark.asyncio
    async def test_normalizes_messy_input(
        self,
        event_queue: asyncio.Queue[str],
        publisher: EventPublisher,
        user_id: UUID,
    ) -> None:
        """handle_ask_user normalizes messy AI-generated question format."""
        # Messy AI-generated payload (string options, missing header)
        result = await handle_ask_user(
            {
                "questions": [
                    {
                        "question": "Which database?",
                        "options": ["PostgreSQL", "MySQL", "SQLite"],
                    }
                ]
            },
            publisher,
            user_id,
        )

        result_text = result["content"][0]["text"]
        result_data = json.loads(result_text)
        assert result_data["status"] == "pending_answer"

        # Verify SSE event was emitted with normalized data
        sse_event = await event_queue.get()
        assert "question_request" in sse_event
        assert "Which database?" in sse_event

    @pytest.mark.asyncio
    async def test_result_message_instructs_claude_to_stop(
        self,
        publisher: EventPublisher,
        user_id: UUID,
    ) -> None:
        """handle_ask_user result message tells Claude not to add commentary."""
        result = await handle_ask_user(
            {
                "questions": [
                    {
                        "question": "Choose",
                        "options": [{"label": "A"}, {"label": "B"}],
                    }
                ]
            },
            publisher,
            user_id,
        )

        result_text = result["content"][0]["text"]
        result_data = json.loads(result_text)
        assert "Do not add commentary" in result_data["message"]
