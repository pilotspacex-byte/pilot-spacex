"""Unit tests for SDKOrchestrator."""

# ruff: noqa: PT019 (mock params from @patch decorator are not fixtures)

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from pilot_space.ai.agents.sdk_base import (
    AgentContext,
    AgentResult,
    SDKBaseAgent,
    StreamingSDKBaseAgent,
)
from pilot_space.ai.sdk_orchestrator import (
    ActionClassification,
    ExecutionResult,
    SDKOrchestrator,
)


class MockAgent(SDKBaseAgent[str, str]):
    """Mock agent for testing."""

    AGENT_NAME = "mock_agent"

    async def execute(self, input_data: str, _context: AgentContext) -> str:
        """Execute mock logic."""
        return f"result: {input_data}"


class MockStreamingAgent(StreamingSDKBaseAgent[str, str]):
    """Mock streaming agent for testing."""

    AGENT_NAME = "mock_streaming"

    async def stream(self, input_data: str, _context: AgentContext):
        """Stream mock output."""
        for word in input_data.split():
            yield word

    async def execute(self, input_data: str, _context: AgentContext) -> str:
        """Execute by collecting stream."""
        chunks: list[str] = []
        async for chunk in self.stream(input_data, _context):
            chunks.append(chunk)
        return " ".join(chunks)


@pytest.fixture
def mock_deps():
    """Create mock dependencies."""
    return {
        "key_storage": MagicMock(),
        "approval_service": MagicMock(),
        "cost_tracker": MagicMock(),
        "session_manager": MagicMock(),
        "provider_selector": MagicMock(),
        "resilient_executor": MagicMock(),
        "tool_registry": MagicMock(),
    }


@pytest.fixture
def orchestrator(mock_deps):
    """Create orchestrator with mocks."""
    return SDKOrchestrator(**mock_deps)


@pytest.fixture
def context():
    """Create test context."""
    return AgentContext(workspace_id=uuid4(), user_id=uuid4())


class TestAgentRegistration:
    """Test agent registration and retrieval."""

    def test_register_agent(self, orchestrator, mock_deps):
        """Verify agent registration."""
        agent = MockAgent(
            tool_registry=mock_deps["tool_registry"],
            provider_selector=mock_deps["provider_selector"],
            cost_tracker=mock_deps["cost_tracker"],
            resilient_executor=mock_deps["resilient_executor"],
        )

        orchestrator.register_agent("test", agent)

        assert orchestrator.get_agent("test") is agent
        assert "test" in orchestrator.list_agents()

    def test_get_unregistered_agent_returns_none(self, orchestrator):
        """Verify getting unregistered agent returns None."""
        assert orchestrator.get_agent("nonexistent") is None

    def test_list_agents_empty_initially(self, orchestrator):
        """Verify agent list is empty initially."""
        assert orchestrator.list_agents() == []

    def test_register_multiple_agents(self, orchestrator, mock_deps):
        """Verify multiple agents can be registered."""
        agent1 = MockAgent(
            tool_registry=mock_deps["tool_registry"],
            provider_selector=mock_deps["provider_selector"],
            cost_tracker=mock_deps["cost_tracker"],
            resilient_executor=mock_deps["resilient_executor"],
        )
        agent2 = MockStreamingAgent(
            tool_registry=mock_deps["tool_registry"],
            provider_selector=mock_deps["provider_selector"],
            cost_tracker=mock_deps["cost_tracker"],
            resilient_executor=mock_deps["resilient_executor"],
        )

        orchestrator.register_agent("agent1", agent1)
        orchestrator.register_agent("agent2", agent2)

        assert len(orchestrator.list_agents()) == 2
        assert "agent1" in orchestrator.list_agents()
        assert "agent2" in orchestrator.list_agents()


class TestActionClassification:
    """Test DD-003 action classification."""

    def test_classify_auto_execute(self, orchestrator):
        """Verify auto-execute actions are classified correctly."""
        classification = orchestrator.classify_action("ghost_text")
        assert classification == ActionClassification.AUTO_EXECUTE

    def test_classify_default_require(self, orchestrator):
        """Verify default require actions are classified correctly."""
        classification = orchestrator.classify_action("create_issue")
        assert classification == ActionClassification.DEFAULT_REQUIRE_APPROVAL

    def test_classify_critical_require(self, orchestrator):
        """Verify critical require actions are classified correctly."""
        classification = orchestrator.classify_action("delete_issue")
        assert classification == ActionClassification.CRITICAL_REQUIRE_APPROVAL

    def test_unknown_action_defaults_to_require(self, orchestrator):
        """Verify unknown actions default to default require."""
        classification = orchestrator.classify_action("unknown_action")
        assert classification == ActionClassification.DEFAULT_REQUIRE_APPROVAL

    def test_all_predefined_classifications(self, orchestrator):
        """Verify all predefined action classifications."""
        auto_execute = ["ghost_text", "margin_annotation", "ai_context", "pr_review"]
        for action in auto_execute:
            assert orchestrator.classify_action(action) == ActionClassification.AUTO_EXECUTE

        default_require = ["create_issue", "create_annotation", "link_commit"]
        for action in default_require:
            assert (
                orchestrator.classify_action(action)
                == ActionClassification.DEFAULT_REQUIRE_APPROVAL
            )

        critical_require = ["delete_issue", "merge_pr", "close_issue"]
        for action in critical_require:
            assert (
                orchestrator.classify_action(action)
                == ActionClassification.CRITICAL_REQUIRE_APPROVAL
            )


@patch("pilot_space.ai.providers.mock.MockProvider.is_enabled", return_value=False)
class TestExecute:
    """Test agent execution without approval.

    Note: _mock_enabled parameter is injected by class-level @patch decorator, not a fixture.
    """

    @pytest.mark.asyncio
    async def test_execute_success(self, _mock_enabled, orchestrator, mock_deps, context):
        """Verify successful agent execution."""
        agent = MockAgent(
            tool_registry=mock_deps["tool_registry"],
            provider_selector=mock_deps["provider_selector"],
            cost_tracker=mock_deps["cost_tracker"],
            resilient_executor=mock_deps["resilient_executor"],
        )

        async def mock_execute(provider, operation):
            return await operation()

        mock_deps["resilient_executor"].execute = AsyncMock(side_effect=mock_execute)
        mock_deps["key_storage"].get_api_key = AsyncMock(return_value="sk-test")

        orchestrator.register_agent("test", agent)
        result = await orchestrator.execute("test", "input", context)

        assert result.success is True
        assert result.output == "result: input"
        assert result.requires_approval is False

    @pytest.mark.asyncio
    async def test_execute_unregistered_agent(self, _mock_enabled, orchestrator, context):
        """Verify executing unregistered agent returns error."""
        result = await orchestrator.execute("unknown", "input", context)

        assert result.success is False
        assert "not registered" in result.error
        assert result.output is None

    @pytest.mark.asyncio
    async def test_execute_no_api_key(self, _mock_enabled, orchestrator, mock_deps, context):
        """Verify execution fails without API key."""
        agent = MockAgent(
            tool_registry=mock_deps["tool_registry"],
            provider_selector=mock_deps["provider_selector"],
            cost_tracker=mock_deps["cost_tracker"],
            resilient_executor=mock_deps["resilient_executor"],
        )
        mock_deps["key_storage"].get_api_key = AsyncMock(return_value=None)

        orchestrator.register_agent("test", agent)

        with pytest.raises(ValueError, match="no anthropic API key"):
            await orchestrator.execute("test", "input", context)


@patch("pilot_space.ai.providers.mock.MockProvider.is_enabled", return_value=False)
class TestExecuteWithApproval:
    """Test agent execution with approval flow."""

    @pytest.mark.asyncio
    async def test_critical_action_requires_approval(
        self, _mock_enabled, orchestrator, mock_deps, context
    ):
        """Verify critical actions always require approval."""
        approval_id = uuid4()
        mock_deps["approval_service"].create_approval_request = AsyncMock(return_value=approval_id)

        result = await orchestrator.execute_with_approval("test", "delete_issue", "input", context)

        assert result.requires_approval is True
        assert result.approval_id == approval_id
        assert result.success is True

    @pytest.mark.asyncio
    async def test_auto_execute_proceeds(self, _mock_enabled, orchestrator, mock_deps, context):
        """Verify auto-execute actions proceed without approval."""
        agent = MockAgent(
            tool_registry=mock_deps["tool_registry"],
            provider_selector=mock_deps["provider_selector"],
            cost_tracker=mock_deps["cost_tracker"],
            resilient_executor=mock_deps["resilient_executor"],
        )

        async def mock_execute(provider, operation):
            return await operation()

        mock_deps["resilient_executor"].execute = AsyncMock(side_effect=mock_execute)
        mock_deps["key_storage"].get_api_key = AsyncMock(return_value="sk-test")

        orchestrator.register_agent("test", agent)
        result = await orchestrator.execute_with_approval("test", "ghost_text", "input", context)

        assert result.requires_approval is False
        assert result.success is True
        assert result.output == "result: input"

    @pytest.mark.asyncio
    async def test_default_require_with_approval_enabled(
        self, _mock_enabled, orchestrator, mock_deps, context
    ):
        """Verify default require actions check workspace settings."""
        approval_id = uuid4()
        mock_deps["approval_service"].check_approval_required = MagicMock(return_value=True)
        mock_deps["approval_service"].create_approval_request = AsyncMock(return_value=approval_id)

        result = await orchestrator.execute_with_approval(
            "test", "create_sub_issues", "input", context
        )

        assert result.requires_approval is True
        assert result.approval_id == approval_id

    @pytest.mark.asyncio
    async def test_default_require_with_approval_disabled(
        self, _mock_enabled, orchestrator, mock_deps, context
    ):
        """Verify default require actions auto-execute when disabled."""
        agent = MockAgent(
            tool_registry=mock_deps["tool_registry"],
            provider_selector=mock_deps["provider_selector"],
            cost_tracker=mock_deps["cost_tracker"],
            resilient_executor=mock_deps["resilient_executor"],
        )

        async def mock_execute(provider, operation):
            return await operation()

        mock_deps["resilient_executor"].execute = AsyncMock(side_effect=mock_execute)
        mock_deps["key_storage"].get_api_key = AsyncMock(return_value="sk-test")
        mock_deps["approval_service"].check_approval_required = MagicMock(return_value=False)

        orchestrator.register_agent("test", agent)
        result = await orchestrator.execute_with_approval(
            "test", "create_sub_issues", "input", context
        )

        assert result.requires_approval is False
        assert result.success is True


@patch("pilot_space.ai.providers.mock.MockProvider.is_enabled", return_value=False)
class TestStreaming:
    """Test streaming execution."""

    @pytest.mark.asyncio
    async def test_stream_success(self, _mock_enabled, orchestrator, mock_deps, context):
        """Verify streaming agent output."""
        agent = MockStreamingAgent(
            tool_registry=mock_deps["tool_registry"],
            provider_selector=mock_deps["provider_selector"],
            cost_tracker=mock_deps["cost_tracker"],
            resilient_executor=mock_deps["resilient_executor"],
        )
        mock_deps["key_storage"].get_api_key = AsyncMock(return_value="sk-test")

        orchestrator.register_agent("streaming", agent)

        chunks = []
        async for chunk in orchestrator.stream("streaming", "hello world", context):
            chunks.append(chunk)

        assert chunks == ["hello", "world"]

    @pytest.mark.asyncio
    async def test_stream_unregistered_agent(self, _mock_enabled, orchestrator, context):
        """Verify streaming unregistered agent yields error."""
        chunks = []
        async for chunk in orchestrator.stream("unknown", "input", context):
            chunks.append(chunk)

        assert len(chunks) == 1
        assert "not registered" in chunks[0]

    @pytest.mark.asyncio
    async def test_stream_non_streaming_agent(
        self, _mock_enabled, orchestrator, mock_deps, context
    ):
        """Verify streaming non-streaming agent yields error."""
        agent = MockAgent(
            tool_registry=mock_deps["tool_registry"],
            provider_selector=mock_deps["provider_selector"],
            cost_tracker=mock_deps["cost_tracker"],
            resilient_executor=mock_deps["resilient_executor"],
        )
        mock_deps["key_storage"].get_api_key = AsyncMock(return_value="sk-test")

        orchestrator.register_agent("non_streaming", agent)

        chunks = []
        async for chunk in orchestrator.stream("non_streaming", "input", context):
            chunks.append(chunk)

        assert len(chunks) == 1
        assert "does not support streaming" in chunks[0]

    @pytest.mark.asyncio
    async def test_stream_no_api_key(self, _mock_enabled, orchestrator, mock_deps, context):
        """Verify streaming fails without API key."""
        agent = MockStreamingAgent(
            tool_registry=mock_deps["tool_registry"],
            provider_selector=mock_deps["provider_selector"],
            cost_tracker=mock_deps["cost_tracker"],
            resilient_executor=mock_deps["resilient_executor"],
        )
        mock_deps["key_storage"].get_api_key = AsyncMock(return_value=None)

        orchestrator.register_agent("streaming", agent)

        chunks = []
        async for chunk in orchestrator.stream("streaming", "input", context):
            chunks.append(chunk)

        assert len(chunks) == 1
        assert "ERROR" in chunks[0]
        assert "API key" in chunks[0]


class TestSessionManagement:
    """Test session management integration."""

    @pytest.mark.asyncio
    async def test_create_session(self, orchestrator, mock_deps, context):
        """Verify session creation."""
        from pilot_space.ai.session.session_manager import AISession

        session_id = uuid4()
        mock_session = AISession(
            id=session_id,
            user_id=context.user_id,
            workspace_id=context.workspace_id,
            agent_name="test",
        )
        mock_deps["session_manager"].create_session = AsyncMock(return_value=mock_session)

        result_id = await orchestrator.create_session(context, "test", {"key": "value"})

        assert result_id == session_id
        mock_deps["session_manager"].create_session.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_session(self, orchestrator, mock_deps):
        """Verify session retrieval."""
        from pilot_space.ai.session.session_manager import AISession

        session_id = uuid4()
        mock_session = AISession(
            id=session_id,
            user_id=uuid4(),
            workspace_id=uuid4(),
            agent_name="test",
        )
        mock_deps["session_manager"].get_session = AsyncMock(return_value=mock_session)

        result = await orchestrator.get_session(session_id)

        assert result is not None
        assert result["id"] == str(session_id)

    @pytest.mark.asyncio
    async def test_get_session_not_found(self, orchestrator, mock_deps):
        """Verify session not found returns None."""
        from pilot_space.ai.session.session_manager import SessionNotFoundError

        session_id = uuid4()
        mock_deps["session_manager"].get_session = AsyncMock(
            side_effect=SessionNotFoundError(session_id)
        )

        result = await orchestrator.get_session(session_id)

        assert result is None

    @pytest.mark.asyncio
    async def test_update_session(self, orchestrator, mock_deps):
        """Verify session update."""
        from pilot_space.ai.session.session_manager import AISession

        session_id = uuid4()
        mock_session = AISession(
            id=session_id,
            user_id=uuid4(),
            workspace_id=uuid4(),
            agent_name="test",
        )
        mock_deps["session_manager"].update_session = AsyncMock(return_value=mock_session)

        await orchestrator.update_session(
            session_id,
            {"message": {"role": "user", "content": "test"}},
        )

        mock_deps["session_manager"].update_session.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_end_session(self, orchestrator, mock_deps):
        """Verify session cleanup."""
        session_id = uuid4()
        mock_deps["session_manager"].end_session = AsyncMock(return_value=True)

        await orchestrator.end_session(session_id)

        mock_deps["session_manager"].end_session.assert_awaited_once_with(session_id)


class TestExecutionResult:
    """Test ExecutionResult factory methods."""

    def test_from_agent_result_success(self):
        """Verify conversion from successful AgentResult."""
        agent_result = AgentResult.ok("output", cost_usd=0.01, input_tokens=100)
        result = ExecutionResult.from_agent_result(agent_result)

        assert result.success is True
        assert result.output == "output"
        assert result.cost_usd == 0.01
        assert result.requires_approval is False
        assert result.error is None

    def test_from_agent_result_failure(self):
        """Verify conversion from failed AgentResult."""
        agent_result = AgentResult.fail("error message")
        result = ExecutionResult.from_agent_result(agent_result)

        assert result.success is False
        assert result.output is None
        assert result.error == "error message"
        assert result.requires_approval is False

    def test_approval_required(self):
        """Verify approval required factory method."""
        approval_id = uuid4()
        result = ExecutionResult.approval_required(approval_id, "Test message")

        assert result.success is True
        assert result.requires_approval is True
        assert result.approval_id == approval_id
        assert result.output["message"] == "Test message"
