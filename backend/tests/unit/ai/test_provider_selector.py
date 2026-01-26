"""Unit tests for ProviderSelector.

Tests DD-011 routing rules, user overrides, fallback logic, and circuit breaker integration.
"""

from __future__ import annotations

import pytest

from pilot_space.ai.circuit_breaker import CircuitBreaker, CircuitBreakerConfig
from pilot_space.ai.providers.provider_selector import (
    Provider,
    ProviderConfig,
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


class TestProviderSelection:
    """Test basic provider selection per DD-011."""

    def test_pr_review_routes_to_claude_opus(self, selector: ProviderSelector) -> None:
        """Verify PR review uses Claude Opus for deep code analysis."""
        provider, model = selector.select(TaskType.PR_REVIEW)

        assert provider == Provider.ANTHROPIC.value
        assert model == ProviderSelector.ANTHROPIC_OPUS

    def test_ghost_text_routes_to_claude_haiku(self, selector: ProviderSelector) -> None:
        """Verify ghost text uses Claude Haiku for low latency."""
        provider, model = selector.select(TaskType.GHOST_TEXT)

        assert provider == Provider.ANTHROPIC.value
        assert model == ProviderSelector.ANTHROPIC_HAIKU

    def test_embeddings_route_to_openai(self, selector: ProviderSelector) -> None:
        """Verify embeddings use OpenAI for superior vectors."""
        provider, model = selector.select(TaskType.EMBEDDINGS)

        assert provider == Provider.OPENAI.value
        assert model == ProviderSelector.OPENAI_EMBEDDING

    def test_doc_generation_routes_to_claude_sonnet(self, selector: ProviderSelector) -> None:
        """Verify doc generation uses Claude Sonnet for balanced performance."""
        provider, model = selector.select(TaskType.DOC_GENERATION)

        assert provider == Provider.ANTHROPIC.value
        assert model == ProviderSelector.ANTHROPIC_SONNET

    def test_all_task_types_have_routing(self, selector: ProviderSelector) -> None:
        """Verify every task type has a routing entry."""
        all_task_types = selector.get_all_task_types()

        for task_type in all_task_types:
            # Should not raise ValueError
            config = selector.select_with_config(task_type)
            assert config.provider
            assert config.model
            assert config.reason


class TestSelectWithConfig:
    """Test select_with_config returns full ProviderConfig."""

    def test_returns_config_with_fallback_info(self, selector: ProviderSelector) -> None:
        """Verify config includes fallback information."""
        config = selector.select_with_config(TaskType.PR_REVIEW)

        assert config.provider == Provider.ANTHROPIC.value
        assert config.model == ProviderSelector.ANTHROPIC_OPUS
        assert config.reason
        assert config.fallback_provider == Provider.ANTHROPIC.value
        assert config.fallback_model == ProviderSelector.ANTHROPIC_SONNET

    def test_embeddings_have_no_fallback(self, selector: ProviderSelector) -> None:
        """Verify embeddings task has no fallback provider."""
        config = selector.select_with_config(TaskType.EMBEDDINGS)

        assert config.provider == Provider.OPENAI.value
        assert config.fallback_provider is None
        assert config.fallback_model is None

    def test_invalid_task_type_raises_error(self, selector: ProviderSelector) -> None:
        """Verify invalid task type raises ValueError."""
        with pytest.raises(ValueError, match="Unknown task type"):
            # Force invalid enum value
            selector.select_with_config("invalid_task")  # type: ignore[arg-type]


class TestUserOverride:
    """Test user override preferences."""

    def test_healthy_override_takes_precedence(self, selector: ProviderSelector) -> None:
        """Verify user override is used when provider is healthy."""
        user_override = (Provider.GOOGLE.value, ProviderSelector.GOOGLE_FLASH)
        config = selector.select_with_config(TaskType.PR_REVIEW, user_override)

        assert config.provider == Provider.GOOGLE.value
        assert config.model == ProviderSelector.GOOGLE_FLASH
        assert "User preference" in config.reason

    def test_unhealthy_override_falls_back_to_default(self, selector: ProviderSelector) -> None:
        """Verify fallback to default when override provider is unhealthy."""
        # Open circuit breaker for Google
        breaker = CircuitBreaker.get_or_create(
            Provider.GOOGLE.value,
            CircuitBreakerConfig(failure_threshold=1),
        )
        # Access private state for testing (allowed in unit tests)
        breaker._state.state = breaker._state.state.__class__.OPEN

        user_override = (Provider.GOOGLE.value, ProviderSelector.GOOGLE_FLASH)
        config = selector.select_with_config(TaskType.PR_REVIEW, user_override)

        # Should fall back to default Claude Opus
        assert config.provider == Provider.ANTHROPIC.value
        assert config.model == ProviderSelector.ANTHROPIC_OPUS

    def test_override_with_fallback_info(self, selector: ProviderSelector) -> None:
        """Verify override config includes default as fallback."""
        user_override = (Provider.GOOGLE.value, ProviderSelector.GOOGLE_PRO)
        config = selector.select_with_config(TaskType.DOC_GENERATION, user_override)

        assert config.provider == Provider.GOOGLE.value
        assert config.fallback_provider == Provider.ANTHROPIC.value
        assert config.fallback_model == ProviderSelector.ANTHROPIC_SONNET


class TestFallbackLogic:
    """Test automatic fallback on provider failures."""

    def test_get_fallback_returns_configured_fallback(self, selector: ProviderSelector) -> None:
        """Verify get_fallback returns correct fallback provider."""
        fallback = selector.get_fallback(TaskType.PR_REVIEW)

        assert fallback is not None
        assert fallback[0] == Provider.ANTHROPIC.value
        assert fallback[1] == ProviderSelector.ANTHROPIC_SONNET

    def test_get_fallback_returns_none_for_no_fallback(self, selector: ProviderSelector) -> None:
        """Verify get_fallback returns None when no fallback configured."""
        fallback = selector.get_fallback(TaskType.EMBEDDINGS)

        assert fallback is None

    def test_unhealthy_primary_uses_fallback(self, selector: ProviderSelector) -> None:
        """Verify fallback provider is used when primary is unhealthy."""
        # Open circuit breaker for Anthropic
        breaker = CircuitBreaker.get_or_create(
            Provider.ANTHROPIC.value,
            CircuitBreakerConfig(failure_threshold=1),
        )
        # Access private state for testing (allowed in unit tests)
        breaker._state.state = breaker._state.state.__class__.OPEN

        # Ghost text should fall back to Google Flash
        config = selector.select_with_config(TaskType.GHOST_TEXT)

        assert config.provider == Provider.GOOGLE.value
        assert config.model == ProviderSelector.GOOGLE_FLASH
        assert "Fallback" in config.reason


class TestCircuitBreakerIntegration:
    """Test integration with CircuitBreaker."""

    def test_is_provider_healthy_returns_true_when_closed(self, selector: ProviderSelector) -> None:
        """Verify healthy provider returns True."""
        is_healthy = selector.is_provider_healthy(Provider.ANTHROPIC.value)

        assert is_healthy is True

    def test_is_provider_healthy_returns_false_when_open(self, selector: ProviderSelector) -> None:
        """Verify unhealthy provider returns False."""
        # Open circuit breaker
        breaker = CircuitBreaker.get_or_create(
            Provider.ANTHROPIC.value,
            CircuitBreakerConfig(failure_threshold=1),
        )
        # Access private state for testing (allowed in unit tests)
        breaker._state.state = breaker._state.state.__class__.OPEN

        is_healthy = selector.is_provider_healthy(Provider.ANTHROPIC.value)

        assert is_healthy is False

    def test_circuit_breaker_created_per_provider(self, selector: ProviderSelector) -> None:
        """Verify circuit breakers are created separately per provider."""
        # Check different providers
        selector.is_provider_healthy(Provider.ANTHROPIC.value)
        selector.is_provider_healthy(Provider.OPENAI.value)
        selector.is_provider_healthy(Provider.GOOGLE.value)

        # Should have created 3 breakers
        # Access private attribute for testing (allowed in unit tests)
        assert len(selector._circuit_breakers) == 3


class TestRoutingInfo:
    """Test routing information retrieval."""

    def test_get_routing_info_returns_complete_info(self, selector: ProviderSelector) -> None:
        """Verify routing info includes all fields."""
        info = selector.get_routing_info(TaskType.PR_REVIEW)

        assert info["task_type"] == TaskType.PR_REVIEW.value
        assert info["provider"] == Provider.ANTHROPIC.value
        assert info["model"] == ProviderSelector.ANTHROPIC_OPUS
        assert info["reason"]
        assert info["fallback_provider"]
        assert info["fallback_model"]

    def test_get_routing_info_handles_no_fallback(self, selector: ProviderSelector) -> None:
        """Verify routing info shows 'None' for missing fallback."""
        info = selector.get_routing_info(TaskType.EMBEDDINGS)

        assert info["fallback_provider"] == "None"
        assert info["fallback_model"] == "None"

    def test_get_routing_info_invalid_task_raises_error(self, selector: ProviderSelector) -> None:
        """Verify invalid task type raises ValueError."""
        with pytest.raises(ValueError, match="Unknown task type"):
            selector.get_routing_info("invalid")  # type: ignore[arg-type]


class TestAllTaskTypes:
    """Test routing for all task types."""

    def test_get_all_task_types_returns_complete_list(self, selector: ProviderSelector) -> None:
        """Verify all task types are returned."""
        task_types = selector.get_all_task_types()

        # Should match TaskType enum members
        assert len(task_types) == len(TaskType)
        assert TaskType.PR_REVIEW in task_types
        assert TaskType.GHOST_TEXT in task_types
        assert TaskType.EMBEDDINGS in task_types


class TestProviderConfigDataclass:
    """Test ProviderConfig dataclass."""

    def test_frozen_prevents_modification(self) -> None:
        """Verify ProviderConfig is immutable."""
        config = ProviderConfig(
            provider=Provider.ANTHROPIC.value,
            model="claude-opus-4-5",
            reason="Test",
        )

        # Frozen dataclass raises AttributeError on modification
        with pytest.raises(AttributeError, match="cannot assign to field"):
            config.provider = "openai"  # type: ignore[misc]

    def test_default_fallback_values_are_none(self) -> None:
        """Verify fallback fields default to None."""
        config = ProviderConfig(
            provider=Provider.ANTHROPIC.value,
            model="claude-opus-4-5",
            reason="Test",
        )

        assert config.fallback_provider is None
        assert config.fallback_model is None


class TestDD011Compliance:
    """Test DD-011 routing table compliance."""

    def test_code_intensive_tasks_use_claude_opus(self, selector: ProviderSelector) -> None:
        """Verify code-intensive tasks route to Claude Opus."""
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

    def test_latency_sensitive_tasks_use_claude_haiku(self, selector: ProviderSelector) -> None:
        """Verify latency-sensitive tasks route to Claude Haiku."""
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

    def test_embedding_tasks_use_openai(self, selector: ProviderSelector) -> None:
        """Verify embedding tasks route to OpenAI."""
        embedding_tasks = [
            TaskType.EMBEDDINGS,
            TaskType.SEMANTIC_SEARCH,
        ]

        for task in embedding_tasks:
            provider, model = selector.select(task)
            assert provider == Provider.OPENAI.value
            assert model == ProviderSelector.OPENAI_EMBEDDING

    def test_standard_tasks_use_claude_sonnet(self, selector: ProviderSelector) -> None:
        """Verify standard tasks route to Claude Sonnet."""
        standard_tasks = [
            TaskType.CODE_GENERATION,
            TaskType.DOC_GENERATION,
            TaskType.ISSUE_ENHANCEMENT,
            TaskType.ISSUE_EXTRACTION,
            TaskType.MARGIN_ANNOTATION,
            TaskType.CONVERSATION,
            TaskType.DUPLICATE_DETECTION,
            TaskType.DIAGRAM_GENERATION,
            TaskType.TEMPLATE_FILLING,
        ]

        for task in standard_tasks:
            provider, model = selector.select(task)
            assert provider == Provider.ANTHROPIC.value
            assert model == ProviderSelector.ANTHROPIC_SONNET


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_both_providers_unhealthy_returns_primary(self, selector: ProviderSelector) -> None:
        """Verify primary is returned even if both providers unhealthy."""
        # Open both circuit breakers
        anthropic_breaker = CircuitBreaker.get_or_create(
            Provider.ANTHROPIC.value,
            CircuitBreakerConfig(failure_threshold=1),
        )
        # Access private state for testing (allowed in unit tests)
        anthropic_breaker._state.state = anthropic_breaker._state.state.__class__.OPEN

        google_breaker = CircuitBreaker.get_or_create(
            Provider.GOOGLE.value,
            CircuitBreakerConfig(failure_threshold=1),
        )
        # Access private state for testing (allowed in unit tests)
        google_breaker._state.state = google_breaker._state.state.__class__.OPEN

        # Ghost text has Google as fallback
        config = selector.select_with_config(TaskType.GHOST_TEXT)

        # Should return primary even though unhealthy
        assert config.provider == Provider.ANTHROPIC.value
        assert config.model == ProviderSelector.ANTHROPIC_HAIKU

    def test_select_and_select_with_config_return_same_provider(
        self, selector: ProviderSelector
    ) -> None:
        """Verify select() and select_with_config() are consistent."""
        for task_type in TaskType:
            provider, model = selector.select(task_type)
            config = selector.select_with_config(task_type)

            assert provider == config.provider
            assert model == config.model
