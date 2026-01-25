"""SQLAlchemy base model with common mixins for Pilot Space.

Provides base classes and mixins for all database models:
- Base: SQLAlchemy declarative base
- TimestampMixin: created_at, updated_at
- SoftDeleteMixin: is_deleted, deleted_at
- WorkspaceScopedMixin: workspace_id for RLS
- BaseModel: Combined base with UUID PK
"""

import re
import uuid
from datetime import UTC, datetime
from typing import Any, ClassVar

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column


class Base(DeclarativeBase):
    """SQLAlchemy declarative base for all models."""

    # Type annotation helpers for relationships
    type_annotation_map: ClassVar[dict[type, Any]] = {
        uuid.UUID: UUID(as_uuid=True),
    }


class TimestampMixin:
    """Mixin for created_at and updated_at timestamps.

    Automatically sets created_at on insert and updated_at on every update.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class SoftDeleteMixin:
    """Mixin for soft delete support.

    Instead of hard deleting records, marks them as deleted.
    Records can be restored within 30 days (per FR-063).
    """

    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        server_default=text("false"),
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    def soft_delete(self) -> None:
        """Mark this record as deleted."""

        self.is_deleted = True
        self.deleted_at = datetime.now(tz=UTC)

    def restore(self) -> None:
        """Restore a soft-deleted record."""
        self.is_deleted = False
        self.deleted_at = None


class WorkspaceScopedMixin:
    """Mixin for workspace-scoped entities supporting RLS.

    Adds workspace_id foreign key with index for efficient queries.
    All workspace-scoped entities must use this mixin.
    """

    @declared_attr
    def workspace_id(cls) -> Mapped[uuid.UUID]:
        """Foreign key to workspaces table with cascade delete."""
        return mapped_column(
            UUID(as_uuid=True),
            ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )


def camel_to_snake(name: str) -> str:
    """Convert CamelCase to snake_case.

    Args:
        name: CamelCase string.

    Returns:
        snake_case string.
    """
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


class BaseModel(Base, TimestampMixin, SoftDeleteMixin):
    """Base model with UUID PK, timestamps, and soft delete.

    All domain models should inherit from this class.
    Automatically generates table name from class name.
    """

    __abstract__ = True

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )

    @declared_attr.directive
    @classmethod
    def __tablename__(cls) -> str:
        """Auto-generate table name from class name (snake_case + pluralized)."""
        # Convert CamelCase to snake_case and add 's' for plural
        snake_name = camel_to_snake(cls.__name__)
        # Handle special pluralization
        if snake_name.endswith("y"):
            return snake_name[:-1] + "ies"
        if snake_name.endswith(("s", "x")):
            return snake_name + "es"
        return snake_name + "s"

    def as_dict(self) -> dict[str, Any]:
        """Convert model instance to dictionary.

        Returns:
            Dictionary with column names as keys.
        """
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    def __repr__(self) -> str:
        """Return string representation of model."""
        return f"<{self.__class__.__name__}(id={self.id})>"


class WorkspaceScopedModel(BaseModel, WorkspaceScopedMixin):
    """Base model for workspace-scoped entities.

    Combines BaseModel with WorkspaceScopedMixin.
    Use this for entities that belong to a specific workspace.
    """

    __abstract__ = True


# Type alias for clarity in type hints
EntityId = uuid.UUID


class SlugMixin:
    """Mixin for entities with URL-friendly slugs."""

    slug: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
    )
