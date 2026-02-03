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
