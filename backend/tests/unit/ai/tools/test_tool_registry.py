"""Unit tests for ToolRegistry extensions (T002).

Tests ToolApprovalLevel enum, ToolResult dataclass, TOOL_APPROVAL_MAP,
and extended _TOOL_CATEGORIES.
"""

from __future__ import annotations

from pilot_space.ai.tools.mcp_server import (
    TOOL_APPROVAL_MAP,
    ToolApprovalLevel,
    ToolRegistry,
    ToolResult,
    get_tool_approval_level,
)


class TestToolApprovalLevel:
    """Tests for ToolApprovalLevel enum."""

    def test_enum_values(self) -> None:
        assert ToolApprovalLevel.AUTO_EXECUTE == "auto_execute"
        assert ToolApprovalLevel.REQUIRE_APPROVAL == "require_approval"
        assert ToolApprovalLevel.ALWAYS_REQUIRE == "always_require"

    def test_enum_is_str(self) -> None:
        assert isinstance(ToolApprovalLevel.AUTO_EXECUTE, str)
        assert f"{ToolApprovalLevel.REQUIRE_APPROVAL}" == "require_approval"

    def test_all_members(self) -> None:
        assert len(ToolApprovalLevel) == 3


class TestToolResult:
    """Tests for ToolResult dataclass."""

    def test_creation_with_required_fields(self) -> None:
        result = ToolResult(
            tool="search_notes",
            operation="search",
            status="executed",
            approval_level=ToolApprovalLevel.AUTO_EXECUTE,
            payload={"notes": [], "total": 0},
        )
        assert result.tool == "search_notes"
        assert result.operation == "search"
        assert result.status == "executed"
        assert result.approval_level == ToolApprovalLevel.AUTO_EXECUTE
        assert result.payload == {"notes": [], "total": 0}
        assert result.preview is None

    def test_creation_with_preview(self) -> None:
        result = ToolResult(
            tool="replace_content",
            operation="replace",
            status="approval_required",
            approval_level=ToolApprovalLevel.REQUIRE_APPROVAL,
            payload={"affected_blocks": ["b1"]},
            preview={"before": "old", "after": "new"},
        )
        assert result.preview == {"before": "old", "after": "new"}


class TestToolApprovalMap:
    """Tests for TOOL_APPROVAL_MAP completeness and correctness."""

    def test_map_has_33_entries(self) -> None:
        """27 spec tools + 6 retained tools = 33 total."""
        assert len(TOOL_APPROVAL_MAP) == 33

    def test_auto_execute_tools(self) -> None:
        auto_tools = [
            "search_notes",
            "search_note_content",
            "get_issue",
            "search_issues",
            "get_project",
            "search_projects",
            "search_comments",
            "get_comments",
            # CM-001: create_comment is non-destructive
            "create_comment",
            # Retained tool: enhance_text is non-destructive
            "enhance_text",
        ]
        for tool_name in auto_tools:
            assert TOOL_APPROVAL_MAP[tool_name] == ToolApprovalLevel.AUTO_EXECUTE, (
                f"{tool_name} should be AUTO_EXECUTE"
            )

    def test_require_approval_tools(self) -> None:
        require_tools = [
            "create_note",
            "update_note",
            "insert_block",
            "remove_block",
            "remove_content",
            "replace_content",
            "create_issue",
            "update_issue",
            "link_issue_to_note",
            "link_issues",
            "add_sub_issue",
            "transition_issue_state",
            "create_project",
            "update_project",
            "update_project_settings",
            "update_comment",
            # Retained tools
            "update_note_block",
            "extract_issues",
            "create_issue_from_note",
            "link_existing_issues",
            "write_to_note",
        ]
        for tool_name in require_tools:
            assert TOOL_APPROVAL_MAP[tool_name] == ToolApprovalLevel.REQUIRE_APPROVAL, (
                f"{tool_name} should be REQUIRE_APPROVAL"
            )

    def test_always_require_tools(self) -> None:
        always_tools = ["unlink_issue_from_note", "unlink_issues"]
        for tool_name in always_tools:
            assert TOOL_APPROVAL_MAP[tool_name] == ToolApprovalLevel.ALWAYS_REQUIRE, (
                f"{tool_name} should be ALWAYS_REQUIRE"
            )

    def test_approval_counts(self) -> None:
        """33 tools: 10 auto + 21 require + 2 always."""
        auto = sum(1 for v in TOOL_APPROVAL_MAP.values() if v == ToolApprovalLevel.AUTO_EXECUTE)
        require = sum(
            1 for v in TOOL_APPROVAL_MAP.values() if v == ToolApprovalLevel.REQUIRE_APPROVAL
        )
        always = sum(1 for v in TOOL_APPROVAL_MAP.values() if v == ToolApprovalLevel.ALWAYS_REQUIRE)
        assert auto == 10
        assert require == 21
        assert always == 2


class TestGetToolApprovalLevel:
    """Tests for get_tool_approval_level helper."""

    def test_known_tool(self) -> None:
        assert get_tool_approval_level("search_notes") == ToolApprovalLevel.AUTO_EXECUTE

    def test_unknown_tool_defaults_to_require(self) -> None:
        assert get_tool_approval_level("nonexistent_tool") == ToolApprovalLevel.REQUIRE_APPROVAL


class TestToolRegistryCategories:
    """Tests for extended _TOOL_CATEGORIES."""

    def test_project_category_exists(self) -> None:
        categories = ToolRegistry.get_categories()
        assert "project" in categories

    def test_comment_category_exists(self) -> None:
        categories = ToolRegistry.get_categories()
        assert "comment" in categories

    def test_all_categories(self) -> None:
        categories = ToolRegistry.get_categories()
        expected = ["database", "github", "search", "note", "issue", "project", "comment"]
        for cat in expected:
            assert cat in categories, f"Missing category: {cat}"
