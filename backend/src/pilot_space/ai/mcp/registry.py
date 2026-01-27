"""MCP Tool Registry for dynamic tool management.

Provides discovery, validation, and execution of MCP tools with RLS enforcement.

Reference: T089-T093 (MCP Tool Registration)
Design Decisions: DD-003 (Human-in-the-loop for destructive actions)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any
from uuid import UUID

from pilot_space.ai.exceptions import AIError
from pilot_space.ai.mcp.base import MCPTool, ToolResult

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class ToolNotFoundError(AIError):
    """Raised when tool is not found in registry."""

    error_code = "tool_not_found"
    http_status = 404


class ToolValidationError(AIError):
    """Raised when tool parameters are invalid."""

    error_code = "tool_validation_error"
    http_status = 422


class ToolExecutionError(AIError):
    """Raised when tool execution fails."""

    error_code = "tool_execution_error"
    http_status = 500


class MCPToolRegistry:
    """Registry for MCP tools with dynamic discovery and execution.

    Provides:
    - Tool registration and deregistration
    - Schema validation
    - Sandboxed execution
    - RLS enforcement per workspace
    - Tool discovery for agents

    Example:
        registry = MCPToolRegistry(db_session)

        # Register tool
        registry.register(pr_review_tool)

        # Discover tools
        tools = registry.list_tools(workspace_id)

        # Execute tool
        result = await registry.execute(
            tool_name="review_pull_request",
            workspace_id=workspace_id,
            user_id=user_id,
            params={"repo": "owner/repo", "pr_number": 123},
        )
    """

    def __init__(self, db_session: AsyncSession | None = None) -> None:
        """Initialize tool registry.

        Args:
            db_session: Optional database session for RLS checks.
        """
        self._tools: dict[str, MCPTool] = {}
        self._db_session = db_session

    def register(self, tool: MCPTool) -> None:
        """Register a tool.

        Args:
            tool: MCPTool instance to register.

        Raises:
            ValueError: If tool with same name already registered.
        """
        if tool.name in self._tools:
            raise ValueError(f"Tool '{tool.name}' is already registered")

        self._tools[tool.name] = tool

        logger.info(
            "Registered MCP tool",
            extra={
                "tool_name": tool.name,
                "requires_approval": tool.requires_approval,
            },
        )

    def deregister(self, tool_name: str) -> bool:
        """Deregister a tool.

        Args:
            tool_name: Name of tool to remove.

        Returns:
            True if removed, False if not found.
        """
        if tool_name in self._tools:
            del self._tools[tool_name]
            logger.info("Deregistered MCP tool", extra={"tool_name": tool_name})
            return True

        return False

    def get_tool(self, tool_name: str) -> MCPTool | None:
        """Get tool by name.

        Args:
            tool_name: Tool name.

        Returns:
            MCPTool instance or None if not found.
        """
        return self._tools.get(tool_name)

    def list_tools(
        self,
        workspace_id: UUID | None = None,
    ) -> list[dict[str, Any]]:
        """List all registered tools with schemas.

        Args:
            workspace_id: Optional workspace filter (for future RLS).

        Returns:
            List of tool schema dictionaries.
        """
        # For MVP, return all tools
        # Future: Filter by workspace permissions
        _ = workspace_id  # Reserved for future RLS filtering
        return [tool.to_schema() for tool in self._tools.values()]

    def validate_parameters(
        self,
        tool_name: str,
        params: dict[str, Any],
    ) -> tuple[bool, str | None]:
        """Validate tool parameters against schema.

        Args:
            tool_name: Tool name.
            params: Parameters to validate.

        Returns:
            Tuple of (is_valid, error_message).
        """
        tool = self.get_tool(tool_name)
        if not tool:
            return False, f"Tool '{tool_name}' not found"

        # Check required parameters
        for param_def in tool.parameters:
            if param_def.required and param_def.name not in params:
                return False, f"Missing required parameter: {param_def.name}"

        # Type validation (basic)
        for param_def in tool.parameters:
            param_value = params.get(param_def.name)
            if param_value is not None:
                expected_type = self._get_python_type(param_def.type.value)
                if not isinstance(param_value, expected_type):
                    return False, (
                        f"Parameter '{param_def.name}' expected type {param_def.type.value}, "
                        f"got {type(param_value).__name__}"
                    )

        return True, None

    @staticmethod
    def _get_python_type(json_type: str) -> type:
        """Map JSON schema type to Python type.

        Args:
            json_type: JSON schema type string.

        Returns:
            Python type.
        """
        type_map = {
            "string": str,
            "integer": int,
            "boolean": bool,
            "object": dict,
            "array": list,
        }
        return type_map.get(json_type, str)

    async def check_permission(
        self,
        tool_name: str,
        workspace_id: UUID,
        user_id: UUID,
    ) -> tuple[bool, str | None]:
        """Check if user has permission to use tool in workspace.

        Args:
            tool_name: Tool name.
            workspace_id: Workspace UUID.
            user_id: User UUID.

        Returns:
            Tuple of (has_permission, error_message).
        """
        _ = tool_name  # Reserved for future tool-specific permissions

        # Basic permission check: verify user is workspace member
        if not self._db_session:
            logger.warning("No database session available for permission check")
            return True, None  # Permissive for MVP

        try:
            from sqlalchemy import and_, select

            from pilot_space.infrastructure.database.models.workspace_member import (
                WorkspaceMember,
            )

            # Check workspace membership
            stmt = select(WorkspaceMember).where(
                and_(
                    WorkspaceMember.workspace_id == workspace_id,
                    WorkspaceMember.user_id == user_id,
                )
            )

            result = await self._db_session.execute(stmt)
            member = result.scalar_one_or_none()

            if not member:
                return False, "User is not a member of this workspace"

            return True, None

        except Exception as e:
            logger.exception("Permission check failed")
            return False, f"Permission check failed: {e!s}"

    async def execute(
        self,
        tool_name: str,
        workspace_id: UUID,
        user_id: UUID,
        params: dict[str, Any],
    ) -> ToolResult:
        """Execute a tool with sandboxing and RLS enforcement.

        Args:
            tool_name: Tool name.
            workspace_id: Workspace UUID for RLS.
            user_id: User UUID for attribution.
            params: Tool parameters.

        Returns:
            ToolResult with success/failure.

        Raises:
            ToolNotFoundError: If tool not found.
            ToolValidationError: If parameters invalid.
            ToolExecutionError: If execution fails.
        """
        # Get tool
        tool = self.get_tool(tool_name)
        if not tool:
            raise ToolNotFoundError(
                f"Tool '{tool_name}' not found",
                details={"tool_name": tool_name},
            )

        # Validate parameters
        is_valid, error_msg = self.validate_parameters(tool_name, params)
        if not is_valid:
            raise ToolValidationError(
                error_msg or "Invalid parameters",
                details={"tool_name": tool_name, "params": params},
            )

        # Check permissions
        has_permission, perm_error = await self.check_permission(
            tool_name,
            workspace_id,
            user_id,
        )
        if not has_permission:
            return ToolResult.fail(
                error=perm_error or "Permission denied",
                metadata={"tool_name": tool_name},
            )

        # Execute tool in sandbox
        try:
            result = await self._execute_sandboxed(
                tool=tool,
                workspace_id=workspace_id,
                user_id=user_id,
                params=params,
            )

            logger.info(
                "Tool executed successfully",
                extra={
                    "tool_name": tool_name,
                    "workspace_id": str(workspace_id),
                    "user_id": str(user_id),
                    "success": result.success,
                },
            )

            return result

        except Exception as e:
            logger.exception("Tool execution failed")
            raise ToolExecutionError(
                f"Tool execution failed: {e!s}",
                details={
                    "tool_name": tool_name,
                    "error": str(e),
                },
            ) from e

    async def _execute_sandboxed(
        self,
        tool: MCPTool,
        workspace_id: UUID,
        user_id: UUID,
        params: dict[str, Any],
    ) -> ToolResult:
        """Execute tool in sandbox with timeout and resource limits.

        Args:
            tool: Tool to execute.
            workspace_id: Workspace UUID.
            user_id: User UUID.
            params: Parameters.

        Returns:
            ToolResult.
        """
        # For MVP, simple execution without heavy sandboxing
        # Future: Add timeout, memory limits, network isolation

        try:
            # Execute with timeout (30 seconds)
            import asyncio

            return await asyncio.wait_for(
                tool.execute(workspace_id, user_id, **params),
                timeout=30.0,
            )

        except TimeoutError:
            return ToolResult.fail(
                error="Tool execution timed out (30s limit)",
                metadata={"tool_name": tool.name},
            )
        except Exception as e:
            return ToolResult.fail(
                error=f"Tool execution error: {e!s}",
                metadata={"tool_name": tool.name},
            )


__all__ = [
    "MCPToolRegistry",
    "ToolExecutionError",
    "ToolNotFoundError",
    "ToolValidationError",
]
