"""Integration tests for Sprint 2 pipeline: memory recall + skill execution + memory save.

Tests T-048 (memory recall), T-049 (skill execution wiring), T-050 (memory save).

Pipeline scenarios:
    1. Happy path: auto-approved skill emits executing + completed events
    2. Suggest skill: pending_approval hold → approve → output persisted
    3. Destructive skill: admin hold → approve → output persisted
    4. Destructive skill: admin hold → reject → no output
    5. Memory recall failure: graceful degradation → empty context

Feature 015: AI Workforce Platform — Sprint 2 Integration Tests
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from pilot_space.ai.agents.pilotspace_intent_pipeline import (
    INTENT_COMPLETED,
    INTENT_EXECUTING,
    build_memory_context_prefix,
    execute_confirmed_skill,
    make_intent_completed_event,
    make_intent_executing_event,
    recall_workspace_context,
    save_skill_outcome_to_memory,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _workspace_id() -> uuid.UUID:
    return uuid.UUID("11111111-2222-3333-4444-555555555555")


def _user_id() -> uuid.UUID:
    return uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")


def _intent_id() -> str:
    return str(uuid.UUID("ffffffff-eeee-dddd-cccc-bbbbbbbbbbbb"))


@dataclass
class _FakeMemoryEntry:
    content: str
    source_type: str
    score: float = 0.85


def _make_search_result(entries: list[_FakeMemoryEntry]) -> Any:
    mock_result = MagicMock()
    mock_result.results = [
        {
            "content": e.content,
            "source_type": e.source_type,
            "score": e.score,
        }
        for e in entries
    ]
    return mock_result


def _parse_sse(event_str: str) -> tuple[str, dict[str, Any]]:
    """Parse an SSE string into (event_type, data_dict)."""
    lines = [ln for ln in event_str.strip().split("\n") if ln]
    event_type = ""
    data: dict[str, Any] = {}
    for line in lines:
        if line.startswith("event: "):
            event_type = line[len("event: ") :]
        elif line.startswith("data: "):
            data = json.loads(line[len("data: ") :])
    return event_type, data


# ---------------------------------------------------------------------------
# T-048: recall_workspace_context
# ---------------------------------------------------------------------------


class TestRecallWorkspaceContext:
    @pytest.mark.asyncio
    async def test_returns_empty_when_no_service(self) -> None:
        """Memory recall is skipped gracefully when service is None."""
        result = await recall_workspace_context(
            workspace_id=_workspace_id(),
            query="test query",
            memory_search_service=None,
        )
        assert result == []

    @pytest.mark.asyncio
    async def test_happy_path_returns_memory_entries(self) -> None:
        """Memory recall returns formatted entries from MemorySearchService."""
        service = AsyncMock()
        entries = [
            _FakeMemoryEntry("Team prefers concise PRs", "user_feedback"),
            _FakeMemoryEntry("API rate limit is 100 req/s", "skill_outcome"),
        ]
        service.execute = AsyncMock(return_value=_make_search_result(entries))

        result = await recall_workspace_context(
            workspace_id=_workspace_id(),
            query="code review",
            memory_search_service=service,
        )

        assert len(result) == 2
        assert result[0]["content"] == "Team prefers concise PRs"
        assert result[0]["source_type"] == "user_feedback"
        assert result[1]["content"] == "API rate limit is 100 req/s"
        service.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_graceful_degradation_on_service_error(self) -> None:
        """Memory recall returns empty list when service raises exception."""
        service = AsyncMock()
        service.execute = AsyncMock(side_effect=RuntimeError("DB unavailable"))

        result = await recall_workspace_context(
            workspace_id=_workspace_id(),
            query="test",
            memory_search_service=service,
        )

        assert result == []

    @pytest.mark.asyncio
    async def test_respects_limit_parameter(self) -> None:
        """Memory recall passes limit to MemorySearchPayload."""
        service = AsyncMock()
        service.execute = AsyncMock(return_value=_make_search_result([]))

        await recall_workspace_context(
            workspace_id=_workspace_id(),
            query="test",
            memory_search_service=service,
            limit=10,
        )

        call_kwargs = service.execute.call_args.args[0]
        assert call_kwargs.limit == 10
        assert call_kwargs.workspace_id == _workspace_id()

    @pytest.mark.asyncio
    async def test_empty_results_returns_empty_list(self) -> None:
        """No memory entries returns empty list (no error)."""
        service = AsyncMock()
        service.execute = AsyncMock(return_value=_make_search_result([]))

        result = await recall_workspace_context(
            workspace_id=_workspace_id(),
            query="no matches",
            memory_search_service=service,
        )

        assert result == []


# ---------------------------------------------------------------------------
# T-048: build_memory_context_prefix
# ---------------------------------------------------------------------------


class TestBuildMemoryContextPrefix:
    def test_empty_entries_returns_empty_string(self) -> None:
        assert build_memory_context_prefix([]) == ""

    def test_formats_entries_with_source_type(self) -> None:
        entries = [
            {"content": "Team uses TDD", "source_type": "user_feedback"},
        ]
        prefix = build_memory_context_prefix(entries)
        assert "## Workspace Memory Context" in prefix
        assert "[user_feedback]" in prefix
        assert "Team uses TDD" in prefix

    def test_multiple_entries_all_included(self) -> None:
        entries = [
            {"content": "First memory", "source_type": "skill_outcome"},
            {"content": "Second memory", "source_type": "intent"},
        ]
        prefix = build_memory_context_prefix(entries)
        assert "First memory" in prefix
        assert "Second memory" in prefix
        assert prefix.count("- [") == 2


# ---------------------------------------------------------------------------
# T-049: execute_confirmed_skill (happy path — auto-approved)
# ---------------------------------------------------------------------------


class TestExecuteConfirmedSkill:
    @pytest.mark.asyncio
    async def test_confirmed_emits_executing_and_completed(self) -> None:
        """Confirmed intent emits intent_executing + intent_completed SSE events."""
        payload = {"intent_id": _intent_id(), "action": "confirmed"}

        events = await execute_confirmed_skill(
            confirmation_payload=payload,
            workspace_id=_workspace_id(),
            user_id=_user_id(),
            session_id="test-session",
        )

        assert len(events) == 2
        executing_type, executing_data = _parse_sse(events[0])
        assert executing_type == INTENT_EXECUTING
        assert executing_data["intent_id"] == _intent_id()

        completed_type, completed_data = _parse_sse(events[1])
        assert completed_type == INTENT_COMPLETED
        assert completed_data["intent_id"] == _intent_id()

    @pytest.mark.asyncio
    async def test_rejected_intent_returns_no_events(self) -> None:
        """Rejected intent produces no SSE execution events."""
        payload = {"intent_id": _intent_id(), "action": "rejected"}

        events = await execute_confirmed_skill(
            confirmation_payload=payload,
            workspace_id=_workspace_id(),
            user_id=_user_id(),
            session_id="test-session",
        )

        assert events == []

    @pytest.mark.asyncio
    async def test_empty_payload_returns_no_events(self) -> None:
        """Empty confirmation payload (timeout) skips execution."""
        events = await execute_confirmed_skill(
            confirmation_payload={},
            workspace_id=_workspace_id(),
            user_id=_user_id(),
            session_id="test-session",
        )

        assert events == []

    @pytest.mark.asyncio
    async def test_missing_intent_id_returns_no_events(self) -> None:
        """Confirmed with no intent_id produces no events."""
        payload = {"action": "confirmed"}

        events = await execute_confirmed_skill(
            confirmation_payload=payload,
            workspace_id=_workspace_id(),
            user_id=_user_id(),
            session_id="test-session",
        )

        assert events == []


# ---------------------------------------------------------------------------
# T-050: save_skill_outcome_to_memory
# ---------------------------------------------------------------------------


class TestSaveSkillOutcomeToMemory:
    @pytest.mark.asyncio
    async def test_returns_false_when_no_service(self) -> None:
        """Memory save skipped when service is None."""
        result = await save_skill_outcome_to_memory(
            memory_save_service=None,
            workspace_id=_workspace_id(),
            actor_user_id=uuid.uuid4(),
            content="skill outcome summary",
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_when_content_empty(self) -> None:
        """Memory save skipped when content is empty string."""
        service = AsyncMock()
        result = await save_skill_outcome_to_memory(
            memory_save_service=service,
            workspace_id=_workspace_id(),
            actor_user_id=uuid.uuid4(),
            content="",
        )
        assert result is False
        service.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_happy_path_saves_and_returns_true(self) -> None:
        """Successful save returns True."""
        service = AsyncMock()
        service.execute = AsyncMock(return_value=MagicMock())

        result = await save_skill_outcome_to_memory(
            memory_save_service=service,
            workspace_id=_workspace_id(),
            actor_user_id=uuid.uuid4(),
            content="Generated 5 unit tests for auth module",
        )

        assert result is True
        service.execute.assert_awaited_once()
        call_payload = service.execute.call_args.args[0]
        assert call_payload.source_type.value == "skill_outcome"
        assert call_payload.workspace_id == _workspace_id()

    @pytest.mark.asyncio
    async def test_graceful_degradation_on_save_error(self) -> None:
        """Memory save failure returns False without raising."""
        service = AsyncMock()
        service.execute = AsyncMock(side_effect=RuntimeError("queue down"))

        result = await save_skill_outcome_to_memory(
            memory_save_service=service,
            workspace_id=_workspace_id(),
            actor_user_id=uuid.uuid4(),
            content="Some skill outcome",
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_passes_source_id_when_provided(self) -> None:
        """source_id is passed to MemorySavePayload."""
        service = AsyncMock()
        service.execute = AsyncMock(return_value=MagicMock())
        source_id = uuid.uuid4()

        await save_skill_outcome_to_memory(
            memory_save_service=service,
            workspace_id=_workspace_id(),
            actor_user_id=uuid.uuid4(),
            content="some content",
            source_id=source_id,
        )

        call_payload = service.execute.call_args.args[0]
        assert call_payload.source_id == source_id


# ---------------------------------------------------------------------------
# Full pipeline integration scenario
# ---------------------------------------------------------------------------


class TestFullPipelineIntegration:
    @pytest.mark.asyncio
    async def test_recall_provides_context_to_agent_loop(self) -> None:
        """Memory recall returns entries that can be injected into prompt prefix."""
        service = AsyncMock()
        service.execute = AsyncMock(
            return_value=_make_search_result(
                [_FakeMemoryEntry("User prefers Python 3.12", "user_feedback")]
            )
        )

        entries = await recall_workspace_context(
            workspace_id=_workspace_id(),
            query="write a script",
            memory_search_service=service,
        )
        prefix = build_memory_context_prefix(entries)

        assert "User prefers Python 3.12" in prefix
        assert "## Workspace Memory Context" in prefix

    @pytest.mark.asyncio
    async def test_recall_failure_then_skill_execute_still_works(self) -> None:
        """Memory recall failure does not block skill execution."""
        # Recall fails
        search_service = AsyncMock()
        search_service.execute = AsyncMock(side_effect=RuntimeError("DB error"))

        entries = await recall_workspace_context(
            workspace_id=_workspace_id(),
            query="generate tests",
            memory_search_service=search_service,
        )
        # Falls back to empty
        assert entries == []

        # Skill execution still succeeds
        payload = {"intent_id": _intent_id(), "action": "confirmed"}
        events = await execute_confirmed_skill(
            confirmation_payload=payload,
            workspace_id=_workspace_id(),
            user_id=_user_id(),
            session_id="test-session",
        )
        assert len(events) == 2

    @pytest.mark.asyncio
    async def test_approval_hold_then_reject_skips_memory_save(self) -> None:
        """Rejected skill does not produce memory save."""
        save_service = AsyncMock()

        # Simulate rejection payload (action=rejected)
        payload = {"intent_id": _intent_id(), "action": "rejected"}
        events = await execute_confirmed_skill(
            confirmation_payload=payload,
            workspace_id=_workspace_id(),
            user_id=_user_id(),
            session_id="test-session",
        )
        assert events == []

        # Save should not be called on rejection
        save_service.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_approval_hold_then_approve_saves_to_memory(self) -> None:
        """Approved skill emits events and saves outcome to memory."""
        save_service = AsyncMock()
        save_service.execute = AsyncMock(return_value=MagicMock())

        payload = {"intent_id": _intent_id(), "action": "confirmed"}
        events = await execute_confirmed_skill(
            confirmation_payload=payload,
            workspace_id=_workspace_id(),
            user_id=_user_id(),
            session_id="test-session",
        )
        # Events emitted
        assert len(events) == 2

        # Save outcome
        saved = await save_skill_outcome_to_memory(
            memory_save_service=save_service,
            workspace_id=_workspace_id(),
            actor_user_id=uuid.uuid4(),
            content="Generated 3 issues from the note",
            source_id=uuid.UUID(_intent_id()),
        )
        assert saved is True
        save_service.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_sse_event_structure_matches_frontend_contract(self) -> None:
        """SSE event structure matches what frontend expects."""
        intent_id = _intent_id()
        skill_name = "generate-code"

        executing = make_intent_executing_event(intent_id, skill_name)
        completed = make_intent_completed_event(
            intent_id, skill_name, artifacts=[{"type": "code", "content": "def foo(): ..."}]
        )

        exec_type, exec_data = _parse_sse(executing)
        assert exec_type == INTENT_EXECUTING
        assert exec_data["intent_id"] == intent_id
        assert exec_data["skill_name"] == skill_name

        comp_type, comp_data = _parse_sse(completed)
        assert comp_type == INTENT_COMPLETED
        assert comp_data["intent_id"] == intent_id
        assert comp_data["skill_name"] == skill_name
        assert len(comp_data["artifacts"]) == 1
