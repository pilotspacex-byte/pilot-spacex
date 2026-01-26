"""Standalone unit tests for ProviderSelector (no conftest dependencies).

Run with: uv run python -m pytest tests/unit/ai/test_provider_selector_standalone.py -v
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add src to path to avoid conftest loading
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

import pytest

from pilot_space.ai.circuit_breaker import CircuitBreaker
from pilot_space.ai.providers.provider_selector import (
    Provider,
    ProviderSelector,
    TaskType,
)


@pytest.fixture
def selector() -> ProviderSelector:
    """Create ProviderSelector instance."""
    return ProviderSelector()


@pytest.fixture(autouse=True)
def reset_circuit_breakers() -> None:
    """Reset all circuit breakers before each test."""
    CircuitBreaker.reset_all()


def test_pr_review_routes_to_claude_opus(selector: ProviderSelector) -> None:
    """Verify PR review uses Claude Opus for deep code analysis."""
    provider, model = selector.select(TaskType.PR_REVIEW)

    assert provider == Provider.ANTHROPIC.value
    assert model == ProviderSelector.ANTHROPIC_OPUS


def test_ghost_text_routes_to_claude_haiku(selector: ProviderSelector) -> None:
    """Verify ghost text uses Claude Haiku for low latency."""
    provider, model = selector.select(TaskType.GHOST_TEXT)

    assert provider == Provider.ANTHROPIC.value
    assert model == ProviderSelector.ANTHROPIC_HAIKU


def test_embeddings_route_to_openai(selector: ProviderSelector) -> None:
    """Verify embeddings use OpenAI for superior vectors."""
    provider, model = selector.select(TaskType.EMBEDDINGS)

    assert provider == Provider.OPENAI.value
    assert model == ProviderSelector.OPENAI_EMBEDDING


def test_all_task_types_have_routing(selector: ProviderSelector) -> None:
    """Verify every task type has a routing entry."""
    all_task_types = selector.get_all_task_types()

    for task_type in all_task_types:
        config = selector.select_with_config(task_type)
        assert config.provider
        assert config.model
        assert config.reason


def test_returns_config_with_fallback_info(selector: ProviderSelector) -> None:
    """Verify config includes fallback information."""
    config = selector.select_with_config(TaskType.PR_REVIEW)

    assert config.provider == Provider.ANTHROPIC.value
    assert config.model == ProviderSelector.ANTHROPIC_OPUS
    assert config.reason
    assert config.fallback_provider == Provider.ANTHROPIC.value
    assert config.fallback_model == ProviderSelector.ANTHROPIC_SONNET


def test_healthy_override_takes_precedence(selector: ProviderSelector) -> None:
    """Verify user override is used when provider is healthy."""
    user_override = (Provider.GOOGLE.value, ProviderSelector.GOOGLE_FLASH)
    config = selector.select_with_config(TaskType.PR_REVIEW, user_override)

    assert config.provider == Provider.GOOGLE.value
    assert config.model == ProviderSelector.GOOGLE_FLASH
    assert "User preference" in config.reason


def test_is_provider_healthy_returns_true_when_closed(
    selector: ProviderSelector,
) -> None:
    """Verify healthy provider returns True."""
    is_healthy = selector.is_provider_healthy(Provider.ANTHROPIC.value)
    assert is_healthy is True


def test_dd011_code_intensive_tasks_use_claude_opus(selector: ProviderSelector) -> None:
    """Verify code-intensive tasks route to Claude Opus per DD-011."""
    code_tasks = [
        TaskType.PR_REVIEW,
        TaskType.AI_CONTEXT,
        TaskType.TASK_DECOMPOSITION,
        TaskType.PATTERN_DETECTION,
    ]

    for task in code_tasks:
        provider, model = selector.select(task)
        assert provider == Provider.ANTHROPIC.value
        assert model == ProviderSelector.ANTHROPIC_OPUS


def test_dd011_latency_sensitive_use_haiku(selector: ProviderSelector) -> None:
    """Verify latency-sensitive tasks route to Claude Haiku per DD-011."""
    latency_tasks = [
        TaskType.GHOST_TEXT,
        TaskType.NOTIFICATION_PRIORITY,
        TaskType.ASSIGNEE_RECOMMENDATION,
        TaskType.COMMIT_LINKING,
    ]

    for task in latency_tasks:
        provider, model = selector.select(task)
        assert provider == Provider.ANTHROPIC.value
        assert model == ProviderSelector.ANTHROPIC_HAIKU


def test_dd011_embeddings_use_openai(selector: ProviderSelector) -> None:
    """Verify embedding tasks route to OpenAI per DD-011."""
    embedding_tasks = [
        TaskType.EMBEDDINGS,
        TaskType.SEMANTIC_SEARCH,
    ]

    for task in embedding_tasks:
        provider, model = selector.select(task)
        assert provider == Provider.OPENAI.value
        assert model == ProviderSelector.OPENAI_EMBEDDING


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
