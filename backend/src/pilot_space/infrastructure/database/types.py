"""Custom SQLAlchemy types for cross-database compatibility.

Provides type decorators that adapt PostgreSQL-specific types to work
with SQLite and other databases.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, TypeDecorator
from sqlalchemy.dialects.postgresql import JSONB

if TYPE_CHECKING:
    from sqlalchemy.engine.interfaces import Dialect


class JSONBCompat(TypeDecorator[Any]):
    """JSONB type that falls back to JSON for non-PostgreSQL databases.

    Uses native JSONB type for PostgreSQL (with indexing and operators)
    and standard JSON type for other databases like SQLite.

    This allows models to use JSONB for development/production (PostgreSQL)
    while still working with SQLite for testing.

    Example:
        ```python
        class MyModel(Base):
            data: Mapped[dict[str, Any]] = mapped_column(JSONBCompat, nullable=False)
        ```

    Attributes:
        impl: Base implementation type (JSON).
        cache_ok: Safe for statement caching.
    """

    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect: Dialect):
        """Load the appropriate type for the dialect.

        Args:
            dialect: SQLAlchemy dialect (postgresql, sqlite, etc.).

        Returns:
            JSONB for PostgreSQL, JSON for others.
        """
        if dialect.name == "postgresql":
            return dialect.type_descriptor(JSONB())
        return dialect.type_descriptor(JSON())


__all__ = ["JSONBCompat"]
