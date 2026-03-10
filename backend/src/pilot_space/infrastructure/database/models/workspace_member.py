"""WorkspaceMember SQLAlchemy model.

Junction table for User-Workspace relationships with role information.
"""

from __future__ import annotations

import uuid
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Enum as SQLEnum,
    ForeignKey,
    Index,
    Numeric,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pilot_space.infrastructure.database.base import BaseModel

if TYPE_CHECKING:
    from pilot_space.infrastructure.database.models.custom_role import CustomRole
    from pilot_space.infrastructure.database.models.user import User
    from pilot_space.infrastructure.database.models.workspace import Workspace


class WorkspaceRole(str, Enum):
    """Roles for workspace membership.

    Hierarchy: owner > admin > member > guest
    """

    OWNER = "OWNER"  # Full control, can delete workspace
    ADMIN = "ADMIN"  # Manage members, settings, integrations
    MEMBER = "MEMBER"  # Create/edit content, standard access
    GUEST = "GUEST"  # Read-only access to specific projects


class WorkspaceMember(BaseModel):
    """Junction model for User-Workspace relationships.

    Tracks which users belong to which workspaces and their roles.

    Attributes:
        user_id: FK to User.
        workspace_id: FK to Workspace.
        role: User's role in this workspace.
        user: Related User object.
        workspace: Related Workspace object.
    """

    __tablename__ = "workspace_members"  # type: ignore[assignment]

    # Foreign keys
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Role
    role: Mapped[WorkspaceRole] = mapped_column(
        SQLEnum(WorkspaceRole, name="workspace_role", create_type=False),
        nullable=False,
        default=WorkspaceRole.MEMBER,
    )

    # T-246: Capacity planning — weekly hours available (from migration 045)
    weekly_available_hours: Mapped[float] = mapped_column(
        Numeric(5, 1),
        nullable=False,
        default=40.0,
        server_default="40",
    )

    # AUTH-05: Custom RBAC — optional custom role assignment
    custom_role_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("custom_roles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # AUTH-07: SCIM provisioning — track active/deactivated members
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )

    # Relationships — use lazy="select" to avoid implicit JOINs;
    # repositories should use joinedload() explicitly when needed.
    user: Mapped[User] = relationship(
        "User",
        back_populates="workspace_memberships",
        lazy="select",
    )
    workspace: Mapped[Workspace] = relationship(
        "Workspace",
        back_populates="members",
        lazy="select",
    )
    custom_role: Mapped[CustomRole | None] = relationship(
        "CustomRole",
        back_populates="members",
        lazy="select",
    )

    # Indexes and constraints
    __table_args__ = (
        Index("ix_workspace_members_user_id", "user_id"),
        Index("ix_workspace_members_role", "role"),
        UniqueConstraint(
            "user_id",
            "workspace_id",
            name="uq_workspace_members_user_workspace",
        ),
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return f"<WorkspaceMember(user_id={self.user_id}, workspace_id={self.workspace_id}, role={self.role})>"

    @property
    def is_owner(self) -> bool:
        """Check if member is workspace owner."""
        return self.role == WorkspaceRole.OWNER

    @property
    def is_admin(self) -> bool:
        """Check if member is admin or higher."""
        return self.role in (WorkspaceRole.OWNER, WorkspaceRole.ADMIN)

    @property
    def can_edit(self) -> bool:
        """Check if member can edit content."""
        return self.role != WorkspaceRole.GUEST
