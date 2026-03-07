"""Pydantic schemas for custom RBAC endpoints — AUTH-05.

Covers custom role CRUD and member role assignment.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CustomRoleCreate(BaseModel):
    """Request body for creating a custom role."""

    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    permissions: list[str] = Field(default_factory=list)


class CustomRoleUpdate(BaseModel):
    """Request body for updating a custom role (partial update)."""

    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = None
    permissions: list[str] | None = None


class CustomRoleResponse(BaseModel):
    """Response schema for a custom role."""

    id: UUID
    workspace_id: UUID
    name: str
    description: str | None
    permissions: list[str]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AssignRoleRequest(BaseModel):
    """Request body for assigning/unassigning a custom role to a member.

    Pass custom_role_id=None to clear the custom role and revert to
    the member's built-in WorkspaceRole permissions.
    """

    custom_role_id: UUID | None


__all__ = [
    "AssignRoleRequest",
    "CustomRoleCreate",
    "CustomRoleResponse",
    "CustomRoleUpdate",
]
