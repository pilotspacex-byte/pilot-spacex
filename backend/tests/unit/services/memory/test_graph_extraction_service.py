"""Unit tests for GraphExtractionService.

Tests cover:
- Decision extraction from conversation
- User preference extraction with user_id binding
- Empty result when api_key is None (BYOK pattern)
- Graceful handling of malformed JSON from LLM
- Pattern extraction with confidence scores
- Empty messages → empty result
- Full flow with all extraction types combined
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from pilot_space.application.services.memory.graph_extraction_service import (
    ConversationExtractionPayload,
    ExtractionResult,
    GraphExtractionService,
    _build_conversation_text,
    _build_pattern_nodes,
    _build_preference_nodes,
    _extract_json_object,
    _parse_llm_response,
)
from pilot_space.domain.graph_node import NodeType

# ---------------------------------------------------------------------------
# Unit tests: _build_conversation_text
# ---------------------------------------------------------------------------


class TestBuildConversationText:
    """Tests for conversation text serialization."""

    def test_single_message(self) -> None:
        messages = [{"role": "user", "content": "Hello there"}]
        result = _build_conversation_text(messages)
        assert "User: Hello there" in result

    def test_multiple_messages(self) -> None:
        messages = [
            {"role": "user", "content": "What should we use?"},
            {"role": "assistant", "content": "We decided to use Redis"},
        ]
        result = _build_conversation_text(messages)
        assert "User:" in result
        assert "Assistant:" in result
        assert "Redis" in result

    def test_empty_messages(self) -> None:
        result = _build_conversation_text([])
        assert result == ""

    def test_strips_whitespace_from_content(self) -> None:
        messages = [{"role": "user", "content": "  trimmed  "}]
        result = _build_conversation_text(messages)
        assert "trimmed" in result


# ---------------------------------------------------------------------------
# Unit tests: _parse_llm_response
# ---------------------------------------------------------------------------


class TestParseLlmResponse:
    """Tests for LLM response JSON parsing."""

    def test_valid_json_dict(self) -> None:
        raw = json.dumps({"decisions": [{"text": "Use Redis", "context": "caching"}]})
        result = _parse_llm_response(raw)
        assert "decisions" in result
        assert result["decisions"][0]["text"] == "Use Redis"

    def test_markdown_fenced_json(self) -> None:
        inner = json.dumps({"patterns": [{"text": "Always test first", "confidence": 0.9}]})
        raw = f"```json\n{inner}\n```"
        result = _parse_llm_response(raw)
        assert "patterns" in result

    def test_plain_fenced_json(self) -> None:
        inner = json.dumps({"decisions": []})
        raw = f"```\n{inner}\n```"
        result = _parse_llm_response(raw)
        assert "decisions" in result

    def test_invalid_json_returns_empty_dict(self) -> None:
        result = _parse_llm_response("this is not json at all")
        assert result == {}

    def test_json_array_returns_empty_dict(self) -> None:
        # LLM returns a list instead of dict — reject it
        result = _parse_llm_response(json.dumps([1, 2, 3]))
        assert result == {}

    def test_empty_string_returns_empty_dict(self) -> None:
        result = _parse_llm_response("")
        assert result == {}

    def test_whitespace_only_returns_empty_dict(self) -> None:
        result = _parse_llm_response("   \n  \t  ")
        assert result == {}

    def test_empty_code_fence_returns_empty_dict(self) -> None:
        result = _parse_llm_response("```json\n```")
        assert result == {}

    def test_code_fence_with_only_whitespace_returns_empty_dict(self) -> None:
        result = _parse_llm_response("```json\n  \n```")
        assert result == {}

    def test_json_wrapped_in_prose_extracted_via_fallback(self) -> None:
        """Non-Anthropic providers may wrap JSON in explanatory text."""
        inner = json.dumps({"decisions": [{"text": "Use Redis", "context": "caching"}]})
        raw = f"Here is the analysis:\n{inner}\nHope this helps!"
        result = _parse_llm_response(raw)
        assert "decisions" in result
        assert result["decisions"][0]["text"] == "Use Redis"

    def test_prose_without_json_returns_empty_dict(self) -> None:
        result = _parse_llm_response("No JSON object here, just plain text.")
        assert result == {}


# ---------------------------------------------------------------------------
# Unit tests: _extract_json_object
# ---------------------------------------------------------------------------


class TestExtractJsonObject:
    """Tests for JSON object extraction from prose."""

    def test_extracts_simple_json_object(self) -> None:
        text = 'prefix {"a": 1} suffix'
        assert _extract_json_object(text) == '{"a": 1}'

    def test_extracts_nested_json_object(self) -> None:
        text = 'before {"outer": {"inner": 42}} after'
        result = _extract_json_object(text)
        assert result is not None
        assert json.loads(result) == {"outer": {"inner": 42}}

    def test_handles_strings_with_braces(self) -> None:
        text = '{"key": "value with { and } inside"}'
        result = _extract_json_object(text)
        assert result is not None
        assert json.loads(result)["key"] == "value with { and } inside"

    def test_handles_escaped_quotes(self) -> None:
        text = r'{"key": "value with \" escaped"}'
        result = _extract_json_object(text)
        assert result is not None

    def test_returns_none_for_no_braces(self) -> None:
        assert _extract_json_object("no json here") is None

    def test_returns_none_for_unbalanced_braces(self) -> None:
        assert _extract_json_object("{unclosed") is None

    def test_empty_string(self) -> None:
        assert _extract_json_object("") is None


# ---------------------------------------------------------------------------
# Unit tests: _build_pattern_nodes
# ---------------------------------------------------------------------------


class TestBuildPatternNodes:
    """Tests for pattern node construction."""

    def test_builds_learned_pattern_node(self) -> None:
        items = [{"text": "Always write tests first", "confidence": 0.9}]
        nodes = _build_pattern_nodes(items)
        assert len(nodes) == 1
        assert nodes[0].node_type == NodeType.LEARNED_PATTERN
        assert nodes[0].content == "Always write tests first"
        assert nodes[0].properties["confidence"] == 0.9

    def test_confidence_clamped_above_one(self) -> None:
        items = [{"text": "Pattern A", "confidence": 1.5}]
        nodes = _build_pattern_nodes(items)
        assert nodes[0].properties["confidence"] == 1.0

    def test_confidence_clamped_below_zero(self) -> None:
        items = [{"text": "Pattern B", "confidence": -0.3}]
        nodes = _build_pattern_nodes(items)
        assert nodes[0].properties["confidence"] == 0.0

    def test_skips_empty_text(self) -> None:
        items = [{"text": "", "confidence": 0.8}, {"text": "Valid", "confidence": 0.7}]
        nodes = _build_pattern_nodes(items)
        assert len(nodes) == 1

    def test_default_confidence_when_missing(self) -> None:
        items = [{"text": "No confidence key"}]
        nodes = _build_pattern_nodes(items)
        assert nodes[0].properties["confidence"] == 0.5


# ---------------------------------------------------------------------------
# Unit tests: _build_preference_nodes
# ---------------------------------------------------------------------------


class TestBuildPreferenceNodes:
    """Tests for user preference node construction."""

    def test_builds_preference_node_with_user_id(self) -> None:
        user_id = uuid4()
        items = [{"key": "code_style", "value": "concise"}]
        nodes = _build_preference_nodes(items, user_id)
        assert len(nodes) == 1
        assert nodes[0].node_type == NodeType.USER_PREFERENCE
        assert nodes[0].user_id == user_id
        assert nodes[0].properties["preference_key"] == "code_style"
        assert nodes[0].properties["preference_value"] == "concise"

    def test_returns_empty_when_user_id_is_none(self) -> None:
        items = [{"key": "style", "value": "verbose"}]
        nodes = _build_preference_nodes(items, None)
        assert nodes == []

    def test_skips_empty_key(self) -> None:
        user_id = uuid4()
        items = [{"key": "", "value": "something"}, {"key": "valid_key", "value": "x"}]
        nodes = _build_preference_nodes(items, user_id)
        assert len(nodes) == 1
        assert nodes[0].properties["preference_key"] == "valid_key"


# ---------------------------------------------------------------------------
# Integration tests: GraphExtractionService
# ---------------------------------------------------------------------------


@pytest.fixture
def service() -> GraphExtractionService:
    """GraphExtractionService instance."""
    return GraphExtractionService()


@pytest.fixture
def base_messages() -> list[dict[str, str]]:
    """Sample conversation messages."""
    return [
        {"role": "user", "content": "Should we use Redis or Memcached?"},
        {
            "role": "assistant",
            "content": (
                "We decided to use Redis for caching. "
                "I prefer Redis because it supports persistence."
            ),
        },
    ]


def _make_anthropic_mock(llm_response: str) -> MagicMock:
    """Build a mock anthropic.AsyncAnthropic client returning the given response."""
    mock_message = MagicMock()
    mock_content_block = MagicMock()
    mock_content_block.text = llm_response
    mock_message.content = [mock_content_block]

    mock_client = MagicMock()
    mock_client.messages.create = AsyncMock(return_value=mock_message)

    return MagicMock(return_value=mock_client)


class TestGraphExtractionServiceReturnEmptyOnMissingApiKey:
    """BYOK: no api_key → empty result, no API call made."""

    @pytest.mark.asyncio
    async def test_returns_empty_on_missing_api_key(
        self, service: GraphExtractionService, base_messages: list[dict[str, str]]
    ) -> None:
        payload = ConversationExtractionPayload(
            messages=base_messages,
            workspace_id=uuid4(),
            api_key=None,
        )

        with patch("anthropic.AsyncAnthropic") as mock_client_cls:
            result = await service.execute(payload)

        mock_client_cls.assert_not_called()
        assert result.nodes == []
        assert result.edges == []
        assert result.decisions == []
        assert result.patterns == []
        assert result.raw_response is None


class TestGraphExtractionServiceDecisions:
    """Verify decision extraction creates DecisionNode inputs."""

    @pytest.mark.asyncio
    async def test_extracts_decisions_from_conversation(
        self, service: GraphExtractionService, base_messages: list[dict[str, str]]
    ) -> None:
        llm_response = json.dumps(
            {
                "decisions": [
                    {"text": "We decided to use Redis for caching", "context": "performance"}
                ],
                "patterns": [],
                "user_preferences": [],
                "entity_references": [],
            }
        )

        mock_anthropic_cls = _make_anthropic_mock(llm_response)

        with patch("anthropic.AsyncAnthropic", mock_anthropic_cls):
            payload = ConversationExtractionPayload(
                messages=base_messages,
                workspace_id=uuid4(),
                api_key="sk-ant-test",  # pragma: allowlist secret,
            )
            result = await service.execute(payload)

        decision_nodes = [n for n in result.nodes if n.node_type == NodeType.DECISION]
        assert len(decision_nodes) == 1
        assert "Redis" in decision_nodes[0].content
        assert "We decided to use Redis for caching" in result.decisions


class TestGraphExtractionServiceUserPreferences:
    """Verify user preference extraction binds user_id correctly."""

    @pytest.mark.asyncio
    async def test_extracts_user_preferences(
        self, service: GraphExtractionService, base_messages: list[dict[str, str]]
    ) -> None:
        user_id = uuid4()
        llm_response = json.dumps(
            {
                "decisions": [],
                "patterns": [],
                "user_preferences": [
                    {"key": "caching_backend", "value": "Redis"},
                    {"key": "persistence", "value": "always"},
                ],
                "entity_references": [],
            }
        )

        mock_anthropic_cls = _make_anthropic_mock(llm_response)

        with patch("anthropic.AsyncAnthropic", mock_anthropic_cls):
            payload = ConversationExtractionPayload(
                messages=base_messages,
                workspace_id=uuid4(),
                user_id=user_id,
                api_key="sk-ant-test",  # pragma: allowlist secret,
            )
            result = await service.execute(payload)

        pref_nodes = [n for n in result.nodes if n.node_type == NodeType.USER_PREFERENCE]
        assert len(pref_nodes) == 2
        for node in pref_nodes:
            assert node.user_id == user_id


class TestGraphExtractionServiceMalformedJson:
    """Verify graceful handling of LLM returning non-parseable output."""

    @pytest.mark.asyncio
    async def test_handles_malformed_json_gracefully(
        self, service: GraphExtractionService, base_messages: list[dict[str, str]]
    ) -> None:
        mock_anthropic_cls = _make_anthropic_mock("This is totally not JSON: {broken")

        with patch("anthropic.AsyncAnthropic", mock_anthropic_cls):
            payload = ConversationExtractionPayload(
                messages=base_messages,
                workspace_id=uuid4(),
                api_key="sk-ant-test",  # pragma: allowlist secret,
            )
            # Must not raise
            result = await service.execute(payload)

        assert isinstance(result, ExtractionResult)
        assert result.nodes == []
        assert result.edges == []

    @pytest.mark.asyncio
    async def test_handles_llm_exception_gracefully(
        self, service: GraphExtractionService, base_messages: list[dict[str, str]]
    ) -> None:
        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(side_effect=RuntimeError("API error"))
        mock_anthropic_cls = MagicMock(return_value=mock_client)

        with patch("anthropic.AsyncAnthropic", mock_anthropic_cls):
            payload = ConversationExtractionPayload(
                messages=base_messages,
                workspace_id=uuid4(),
                api_key="sk-ant-test",  # pragma: allowlist secret,
            )
            result = await service.execute(payload)

        assert result.nodes == []


class TestGraphExtractionServiceWhitespaceResponse:
    """Verify empty/whitespace LLM responses return empty result (not JSONDecodeError)."""

    @pytest.mark.asyncio
    async def test_whitespace_only_llm_response_returns_empty(
        self, service: GraphExtractionService, base_messages: list[dict[str, str]]
    ) -> None:
        mock_anthropic_cls = _make_anthropic_mock("   \n  ")

        with patch("anthropic.AsyncAnthropic", mock_anthropic_cls):
            payload = ConversationExtractionPayload(
                messages=base_messages,
                workspace_id=uuid4(),
                api_key="sk-ant-test",  # pragma: allowlist secret
            )
            result = await service.execute(payload)

        assert result.nodes == []
        assert result.raw_response is None

    @pytest.mark.asyncio
    async def test_empty_fence_llm_response_returns_empty(
        self, service: GraphExtractionService, base_messages: list[dict[str, str]]
    ) -> None:
        mock_anthropic_cls = _make_anthropic_mock("```json\n```")

        with patch("anthropic.AsyncAnthropic", mock_anthropic_cls):
            payload = ConversationExtractionPayload(
                messages=base_messages,
                workspace_id=uuid4(),
                api_key="sk-ant-test",  # pragma: allowlist secret
            )
            result = await service.execute(payload)

        assert result.nodes == []


class TestGraphExtractionServicePatterns:
    """Verify pattern extraction with confidence scores."""

    @pytest.mark.asyncio
    async def test_extracts_patterns_with_confidence(
        self, service: GraphExtractionService, base_messages: list[dict[str, str]]
    ) -> None:
        llm_response = json.dumps(
            {
                "decisions": [],
                "patterns": [
                    {"text": "Always use connection pooling for Redis", "confidence": 0.92},
                    {"text": "Prefer TTL over manual invalidation", "confidence": 0.75},
                ],
                "user_preferences": [],
                "entity_references": [],
            }
        )

        mock_anthropic_cls = _make_anthropic_mock(llm_response)

        with patch("anthropic.AsyncAnthropic", mock_anthropic_cls):
            payload = ConversationExtractionPayload(
                messages=base_messages,
                workspace_id=uuid4(),
                api_key="sk-ant-test",  # pragma: allowlist secret,
            )
            result = await service.execute(payload)

        pattern_nodes = [n for n in result.nodes if n.node_type == NodeType.LEARNED_PATTERN]
        assert len(pattern_nodes) == 2
        confidences = [float(n.properties["confidence"]) for n in pattern_nodes]
        assert 0.92 in confidences
        assert 0.75 in confidences
        assert len(result.patterns) == 2

    @pytest.mark.asyncio
    async def test_empty_messages_returns_empty_result(
        self, service: GraphExtractionService
    ) -> None:
        payload = ConversationExtractionPayload(
            messages=[],
            workspace_id=uuid4(),
            api_key="sk-ant-test",  # pragma: allowlist secret,
        )
        result = await service.execute(payload)
        assert result.nodes == []
        assert result.decisions == []
        assert result.patterns == []


# ---------------------------------------------------------------------------
# Unit tests: _background_graph_extraction
# ---------------------------------------------------------------------------


class TestBackgroundGraphExtraction:
    """Verify the fire-and-forget background extraction wrapper."""

    @pytest.mark.asyncio
    async def test_runs_extraction_with_own_db_session(self) -> None:
        """DB session opened only during write phase, after LLM extraction completes."""
        from pilot_space.ai.agents.pilotspace_agent import _background_graph_extraction

        mock_result = MagicMock()
        mock_result.nodes = [MagicMock()]
        mock_result.edges = []

        mock_extraction_svc = MagicMock()
        mock_extraction_svc.execute = AsyncMock(return_value=mock_result)

        mock_write_svc = MagicMock()
        mock_write_svc.execute = AsyncMock()

        mock_session = AsyncMock()
        mock_cm = MagicMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_cm.__aexit__ = AsyncMock(return_value=False)

        with (
            patch(
                "pilot_space.application.services.memory.graph_extraction_service.GraphExtractionService",
                return_value=mock_extraction_svc,
            ),
            patch(
                "pilot_space.infrastructure.database.get_db_session",
                return_value=mock_cm,
            ) as mock_get_db,
            patch(
                "pilot_space.infrastructure.database.rls.set_rls_context",
                new=AsyncMock(),
            ),
            patch(
                "pilot_space.ai.agents.pilotspace_agent.build_graph_write_service_for_session",
                return_value=mock_write_svc,
            ) as mock_build_svc,
        ):
            ws_id = uuid4()
            user_id = uuid4()
            messages = [{"role": "user", "content": "test"}]

            await _background_graph_extraction(
                graph_queue_client=None,
                workspace_id=ws_id,
                user_id=user_id,
                messages=messages,
                anthropic_api_key="sk-test",  # pragma: allowlist secret
            )

        # DB session must be opened (for write phase)
        mock_get_db.assert_called_once()
        mock_build_svc.assert_called_once_with(mock_session, None)
        mock_write_svc.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_swallows_exceptions_without_raising(self) -> None:
        from pilot_space.ai.agents.pilotspace_agent import _background_graph_extraction

        mock_result = MagicMock()
        mock_result.nodes = [MagicMock()]
        mock_result.edges = []

        mock_extraction_svc = MagicMock()
        mock_extraction_svc.execute = AsyncMock(return_value=mock_result)

        mock_cm = MagicMock()
        mock_cm.__aenter__ = AsyncMock(side_effect=RuntimeError("DB unavailable"))
        mock_cm.__aexit__ = AsyncMock(return_value=False)

        with (
            patch(
                "pilot_space.application.services.memory.graph_extraction_service.GraphExtractionService",
                return_value=mock_extraction_svc,
            ),
            patch(
                "pilot_space.infrastructure.database.get_db_session",
                return_value=mock_cm,
            ),
        ):
            # Must not raise
            await _background_graph_extraction(
                graph_queue_client=None,
                workspace_id=uuid4(),
                user_id=uuid4(),
                messages=[{"role": "user", "content": "test"}],
                anthropic_api_key="sk-test",  # pragma: allowlist secret
            )
