"""Unit tests for extract_and_persist_to_graph.

Verifies the LLM-based extraction flow: BYOK gating, empty result filtering,
and successful node persistence.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from pilot_space.ai.agents.pilotspace_agent import extract_and_persist_to_graph


def _make_extraction_result(nodes: list, edges: list | None = None) -> MagicMock:
    result = MagicMock()
    result.nodes = nodes
    result.edges = edges or []
    return result


@pytest.fixture
def workspace_id():
    return uuid4()


@pytest.fixture
def user_id():
    return uuid4()


@pytest.fixture
def messages():
    return [
        {"role": "user", "content": "We decided to use Redis for rate limiting."},
        {"role": "assistant", "content": "That's a solid choice for rate limiting at scale."},
    ]


@pytest.mark.asyncio
async def test_empty_messages_returns_false(workspace_id, user_id) -> None:
    """Empty messages list → False without calling extraction."""
    graph_write_svc = AsyncMock()
    result = await extract_and_persist_to_graph(
        graph_write_service=graph_write_svc,
        workspace_id=workspace_id,
        user_id=user_id,
        messages=[],
        anthropic_api_key="sk-test",  # pragma: allowlist secret
    )
    assert result is False
    graph_write_svc.execute.assert_not_called()


@pytest.mark.asyncio
async def test_no_api_key_returns_false(workspace_id, user_id, messages) -> None:
    """No API key (BYOK pattern) → False without calling extraction."""
    graph_write_svc = AsyncMock()
    result = await extract_and_persist_to_graph(
        graph_write_service=graph_write_svc,
        workspace_id=workspace_id,
        user_id=user_id,
        messages=messages,
        anthropic_api_key=None,
    )
    assert result is False
    graph_write_svc.execute.assert_not_called()


@pytest.mark.asyncio
async def test_extraction_empty_nodes_returns_false_no_write(
    workspace_id, user_id, messages
) -> None:
    """Extraction yields no nodes → False, GraphWriteService.execute NOT called."""
    graph_write_svc = AsyncMock()
    empty_result = _make_extraction_result(nodes=[])

    _EXTRACTION_SVC_PATH = (
        "pilot_space.application.services.memory.graph_extraction_service.GraphExtractionService"
    )

    with patch(_EXTRACTION_SVC_PATH) as MockExtraction:
        MockExtraction.return_value.execute = AsyncMock(return_value=empty_result)
        result = await extract_and_persist_to_graph(
            graph_write_service=graph_write_svc,
            workspace_id=workspace_id,
            user_id=user_id,
            messages=messages,
            anthropic_api_key="sk-test",  # pragma: allowlist secret
        )

    assert result is False
    graph_write_svc.execute.assert_not_called()


_EXTRACTION_SVC_PATH = (
    "pilot_space.application.services.memory.graph_extraction_service.GraphExtractionService"
)


@pytest.mark.asyncio
async def test_extraction_with_nodes_calls_write_service(workspace_id, user_id, messages) -> None:
    """Extraction yields nodes → GraphWriteService.execute called, returns True."""
    graph_write_svc = AsyncMock()
    node_mock = MagicMock()
    edge_mock = MagicMock()
    extraction_result = _make_extraction_result(nodes=[node_mock], edges=[edge_mock])

    with patch(_EXTRACTION_SVC_PATH) as MockExtraction:
        MockExtraction.return_value.execute = AsyncMock(return_value=extraction_result)
        result = await extract_and_persist_to_graph(
            graph_write_service=graph_write_svc,
            workspace_id=workspace_id,
            user_id=user_id,
            messages=messages,
            anthropic_api_key="sk-test",  # pragma: allowlist secret
        )

    assert result is True
    graph_write_svc.execute.assert_called_once()
    call_payload = graph_write_svc.execute.call_args[0][0]
    assert call_payload.nodes == [node_mock]
    assert call_payload.edges == [edge_mock]
    assert call_payload.workspace_id == workspace_id
    assert call_payload.user_id == user_id


@pytest.mark.asyncio
async def test_extraction_raises_returns_false(workspace_id, user_id, messages) -> None:
    """Extraction raises → returns False (non-fatal)."""
    graph_write_svc = AsyncMock()

    with patch(_EXTRACTION_SVC_PATH) as MockExtraction:
        MockExtraction.return_value.execute = AsyncMock(side_effect=RuntimeError("LLM error"))
        result = await extract_and_persist_to_graph(
            graph_write_service=graph_write_svc,
            workspace_id=workspace_id,
            user_id=user_id,
            messages=messages,
            anthropic_api_key="sk-test",  # pragma: allowlist secret
        )

    assert result is False
    graph_write_svc.execute.assert_not_called()


@pytest.mark.asyncio
async def test_issue_id_passed_to_extraction(workspace_id, user_id, messages) -> None:
    """issue_id is forwarded to extraction payload."""
    issue_id = uuid4()
    graph_write_svc = AsyncMock()
    empty_result = _make_extraction_result(nodes=[])

    with patch(_EXTRACTION_SVC_PATH) as MockExtraction:
        exec_mock = AsyncMock(return_value=empty_result)
        MockExtraction.return_value.execute = exec_mock
        await extract_and_persist_to_graph(
            graph_write_service=graph_write_svc,
            workspace_id=workspace_id,
            user_id=user_id,
            messages=messages,
            issue_id=issue_id,
            anthropic_api_key="sk-test",  # pragma: allowlist secret
        )

    call_payload = exec_mock.call_args[0][0]
    assert call_payload.issue_id == issue_id
    assert call_payload.api_key == "sk-test"  # pragma: allowlist secret
