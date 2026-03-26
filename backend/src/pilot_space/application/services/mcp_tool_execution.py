"""MCP Tool execution service.

Extracts tool registry management and execution logic from mcp_tools router
into a proper service layer.

Reference: T093 (MCP Tool Discovery Endpoint)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from pilot_space.domain.exceptions import AppError, NotFoundError, ValidationError
from pilot_space.infrastructure.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ToolInfo:
    """Representation of a tool schema for discovery."""

    name: str
    description: str
    requires_approval: bool
    parameters: dict[str, Any]


@dataclass
class ToolExecutionResult:
    """Result of executing an MCP tool."""

    success: bool
    data: dict[str, Any] | None = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class MCPToolExecutionService:
    """Service for MCP tool discovery and execution.

    Manages tool registry lifecycle and delegates execution
    to registered MCP tools.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _create_registry(self) -> Any:
        """Create and populate a tool registry with available tools.

        Returns:
            Populated MCPToolRegistry.
        """
        from pilot_space.ai.mcp.registry import MCPToolRegistry
        from pilot_space.ai.mcp.tools.pr_review import PRReviewTool
        from pilot_space.integrations.github import GitHubClient

        registry = MCPToolRegistry(self._session)

        # Initialize GitHub client (placeholder - should come from workspace config)
        github_client = GitHubClient(access_token="placeholder")
        pr_review_tool = PRReviewTool(github_client)
        registry.register(pr_review_tool)

        return registry

    async def list_available_tools(
        self,
        workspace_id: UUID | None = None,
    ) -> list[ToolInfo]:
        """List all available MCP tools.

        Args:
            workspace_id: Optional workspace filter.

        Returns:
            List of tool info for discovery.
        """
        from pilot_space.ai.mcp.registry import MCPToolRegistry
        from pilot_space.ai.mcp.tools.pr_review import PRReviewTool
        from pilot_space.integrations.github import GitHubClient

        registry = MCPToolRegistry()
        github_client = GitHubClient(access_token="placeholder")
        pr_review_tool = PRReviewTool(github_client)
        registry.register(pr_review_tool)

        tools_data = registry.list_tools(workspace_id=workspace_id)
        return [
            ToolInfo(
                name=tool["name"],
                description=tool["description"],
                requires_approval=tool["requires_approval"],
                parameters=tool["parameters"],
            )
            for tool in tools_data
        ]

    async def execute_tool(
        self,
        tool_name: str,
        workspace_id: UUID,
        user_id: UUID,
        params: dict[str, Any],
    ) -> ToolExecutionResult:
        """Execute an MCP tool.

        Args:
            tool_name: Name of the tool to execute.
            workspace_id: Workspace context.
            user_id: User executing the tool.
            params: Tool parameters.

        Returns:
            Tool execution result.

        Raises:
            NotFoundError: If tool not found.
            ValidationError: If tool parameters are invalid.
            AppError: If tool execution fails.
        """
        from pilot_space.ai.mcp.registry import (
            ToolNotFoundError,
            ToolValidationError,
        )

        registry = self._create_registry()

        try:
            result = await registry.execute(
                tool_name=tool_name,
                workspace_id=workspace_id,
                user_id=user_id,
                params=params,
            )

            return ToolExecutionResult(
                success=result.success,
                data=result.data,
                error=result.error,
                metadata=result.metadata,
            )
        except ToolNotFoundError as e:
            raise NotFoundError(str(e)) from e
        except ToolValidationError as e:
            raise ValidationError(str(e)) from e
        except Exception as e:
            raise AppError(f"Tool execution failed: {e!s}") from e


__all__ = ["MCPToolExecutionService", "ToolExecutionResult", "ToolInfo"]
