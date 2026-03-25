"""Unit tests for cost_hooks.track_llm_cost.

Verifies that cost tracking extracts tokens correctly and
swallows errors without propagating to the caller.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

from pilot_space.ai.proxy.cost_hooks import track_llm_cost

WS_ID = uuid4()
USER_ID = uuid4()


async def test_track_llm_cost_calls_tracker() -> None:
    """track_llm_cost extracts tokens and calls cost_tracker.track correctly."""
    mock_tracker = AsyncMock()
    mock_tracker.track = AsyncMock()

    response = SimpleNamespace(
        usage=SimpleNamespace(prompt_tokens=150, completion_tokens=75),
    )

    await track_llm_cost(
        mock_tracker,
        workspace_id=WS_ID,
        user_id=USER_ID,
        model="anthropic/claude-sonnet-4-20250514",
        agent_name="test_agent",
        response=response,
    )

    mock_tracker.track.assert_called_once()
    kwargs = mock_tracker.track.call_args.kwargs
    assert kwargs["workspace_id"] == WS_ID
    assert kwargs["user_id"] == USER_ID
    assert kwargs["provider"] == "anthropic"
    assert kwargs["model"] == "claude-sonnet-4-20250514"
    assert kwargs["input_tokens"] == 150
    assert kwargs["output_tokens"] == 75
    assert kwargs["agent_name"] == "test_agent"


async def test_track_llm_cost_swallows_errors() -> None:
    """track_llm_cost catches exceptions from cost_tracker.track."""
    mock_tracker = AsyncMock()
    mock_tracker.track = AsyncMock(side_effect=RuntimeError("db connection failed"))

    response = SimpleNamespace(
        usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5),
    )

    # Should NOT raise
    await track_llm_cost(
        mock_tracker,
        workspace_id=WS_ID,
        user_id=USER_ID,
        model="openai/gpt-4o",
        agent_name="test",
        response=response,
    )


async def test_track_llm_cost_handles_missing_usage() -> None:
    """track_llm_cost handles response with no usage attribute."""
    mock_tracker = AsyncMock()
    mock_tracker.track = AsyncMock()

    response = SimpleNamespace()  # No usage attribute

    await track_llm_cost(
        mock_tracker,
        workspace_id=WS_ID,
        user_id=USER_ID,
        model="anthropic/claude-3-5-haiku-20241022",
        agent_name="test",
        response=response,
    )

    mock_tracker.track.assert_called_once()
    kwargs = mock_tracker.track.call_args.kwargs
    assert kwargs["input_tokens"] == 0
    assert kwargs["output_tokens"] == 0
