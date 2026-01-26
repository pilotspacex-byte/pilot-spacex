"""Unit tests for MCP tool registry and database tools.

T017-T018: Test tool registration and get_issue_context implementation.
"""

from __future__ import annotations

from pilot_space.ai.tools.database_tools import get_issue_context
from pilot_space.ai.tools.mcp_server import ToolRegistry


class TestToolRegistry:
    """Test suite for ToolRegistry."""

    def test_get_all_tool_names(self) -> None:
        """Verify all registered tools are returned."""
        tools = ToolRegistry.get_all_tool_names()
        assert "get_issue_context" in tools
        assert isinstance(tools, list)

    def test_get_tools_by_category(self) -> None:
        """Verify tools can be retrieved by category."""
        database_tools = ToolRegistry.get_tools_by_category("database")
        assert "get_issue_context" in database_tools
        assert isinstance(database_tools, list)

    def test_get_categories(self) -> None:
        """Verify all categories are returned."""
        categories = ToolRegistry.get_categories()
        assert "database" in categories
        assert "github" in categories
        assert "search" in categories

    def test_get_tool_by_name(self) -> None:
        """Verify specific tool can be retrieved by name."""
        tool = ToolRegistry.get_tool("get_issue_context")
        assert tool is not None
        assert tool.__name__ == "get_issue_context"

    def test_get_tools_with_category_filter(self) -> None:
        """Verify tools can be filtered by category."""
        tools = ToolRegistry.get_tools(categories=["database"])
        assert len(tools) >= 1
        assert get_issue_context in tools

    def test_get_tools_with_name_filter(self) -> None:
        """Verify tools can be retrieved by name list."""
        tools = ToolRegistry.get_tools(names=["get_issue_context"])
        assert len(tools) == 1
        assert tools[0].__name__ == "get_issue_context"

    def test_get_tools_returns_all_when_no_filter(self) -> None:
        """Verify all tools returned when no filter specified."""
        tools = ToolRegistry.get_tools()
        assert len(tools) >= 1

    def test_get_tools_avoids_duplicates(self) -> None:
        """Verify no duplicates when same tool matches multiple filters."""
        tools = ToolRegistry.get_tools(names=["get_issue_context"], categories=["database"])
        # Should only appear once even though it matches both filters
        assert sum(1 for t in tools if t.__name__ == "get_issue_context") == 1
