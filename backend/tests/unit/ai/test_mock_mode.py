"""Tests for AI mock mode functionality.

Validates that mock provider:
- Activates only in development with AI_FAKE_MODE=true
- Returns realistic mock responses
- Registers all agent generators
- Tracks mock calls for debugging
"""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from pilot_space.ai.agents.agent_base import AgentContext
from pilot_space.ai.providers.mock import MockProvider, MockResponseRegistry
from pilot_space.config import Settings


@pytest.fixture
def mock_settings_dev_mode() -> Settings:
    """Settings with development + AI_FAKE_MODE enabled."""
    return Settings(
        app_env="development",
        ai_fake_mode=True,
        ai_fake_latency_ms=100,
        ai_fake_streaming_chunk_delay_ms=20,
    )


@pytest.fixture
def mock_settings_prod_mode() -> Settings:
    """Settings with production mode (mock disabled)."""
    return Settings(
        app_env="production",
        ai_fake_mode=False,
    )


@pytest.fixture
def agent_context() -> AgentContext:
    """Agent execution context."""
    return AgentContext(
        workspace_id=uuid4(),
        user_id=uuid4(),
        operation_id=uuid4(),
    )


@pytest.fixture(autouse=True)
def _reset_mock_provider() -> None:
    """Reset mock provider singleton between tests."""
    MockProvider.reset_instance()
    MockResponseRegistry.clear_history()


class TestMockProviderActivation:
    """Test mock provider activation logic."""

    def test_enabled_in_dev_with_fake_mode(
        self,
        mock_settings_dev_mode: Settings,
    ) -> None:
        """Verify mock mode activates in development with AI_FAKE_MODE=true."""
        with patch(
            "pilot_space.ai.providers.mock.get_settings", return_value=mock_settings_dev_mode
        ):
            provider = MockProvider.get_instance()
            assert provider.is_enabled()

    def test_disabled_in_production(
        self,
        mock_settings_prod_mode: Settings,
    ) -> None:
        """Verify mock mode never activates in production."""
        with patch(
            "pilot_space.ai.providers.mock.get_settings", return_value=mock_settings_prod_mode
        ):
            provider = MockProvider.get_instance()
            assert not provider.is_enabled()

    def test_disabled_in_dev_without_fake_mode(self) -> None:
        """Verify mock mode requires AI_FAKE_MODE=true even in dev."""
        settings = Settings(app_env="development", ai_fake_mode=False)
        with patch("pilot_space.ai.providers.mock.get_settings", return_value=settings):
            provider = MockProvider.get_instance()
            assert not provider.is_enabled()


class TestMockResponseGeneration:
    """Test mock response generators."""

    @pytest.mark.asyncio
    async def test_ghost_text_generation(
        self,
        mock_settings_dev_mode: Settings,
        agent_context: AgentContext,
    ) -> None:
        """Test ghost text mock response."""
        # Import to register generators
        from pilot_space.ai.providers import mock_generators  # noqa: F401

        with patch(
            "pilot_space.ai.providers.mock.get_settings", return_value=mock_settings_dev_mode
        ):
            # Create mock agent
            mock_agent = AsyncMock(spec=["__class__"])
            mock_agent.__class__.__name__ = "GhostTextAgent"

            provider = MockProvider.get_instance()

            input_data = {
                "current_text": "def process_",
                "cursor_position": 12,
                "is_code": True,
            }

            result = await provider.execute(mock_agent, input_data, agent_context)

            assert result.success
            assert result.output is not None
            assert isinstance(result.output, str)
            assert len(result.output) > 0
            assert result.cost_usd > 0
            assert result.input_tokens > 0
            assert result.output_tokens > 0

    @pytest.mark.asyncio
    async def test_pr_review_generation(
        self,
        mock_settings_dev_mode: Settings,
        agent_context: AgentContext,
    ) -> None:
        """Test PR review mock response."""
        from pilot_space.ai.providers import mock_generators  # noqa: F401

        with patch(
            "pilot_space.ai.providers.mock.get_settings", return_value=mock_settings_dev_mode
        ):
            mock_agent = AsyncMock(spec=["__class__"])
            mock_agent.__class__.__name__ = "PRReviewAgent"

            provider = MockProvider.get_instance()

            input_data = {
                "pr_number": 123,
                "pr_title": "Add authentication",
                "diff": "diff content",
            }

            result = await provider.execute(mock_agent, input_data, agent_context)

            assert result.success
            assert result.output is not None
            assert isinstance(result.output, dict)
            assert "summary" in result.output
            assert "comments" in result.output
            assert "approval_recommendation" in result.output


class TestMockCallTracking:
    """Test mock call history tracking."""

    @pytest.mark.asyncio
    async def test_call_tracking(
        self,
        mock_settings_dev_mode: Settings,
        agent_context: AgentContext,
    ) -> None:
        """Verify mock calls are tracked for debugging."""
        from pilot_space.ai.providers import mock_generators  # noqa: F401

        with patch(
            "pilot_space.ai.providers.mock.get_settings", return_value=mock_settings_dev_mode
        ):
            mock_agent = AsyncMock(spec=["__class__"])
            mock_agent.__class__.__name__ = "GhostTextAgent"

            provider = MockProvider.get_instance()

            # Make a mock call
            await provider.execute(mock_agent, {"current_text": "test"}, agent_context)

            # Check history
            history = MockResponseRegistry.get_history()
            assert len(history) == 1
            assert history[0].agent_name == "GhostTextAgent"
            assert "test" in history[0].input_summary

    def test_clear_history(self) -> None:
        """Test clearing mock call history."""
        # Create a mock record
        from pilot_space.ai.providers.mock import MockCallRecord

        MockResponseRegistry.record_call(
            MockCallRecord(
                agent_name="TestAgent",
                input_summary="test input",
                output_summary="test output",
                latency_ms=100,
            )
        )

        assert len(MockResponseRegistry.get_history()) == 1

        MockResponseRegistry.clear_history()

        assert len(MockResponseRegistry.get_history()) == 0


class TestGeneratorRegistry:
    """Test mock generator registration."""

    def test_all_agents_have_generators(self) -> None:
        """Verify all agents have registered mock generators."""
        from pilot_space.ai.providers import (
            mock_generators,  # noqa: F401
            mock_generators_supporting,  # noqa: F401
        )

        registered = MockResponseRegistry.list_registered()

        # Expected agents (from orchestrator AgentName enum)
        expected_agents = [
            "GhostTextAgent",
            "AIContextAgent",
            "PRReviewAgent",
            "IssueExtractorAgent",
            "IssueExtractorSDKAgent",
            "MarginAnnotationAgent",
            "MarginAnnotationAgentSDK",
            "ConversationAgent",
            "ConversationAgentSDK",
            "IssueEnhancerAgent",
            "IssueEnhancerAgentSDK",
            "AssigneeRecommenderAgent",
            "AssigneeRecommenderAgentSDK",
            "DuplicateDetectorAgent",
            "DuplicateDetectorAgentSDK",
            "DocGeneratorAgent",
            "TaskDecomposerAgent",
            "DiagramGeneratorAgent",
            "CommitLinkerAgent",
            "CommitLinkerAgentSDK",
        ]

        # Verify all expected agents are registered
        for agent in expected_agents:
            assert agent in registered, f"Missing mock generator for {agent}"

    def test_generator_produces_valid_output(self) -> None:
        """Test that generators produce non-empty output."""
        from pilot_space.ai.providers import (
            mock_generators,  # noqa: F401
            mock_generators_supporting,  # noqa: F401
        )

        registered = MockResponseRegistry.list_registered()

        # Test a few key generators
        test_cases = [
            ("GhostTextAgent", {"current_text": "test"}),
            ("AIContextAgent", {"issue_id": str(uuid4())}),
            ("PRReviewAgent", {"pr_number": 1, "pr_title": "Test"}),
        ]

        for agent_name, input_data in test_cases:
            if agent_name in registered:
                generator = MockResponseRegistry.get_generator(agent_name)
                assert generator is not None
                output = generator(input_data)
                assert output is not None
                assert len(str(output)) > 0


@pytest.mark.asyncio
async def test_mock_mode_environment_variable() -> None:
    """Test mock mode respects environment variables."""
    # Save original env
    original_env = os.environ.get("APP_ENV")
    original_fake = os.environ.get("AI_FAKE_MODE")

    try:
        # Test with env vars set
        os.environ["APP_ENV"] = "development"
        os.environ["AI_FAKE_MODE"] = "true"

        # Force settings reload
        MockProvider.reset_instance()

        provider = MockProvider.get_instance()
        assert provider.is_enabled()

    finally:
        # Restore original env
        if original_env:
            os.environ["APP_ENV"] = original_env
        else:
            os.environ.pop("APP_ENV", None)

        if original_fake:
            os.environ["AI_FAKE_MODE"] = original_fake
        else:
            os.environ.pop("AI_FAKE_MODE", None)

        MockProvider.reset_instance()
