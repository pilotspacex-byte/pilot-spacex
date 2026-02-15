"""Unit tests for QuestionAdapter.

Tests:
- register_question creates UUID and stores in registry (SYNC)
- mark_resolved returns PendingQuestion and removes from registry
- mark_resolved returns None for unknown questionId
- mark_resolved returns None for user_id mismatch
- cleanup_expired removes old questions
- get_question_status returns metadata
- start/stop cleanup task lifecycle
- can_use_tool returns PermissionResultDeny as safety net for AskUserQuestion
- can_use_tool passes through non-AskUserQuestion tools

Reference: specs/014-approval-input-ux/spec.md (T05)
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from pilot_space.ai.sdk.question_adapter import (
    PendingQuestion,
    Question,
    QuestionAdapter,
    QuestionOption,
    normalize_questions,
)


@pytest.fixture
def adapter() -> QuestionAdapter:
    """Create QuestionAdapter instance."""
    return QuestionAdapter()


@pytest.fixture
def sample_questions() -> list[dict]:
    """Sample question data in SDK format."""
    return [
        {
            "question": "Select approval action",
            "options": [
                {"label": "Approve", "description": "Accept the changes"},
                {"label": "Reject", "description": "Deny the changes"},
                {"label": "Modify", "description": "Request changes"},
            ],
            "multi_select": False,
            "header": "Approval Decision",
        }
    ]


@pytest.fixture
def test_user_id() -> UUID:
    """Test user ID for question ownership."""
    return uuid4()


def test_register_question_creates_uuid_and_stores(
    adapter: QuestionAdapter,
    sample_questions: list[dict],
    test_user_id: UUID,
) -> None:
    """Test register_question creates UUID, stores in registry, returns SSE event."""
    question_id, sse_event = adapter.register_question(
        message_id="msg_123",
        tool_call_id="tool_456",
        questions=sample_questions,
        user_id=test_user_id,
    )

    # Verify UUID was generated
    assert isinstance(question_id, UUID)

    # Verify SSE event contains expected fields
    assert "event: question_request" in sse_event
    assert str(question_id) in sse_event
    assert "tool_456" in sse_event

    # Verify question registered
    assert adapter.get_pending_count() == 1


@pytest.mark.asyncio
async def test_mark_resolved_returns_pending_question(
    adapter: QuestionAdapter,
    sample_questions: list[dict],
    test_user_id: UUID,
) -> None:
    """Test mark_resolved returns PendingQuestion and removes from registry."""
    question_id, _ = adapter.register_question(
        message_id="msg_123",
        tool_call_id="tool_456",
        questions=sample_questions,
        user_id=test_user_id,
    )

    resolved = await adapter.mark_resolved(question_id, test_user_id)

    # Verify PendingQuestion returned with correct tool_call_id
    assert resolved is not None
    assert isinstance(resolved, PendingQuestion)
    assert resolved.tool_call_id == "tool_456"
    assert resolved.question_id == question_id
    assert resolved.user_id == test_user_id

    # Verify question removed from registry
    assert adapter.get_pending_count() == 0


@pytest.mark.asyncio
async def test_mark_resolved_unknown_question_returns_none(
    adapter: QuestionAdapter,
    test_user_id: UUID,
) -> None:
    """Test mark_resolved returns None for unknown questionId."""
    unknown_id = UUID("00000000-0000-0000-0000-000000000000")
    resolved = await adapter.mark_resolved(unknown_id, test_user_id)

    assert resolved is None


@pytest.mark.asyncio
async def test_mark_resolved_already_resolved_returns_none(
    adapter: QuestionAdapter,
    sample_questions: list[dict],
    test_user_id: UUID,
) -> None:
    """Test mark_resolved returns None if already resolved."""
    question_id, _ = adapter.register_question(
        message_id="msg_123",
        tool_call_id="tool_456",
        questions=sample_questions,
        user_id=test_user_id,
    )

    # Resolve once
    resolved1 = await adapter.mark_resolved(question_id, test_user_id)
    assert resolved1 is not None

    # Try to resolve again (should fail - already resolved)
    resolved2 = await adapter.mark_resolved(question_id, test_user_id)
    assert resolved2 is None


@pytest.mark.asyncio
async def test_mark_resolved_user_mismatch_returns_none(
    adapter: QuestionAdapter,
    sample_questions: list[dict],
    test_user_id: UUID,
) -> None:
    """Test mark_resolved returns None when user_id does not match."""
    question_id, _ = adapter.register_question(
        message_id="msg_123",
        tool_call_id="tool_456",
        questions=sample_questions,
        user_id=test_user_id,
    )

    # Try to resolve with different user_id
    wrong_user_id = uuid4()
    resolved = await adapter.mark_resolved(question_id, wrong_user_id)

    # Should fail due to user mismatch
    assert resolved is None

    # Question should still be pending (not removed)
    assert adapter.get_pending_count() == 1


@pytest.mark.asyncio
async def test_cleanup_expired_removes_old_questions(
    adapter: QuestionAdapter,
    sample_questions: list[dict],
    test_user_id: UUID,
) -> None:
    """Test cleanup_expired removes questions older than timeout."""
    adapter.register_question(
        message_id="msg_123",
        tool_call_id="tool_456",
        questions=sample_questions,
        user_id=test_user_id,
    )

    assert adapter.get_pending_count() == 1

    # Cleanup with timeout=0 (should remove immediately)
    removed_count = await adapter.cleanup_expired(timeout_seconds=0.0)

    assert removed_count == 1
    assert adapter.get_pending_count() == 0


@pytest.mark.asyncio
async def test_cleanup_expired_preserves_recent_questions(
    adapter: QuestionAdapter,
    sample_questions: list[dict],
    test_user_id: UUID,
) -> None:
    """Test cleanup_expired preserves questions within timeout."""
    adapter.register_question(
        message_id="msg_123",
        tool_call_id="tool_456",
        questions=sample_questions,
        user_id=test_user_id,
    )

    # Cleanup with very long timeout (should not remove)
    removed_count = await adapter.cleanup_expired(timeout_seconds=9999.0)

    assert removed_count == 0
    assert adapter.get_pending_count() == 1


@pytest.mark.asyncio
async def test_get_question_status_returns_metadata(
    adapter: QuestionAdapter,
    sample_questions: list[dict],
    test_user_id: UUID,
) -> None:
    """Test get_question_status returns metadata for pending question."""
    question_id, _ = adapter.register_question(
        message_id="msg_123",
        tool_call_id="tool_456",
        questions=sample_questions,
        user_id=test_user_id,
    )

    status = await adapter.get_question_status(question_id)

    assert status is not None
    assert status["question_id"] == str(question_id)
    assert status["tool_call_id"] == "tool_456"
    assert status["question_count"] == 1
    assert status["age_seconds"] >= 0.0


@pytest.mark.asyncio
async def test_get_question_status_returns_none_for_unknown(
    adapter: QuestionAdapter,
) -> None:
    """Test get_question_status returns None for unknown questionId."""
    unknown_id = UUID("00000000-0000-0000-0000-000000000000")
    status = await adapter.get_question_status(unknown_id)

    assert status is None


def test_register_question_normalizes_invalid_to_empty_question(
    adapter: QuestionAdapter,
    test_user_id: UUID,
) -> None:
    """Test register_question normalizes invalid data to empty question (graceful degradation)."""
    # Invalid question (missing required fields) — normalization handles it
    invalid_questions = [{"invalid": "data"}]

    question_id, sse_event = adapter.register_question(
        message_id="msg_123",
        tool_call_id="tool_456",
        questions=invalid_questions,
        user_id=test_user_id,
    )

    # Normalization converts to empty question (no error)
    assert "event: question_request" in sse_event
    assert adapter.get_pending_count() == 1


def test_register_question_skips_non_dict_items(
    adapter: QuestionAdapter,
    test_user_id: UUID,
) -> None:
    """Test register_question skips non-dict items in questions list."""
    # Mix of dict and non-dict items
    mixed_questions = [
        {"question": "Valid?", "options": [{"label": "Yes"}]},
        "not a dict",
        42,
    ]

    question_id, sse_event = adapter.register_question(
        message_id="msg_123",
        tool_call_id="tool_456",
        questions=mixed_questions,  # type: ignore[arg-type]
        user_id=test_user_id,
    )

    # Only the valid dict item should be included
    assert "event: question_request" in sse_event
    assert adapter.get_pending_count() == 1


@pytest.mark.asyncio
async def test_get_pending_sse_events_returns_events_for_recovery(
    adapter: QuestionAdapter,
    sample_questions: list[dict],
    test_user_id: UUID,
) -> None:
    """Test get_pending_sse_events returns SSE strings for session recovery."""
    q1_id, _ = adapter.register_question(
        message_id="msg_1",
        tool_call_id="tool_1",
        questions=sample_questions,
        user_id=test_user_id,
    )
    q2_id, _ = adapter.register_question(
        message_id="msg_2",
        tool_call_id="tool_2",
        questions=sample_questions,
        user_id=test_user_id,
    )

    events = await adapter.get_pending_sse_events()

    # Should return 2 events
    assert len(events) == 2

    # Each event should be a valid SSE string with question_request type
    for event_str in events:
        assert "event: question_request" in event_str
        assert "data:" in event_str

    # Verify both question IDs appear in events
    combined = "".join(events)
    assert str(q1_id) in combined
    assert str(q2_id) in combined


@pytest.mark.asyncio
async def test_get_pending_sse_events_empty_when_no_pending(
    adapter: QuestionAdapter,
) -> None:
    """Test get_pending_sse_events returns empty list when no pending questions."""
    events = await adapter.get_pending_sse_events()
    assert events == []


@pytest.mark.asyncio
async def test_pydantic_model_validation() -> None:
    """Test Pydantic models for question data."""
    # Test QuestionOption
    option = QuestionOption(label="Test", description="Test desc")
    assert option.label == "Test"
    assert option.description == "Test desc"

    # Test Question with alias support
    question_data = {
        "question": "Choose one",
        "options": [{"label": "A"}, {"label": "B"}],
        "multi_select": True,
        "header": "Section 1",
    }
    question = Question.model_validate(question_data)
    assert question.question == "Choose one"
    assert len(question.options) == 2
    assert question.multiSelect is True
    assert question.header == "Section 1"


@pytest.mark.asyncio
async def test_start_stop_cleanup_task(
    adapter: QuestionAdapter,
) -> None:
    """Test start and stop cleanup task lifecycle."""
    import asyncio

    # Start cleanup task
    await adapter.start_cleanup_task(interval_seconds=0.1)

    # Verify task is running
    assert adapter._cleanup_task is not None
    assert not adapter._cleanup_task.done()

    # Let it run briefly
    await asyncio.sleep(0.15)

    # Stop cleanup task
    await adapter.stop_cleanup_task()

    # Verify task is done
    assert adapter._cleanup_task.done()


def test_register_question_is_sync(
    adapter: QuestionAdapter,
    sample_questions: list[dict],
    test_user_id: UUID,
) -> None:
    """Test register_question works in synchronous context (no await needed)."""
    # This test verifies the method is truly sync (critical for transform chain)
    question_id, sse_event = adapter.register_question(
        message_id="msg_sync",
        tool_call_id="tool_sync",
        questions=sample_questions,
        user_id=test_user_id,
    )

    assert isinstance(question_id, UUID)
    assert "event: question_request" in sse_event
    assert adapter.get_pending_count() == 1


# ---------------------------------------------------------------------------
# Normalization tests
# ---------------------------------------------------------------------------


def test_normalize_string_options_to_objects() -> None:
    """Test normalization converts string options to {label, description} objects."""
    raw = [
        {
            "question": "Pick one",
            "options": ["Option A", "Option B", "Option C"],
            "header": "Pick",
        }
    ]
    result = normalize_questions(raw)

    assert len(result) == 1
    assert result[0]["question"] == "Pick one"
    for opt in result[0]["options"]:
        assert "label" in opt
        assert "description" in opt
    assert result[0]["options"][0]["label"] == "Option A"


def test_normalize_text_field_mapped_to_question() -> None:
    """Test normalization maps 'text' field to 'question'."""
    raw = [
        {
            "text": "Which approach?",
            "options": [{"label": "A", "description": "Desc A"}],
        }
    ]
    result = normalize_questions(raw)

    assert result[0]["question"] == "Which approach?"


def test_normalize_missing_header_auto_generated() -> None:
    """Test normalization generates header from question text when missing."""
    raw = [
        {
            "question": "Security approach for auth?",
            "options": [{"label": "JWT"}, {"label": "Session"}],
        }
    ]
    result = normalize_questions(raw)

    assert result[0]["header"] is not None
    assert len(result[0]["header"]) <= 12


def test_normalize_truncates_to_max_4_questions() -> None:
    """Test normalization truncates to max 4 questions."""
    raw = [{"question": f"Q{i}", "options": [{"label": "A"}]} for i in range(10)]
    result = normalize_questions(raw)

    assert len(result) == 4


def test_normalize_strips_unknown_fields() -> None:
    """Test normalization strips extra fields like id, type, label at question level."""
    raw = [
        {
            "id": "q1",
            "type": "single_select",
            "label": "Some label used as question",
            "question": "Actual question?",
            "options": [{"label": "A", "description": "D"}],
        }
    ]
    result = normalize_questions(raw)

    # Only known fields should remain
    assert set(result[0].keys()) == {"question", "options", "multiSelect", "header", "skipWhen"}


def test_normalize_defaults_multiselect_false() -> None:
    """Test normalization defaults multiSelect to False."""
    raw = [{"question": "Q?", "options": [{"label": "A"}]}]
    result = normalize_questions(raw)

    assert result[0]["multiSelect"] is False


def test_normalize_auto_appends_other_option() -> None:
    """Test normalization auto-appends 'Other' free-text option if not present."""
    raw = [
        {
            "question": "Pick priority",
            "options": [{"label": "High"}, {"label": "Low"}],
        }
    ]
    result = normalize_questions(raw)

    options = result[0]["options"]
    assert len(options) == 3
    assert options[-1]["label"] == "Other"
    assert options[-1]["description"] == "Provide your own answer"


def test_normalize_does_not_duplicate_existing_other() -> None:
    """Test normalization does not add 'Other' when already present."""
    raw = [
        {
            "question": "Pick one",
            "options": [
                {"label": "A"},
                {"label": "Other", "description": "Custom input"},
            ],
        }
    ]
    result = normalize_questions(raw)

    options = result[0]["options"]
    assert len(options) == 2
    assert options[-1]["label"] == "Other"


def test_normalize_detects_other_case_insensitive() -> None:
    """Test normalization detects 'other' regardless of case."""
    raw = [
        {
            "question": "Pick one",
            "options": [{"label": "A"}, {"label": "other (custom)"}],
        }
    ]
    result = normalize_questions(raw)

    # Should not add another "Other" since one already starts with "other"
    assert len(result[0]["options"]) == 2


def test_normalize_skipwhen_passthrough() -> None:
    """Test normalization passes through skipWhen conditions."""
    raw = [
        {
            "question": "Q1",
            "options": [{"label": "A"}, {"label": "B"}],
            "skipWhen": [{"questionIndex": 0, "selectedLabel": "A"}],
        }
    ]
    result = normalize_questions(raw)

    assert "skipWhen" in result[0]
    assert len(result[0]["skipWhen"]) == 1
    assert result[0]["skipWhen"][0]["questionIndex"] == 0
    assert result[0]["skipWhen"][0]["selectedLabel"] == "A"


def test_normalize_skipwhen_snake_case_alias() -> None:
    """Test normalization accepts skip_when (snake_case) as alias for skipWhen."""
    raw = [
        {
            "question": "Q1",
            "options": [{"label": "A"}],
            "skip_when": [{"questionIndex": 1, "selectedLabel": "X"}],
        }
    ]
    result = normalize_questions(raw)

    assert len(result[0]["skipWhen"]) == 1


def test_normalize_skipwhen_defaults_to_empty() -> None:
    """Test normalization defaults skipWhen to empty list when not provided."""
    raw = [{"question": "Q?", "options": [{"label": "A"}]}]
    result = normalize_questions(raw)

    assert result[0]["skipWhen"] == []


def test_skipwhen_pydantic_model_validation() -> None:
    """Test SkipCondition Pydantic model validates correctly."""
    from pilot_space.ai.sdk.question_adapter import SkipCondition

    # camelCase
    cond = SkipCondition(questionIndex=0, selectedLabel="Yes")
    assert cond.questionIndex == 0
    assert cond.selectedLabel == "Yes"

    # snake_case alias
    cond2 = SkipCondition.model_validate({"question_index": 1, "selected_label": "No"})
    assert cond2.questionIndex == 1
    assert cond2.selectedLabel == "No"


def test_register_question_normalizes_before_validation(
    adapter: QuestionAdapter,
    test_user_id: UUID,
) -> None:
    """Test register_question normalizes messy AI output into valid schema."""
    # Simulate actual AI-generated payload (wrong format)
    messy_questions = [
        {
            "id": "oauth_scope",
            "label": "OAuth Integration Scope",
            "question": "Should OAuth be part of Phase 1?",
            "type": "single_select",
            "options": [
                "Include in Phase 1",
                "Defer to Phase 2",
                "Exclude entirely",
            ],
        }
    ]

    question_id, sse_event = adapter.register_question(
        message_id="msg_messy",
        tool_call_id="tool_messy",
        questions=messy_questions,
        user_id=test_user_id,
    )

    # Should succeed (not return error event)
    assert "event: question_request" in sse_event
    assert "event: error" not in sse_event
    assert adapter.get_pending_count() == 1


# ---------------------------------------------------------------------------
# get_question tests (non-destructive peek)
# ---------------------------------------------------------------------------


def test_get_question_returns_pending_without_removing(
    adapter: QuestionAdapter,
    sample_questions: list[dict],
    test_user_id: UUID,
) -> None:
    """Test get_question returns PendingQuestion without removing from registry."""
    question_id, _ = adapter.register_question(
        message_id="msg_123",
        tool_call_id="tool_456",
        questions=sample_questions,
        user_id=test_user_id,
    )

    result = adapter.get_question(question_id)

    assert result is not None
    assert isinstance(result, PendingQuestion)
    assert result.question_id == question_id
    assert result.tool_call_id == "tool_456"
    assert len(result.questions) == 1
    assert result.questions[0].question == "Select approval action"

    # Verify question is still in registry (non-destructive)
    assert adapter.get_pending_count() == 1


def test_get_question_unknown_id_returns_none(
    adapter: QuestionAdapter,
) -> None:
    """Test get_question returns None for unknown questionId."""
    unknown_id = UUID("00000000-0000-0000-0000-000000000000")
    result = adapter.get_question(unknown_id)
    assert result is None


# ---------------------------------------------------------------------------
# create_can_use_tool_callback tests (safety net for AskUserQuestion)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_can_use_tool_callback_non_ask_user_passes_through(
    test_user_id: UUID,
) -> None:
    """Test can_use_tool callback passes through non-AskUserQuestion tools."""
    import asyncio

    from claude_agent_sdk.types import PermissionResultAllow, ToolPermissionContext

    from pilot_space.ai.sdk.question_adapter import create_can_use_tool_callback

    queue: asyncio.Queue[str] = asyncio.Queue()
    callback = create_can_use_tool_callback(queue, test_user_id)

    result = await callback(
        "some_other_tool",
        {"key": "value"},
        ToolPermissionContext(),
    )

    assert isinstance(result, PermissionResultAllow)
    assert result.updated_input is None


@pytest.mark.asyncio
async def test_can_use_tool_callback_ask_user_returns_deny_as_safety_net(
    test_user_id: UUID,
) -> None:
    """Test can_use_tool callback returns Deny for AskUserQuestion (safety net).

    The primary question flow uses the ask_user MCP tool. If Claude somehow
    still calls AskUserQuestion, the callback denies with a redirect message.
    """
    import asyncio

    from claude_agent_sdk.types import PermissionResultDeny, ToolPermissionContext

    from pilot_space.ai.sdk.question_adapter import create_can_use_tool_callback

    queue: asyncio.Queue[str] = asyncio.Queue()
    callback = create_can_use_tool_callback(queue, test_user_id)

    raw_input = {
        "questions": [
            {
                "question": "Pick one?",
                "options": ["A", "B"],
                "header": "Pick",
            }
        ],
    }

    result = await callback(
        "AskUserQuestion",
        raw_input,
        ToolPermissionContext(),
    )

    # Verify Deny result with redirect message
    assert isinstance(result, PermissionResultDeny)
    assert "ask_user" in result.message

    # Verify NO SSE event was emitted (safety net does not register questions)
    assert queue.empty()
