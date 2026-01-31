"""Verification tests for Claude Agent SDK installation.

These tests verify that the claude-agent-sdk package is correctly installed
and all required imports are available.

References:
- T002: Verify SDK installation with import test
- specs/004-mvp-agents-build/tasks/P1-T001-T005.md
"""


class TestSDKInstallation:
    """Verify Claude Agent SDK is properly installed and importable."""

    def test_query_import(self) -> None:
        """AC1: from claude_agent_sdk import query succeeds."""
        from claude_agent_sdk import query

        assert query is not None
        assert callable(query)

    def test_client_import(self) -> None:
        """AC2: from claude_agent_sdk import ClaudeSDKClient succeeds."""
        from claude_agent_sdk import ClaudeSDKClient

        assert ClaudeSDKClient is not None

    def test_options_import(self) -> None:
        """AC3: from claude_agent_sdk import ClaudeAgentOptions succeeds."""
        from claude_agent_sdk import ClaudeAgentOptions

        assert ClaudeAgentOptions is not None

    def test_tool_import(self) -> None:
        """AC4: from claude_agent_sdk import tool succeeds."""
        from claude_agent_sdk import tool

        assert tool is not None
        assert callable(tool)

    def test_mcp_server_import(self) -> None:
        """AC4: from claude_agent_sdk import create_sdk_mcp_server succeeds."""
        from claude_agent_sdk import create_sdk_mcp_server

        assert create_sdk_mcp_server is not None
        assert callable(create_sdk_mcp_server)

    def test_types_import(self) -> None:
        """Verify type imports for response handling."""
        from claude_agent_sdk import (
            AssistantMessage,
            ResultMessage,
            TextBlock,
            ToolUseBlock,
        )

        assert AssistantMessage is not None
        assert ResultMessage is not None
        assert TextBlock is not None
        assert ToolUseBlock is not None

    def test_mcp_server_config_import(self) -> None:
        """Verify MCP server configuration types."""
        from claude_agent_sdk import McpSdkServerConfig

        assert McpSdkServerConfig is not None


class TestSDKVersion:
    """Verify SDK version meets requirements."""

    def test_version_available(self) -> None:
        """SDK version should be accessible."""
        import claude_agent_sdk

        assert hasattr(claude_agent_sdk, "__version__")

    def test_version_constraint(self) -> None:
        """SDK version should be >=0.1.0,<1.0."""
        import claude_agent_sdk

        version = claude_agent_sdk.__version__
        major, minor, _patch = map(int, version.split(".")[:3])

        # Version should be 0.x.x
        assert major == 0, f"Expected major version 0, got {major}"
        assert minor >= 1, f"Expected minor version >= 1, got {minor}"


class TestAIContextAgentMigration:
    """Test AIContextAgent SDK migration (T038-T043)."""

    def test_sdk_base_import(self) -> None:
        """Verify SDK base classes can be imported."""
        from pilot_space.ai.agents.agent_base import (
            AgentContext,
            AgentResult,
            SDKBaseAgent,
            StreamingSDKBaseAgent,
        )

        assert AgentContext is not None
        assert AgentResult is not None
        assert SDKBaseAgent is not None
        assert StreamingSDKBaseAgent is not None

    def test_ai_context_agent_direct_import(self) -> None:
        """Verify AIContextAgent can be imported directly."""
        from importlib import import_module

        # Import module directly to avoid __init__.py circular import
        module = import_module("pilot_space.ai.agents.ai_context_agent")

        assert hasattr(module, "AIContextAgent")
        assert hasattr(module, "AIContextInput")
        assert hasattr(module, "AIContextOutput")

    def test_ai_context_agent_instantiation(self) -> None:
        """Verify AIContextAgent can be instantiated with mocked dependencies."""
        from unittest.mock import AsyncMock, MagicMock

        from pilot_space.ai.agents.ai_context_agent import AIContextAgent

        # Create mocked dependencies
        mock_tool_registry = MagicMock()
        mock_provider_selector = MagicMock()
        mock_cost_tracker = AsyncMock()
        mock_cost_tracker.track = AsyncMock(return_value=MagicMock(cost_usd=0.05))
        mock_resilient_executor = MagicMock()

        # Instantiate agent
        agent = AIContextAgent(
            tool_registry=mock_tool_registry,
            provider_selector=mock_provider_selector,
            cost_tracker=mock_cost_tracker,
            resilient_executor=mock_resilient_executor,
        )

        # Verify agent attributes
        assert agent.AGENT_NAME == "ai_context"
        assert agent.DEFAULT_MODEL == "claude-opus-4-5-20251101"

        # Verify get_model
        provider, model = agent.get_model()
        assert provider == "anthropic"
        assert model == "claude-opus-4-5-20251101"

    def test_data_classes(self) -> None:
        """Verify data classes work correctly."""
        from uuid import uuid4

        from pilot_space.ai.agents.ai_context_agent import (
            CodeReference,
            RelatedItem,
            TaskItem,
        )

        # Test RelatedItem
        item = RelatedItem(
            id=str(uuid4()),
            type="issue",
            title="Test",
            relevance_score=0.85,
            excerpt="Test excerpt",
            identifier="PILOT-1",
            state="open",
        )
        item_dict = item.to_dict()
        assert item_dict["type"] == "issue"
        assert item_dict["relevance_score"] == 0.85

        # Test CodeReference
        ref = CodeReference(
            file_path="src/main.py",
            line_range=(10, 20),
            description="Main function",
            relevance="high",
        )
        ref_dict = ref.to_dict()
        assert ref_dict["file_path"] == "src/main.py"
        assert ref_dict["line_start"] == 10

        # Test TaskItem
        task = TaskItem(
            id="task-1",
            description="Implement feature",
            completed=False,
            dependencies=[],
            estimated_effort="M",
            order=1,
        )
        task_dict = task.to_dict()
        assert task_dict["id"] == "task-1"
        assert task_dict["estimated_effort"] == "M"
