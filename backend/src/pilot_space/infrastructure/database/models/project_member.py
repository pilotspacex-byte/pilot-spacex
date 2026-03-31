"""ProjectMember SQLAlchemy model.

Junction table mapping workspace members to specific projects for RBAC.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    UniqueConstraint,
    func as sa_func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pilot_space.infrastructure.database.base import BaseModel

if TYPE_CHECKING:
    from pilot_space.infrastructure.database.models.project import Project
    from pilot_space.infrastructure.database.models.user import User


class ProjectMember(BaseModel):
    """Junction model for User-Project relationships (project-scoped RBAC).

    Tracks which users are assigned to which projects.
    Admins and Owners implicitly have access to all projects in their workspace
    without needing a row here; regular Members and Guests require an explicit
    row with is_active=True.

    Attributes:
        project_id: FK to Project.
        user_id: FK to User.
        assigned_at: Timestamp when the assignment was made.
        assigned_by: FK to the Admin who made the assignment (nullable).
        is_active: Whether the membership is active (soft-deactivation).
    """

    __tablename__ = "project_members"  # type: ignore[assignment]

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=sa_func.now(),
        nullable=False,
    )
    assigned_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )

    # Relationships
    project: Mapped[Project] = relationship(
        "Project",
        back_populates="members",
        lazy="select",
    )
    user: Mapped[User] = relationship(
        "User",
        foreign_keys=[user_id],
        lazy="select",
    )
    assigner: Mapped[User | None] = relationship(
        "User",
        foreign_keys=[assigned_by],
        lazy="select",
    )

    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "user_id",
            name="uq_project_members_project_user",
        ),
        Index("ix_project_members_project_id", "project_id"),
        Index("ix_project_members_user_id", "user_id"),
        Index("ix_project_members_is_active", "is_active"),
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"<ProjectMember(project_id={self.project_id}, "
            f"user_id={self.user_id}, is_active={self.is_active})>"
        )
