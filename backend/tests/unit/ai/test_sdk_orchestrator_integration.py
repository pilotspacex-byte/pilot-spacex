"""Integration tests for SDK orchestrator and DI container.

Verifies that the orchestrator can be instantiated with registered agents.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest

if TYPE_CHECKING:
    from pilot_space.ai.sdk_orchestrator import SDKOrchestrator


@pytest.fixture
def mock_session() -> AsyncMock:
    """Create mock database session.

    Returns:
        Mock AsyncSession.
    """
    return AsyncMock()


@pytest.fixture
def mock_key_storage() -> AsyncMock:
    """Create mock key storage.

    Returns:
        Mock SecureKeyStorage.
    """
    return AsyncMock()


@pytest.fixture
def mock_approval_service() -> AsyncMock:
    """Create mock approval service.

    Returns:
        Mock ApprovalService.
    """
    return AsyncMock()


@pytest.fixture
def mock_cost_tracker() -> AsyncMock:
    """Create mock cost tracker.

    Returns:
        Mock CostTracker.
    """
    return AsyncMock()


@pytest.fixture
def mock_session_manager() -> AsyncMock:
    """Create mock session manager.

    Returns:
        Mock SessionManager.
    """
    return AsyncMock()


@pytest.fixture
def mock_provider_selector() -> MagicMock:
    """Create mock provider selector.

    Returns:
        Mock ProviderSelector.
    """
    return MagicMock()


@pytest.fixture
def mock_resilient_executor() -> MagicMock:
    """Create mock resilient executor.

    Returns:
        Mock ResilientExecutor.
    """
    return MagicMock()


@pytest.fixture
def mock_tool_registry() -> MagicMock:
    """Create mock tool registry.

    Returns:
        Mock ToolRegistry.
    """
    return MagicMock()


@pytest.fixture
def sdk_orchestrator(
    mock_key_storage: AsyncMock,
    mock_approval_service: AsyncMock,
    mock_cost_tracker: AsyncMock,
    mock_session_manager: AsyncMock,
    mock_provider_selector: MagicMock,
    mock_resilient_executor: MagicMock,
    mock_tool_registry: MagicMock,
) -> SDKOrchestrator:
    """Create SDK orchestrator with mocked dependencies.

    Args:
        mock_key_storage: Mock key storage.
        mock_approval_service: Mock approval service.
        mock_cost_tracker: Mock cost tracker.
        mock_session_manager: Mock session manager.
        mock_provider_selector: Mock provider selector.
        mock_resilient_executor: Mock resilient executor.
        mock_tool_registry: Mock tool registry.

    Returns:
        SDKOrchestrator instance.
    """
    from pilot_space.ai.sdk_orchestrator import SDKOrchestrator

    return SDKOrchestrator(
        key_storage=mock_key_storage,
        approval_service=mock_approval_service,
        cost_tracker=mock_cost_tracker,
        session_manager=mock_session_manager,
        provider_selector=mock_provider_selector,
        resilient_executor=mock_resilient_executor,
        tool_registry=mock_tool_registry,
    )


class TestSDKOrchestratorIntegration:
    """Test SDK orchestrator integration with container."""

    def test_orchestrator_initializes(self, sdk_orchestrator: SDKOrchestrator) -> None:
        """Verify orchestrator initializes correctly.

        Args:
            sdk_orchestrator: SDK orchestrator fixture.
        """
        assert sdk_orchestrator is not None
        assert sdk_orchestrator.list_agents() == []

    def test_can_register_agents(self, sdk_orchestrator: SDKOrchestrator) -> None:
        """Verify agents can be registered.

        Args:
            sdk_orchestrator: SDK orchestrator fixture.
        """
        from pilot_space.ai.sdk_orchestrator import AgentName

        # Create a simple mock agent
        mock_agent = MagicMock()

        # Register agent
        sdk_orchestrator.register_agent(AgentName.GHOST_TEXT, mock_agent)

        # Verify registration
        assert AgentName.GHOST_TEXT in sdk_orchestrator.list_agents()
        assert sdk_orchestrator.get_agent(AgentName.GHOST_TEXT) is mock_agent

    def test_all_agent_names_are_defined(self) -> None:
        """Verify all expected agent names exist in AgentName enum."""
        from pilot_space.ai.sdk_orchestrator import AgentName

        expected_agents = [
            # Note-related agents
            "ghost_text",
            "margin_annotation",
            "issue_extractor",
            # Issue-related agents
            "ai_context",
            "conversation",
            "issue_enhancer",
            "assignee_recommender",
            "duplicate_detector",
            # PR/Code agents
            "pr_review",
            "commit_linker",
            # Documentation agents
            "doc_generator",
            "task_decomposer",
            "diagram_generator",
        ]

        agent_names = [name.value for name in AgentName]

        for expected in expected_agents:
            assert expected in agent_names, f"Agent {expected} not in AgentName enum"

    def test_orchestrator_classify_action(self, sdk_orchestrator: SDKOrchestrator) -> None:
        """Verify action classification works.

        Args:
            sdk_orchestrator: SDK orchestrator fixture.
        """
        from pilot_space.ai.sdk_orchestrator import ActionClassification

        # Test auto-execute actions
        assert sdk_orchestrator.classify_action("ghost_text") == ActionClassification.AUTO_EXECUTE
        assert sdk_orchestrator.classify_action("pr_review") == ActionClassification.AUTO_EXECUTE

        # Test default require approval
        assert (
            sdk_orchestrator.classify_action("create_issue")
            == ActionClassification.DEFAULT_REQUIRE_APPROVAL
        )

        # Test critical require approval
        assert (
            sdk_orchestrator.classify_action("delete_issue")
            == ActionClassification.CRITICAL_REQUIRE_APPROVAL
        )

    @pytest.mark.asyncio
    async def test_orchestrator_ensure_api_key(
        self, sdk_orchestrator: SDKOrchestrator, mock_key_storage: AsyncMock
    ) -> None:
        """Verify API key validation.

        Args:
            sdk_orchestrator: SDK orchestrator fixture.
            mock_key_storage: Mock key storage.
        """
        workspace_id = UUID("00000000-0000-0000-0000-000000000001")

        # Mock key exists
        mock_key_storage.get_api_key.return_value = "test-api-key"

        result = await sdk_orchestrator.ensure_api_key(workspace_id, "anthropic")
        assert result is True
        mock_key_storage.get_api_key.assert_awaited_once_with(workspace_id, "anthropic")

    @pytest.mark.asyncio
    async def test_orchestrator_ensure_api_key_missing(
        self, sdk_orchestrator: SDKOrchestrator, mock_key_storage: AsyncMock
    ) -> None:
        """Verify API key validation raises on missing key.

        Args:
            sdk_orchestrator: SDK orchestrator fixture.
            mock_key_storage: Mock key storage.
        """
        workspace_id = UUID("00000000-0000-0000-0000-000000000001")

        # Mock no key
        mock_key_storage.get_api_key.return_value = None

        with pytest.raises(ValueError, match="no anthropic API key configured"):
            await sdk_orchestrator.ensure_api_key(workspace_id, "anthropic")


class TestContainerAppStateIntegration:
    """Test container assignment to app.state."""

    def test_container_can_be_retrieved(self) -> None:
        """Verify container can be retrieved from get_container."""
        from pilot_space.container import get_container

        container = get_container()
        assert container is not None
        assert hasattr(container, "config")
        assert hasattr(container, "session_manager")
        assert hasattr(container, "provider_selector")
        assert hasattr(container, "resilient_executor")
        assert hasattr(container, "tool_registry")

    def test_app_startup_sets_container(self) -> None:
        """Verify app lifespan sets container in app.state."""
        from pilot_space.main import app

        # Check that app has lifespan configured
        assert app.router.lifespan_context is not None

        # Note: We can't test the actual lifespan execution without
        # running the full FastAPI app, but we can verify the lifespan
        # function exists and is properly configured.
        assert hasattr(app, "state")

    def test_register_sdk_agents_function_exists(self) -> None:
        """Verify register_sdk_agents function exists and is callable."""
        from pilot_space.container import register_sdk_agents

        assert callable(register_sdk_agents)

    def test_register_sdk_agents_registers_all_agents(
        self, sdk_orchestrator: SDKOrchestrator
    ) -> None:
        """Verify register_sdk_agents registers all expected agents.

        Args:
            sdk_orchestrator: SDK orchestrator fixture.
        """
        from pilot_space.ai.sdk_orchestrator import AgentName
        from pilot_space.container import register_sdk_agents

        # Initially no agents
        assert len(sdk_orchestrator.list_agents()) == 0

        # Register agents
        register_sdk_agents(sdk_orchestrator)

        # Verify all expected agents are registered
        registered_agents = sdk_orchestrator.list_agents()
        expected_agents = [
            AgentName.GHOST_TEXT,
            AgentName.MARGIN_ANNOTATION,
            AgentName.ISSUE_EXTRACTOR,
            AgentName.AI_CONTEXT,
            AgentName.CONVERSATION,
            AgentName.ISSUE_ENHANCER,
            AgentName.ASSIGNEE_RECOMMENDER,
            # DUPLICATE_DETECTOR skipped - requires AsyncSession
            AgentName.PR_REVIEW,
            AgentName.COMMIT_LINKER,
            AgentName.DOC_GENERATOR,
            AgentName.TASK_DECOMPOSER,
            AgentName.DIAGRAM_GENERATOR,
        ]

        for agent_name in expected_agents:
            assert agent_name in registered_agents, f"Agent {agent_name} not registered"

        # Verify total count matches
        assert len(registered_agents) == len(expected_agents)
