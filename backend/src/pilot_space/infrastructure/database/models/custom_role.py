"""CustomRole SQLAlchemy model.

Workspace-defined roles with granular permissions for RBAC (AUTH-05).
Custom roles extend the built-in WorkspaceRole hierarchy with fine-grained
permission sets stored as a JSONB list of permission strings.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pilot_space.infrastructure.database.base import WorkspaceScopedModel
from pilot_space.infrastructure.database.types import JSONBCompat

if TYPE_CHECKING:
    from pilot_space.infrastructure.database.models.workspace import Workspace
    from pilot_space.infrastructure.database.models.workspace_member import WorkspaceMember


class CustomRole(WorkspaceScopedModel):
    """Workspace-defined role with granular permission set.

    Custom roles complement built-in roles (OWNER/ADMIN/MEMBER/GUEST) by
    allowing workspace admins to define fine-grained permissions per role.
    A workspace member can be assigned at most one custom role in addition
    to their built-in role.

    Attributes:
        workspace_id: FK to owning workspace (from WorkspaceScopedModel).
        name: Human-readable role name, unique per workspace.
        description: Optional description of the role's purpose.
        permissions: List of permission strings (e.g. ["issues:write", "notes:read"]).
        workspace: Related Workspace object.
        members: WorkspaceMembers assigned this role.
    """

    __tablename__ = "custom_roles"  # type: ignore[assignment]
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "name",
            name="uq_custom_roles_workspace_name",
        ),
        Index("ix_custom_roles_workspace_id", "workspace_id"),
    )

    # Role identity
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="Role name, unique per workspace",
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Optional description of the role's purpose",
    )

    # Permission set — list of permission strings
    permissions: Mapped[list[str] | None] = mapped_column(
        JSONBCompat,
        nullable=True,
        default=list,
        doc="List of permission strings granted by this role",
    )

    # Relationships
    workspace: Mapped[Workspace] = relationship(
        "Workspace",
        back_populates="custom_roles",
        lazy="select",
    )
    members: Mapped[list[WorkspaceMember]] = relationship(
        "WorkspaceMember",
        back_populates="custom_role",
        lazy="select",
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return f"<CustomRole(workspace_id={self.workspace_id}, name={self.name!r})>"
