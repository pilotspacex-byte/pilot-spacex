"""Integration tests for Unit 11: Backend Integration (DI + Agent + Prompt).

Tests:
    - recall_graph_context returns empty list when service is None
    - extract_and_persist_to_graph returns False on empty messages
    - extract_and_persist_to_graph returns False when no anthropic_api_key (BYOK gate)
    - extract_and_persist_to_graph extracts and persists when key + nodes present
    - extract_and_persist_to_graph returns False on service error
    - format_graph_context formats nodes correctly
    - format_graph_context returns empty string on empty input
    - _build_session_section uses graph_context when available
    - _build_session_section falls back to memory_entries when no graph_context
"""

from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pilot_space.ai.agents.pilotspace_agent import (
    extract_and_persist_to_graph,
    recall_graph_context,
)
from pilot_space.ai.prompt.models import PromptLayerConfig
from pilot_space.ai.prompt.prompt_assembler import (
    _build_session_section,
    format_graph_context,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_WORKSPACE_ID = uuid.UUID("11111111-2222-3333-4444-555555555555")
_USER_ID = uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")


def _make_scored_node(node_type: str, label: str, content: str, score: float) -> Any:
    """Build a minimal ScoredNode-like object for mocking."""
    node = MagicMock()
    node.content = content
    node.label = label
    node.node_type = MagicMock()
    node.node_type.value = node_type
    node.properties = {}

    scored = MagicMock()
    scored.node = node
    scored.score = score
    return scored


# ---------------------------------------------------------------------------
# recall_graph_context tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_recall_graph_context_returns_empty_when_no_service() -> None:
    """recall_graph_context returns [] when graph_search_service is None."""
    result = await recall_graph_context(
        workspace_id=_WORKSPACE_ID,
        user_id=_USER_ID,
        query="test query",
        graph_search_service=None,
    )
    assert result == []


@pytest.mark.asyncio
async def test_recall_graph_context_returns_nodes_from_service() -> None:
    """recall_graph_context maps ScoredNode objects to dicts."""
    mock_service = AsyncMock()
    mock_result = MagicMock()
    mock_result.nodes = [
        _make_scored_node("skill_outcome", "Sprint planning", "Completed sprint 5", 0.9),
        _make_scored_node("requirement", "Auth feature", "JWT-based auth required", 0.7),
    ]
    mock_service.execute.return_value = mock_result

    result = await recall_graph_context(
        workspace_id=_WORKSPACE_ID,
        user_id=_USER_ID,
        query="sprint planning",
        graph_search_service=mock_service,
    )

    assert len(result) == 2
    assert result[0]["node_type"] == "skill_outcome"
    assert result[0]["label"] == "Sprint planning"
    assert result[0]["content"] == "Completed sprint 5"
    assert result[0]["score"] == 0.9
    assert result[1]["node_type"] == "requirement"


@pytest.mark.asyncio
async def test_recall_graph_context_returns_empty_on_service_error() -> None:
    """recall_graph_context returns [] gracefully when the service raises."""
    mock_service = AsyncMock()
    mock_service.execute.side_effect = RuntimeError("DB unavailable")

    result = await recall_graph_context(
        workspace_id=_WORKSPACE_ID,
        user_id=None,
        query="test",
        graph_search_service=mock_service,
    )
    assert result == []


# ---------------------------------------------------------------------------
# extract_and_persist_to_graph tests
# ---------------------------------------------------------------------------


_EXTRACTION_SVC_PATH = (
    "pilot_space.application.services.memory.graph_extraction_service.GraphExtractionService"
)


@pytest.mark.asyncio
async def test_extract_and_persist_returns_false_on_empty_messages() -> None:
    """extract_and_persist_to_graph returns False when messages list is empty."""
    mock_service = AsyncMock()
    result = await extract_and_persist_to_graph(
        graph_write_service=mock_service,
        workspace_id=_WORKSPACE_ID,
        user_id=_USER_ID,
        messages=[],
        anthropic_api_key="sk-test",  # pragma: allowlist secret
    )
    assert result is False
    mock_service.execute.assert_not_called()


@pytest.mark.asyncio
async def test_extract_and_persist_returns_false_when_no_api_key() -> None:
    """extract_and_persist_to_graph returns False when no anthropic_api_key (BYOK gate)."""
    mock_service = AsyncMock()
    result = await extract_and_persist_to_graph(
        graph_write_service=mock_service,
        workspace_id=_WORKSPACE_ID,
        user_id=_USER_ID,
        messages=[{"role": "user", "content": "Hello"}, {"role": "assistant", "content": "Hi"}],
        anthropic_api_key=None,
    )
    assert result is False
    mock_service.execute.assert_not_called()


@pytest.mark.asyncio
async def test_extract_and_persist_calls_write_service_when_nodes_found() -> None:
    """extract_and_persist_to_graph calls GraphWriteService when extraction yields nodes."""
    mock_service = AsyncMock()
    messages = [
        {"role": "user", "content": "Plan the sprint"},
        {"role": "assistant", "content": "Sprint 6 planned with 12 issues"},
    ]
    node_mock = MagicMock()
    extraction_result = MagicMock()
    extraction_result.nodes = [node_mock]
    extraction_result.edges = []

    with patch(_EXTRACTION_SVC_PATH) as MockExtraction:
        MockExtraction.return_value.execute = AsyncMock(return_value=extraction_result)
        result = await extract_and_persist_to_graph(
            graph_write_service=mock_service,
            workspace_id=_WORKSPACE_ID,
            user_id=_USER_ID,
            messages=messages,
            anthropic_api_key="sk-test",  # pragma: allowlist secret
        )

    assert result is True
    mock_service.execute.assert_called_once()
    call_args = mock_service.execute.call_args[0][0]
    assert call_args.workspace_id == _WORKSPACE_ID


@pytest.mark.asyncio
async def test_extract_and_persist_returns_false_on_extraction_error() -> None:
    """extract_and_persist_to_graph returns False gracefully when extraction raises."""
    mock_service = AsyncMock()

    with patch(_EXTRACTION_SVC_PATH) as MockExtraction:
        MockExtraction.return_value.execute = AsyncMock(side_effect=RuntimeError("LLM down"))
        result = await extract_and_persist_to_graph(
            graph_write_service=mock_service,
            workspace_id=_WORKSPACE_ID,
            user_id=None,
            messages=[
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "World"},
            ],
            anthropic_api_key="sk-test",  # pragma: allowlist secret
        )
    assert result is False
    mock_service.execute.assert_not_called()


# ---------------------------------------------------------------------------
# format_graph_context tests
# ---------------------------------------------------------------------------


def test_format_graph_context_returns_empty_string_on_empty_input() -> None:
    """format_graph_context returns empty string when list is empty."""
    result = format_graph_context([])
    assert result == ""


def test_format_graph_context_formats_nodes_correctly() -> None:
    """format_graph_context produces correct markdown lines."""
    nodes: list[dict[str, Any]] = [
        {
            "node_type": "skill_outcome",
            "label": "PR review completed",
            "content": "Reviewed PR #42",
            "score": 0.95,
            "properties": {},
        },
        {
            "node_type": "requirement",
            "label": "Auth requirement",
            "content": "Use Supabase Auth",
            "score": 0.80,
            "properties": {},
        },
    ]

    result = format_graph_context(nodes)

    # Phase 69-05: renders as <memory> XML block with per-item provenance
    # attributes (type, id, score). Content is HTML-escaped.
    assert result.startswith("<memory>")
    assert result.rstrip().endswith("</memory>")
    assert 'type="skill_outcome"' in result
    assert 'type="requirement"' in result
    assert "Reviewed PR #42" in result
    assert "Use Supabase Auth" in result
    assert 'score="0.95"' in result
    assert 'score="0.80"' in result


def test_format_graph_context_handles_missing_fields() -> None:
    """format_graph_context uses defaults when dict fields are missing."""
    nodes: list[dict[str, Any]] = [{"score": 0.5}]
    result = format_graph_context(nodes)
    assert 'type="unknown"' in result
    assert 'score="0.50"' in result


# ---------------------------------------------------------------------------
# _build_session_section tests
# ---------------------------------------------------------------------------


def test_build_session_section_uses_graph_context_when_available() -> None:
    """_build_session_section includes graph context when graph_context is set."""
    config = PromptLayerConfig(
        graph_context=[
            {
                "node_type": "skill_outcome",
                "label": "done",
                "content": "task finished",
                "score": 1.0,
                "properties": {},
            }
        ],
        memory_entries=[{"content": "old memory", "source_type": "skill_outcome", "score": 0.5}],
    )
    parts = _build_session_section(config)
    combined = "\n".join(parts)
    assert "<memory>" in combined
    assert "task finished" in combined
    assert "old memory" not in combined


def test_build_session_section_falls_back_to_memory_entries() -> None:
    """_build_session_section uses memory_entries when graph_context is empty."""
    config = PromptLayerConfig(
        graph_context=[],
        memory_entries=[{"content": "legacy memory", "source_type": "skill_outcome", "score": 0.5}],
    )
    parts = _build_session_section(config)
    combined = "\n".join(parts)
    assert "legacy memory" in combined
    assert "<memory>" not in combined


def test_build_session_section_empty_when_no_context() -> None:
    """_build_session_section returns empty list when no context or state."""
    config = PromptLayerConfig()
    parts = _build_session_section(config)
    assert parts == []
