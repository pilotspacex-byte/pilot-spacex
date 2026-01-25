"""Workspace schemas for API requests/responses.

Pydantic models for workspace CRUD and member management.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field

from pilot_space.api.v1.schemas.base import BaseSchema, EntitySchema


class WorkspaceCreate(BaseSchema):
    """Create workspace request.

    Attributes:
        name: Workspace display name.
        slug: URL-friendly unique identifier.
        description: Optional workspace description.
    """

    name: str = Field(
        min_length=1,
        max_length=255,
        description="Workspace display name",
    )
    slug: str = Field(
        min_length=2,
        max_length=100,
        pattern=r"^[a-z0-9][a-z0-9-]*[a-z0-9]$|^[a-z0-9]$",
        description="URL-friendly identifier (lowercase letters, numbers, hyphens)",
    )
    description: str | None = Field(
        default=None,
        max_length=2000,
        description="Workspace description",
    )


class WorkspaceUpdate(BaseSchema):
    """Update workspace request.

    Attributes:
        name: New workspace name.
        description: New workspace description.
        settings: Workspace-level settings.
    """

    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
        description="New workspace name",
    )
    description: str | None = Field(
        default=None,
        max_length=2000,
        description="New description",
    )
    settings: dict[str, Any] | None = Field(
        default=None,
        description="Workspace settings (merged with existing)",
    )


class WorkspaceResponse(EntitySchema):
    """Workspace response.

    Attributes:
        name: Workspace display name.
        slug: URL-friendly identifier.
        description: Workspace description.
        owner_id: Owner user ID.
        member_count: Number of members.
        project_count: Number of projects.
    """

    name: str = Field(description="Workspace display name")
    slug: str = Field(description="URL-friendly identifier")
    description: str | None = Field(default=None, description="Workspace description")
    owner_id: UUID | None = Field(default=None, description="Owner user ID")
    member_count: int = Field(default=0, description="Number of members")
    project_count: int = Field(default=0, description="Number of projects")


class WorkspaceDetailResponse(WorkspaceResponse):
    """Detailed workspace response with settings.

    Attributes:
        settings: Workspace-level settings.
        current_user_role: Current user's role in workspace.
    """

    settings: dict[str, Any] | None = Field(default=None, description="Workspace settings")
    current_user_role: str | None = Field(default=None, description="Current user's role")


# Member management schemas
class WorkspaceMemberCreate(BaseSchema):
    """Add workspace member request.

    Attributes:
        email: User email to invite.
        role: Role to assign (admin, member, viewer).
    """

    email: str = Field(description="User email to invite")
    role: str = Field(
        default="member",
        pattern="^(admin|member|viewer)$",
        description="Role to assign",
    )


class WorkspaceMemberUpdate(BaseSchema):
    """Update workspace member request.

    Attributes:
        role: New role for member.
    """

    role: str = Field(
        pattern="^(admin|member|viewer)$",
        description="New role for member",
    )


class WorkspaceMemberResponse(BaseSchema):
    """Workspace member response.

    Attributes:
        user_id: Member user ID.
        email: Member email.
        full_name: Member display name.
        avatar_url: Member profile image.
        role: Member role.
        joined_at: When member joined.
    """

    user_id: UUID = Field(description="Member user ID")
    email: str = Field(description="Member email")
    full_name: str | None = Field(default=None, description="Member display name")
    avatar_url: str | None = Field(default=None, description="Profile image URL")
    role: str = Field(description="Member role")
    joined_at: datetime = Field(description="When member joined")


__all__ = [
    "WorkspaceCreate",
    "WorkspaceDetailResponse",
    "WorkspaceMemberCreate",
    "WorkspaceMemberResponse",
    "WorkspaceMemberUpdate",
    "WorkspaceResponse",
    "WorkspaceUpdate",
]
