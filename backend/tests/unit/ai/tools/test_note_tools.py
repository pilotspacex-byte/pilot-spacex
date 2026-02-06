"""Unit tests for note manipulation MCP tools.

Tests for 6 note/issue tools that AI agents use to manipulate notes
and create/link issues during conversations.

Following TDD: Write failing tests first, then implement.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from pilot_space.ai.tools.mcp_server import ToolRegistry
from pilot_space.ai.tools.note_tools import (
    create_issue_from_note,
    enhance_text,
    extract_issues,
    link_existing_issues,
    update_note_block,
)


class TestUpdateNoteBlock:
    """Test suite for update_note_block tool."""

    def test_that_tool_is_registered(self) -> None:
        """Verify update_note_block is registered in note category."""
        tool = ToolRegistry.get_tool("update_note_block")
        assert tool is not None
        assert tool.__name__ == "update_note_block"

        note_tools = ToolRegistry.get_tools_by_category("note")
        assert "update_note_block" in note_tools

    @pytest.mark.asyncio
    async def test_that_returns_correct_structure_for_replace(self) -> None:
        """Verify replace operation returns correct dict structure."""
        # Act
        result = await update_note_block(
            note_id=str(uuid4()),
            block_id="block-123",
            new_content_markdown="# Updated heading",
            operation="replace",
        )

        # Assert
        assert result["tool"] == "update_note_block"
        assert result["operation"] == "replace_block"
        assert result["block_id"] == "block-123"
        assert result["markdown"] == "# Updated heading"
        assert result["status"] == "pending_apply"
        assert "note_id" in result

    @pytest.mark.asyncio
    async def test_that_returns_correct_structure_for_append(self) -> None:
        """Verify append operation returns correct dict structure."""
        # Act
        result = await update_note_block(
            note_id=str(uuid4()),
            block_id="block-456",
            new_content_markdown="New paragraph content",
            operation="append",
        )

        # Assert
        assert result["tool"] == "update_note_block"
        assert result["operation"] == "append_blocks"
        assert result["block_id"] == "block-456"
        assert result["markdown"] == "New paragraph content"
        assert result["status"] == "pending_apply"

    @pytest.mark.asyncio
    async def test_that_validates_operation_type(self) -> None:
        """Verify invalid operation type is rejected."""
        # Act
        result = await update_note_block(
            note_id=str(uuid4()),
            block_id="block-123",
            new_content_markdown="Content",
            operation="invalid",
        )

        # Assert
        assert "error" in result
        assert "operation" in result["error"].lower()


class TestEnhanceText:
    """Test suite for enhance_text tool."""

    def test_that_tool_is_registered(self) -> None:
        """Verify enhance_text is registered in note category."""
        tool = ToolRegistry.get_tool("enhance_text")
        assert tool is not None
        assert tool.__name__ == "enhance_text"

        note_tools = ToolRegistry.get_tools_by_category("note")
        assert "enhance_text" in note_tools

    @pytest.mark.asyncio
    async def test_that_returns_enhanced_content_structure(self) -> None:
        """Verify returns correct structure with enhanced content."""
        # Act
        result = await enhance_text(
            note_id=str(uuid4()),
            block_id="block-789",
            enhanced_markdown="This is **improved** content with better clarity.",
        )

        # Assert
        assert result["tool"] == "enhance_text"
        assert result["operation"] == "replace_block"
        assert result["block_id"] == "block-789"
        assert result["markdown"] == "This is **improved** content with better clarity."
        assert result["status"] == "pending_apply"

    @pytest.mark.asyncio
    async def test_that_includes_block_id_and_markdown(self) -> None:
        """Verify all required fields are present."""
        # Act
        result = await enhance_text(
            note_id=str(uuid4()),
            block_id="block-999",
            enhanced_markdown="Enhanced text",
        )

        # Assert
        assert "note_id" in result
        assert "block_id" in result
        assert "markdown" in result
        assert result["block_id"] == "block-999"


class TestExtractIssues:
    """Test suite for extract_issues tool."""

    def test_that_tool_is_registered(self) -> None:
        """Verify extract_issues is registered in note category."""
        tool = ToolRegistry.get_tool("extract_issues")
        assert tool is not None
        assert tool.__name__ == "extract_issues"

        note_tools = ToolRegistry.get_tools_by_category("note")
        assert "extract_issues" in note_tools

    @pytest.mark.asyncio
    async def test_that_returns_created_issues_list(self) -> None:
        """Verify returns list of issues to create."""
        issues_data = [
            {
                "title": "Implement user authentication",
                "description": "Add JWT-based auth",
                "priority": "high",
                "type": "feature",
            },
            {
                "title": "Fix login bug",
                "description": "Users can't login with email",
                "priority": "urgent",
                "type": "bug",
            },
        ]

        # Act
        result = await extract_issues(
            note_id=str(uuid4()),
            block_ids=["block-1", "block-2"],
            issues=issues_data,
        )

        # Assert
        assert result["tool"] == "extract_issues"
        assert result["operation"] == "create_issues"
        assert result["status"] == "pending_apply"
        assert len(result["issues"]) == 2
        assert result["issues"][0]["title"] == "Implement user authentication"
        assert result["issues"][1]["priority"] == "urgent"

    @pytest.mark.asyncio
    async def test_that_handles_multiple_issues(self) -> None:
        """Verify can handle multiple issue extractions."""
        issues_data = [
            {
                "title": f"Issue {i}",
                "description": f"Desc {i}",
                "priority": "medium",
                "type": "task",
            }
            for i in range(5)
        ]

        # Act
        result = await extract_issues(
            note_id=str(uuid4()),
            block_ids=[f"block-{i}" for i in range(5)],
            issues=issues_data,
        )

        # Assert
        assert len(result["issues"]) == 5
        assert all("title" in issue for issue in result["issues"])

    @pytest.mark.asyncio
    async def test_that_validates_issue_data_structure(self) -> None:
        """Verify validates issue data has required fields."""
        invalid_issues = [{"title": "No type or priority"}]

        # Act
        result = await extract_issues(
            note_id=str(uuid4()),
            block_ids=["block-1"],
            issues=invalid_issues,
        )

        # Assert - Should still work with defaults
        assert result["tool"] == "extract_issues"
        assert len(result["issues"]) == 1


class TestCreateIssueFromNote:
    """Test suite for create_issue_from_note tool."""

    def test_that_tool_is_registered(self) -> None:
        """Verify create_issue_from_note is registered in issue category."""
        tool = ToolRegistry.get_tool("create_issue_from_note")
        assert tool is not None
        assert tool.__name__ == "create_issue_from_note"

        issue_tools = ToolRegistry.get_tools_by_category("issue")
        assert "create_issue_from_note" in issue_tools

    @pytest.mark.asyncio
    async def test_that_returns_issue_data_structure(self) -> None:
        """Verify returns issue creation data."""
        # Act
        result = await create_issue_from_note(
            note_id=str(uuid4()),
            block_id="block-555",
            title="Setup CI/CD pipeline",
            description="Configure GitHub Actions",
            priority="high",
            issue_type="feature",
        )

        # Assert
        assert result["tool"] == "create_issue_from_note"
        assert result["operation"] == "create_single_issue"
        assert result["status"] == "pending_apply"
        assert result["issue"]["title"] == "Setup CI/CD pipeline"
        assert result["issue"]["priority"] == "high"
        assert result["issue"]["type"] == "feature"

    @pytest.mark.asyncio
    async def test_that_includes_note_link_info(self) -> None:
        """Verify includes note link metadata."""
        note_id = str(uuid4())

        # Act
        result = await create_issue_from_note(
            note_id=note_id,
            block_id="block-777",
            title="Test issue",
            description="Description",
        )

        # Assert
        assert result["note_id"] == note_id
        assert result["block_id"] == "block-777"
        assert result["link_type"] == "extracted"

    @pytest.mark.asyncio
    async def test_that_handles_default_priority_and_type(self) -> None:
        """Verify uses defaults when not specified."""
        # Act
        result = await create_issue_from_note(
            note_id=str(uuid4()),
            block_id="block-888",
            title="Issue with defaults",
            description="Test defaults",
        )

        # Assert
        assert result["issue"]["priority"] == "medium"
        assert result["issue"]["type"] == "task"


class TestLinkExistingIssues:
    """Test suite for link_existing_issues tool."""

    def test_that_tool_is_registered(self) -> None:
        """Verify link_existing_issues is registered in note category."""
        tool = ToolRegistry.get_tool("link_existing_issues")
        assert tool is not None
        assert tool.__name__ == "link_existing_issues"

        note_tools = ToolRegistry.get_tools_by_category("note")
        assert "link_existing_issues" in note_tools

    @pytest.mark.asyncio
    async def test_that_returns_search_results_structure(self) -> None:
        """Verify returns search results for linking."""
        # Act
        result = await link_existing_issues(
            note_id=str(uuid4()),
            search_query="authentication bug",
            workspace_id=str(uuid4()),
        )

        # Assert
        assert result["tool"] == "link_existing_issues"
        assert result["operation"] == "search_issues"
        assert result["status"] == "pending_apply"
        assert "search_query" in result
        assert result["search_query"] == "authentication bug"

    @pytest.mark.asyncio
    async def test_that_includes_workspace_context(self) -> None:
        """Verify includes workspace ID for scoped search."""
        workspace_id = str(uuid4())

        # Act
        result = await link_existing_issues(
            note_id=str(uuid4()),
            search_query="query",
            workspace_id=workspace_id,
        )

        # Assert
        assert result["workspace_id"] == workspace_id


class TestToolCategoryRegistration:
    """Test suite for verifying all tools are registered in correct categories."""

    def test_that_all_note_tools_are_registered(self) -> None:
        """Verify all 5 retained note tools are registered and accessible."""
        note_tools = ToolRegistry.get_tools_by_category("note")

        expected_note_tools = [
            "update_note_block",
            "enhance_text",
            "extract_issues",
            "link_existing_issues",
        ]

        for tool_name in expected_note_tools:
            assert tool_name in note_tools, f"{tool_name} not found in note category"

    def test_that_issue_tool_is_registered(self) -> None:
        """Verify create_issue_from_note is in issue category."""
        issue_tools = ToolRegistry.get_tools_by_category("issue")
        assert "create_issue_from_note" in issue_tools

    def test_that_all_tools_have_docstrings(self) -> None:
        """Verify all retained tools have documentation."""
        tool_names = [
            "update_note_block",
            "enhance_text",
            "extract_issues",
            "create_issue_from_note",
            "link_existing_issues",
        ]

        for tool_name in tool_names:
            tool = ToolRegistry.get_tool(tool_name)
            assert tool is not None
            assert tool.__doc__ is not None
            assert len(tool.__doc__.strip()) > 10, f"{tool_name} has insufficient docstring"
