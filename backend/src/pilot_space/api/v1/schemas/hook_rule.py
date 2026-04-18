"""Pydantic request/response schemas for workspace hook rule CRUD.

Phase 83 -- uses BaseSchema for camelCase serialization contract.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field

from pilot_space.api.v1.schemas.base import BaseSchema


class CreateHookRuleRequest(BaseSchema):
    """Request body for creating a workspace hook rule.

    Attributes:
        name: Human-readable rule name (unique per workspace).
        tool_pattern: Glob, regex, or exact match pattern for tool names.
        action: Action to take when the rule matches.
        event_type: Hook event type (default: PreToolUse).
        priority: Evaluation order -- lower number = higher priority.
        description: Optional description of the rule's purpose.
    """

    name: str = Field(
        ...,
        max_length=128,
        description="Human-readable rule name",
    )
    tool_pattern: str = Field(
        ...,
        max_length=256,
        description="Glob, regex, or exact match pattern for tool names",
    )
    action: Literal["allow", "deny", "require_approval"] = Field(
        ...,
        description="Action: allow, deny, or require_approval",
    )
    event_type: Literal["PreToolUse", "PostToolUse", "Stop"] = Field(
        default="PreToolUse",
        description="Hook event type",
    )
    priority: int = Field(
        default=100,
        ge=0,
        le=9999,
        description="Evaluation order (lower = higher priority)",
    )
    description: str | None = Field(
        default=None,
        max_length=512,
        description="Optional description of the rule's purpose",
    )


class UpdateHookRuleRequest(BaseSchema):
    """Request body for updating a workspace hook rule (partial update).

    All fields are optional -- only provided fields are updated.

    Attributes:
        name: New human-readable rule name.
        tool_pattern: New pattern for tool name matching.
        action: New action to take when the rule matches.
        event_type: New hook event type.
        priority: New evaluation priority.
        description: New description.
        is_enabled: Enable or disable the rule.
    """

    name: str | None = Field(
        default=None,
        max_length=128,
        description="Human-readable rule name",
    )
    tool_pattern: str | None = Field(
        default=None,
        max_length=256,
        description="Glob, regex, or exact match pattern for tool names",
    )
    action: Literal["allow", "deny", "require_approval"] | None = Field(
        default=None,
        description="Action: allow, deny, or require_approval",
    )
    event_type: Literal["PreToolUse", "PostToolUse", "Stop"] | None = Field(
        default=None,
        description="Hook event type",
    )
    priority: int | None = Field(
        default=None,
        ge=0,
        le=9999,
        description="Evaluation order (lower = higher priority)",
    )
    description: str | None = Field(
        default=None,
        max_length=512,
        description="Optional description of the rule's purpose",
    )
    is_enabled: bool | None = Field(
        default=None,
        description="Enable or disable the rule",
    )


class HookRuleResponse(BaseSchema):
    """Response schema for a single workspace hook rule.

    Attributes:
        id: Unique identifier of the rule.
        name: Human-readable rule name.
        tool_pattern: Pattern for tool name matching.
        action: Action taken when the rule matches.
        event_type: Hook event type.
        priority: Evaluation order.
        is_enabled: Whether the rule is active.
        description: Optional description.
        created_by: UUID of the user who created the rule.
        updated_by: UUID of the user who last modified the rule.
        created_at: Timestamp when the rule was created.
        updated_at: Timestamp when the rule was last modified.
    """

    id: str = Field(description="Unique identifier")
    name: str = Field(description="Human-readable rule name")
    tool_pattern: str = Field(description="Pattern for tool name matching")
    action: str = Field(description="Action: allow, deny, or require_approval")
    event_type: str = Field(description="Hook event type")
    priority: int = Field(description="Evaluation order")
    is_enabled: bool = Field(description="Whether the rule is active")
    description: str | None = Field(description="Optional description")
    created_by: str = Field(description="User who created the rule")
    updated_by: str = Field(description="User who last modified the rule")
    created_at: datetime = Field(description="Creation timestamp")
    updated_at: datetime = Field(description="Last modification timestamp")


class HookRuleListResponse(BaseSchema):
    """Response schema for listing workspace hook rules.

    Attributes:
        rules: List of hook rules.
        count: Total number of rules in the response.
    """

    rules: list[HookRuleResponse] = Field(
        description="List of hook rules",
    )
    count: int = Field(description="Total number of rules")


__all__ = [
    "CreateHookRuleRequest",
    "HookRuleListResponse",
    "HookRuleResponse",
    "UpdateHookRuleRequest",
]
