"""Generic base repository with CRUD, soft delete, and cursor pagination.

Provides consistent data access patterns for all entities.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, TypeVar
from uuid import UUID

from sqlalchemy import Select, and_, asc, desc, func, or_, select
from sqlalchemy.orm import lazyload

from pilot_space.infrastructure.database.base import BaseModel

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar("T", bound=BaseModel)


@dataclass
class CursorPage[T: BaseModel]:
    """Cursor-based pagination result.

    Attributes:
        items: The items in the current page.
        total: Total count of items matching the query.
        next_cursor: Cursor for fetching the next page, None if no more pages.
        prev_cursor: Cursor for fetching the previous page, None if at start.
        has_next: Whether there are more items after this page.
        has_prev: Whether there are items before this page.
    """

    items: Sequence[T]
    total: int
    next_cursor: str | None = None
    prev_cursor: str | None = None
    has_next: bool = False
    has_prev: bool = False
    page_size: int = 20
    filters: dict[str, Any] = field(default_factory=dict)  # type: ignore[var-annotated]


class BaseRepository[T: BaseModel]:
    """Generic repository with CRUD, soft delete, restore, and cursor pagination.

    Provides consistent data access patterns for all entities.
    Uses soft delete by default - entities are marked as deleted rather than removed.

    Type Parameters:
        T: The SQLAlchemy model type.

    Attributes:
        session: The async database session.
        model_class: The SQLAlchemy model class.
    """

    def __init__(self, session: AsyncSession, model_class: type[T]) -> None:
        """Initialize repository with session and model class.

        Args:
            session: The async database session.
            model_class: The SQLAlchemy model class.
        """
        self.session = session
        self.model_class = model_class

    async def get_by_id(
        self,
        entity_id: UUID,
        *,
        include_deleted: bool = False,
    ) -> T | None:
        """Get entity by ID.

        Args:
            entity_id: The entity UUID.
            include_deleted: Whether to include soft-deleted entities.

        Returns:
            The entity if found, None otherwise.
        """
        query = select(self.model_class).where(self.model_class.id == entity_id)
        if not include_deleted:
            query = query.where(self.model_class.is_deleted == False)  # noqa: E712
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_id_scalar(
        self,
        entity_id: UUID,
        *,
        include_deleted: bool = False,
    ) -> T | None:
        """Get entity by ID loading only scalar columns (no relationships).

        Overrides model-level eager loading (selectin/joined) to prevent
        unnecessary relationship queries. Use for validation checks where
        only scalar fields (id, workspace_id, etc.) are needed.

        Args:
            entity_id: The entity UUID.
            include_deleted: Whether to include soft-deleted entities.

        Returns:
            The entity with scalar columns only, or None.
        """
        query = (
            select(self.model_class).options(lazyload("*")).where(self.model_class.id == entity_id)
        )
        if not include_deleted:
            query = query.where(self.model_class.is_deleted == False)  # noqa: E712
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_all(
        self,
        *,
        include_deleted: bool = False,
        limit: int | None = None,
        offset: int | None = None,
    ) -> Sequence[T]:
        """Get all entities with optional pagination.

        Args:
            include_deleted: Whether to include soft-deleted entities.
            limit: Maximum number of entities to return.
            offset: Number of entities to skip.

        Returns:
            List of entities.
        """
        query = select(self.model_class)
        if not include_deleted:
            query = query.where(self.model_class.is_deleted == False)  # noqa: E712
        query = query.order_by(self.model_class.created_at.desc())
        if limit:
            query = query.limit(limit)
        if offset:
            query = query.offset(offset)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def create(self, entity: T) -> T:
        """Create a new entity.

        Args:
            entity: The entity to create.

        Returns:
            The created entity with generated ID.
        """
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def update(self, entity: T) -> T:
        """Update an existing entity.

        Args:
            entity: The entity to update.

        Returns:
            The updated entity.
        """
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def delete(self, entity: T, *, hard: bool = False) -> None:
        """Delete an entity (soft delete by default).

        Args:
            entity: The entity to delete.
            hard: If True, permanently delete. If False, soft delete.
        """
        if hard:
            await self.session.delete(entity)
        else:
            entity.is_deleted = True
            entity.deleted_at = datetime.now(tz=UTC)
        await self.session.flush()

    async def restore(self, entity: T) -> T:
        """Restore a soft-deleted entity.

        Args:
            entity: The entity to restore.

        Returns:
            The restored entity.
        """
        entity.is_deleted = False
        entity.deleted_at = None
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def count(
        self,
        *,
        include_deleted: bool = False,
        filters: dict[str, Any] | None = None,
    ) -> int:
        """Count entities matching criteria.

        Args:
            include_deleted: Whether to include soft-deleted entities.
            filters: Additional filter criteria as column=value pairs.

        Returns:
            Count of matching entities.
        """
        query = select(func.count()).select_from(self.model_class)
        if not include_deleted:
            query = query.where(self.model_class.is_deleted == False)  # noqa: E712
        if filters:
            query = self._apply_filters(query, filters)  # type: ignore[arg-type]
        result = await self.session.execute(query)
        return result.scalar() or 0

    async def exists(
        self,
        entity_id: UUID,
        *,
        include_deleted: bool = False,
    ) -> bool:
        """Check if entity exists.

        Args:
            entity_id: The entity UUID.
            include_deleted: Whether to include soft-deleted entities.

        Returns:
            True if entity exists, False otherwise.
        """
        query = (
            select(func.count())
            .select_from(self.model_class)
            .where(self.model_class.id == entity_id)
        )
        if not include_deleted:
            query = query.where(self.model_class.is_deleted == False)  # noqa: E712
        result = await self.session.execute(query)
        return (result.scalar() or 0) > 0

    async def paginate(
        self,
        *,
        cursor: str | None = None,
        page_size: int = 20,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        include_deleted: bool = False,
        filters: dict[str, Any] | None = None,
    ) -> CursorPage[T]:
        """Get paginated results using cursor-based pagination.

        Uses cursor-based pagination for efficient large dataset handling.
        Cursor is the last item's sort field value encoded as string.

        Args:
            cursor: Cursor from previous page (sort field value).
            page_size: Number of items per page (max 100).
            sort_by: Column name to sort by.
            sort_order: Sort direction ('asc' or 'desc').
            include_deleted: Whether to include soft-deleted entities.
            filters: Additional filter criteria.

        Returns:
            CursorPage with items, pagination info, and metadata.
        """
        page_size = min(page_size, 100)  # Cap at 100

        # Build base query
        query = select(self.model_class)
        if not include_deleted:
            query = query.where(self.model_class.is_deleted == False)  # noqa: E712

        if filters:
            query = self._apply_filters(query, filters)

        # Get total count
        count_query = select(func.count()).select_from(self.model_class)
        if not include_deleted:
            count_query = count_query.where(
                self.model_class.is_deleted == False  # noqa: E712
            )
        if filters:
            count_query = self._apply_filters(count_query, filters)  # type: ignore[arg-type]
        count_result = await self.session.execute(count_query)
        total = count_result.scalar() or 0

        # Get sort column
        sort_column = getattr(self.model_class, sort_by, self.model_class.created_at)
        order_func = desc if sort_order == "desc" else asc

        # Apply cursor filter
        if cursor:
            cursor_value = self._decode_cursor(cursor, sort_by)
            if cursor_value:
                if sort_order == "desc":
                    query = query.where(sort_column < cursor_value)
                else:
                    query = query.where(sort_column > cursor_value)

        # Apply ordering and limit (fetch one extra to check for next page)
        query = query.order_by(order_func(sort_column)).limit(page_size + 1)

        # Execute query
        result = await self.session.execute(query)
        items = list(result.scalars().all())

        # Determine if there's a next page
        has_next = len(items) > page_size
        if has_next:
            items = items[:page_size]  # Remove the extra item

        # Build next cursor from last item
        next_cursor = None
        if has_next and items:
            last_item = items[-1]
            next_cursor = self._encode_cursor(getattr(last_item, sort_by))

        # Build prev cursor from first item (if cursor was provided)
        prev_cursor = None
        has_prev = cursor is not None
        if has_prev and items:
            first_item = items[0]
            prev_cursor = self._encode_cursor(getattr(first_item, sort_by))

        return CursorPage(
            items=items,
            total=total,
            next_cursor=next_cursor,
            prev_cursor=prev_cursor,
            has_next=has_next,
            has_prev=has_prev,
            page_size=page_size,
            filters=filters or {},
        )

    def _apply_filters(
        self,
        query: Select[tuple[T]],
        filters: dict[str, Any],
    ) -> Select[tuple[T]]:
        """Apply filter criteria to query.

        Args:
            query: The SQLAlchemy query.
            filters: Filter criteria as column=value pairs.

        Returns:
            Query with filters applied.
        """
        conditions: list[Any] = []
        for key, value in filters.items():
            if hasattr(self.model_class, key):
                column = getattr(self.model_class, key)
                if isinstance(value, list):
                    conditions.append(column.in_(value))
                elif value is None:
                    conditions.append(column.is_(None))
                else:
                    conditions.append(column == value)
        if conditions:
            query = query.where(and_(*conditions))  # type: ignore[arg-type]
        return query

    def _encode_cursor(self, value: Any) -> str:
        """Encode a value as cursor string.

        Args:
            value: The value to encode.

        Returns:
            Encoded cursor string.
        """
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, UUID):
            return str(value)
        return str(value)

    def _decode_cursor(self, cursor: str, sort_by: str) -> Any:
        """Decode cursor string to value.

        Args:
            cursor: The cursor string.
            sort_by: The sort column name.

        Returns:
            Decoded value appropriate for the sort column.
        """
        sort_column = getattr(self.model_class, sort_by, None)
        if sort_column is None:
            return None

        # Get column type info
        column_type = sort_column.type
        type_name = type(column_type).__name__

        if type_name in ("DateTime", "TIMESTAMP"):
            return datetime.fromisoformat(cursor)
        if type_name in ("UUID",):
            return UUID(cursor)
        if type_name in ("Integer", "BigInteger"):
            return int(cursor)
        return cursor

    async def find_by(
        self,
        *,
        include_deleted: bool = False,
        **kwargs: Any,
    ) -> Sequence[T]:
        """Find entities by attribute values.

        Args:
            include_deleted: Whether to include soft-deleted entities.
            **kwargs: Column=value pairs to filter by.

        Returns:
            List of matching entities.
        """
        query = select(self.model_class)
        if not include_deleted:
            query = query.where(self.model_class.is_deleted == False)  # noqa: E712
        query = self._apply_filters(query, kwargs)
        query = query.order_by(self.model_class.created_at.desc())
        result = await self.session.execute(query)
        return result.scalars().all()

    async def find_one_by(
        self,
        *,
        include_deleted: bool = False,
        **kwargs: Any,
    ) -> T | None:
        """Find single entity by attribute values.

        Args:
            include_deleted: Whether to include soft-deleted entities.
            **kwargs: Column=value pairs to filter by.

        Returns:
            The entity if found, None otherwise.
        """
        query = select(self.model_class)
        if not include_deleted:
            query = query.where(self.model_class.is_deleted == False)  # noqa: E712
        query = self._apply_filters(query, kwargs)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def search(
        self,
        search_term: str,
        search_columns: list[str],
        *,
        include_deleted: bool = False,
        limit: int = 20,
    ) -> Sequence[T]:
        """Search entities by text in specified columns.

        Args:
            search_term: Text to search for.
            search_columns: Column names to search in.
            include_deleted: Whether to include soft-deleted entities.
            limit: Maximum results to return.

        Returns:
            List of matching entities.
        """
        query = select(self.model_class)
        if not include_deleted:
            query = query.where(self.model_class.is_deleted == False)  # noqa: E712

        # Build OR conditions for text search
        search_conditions: list[Any] = []
        search_pattern = f"%{search_term}%"
        for col_name in search_columns:
            if hasattr(self.model_class, col_name):
                column = getattr(self.model_class, col_name)
                search_conditions.append(column.ilike(search_pattern))

        if search_conditions:
            query = query.where(or_(*search_conditions))  # type: ignore[arg-type]

        query = query.order_by(self.model_class.created_at.desc()).limit(limit)
        result = await self.session.execute(query)
        return result.scalars().all()
