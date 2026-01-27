"""Base classes for MCP tools.

Defines the protocol for creating and executing MCP tools.

Reference: T084-T093 (MCP Tool Infrastructure)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any
from uuid import UUID


class ToolParameterType(StrEnum):
    """Tool parameter types."""

    STRING = "string"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    OBJECT = "object"
    ARRAY = "array"


@dataclass(frozen=True, slots=True)
class ToolParameter:
    """Tool parameter definition.

    Attributes:
        name: Parameter name.
        type: Parameter type.
        description: Human-readable description.
        required: Whether parameter is required.
        default: Optional default value.
        enum: Optional allowed values.
    """

    name: str
    type: ToolParameterType
    description: str
    required: bool = True
    default: Any = None
    enum: list[str] | None = None

    def to_schema(self) -> dict[str, Any]:
        """Convert to JSON schema format.

        Returns:
            JSON schema dictionary.
        """
        schema: dict[str, Any] = {
            "type": self.type.value,
            "description": self.description,
        }

        if self.enum:
            schema["enum"] = self.enum

        if self.default is not None:
            schema["default"] = self.default

        return schema


@dataclass
class ToolResult:
    """Tool execution result.

    Attributes:
        success: Whether execution succeeded.
        data: Result data (if success).
        error: Error message (if failure).
        metadata: Additional metadata.
    """

    success: bool
    data: dict[str, Any] | None = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def ok(cls, data: dict[str, Any], metadata: dict[str, Any] | None = None) -> ToolResult:
        """Create successful result.

        Args:
            data: Result data.
            metadata: Optional metadata.

        Returns:
            ToolResult with success=True.
        """
        return cls(
            success=True,
            data=data,
            metadata=metadata or {},
        )

    @classmethod
    def fail(cls, error: str, metadata: dict[str, Any] | None = None) -> ToolResult:
        """Create failure result.

        Args:
            error: Error message.
            metadata: Optional metadata.

        Returns:
            ToolResult with success=False.
        """
        return cls(
            success=False,
            error=error,
            metadata=metadata or {},
        )


class MCPTool(ABC):
    """Base class for MCP tools.

    All tools must inherit from this class and implement the
    execute() method.

    Example:
        class MyTool(MCPTool):
            @property
            def name(self) -> str:
                return "my_tool"

            @property
            def description(self) -> str:
                return "Does something useful"

            @property
            def parameters(self) -> list[ToolParameter]:
                return [
                    ToolParameter(
                        name="input",
                        type=ToolParameterType.STRING,
                        description="Input text",
                    )
                ]

            async def execute(
                self,
                workspace_id: UUID,
                user_id: UUID,
                **params: Any,
            ) -> ToolResult:
                input_text = params.get("input")
                # Do work
                return ToolResult.ok({"output": "result"})
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Tool name (unique identifier).

        Returns:
            Tool name string.
        """

    @property
    @abstractmethod
    def description(self) -> str:
        """Tool description.

        Returns:
            Human-readable description.
        """

    @property
    @abstractmethod
    def parameters(self) -> list[ToolParameter]:
        """Tool parameters.

        Returns:
            List of parameter definitions.
        """

    @property
    def requires_approval(self) -> bool:
        """Whether tool requires human approval.

        Override to return True for destructive actions.

        Returns:
            True if approval required, False otherwise.
        """
        return False

    @abstractmethod
    async def execute(
        self,
        workspace_id: UUID,
        user_id: UUID,
        **params: Any,
    ) -> ToolResult:
        """Execute the tool.

        Args:
            workspace_id: Workspace UUID for RLS.
            user_id: User UUID for attribution.
            **params: Tool parameters.

        Returns:
            ToolResult with success/failure.
        """

    def to_schema(self) -> dict[str, Any]:
        """Convert tool to JSON schema.

        Returns:
            Tool schema dictionary for discovery.
        """
        # Build parameters schema
        properties: dict[str, dict[str, Any]] = {}
        required: list[str] = []

        for param in self.parameters:
            properties[param.name] = param.to_schema()
            if param.required:
                required.append(param.name)

        return {
            "name": self.name,
            "description": self.description,
            "requires_approval": self.requires_approval,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        }


__all__ = [
    "MCPTool",
    "ToolParameter",
    "ToolParameterType",
    "ToolResult",
]
