"""Issue repository with workspace-scoped queries.

T122: Create IssueRepository with advanced filtering, sorting, and eager loading.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from sqlalchemy import Select, and_, asc, desc, func, or_, select, text
from sqlalchemy.orm import joinedload, lazyload, selectinload

from pilot_space.infrastructure.database.models import Issue, IssuePriority, StateGroup
from pilot_space.infrastructure.database.repositories.base import BaseRepository, CursorPage

if TYPE_CHECKING:
    from collections.abc import Sequence
    from datetime import date
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession


@dataclass
class IssueFilters:
    """Filter parameters for issue queries.

    All filters are optional and combined with AND logic.
    """

    project_id: UUID | None = None
    state_ids: list[UUID] | None = None
    state_groups: list[StateGroup] | None = None
    assignee_ids: list[UUID] | None = None
    reporter_ids: list[UUID] | None = None
    label_ids: list[UUID] | None = None
    cycle_id: UUID | None = None
    module_id: UUID | None = None
    parent_id: UUID | None = None  # None means no filter, use explicit value for top-level
    priorities: list[IssuePriority] | None = None
    start_date_from: date | None = None
    start_date_to: date | None = None
    target_date_from: date | None = None
    target_date_to: date | None = None
    search_term: str | None = None
    has_ai_enhancements: bool | None = None


class IssueRepository(BaseRepository[Issue]):
    """Repository for Issue entities with workspace-scoped queries.

    Provides:
    - Workspace-scoped CRUD operations
    - Advanced filtering by multiple criteria
    - Eager loading to avoid N+1 queries
    - Cursor-based pagination
    - Full-text search
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository.

        Args:
            session: Async database session.
        """
        super().__init__(session, Issue)

    async def get_by_id_with_relations(
        self,
        issue_id: UUID,
        *,
        include_deleted: bool = False,
    ) -> Issue | None:
        """Get issue by ID with all relationships eagerly loaded.

        Args:
            issue_id: Issue UUID.
            include_deleted: Whether to include soft-deleted issues.

        Returns:
            Issue with relations or None.
        """
        query = (
            select(Issue)
            .options(
                joinedload(Issue.project),
                joinedload(Issue.state),
                joinedload(Issue.assignee),
                joinedload(Issue.reporter),
                joinedload(Issue.module),
                selectinload(Issue.labels),
                selectinload(Issue.sub_issues),
                selectinload(Issue.note_links),
            )
            .where(Issue.id == issue_id)
        )
        if not include_deleted:
            query = query.where(Issue.is_deleted == False)  # noqa: E712
        result = await self.session.execute(query)
        return result.unique().scalar_one_or_none()

    async def get_by_id_for_response(
        self,
        issue_id: UUID,
        *,
        include_deleted: bool = False,
    ) -> Issue | None:
        """Get issue with only the relations needed for IssueResponse.

        Overrides the model's default eager loading (6 selectin + 4 joined)
        to load only what IssueResponse.from_issue() actually uses:
        project, state, assignee, reporter, labels, sub_issues.

        Skips: cycle, module, parent, note_links, ai_context, activities.

        Args:
            issue_id: Issue UUID.
            include_deleted: Whether to include soft-deleted issues.

        Returns:
            Issue with response relations or None.
        """
        query = (
            select(Issue)
            .options(
                # Override all default eager loading to lazy
                lazyload("*"),
                # Then explicitly load only what IssueResponse needs
                joinedload(Issue.project),
                joinedload(Issue.state),
                joinedload(Issue.assignee),
                joinedload(Issue.reporter),
                selectinload(Issue.labels),
                # Load sub_issues but prevent cascading eager loads on children
                selectinload(Issue.sub_issues).lazyload("*"),
            )
            .where(Issue.id == issue_id)
        )
        if not include_deleted:
            query = query.where(Issue.is_deleted == False)  # noqa: E712
        result = await self.session.execute(query)
        return result.unique().scalar_one_or_none()

    async def get_by_identifier(
        self,
        workspace_id: UUID,
        project_identifier: str,
        sequence_id: int,
    ) -> Issue | None:
        """Get issue by human-readable identifier (e.g., PILOT-123).

        Args:
            workspace_id: Workspace UUID.
            project_identifier: Project identifier code.
            sequence_id: Issue sequence number within project.

        Returns:
            Issue if found, None otherwise.
        """
        query = (
            select(Issue)
            .options(joinedload(Issue.project))
            .join(Issue.project)
            .where(
                and_(
                    Issue.workspace_id == workspace_id,
                    Issue.project.has(identifier=project_identifier),
                    Issue.sequence_id == sequence_id,
                    Issue.is_deleted == False,  # noqa: E712
                )
            )
        )
        result = await self.session.execute(query)
        return result.unique().scalar_one_or_none()

    async def find_by_identifier(
        self,
        workspace_id: UUID,
        project_identifier: str,
        sequence_id: int,
    ) -> Issue | None:
        """Alias for get_by_identifier for sync service compatibility.

        Args:
            workspace_id: Workspace UUID.
            project_identifier: Project identifier code.
            sequence_id: Issue sequence number within project.

        Returns:
            Issue if found, None otherwise.
        """
        return await self.get_by_identifier(
            workspace_id=workspace_id,
            project_identifier=project_identifier,
            sequence_id=sequence_id,
        )

    async def get_workspace_issues(
        self,
        workspace_id: UUID,
        *,
        filters: IssueFilters | None = None,
        cursor: str | None = None,
        page_size: int = 20,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        include_deleted: bool = False,
    ) -> CursorPage[Issue]:
        """Get paginated issues for a workspace with filtering.

        Args:
            workspace_id: Workspace UUID.
            filters: Optional filter criteria.
            cursor: Pagination cursor.
            page_size: Number of items per page.
            sort_by: Column to sort by.
            sort_order: Sort direction ('asc' or 'desc').
            include_deleted: Whether to include soft-deleted.

        Returns:
            CursorPage with filtered issues.
        """
        page_size = min(page_size, 100)

        # Build base query with eager loading
        query = (
            select(Issue)
            .options(
                joinedload(Issue.project),
                joinedload(Issue.state),
                joinedload(Issue.assignee),
                selectinload(Issue.labels),
            )
            .where(Issue.workspace_id == workspace_id)
        )

        if not include_deleted:
            query = query.where(Issue.is_deleted == False)  # noqa: E712

        # Apply filters
        if filters:
            query = self._apply_issue_filters(query, filters)

        # Count query (without pagination/ordering)
        count_query = (
            select(func.count()).select_from(Issue).where(Issue.workspace_id == workspace_id)
        )
        if not include_deleted:
            count_query = count_query.where(Issue.is_deleted == False)  # noqa: E712
        if filters:
            count_query = self._apply_issue_filters(count_query, filters)  # type: ignore[arg-type]
        count_result = await self.session.execute(count_query)
        total = count_result.scalar() or 0

        # Get sort column
        sort_column = getattr(Issue, sort_by, Issue.created_at)
        order_func = desc if sort_order == "desc" else asc

        # Apply cursor
        if cursor:
            cursor_value = self._decode_cursor(cursor, sort_by)
            if cursor_value:
                if sort_order == "desc":
                    query = query.where(sort_column < cursor_value)
                else:
                    query = query.where(sort_column > cursor_value)

        # Apply ordering and limit
        query = query.order_by(order_func(sort_column)).limit(page_size + 1)

        # Execute
        result = await self.session.execute(query)
        items = list(result.unique().scalars().all())

        # Build pagination info
        has_next = len(items) > page_size
        if has_next:
            items = items[:page_size]

        next_cursor = None
        if has_next and items:
            next_cursor = self._encode_cursor(getattr(items[-1], sort_by))

        prev_cursor = None
        has_prev = cursor is not None
        if has_prev and items:
            prev_cursor = self._encode_cursor(getattr(items[0], sort_by))

        return CursorPage(
            items=items,
            total=total,
            next_cursor=next_cursor,
            prev_cursor=prev_cursor,
            has_next=has_next,
            has_prev=has_prev,
            page_size=page_size,
        )

    async def get_project_issues(
        self,
        project_id: UUID,
        *,
        filters: IssueFilters | None = None,
        cursor: str | None = None,
        page_size: int = 20,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> CursorPage[Issue]:
        """Get paginated issues for a project.

        Convenience method that sets project filter and delegates to workspace query.

        Args:
            project_id: Project UUID.
            filters: Additional filter criteria.
            cursor: Pagination cursor.
            page_size: Items per page.
            sort_by: Sort column.
            sort_order: Sort direction.

        Returns:
            CursorPage with project issues.
        """
        if filters is None:
            filters = IssueFilters()
        filters.project_id = project_id

        # Get workspace_id from an issue or project lookup
        query = select(Issue.workspace_id).where(Issue.project_id == project_id).limit(1)
        result = await self.session.execute(query)
        workspace_id = result.scalar_one_or_none()

        if not workspace_id:
            # Try getting workspace from project directly
            from pilot_space.infrastructure.database.models import Project

            proj_query = select(Project.workspace_id).where(Project.id == project_id)
            proj_result = await self.session.execute(proj_query)
            workspace_id = proj_result.scalar_one_or_none()

        if not workspace_id:
            return CursorPage(items=[], total=0, page_size=page_size)

        return await self.get_workspace_issues(
            workspace_id,
            filters=filters,
            cursor=cursor,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order,
        )

    async def get_next_sequence_id(self, project_id: UUID) -> int:
        """Get the next sequence ID for a project.

        Thread-safe using database function.

        Args:
            project_id: Project UUID.

        Returns:
            Next available sequence ID.
        """
        result = await self.session.execute(
            text("SELECT get_next_issue_sequence(:project_id)"),
            {"project_id": project_id},
        )
        return result.scalar() or 1

    async def get_assignee_issues(
        self,
        assignee_id: UUID,
        workspace_id: UUID,
        *,
        include_completed: bool = False,
    ) -> Sequence[Issue]:
        """Get all issues assigned to a user.

        Args:
            assignee_id: User UUID.
            workspace_id: Workspace UUID.
            include_completed: Whether to include completed issues.

        Returns:
            List of assigned issues.
        """
        query = (
            select(Issue)
            .options(
                joinedload(Issue.project),
                joinedload(Issue.state),
            )
            .where(
                and_(
                    Issue.workspace_id == workspace_id,
                    Issue.assignee_id == assignee_id,
                    Issue.is_deleted == False,  # noqa: E712
                )
            )
        )

        if not include_completed:
            from pilot_space.infrastructure.database.models import State

            query = query.join(Issue.state).where(
                State.group.notin_([StateGroup.COMPLETED, StateGroup.CANCELLED])
            )

        query = query.order_by(Issue.created_at.desc())
        result = await self.session.execute(query)
        return result.unique().scalars().all()

    async def search_issues(
        self,
        workspace_id: UUID,
        search_term: str,
        *,
        limit: int = 20,
        project_id: UUID | None = None,
    ) -> Sequence[Issue]:
        """Full-text search for issues.

        Searches in issue name using PostgreSQL full-text search.

        Args:
            workspace_id: Workspace UUID.
            search_term: Search query.
            limit: Max results.
            project_id: Optional project filter.

        Returns:
            Matching issues.
        """
        # Use PostgreSQL full-text search
        # selectinload avoids cartesian product joins when multiple collections are loaded
        query = (
            select(Issue)
            .options(
                selectinload(Issue.project),
                selectinload(Issue.state),
            )
            .where(
                and_(
                    Issue.workspace_id == workspace_id,
                    Issue.is_deleted == False,  # noqa: E712
                    func.to_tsvector("english", Issue.name).match(search_term),
                )
            )
        )

        if project_id:
            query = query.where(Issue.project_id == project_id)

        query = query.limit(limit)
        result = await self.session.execute(query)
        return result.unique().scalars().all()

    async def get_sub_issues(self, parent_id: UUID) -> Sequence[Issue]:
        """Get all sub-issues for a parent issue.

        Args:
            parent_id: Parent issue UUID.

        Returns:
            List of sub-issues.
        """
        query = (
            select(Issue)
            .options(
                joinedload(Issue.state),
                joinedload(Issue.assignee),
            )
            .where(
                and_(
                    Issue.parent_id == parent_id,
                    Issue.is_deleted == False,  # noqa: E712
                )
            )
            .order_by(Issue.sort_order, Issue.created_at)
        )
        result = await self.session.execute(query)
        return result.unique().scalars().all()

    async def get_cycle_issues(
        self,
        cycle_id: UUID,
        *,
        include_completed: bool = True,
    ) -> Sequence[Issue]:
        """Get all issues in a cycle.

        Args:
            cycle_id: Cycle UUID.
            include_completed: Whether to include completed issues.

        Returns:
            List of cycle issues.
        """
        query = (
            select(Issue)
            .options(
                joinedload(Issue.state),
                joinedload(Issue.assignee),
                selectinload(Issue.labels),
            )
            .where(
                and_(
                    Issue.cycle_id == cycle_id,
                    Issue.is_deleted == False,  # noqa: E712
                )
            )
        )

        if not include_completed:
            from pilot_space.infrastructure.database.models import State

            query = query.join(Issue.state).where(
                State.group.notin_([StateGroup.COMPLETED, StateGroup.CANCELLED])
            )

        query = query.order_by(Issue.sort_order, Issue.created_at)
        result = await self.session.execute(query)
        return result.unique().scalars().all()

    async def bulk_update_labels(
        self,
        issue_id: UUID,
        label_ids: list[UUID],
    ) -> None:
        """Replace all labels for an issue using bulk SQL operations.

        Uses direct DELETE + INSERT on the junction table instead of
        loading the full issue with relations. Reduces from ~14 queries
        to 2 queries regardless of label count.

        Args:
            issue_id: Issue UUID.
            label_ids: New label UUIDs.
        """
        from sqlalchemy import delete, insert

        from pilot_space.infrastructure.database.models.issue_label import issue_labels

        # Bulk delete all existing labels for this issue
        await self.session.execute(delete(issue_labels).where(issue_labels.c.issue_id == issue_id))

        # Bulk insert new labels
        if label_ids:
            await self.session.execute(
                insert(issue_labels),
                [{"issue_id": issue_id, "label_id": lid} for lid in label_ids],
            )

        await self.session.flush()

    def _apply_issue_filters(
        self,
        query: Select[tuple[Issue]],
        filters: IssueFilters,
    ) -> Select[tuple[Issue]]:
        """Apply filter criteria to query.

        Args:
            query: Base SQLAlchemy query.
            filters: Filter criteria.

        Returns:
            Query with filters applied.
        """
        conditions: list[Any] = []

        if filters.project_id:
            conditions.append(Issue.project_id == filters.project_id)

        if filters.state_ids:
            conditions.append(Issue.state_id.in_(filters.state_ids))

        if filters.state_groups:
            from pilot_space.infrastructure.database.models import State

            subquery = select(State.id).where(State.group.in_(filters.state_groups))
            conditions.append(Issue.state_id.in_(subquery))

        if filters.assignee_ids:
            conditions.append(Issue.assignee_id.in_(filters.assignee_ids))

        if filters.reporter_ids:
            conditions.append(Issue.reporter_id.in_(filters.reporter_ids))

        if filters.label_ids:
            from pilot_space.infrastructure.database.models import issue_labels

            subquery = (
                select(issue_labels.c.issue_id)
                .where(issue_labels.c.label_id.in_(filters.label_ids))
                .distinct()
            )
            conditions.append(Issue.id.in_(subquery))

        if filters.cycle_id:
            conditions.append(Issue.cycle_id == filters.cycle_id)

        if filters.module_id:
            conditions.append(Issue.module_id == filters.module_id)

        if filters.parent_id is not None:
            conditions.append(Issue.parent_id == filters.parent_id)

        if filters.priorities:
            conditions.append(Issue.priority.in_(filters.priorities))

        if filters.start_date_from:
            conditions.append(Issue.start_date >= filters.start_date_from)

        if filters.start_date_to:
            conditions.append(Issue.start_date <= filters.start_date_to)

        if filters.target_date_from:
            conditions.append(Issue.target_date >= filters.target_date_from)

        if filters.target_date_to:
            conditions.append(Issue.target_date <= filters.target_date_to)

        if filters.search_term:
            safe_term = filters.search_term.replace("%", r"\%").replace("_", r"\_")
            search_pattern = f"%{safe_term}%"
            conditions.append(
                or_(
                    Issue.name.ilike(search_pattern),
                    Issue.description.ilike(search_pattern),
                )
            )

        if filters.has_ai_enhancements is not None:
            if filters.has_ai_enhancements:
                conditions.append(Issue.ai_metadata.isnot(None))
                conditions.append(
                    or_(
                        Issue.ai_metadata["title_enhanced"].astext == "true",
                        Issue.ai_metadata["description_expanded"].astext == "true",
                        Issue.ai_metadata["labels_suggested"].isnot(None),
                    )
                )
            else:
                conditions.append(
                    or_(
                        Issue.ai_metadata.is_(None),
                        and_(
                            Issue.ai_metadata["title_enhanced"].astext != "true",
                            Issue.ai_metadata["description_expanded"].astext != "true",
                        ),
                    )
                )

        if conditions:
            query = query.where(and_(*conditions))

        return query

    async def get_active_by_ids(
        self,
        issue_ids: list[UUID],
    ) -> dict[UUID, Issue]:
        """Batch-fetch active (non-deleted) issues by IDs.

        Used for enriching search results that already have UUIDs (e.g.
        KG-based related-issue suggestions) without issuing N individual
        queries.

        Args:
            issue_ids: List of issue UUIDs to retrieve.

        Returns:
            Dict mapping issue.id -> Issue for all found non-deleted rows.
        """
        if not issue_ids:
            return {}
        query = select(Issue).where(
            and_(
                Issue.id.in_(issue_ids),
                Issue.is_deleted == False,  # noqa: E712
            )
        )
        result = await self.session.execute(query)
        return {issue.id: issue for issue in result.scalars().all()}


__all__ = ["IssueFilters", "IssueRepository"]
