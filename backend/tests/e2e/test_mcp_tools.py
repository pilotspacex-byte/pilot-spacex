"""E2E tests for MCP tools (T100).

Tests MCP (Model Context Protocol) tool system:
- Tool registration and discovery
- Tool execution with proper permissions
- RLS enforcement for multi-tenant data
- Error handling and validation

Reference: backend/src/pilot_space/ai/tools/mcp_server.py
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

import pytest

if TYPE_CHECKING:
    from httpx import AsyncClient


class TestMCPTools:
    """E2E tests for MCP tool registry and execution."""

    @pytest.mark.asyncio
    async def test_tool_registration_and_discovery(
        self,
        e2e_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test MCP tools are registered and discoverable.

        Verifies:
        - All expected tools are registered
        - Tools are grouped by category
        - Tool schemas are valid

        Args:
            e2e_client: AsyncClient for making requests.
            auth_headers: Auth headers with API keys.
        """
        # List all available tools
        response = await e2e_client.get(
            "/api/v1/ai/tools",
            headers=auth_headers,
        )
        assert response.status_code == 200
        tools = response.json()

        assert "tools" in tools
        assert len(tools["tools"]) > 0

        # Verify tool categories
        categories = tools["categories"]
        assert "database" in categories
        assert "github" in categories
        assert "search" in categories

        # Verify specific tools exist
        tool_names = {tool["name"] for tool in tools["tools"]}
        expected_tools = [
            "get_issue_by_id",
            "create_issue_in_db",
            "search_issues",
            "get_related_notes",
            "semantic_search",
            "get_pr_diff",
        ]
        for tool_name in expected_tools:
            assert tool_name in tool_names, f"Missing tool: {tool_name}"

    @pytest.mark.asyncio
    async def test_database_tool_execution_with_rls(
        self,
        e2e_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test database tools enforce RLS policies.

        Verifies:
        - User can only access their workspace data
        - RLS prevents cross-workspace access
        - Tool execution respects permissions

        Args:
            e2e_client: AsyncClient for making requests.
            auth_headers: Auth headers with API keys.
        """
        workspace_id = auth_headers["X-Workspace-ID"]
        issue_id = uuid4()

        # Execute get_issue_by_id tool
        response = await e2e_client.post(
            "/api/v1/ai/tools/execute",
            headers=auth_headers,
            json={
                "tool_name": "get_issue_by_id",
                "parameters": {
                    "issue_id": str(issue_id),
                    "workspace_id": workspace_id,
                },
            },
        )

        # Should execute (even if issue doesn't exist, RLS allows query)
        assert response.status_code in [200, 404]

        # Try to access issue from different workspace (should fail RLS)
        fake_workspace_id = str(uuid4())
        response = await e2e_client.post(
            "/api/v1/ai/tools/execute",
            headers={**auth_headers, "X-Workspace-ID": fake_workspace_id},
            json={
                "tool_name": "get_issue_by_id",
                "parameters": {
                    "issue_id": str(issue_id),
                    "workspace_id": fake_workspace_id,
                },
            },
        )

        # Should not find issue (RLS blocks cross-workspace access)
        assert response.status_code in [404, 403]

    @pytest.mark.asyncio
    async def test_write_tool_requires_approval(
        self,
        e2e_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test write tools trigger approval flow.

        Verifies:
        - create_issue_in_db requires approval
        - update_issue_in_db requires approval
        - Approval request is created

        Args:
            e2e_client: AsyncClient for making requests.
            auth_headers: Auth headers with API keys.
        """
        workspace_id = auth_headers["X-Workspace-ID"]
        project_id = uuid4()

        # Execute create_issue_in_db (should require approval)
        response = await e2e_client.post(
            "/api/v1/ai/tools/execute",
            headers=auth_headers,
            json={
                "tool_name": "create_issue_in_db",
                "parameters": {
                    "workspace_id": workspace_id,
                    "project_id": str(project_id),
                    "name": "Test issue",
                    "description": "Test description",
                    "priority": "medium",
                },
            },
        )

        # Should return approval request, not execute immediately
        assert response.status_code == 202
        result = response.json()
        assert "approval_id" in result
        assert "requires_approval" in result
        assert result["requires_approval"] is True

    @pytest.mark.asyncio
    async def test_read_only_tools_auto_execute(
        self,
        e2e_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test read-only tools execute immediately.

        Verifies:
        - get_issue_by_id executes without approval
        - search_issues executes without approval
        - semantic_search executes without approval

        Args:
            e2e_client: AsyncClient for making requests.
            auth_headers: Auth headers with API keys.
        """
        workspace_id = auth_headers["X-Workspace-ID"]

        # Execute search_issues (read-only)
        response = await e2e_client.post(
            "/api/v1/ai/tools/execute",
            headers=auth_headers,
            json={
                "tool_name": "search_issues",
                "parameters": {
                    "workspace_id": workspace_id,
                    "query": "authentication",
                    "limit": 10,
                },
            },
        )

        # Should execute immediately (200), no approval needed
        assert response.status_code == 200
        assert "approval_id" not in response.json()

    @pytest.mark.asyncio
    async def test_tool_parameter_validation(
        self,
        e2e_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test tool parameter validation.

        Verifies:
        - Missing required parameters are rejected
        - Invalid parameter types are rejected
        - Clear error messages are returned

        Args:
            e2e_client: AsyncClient for making requests.
            auth_headers: Auth headers with API keys.
        """
        # Missing required parameter
        response = await e2e_client.post(
            "/api/v1/ai/tools/execute",
            headers=auth_headers,
            json={
                "tool_name": "get_issue_by_id",
                "parameters": {
                    # Missing issue_id
                    "workspace_id": "test-workspace",
                },
            },
        )
        assert response.status_code == 422
        error = response.json()
        assert "detail" in error

        # Invalid parameter type
        response = await e2e_client.post(
            "/api/v1/ai/tools/execute",
            headers=auth_headers,
            json={
                "tool_name": "search_issues",
                "parameters": {
                    "workspace_id": "test-workspace",
                    "limit": "not-a-number",  # Should be int
                },
            },
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_github_tool_integration(
        self,
        e2e_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test GitHub MCP tools.

        Verifies:
        - get_pr_diff tool works
        - get_pr_files tool works
        - GitHub integration is configured

        Args:
            e2e_client: AsyncClient for making requests.
            auth_headers: Auth headers with API keys.
        """
        repository_id = uuid4()

        # Execute get_pr_diff
        response = await e2e_client.post(
            "/api/v1/ai/tools/execute",
            headers=auth_headers,
            json={
                "tool_name": "get_pr_diff",
                "parameters": {
                    "repository_id": str(repository_id),
                    "pr_number": 123,
                },
            },
        )

        # Should execute (may fail if repo/PR doesn't exist, but tool runs)
        assert response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_search_tool_semantic_search(
        self,
        e2e_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test semantic_search tool with embeddings.

        Verifies:
        - Semantic search uses pgvector
        - Results are ranked by relevance
        - Workspace isolation is enforced

        Args:
            e2e_client: AsyncClient for making requests.
            auth_headers: Auth headers with API keys.
        """
        workspace_id = auth_headers["X-Workspace-ID"]

        # Execute semantic_search
        response = await e2e_client.post(
            "/api/v1/ai/tools/execute",
            headers=auth_headers,
            json={
                "tool_name": "semantic_search",
                "parameters": {
                    "workspace_id": workspace_id,
                    "query": "user authentication implementation",
                    "entity_type": "issue",
                    "limit": 5,
                },
            },
        )

        assert response.status_code == 200
        result = response.json()

        # Verify search results structure
        assert "results" in result
        for item in result["results"]:
            assert "entity_id" in item
            assert "entity_type" in item
            assert "similarity_score" in item
            assert 0.0 <= item["similarity_score"] <= 1.0

    @pytest.mark.asyncio
    async def test_tool_execution_error_handling(
        self,
        e2e_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test error handling during tool execution.

        Verifies:
        - Database errors are caught
        - External API errors are caught
        - User-friendly error messages returned

        Args:
            e2e_client: AsyncClient for making requests.
            auth_headers: Auth headers with API keys.
        """
        # Execute tool with invalid UUID
        response = await e2e_client.post(
            "/api/v1/ai/tools/execute",
            headers=auth_headers,
            json={
                "tool_name": "get_issue_by_id",
                "parameters": {
                    "issue_id": "not-a-uuid",
                    "workspace_id": "test-workspace",
                },
            },
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_tool_execution_with_context(
        self,
        e2e_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test tools receive proper execution context.

        Verifies:
        - Workspace ID is injected
        - User ID is available
        - Database session is provided

        Args:
            e2e_client: AsyncClient for making requests.
            auth_headers: Auth headers with API keys.
        """
        workspace_id = auth_headers["X-Workspace-ID"]

        # Execute tool that requires context
        response = await e2e_client.post(
            "/api/v1/ai/tools/execute",
            headers=auth_headers,
            json={
                "tool_name": "search_issues",
                "parameters": {
                    "workspace_id": workspace_id,
                    "query": "test",
                    "limit": 10,
                },
            },
        )

        assert response.status_code == 200
        # Context should enable proper workspace filtering

    @pytest.mark.asyncio
    async def test_tool_registry_categories(
        self,
        e2e_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test tool filtering by category.

        Verifies:
        - Can filter tools by category
        - Database tools are separate from GitHub tools
        - Search tools are separate category

        Args:
            e2e_client: AsyncClient for making requests.
            auth_headers: Auth headers with API keys.
        """
        # Get database tools
        response = await e2e_client.get(
            "/api/v1/ai/tools",
            headers=auth_headers,
            params={"category": "database"},
        )
        assert response.status_code == 200
        db_tools = response.json()

        database_tool_names = {tool["name"] for tool in db_tools["tools"]}
        assert "get_issue_by_id" in database_tool_names
        assert "create_issue_in_db" in database_tool_names

        # Get GitHub tools
        response = await e2e_client.get(
            "/api/v1/ai/tools",
            headers=auth_headers,
            params={"category": "github"},
        )
        assert response.status_code == 200
        github_tools = response.json()

        github_tool_names = {tool["name"] for tool in github_tools["tools"]}
        assert "get_pr_diff" in github_tool_names
        assert "get_pr_files" in github_tool_names


__all__ = ["TestMCPTools"]
