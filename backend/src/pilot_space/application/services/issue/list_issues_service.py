"""List Issues service with filtering and pagination.

T128: Create ListIssuesService with advanced filtering.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from pilot_space.infrastructure.database.models import IssuePriority, StateGroup
from pilot_space.infrastructure.database.repositories import CursorPage, IssueFilters

if TYPE_CHECKING:
    from datetime import date
    from uuid import UUID

    from pilot_space.infrastructure.database.models import Issue
    from pilot_space.infrastructure.database.repositories import IssueRepository

logger = logging.getLogger(__name__)


@dataclass
class ListIssuesPayload:
    """Payload for listing issues.

    All filter fields are optional.
    """

    workspace_id: UUID

    # Pagination
    cursor: str | None = None
    page_size: int = 20
    sort_by: str = "created_at"
    sort_order: str = "desc"

    # Filters
    project_id: UUID | None = None
    state_ids: list[UUID] | None = None
    state_groups: list[StateGroup] | None = None
    assignee_ids: list[UUID] | None = None
    reporter_ids: list[UUID] | None = None
    label_ids: list[UUID] | None = None
    cycle_id: UUID | None = None
    module_id: UUID | None = None
    parent_id: UUID | None = None
    priorities: list[IssuePriority] | None = None
    start_date_from: date | None = None
    start_date_to: date | None = None
    target_date_from: date | None = None
    target_date_to: date | None = None
    search_term: str | None = None
    has_ai_enhancements: bool | None = None
    include_deleted: bool = False


@dataclass
class ListIssuesResult:
    """Result from listing issues."""

    items: list[Issue] = field(default_factory=list)
    total: int = 0
    next_cursor: str | None = None
    prev_cursor: str | None = None
    has_next: bool = False
    has_prev: bool = False
    page_size: int = 20


class ListIssuesService:
    """Service for listing issues with filtering and pagination.

    Supports:
    - Multiple filter criteria with AND logic
    - Cursor-based pagination
    - Configurable sorting
    - Full-text search
    """

    def __init__(
        self,
        issue_repository: IssueRepository,
    ) -> None:
        """Initialize service.

        Args:
            issue_repository: Issue repository.
        """
        self._issue_repo = issue_repository

    async def execute(self, payload: ListIssuesPayload) -> ListIssuesResult:
        """List issues with filtering and pagination.

        Args:
            payload: List parameters.

        Returns:
            ListIssuesResult with paginated issues.
        """
        logger.debug(
            "Listing issues",
            extra={
                "workspace_id": str(payload.workspace_id),
                "project_id": str(payload.project_id) if payload.project_id else None,
                "page_size": payload.page_size,
            },
        )

        # Build filters
        filters = IssueFilters(
            project_id=payload.project_id,
            state_ids=payload.state_ids,
            state_groups=payload.state_groups,
            assignee_ids=payload.assignee_ids,
            reporter_ids=payload.reporter_ids,
            label_ids=payload.label_ids,
            cycle_id=payload.cycle_id,
            module_id=payload.module_id,
            parent_id=payload.parent_id,
            priorities=payload.priorities,
            start_date_from=payload.start_date_from,
            start_date_to=payload.start_date_to,
            target_date_from=payload.target_date_from,
            target_date_to=payload.target_date_to,
            search_term=payload.search_term,
            has_ai_enhancements=payload.has_ai_enhancements,
        )

        # Get paginated results
        page: CursorPage[Issue] = await self._issue_repo.get_workspace_issues(
            payload.workspace_id,
            filters=filters,
            cursor=payload.cursor,
            page_size=payload.page_size,
            sort_by=payload.sort_by,
            sort_order=payload.sort_order,
            include_deleted=payload.include_deleted,
        )

        return ListIssuesResult(
            items=list(page.items),
            total=page.total,
            next_cursor=page.next_cursor,
            prev_cursor=page.prev_cursor,
            has_next=page.has_next,
            has_prev=page.has_prev,
            page_size=page.page_size,
        )

    async def execute_for_project(
        self,
        project_id: UUID,
        *,
        cursor: str | None = None,
        page_size: int = 20,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        state_groups: list[StateGroup] | None = None,
    ) -> ListIssuesResult:
        """Convenience method for listing project issues.

        Args:
            project_id: Project UUID.
            cursor: Pagination cursor.
            page_size: Items per page.
            sort_by: Sort column.
            sort_order: Sort direction.
            state_groups: Optional state group filter.

        Returns:
            ListIssuesResult with project issues.
        """
        filters = IssueFilters(
            project_id=project_id,
            state_groups=state_groups,
        )

        page = await self._issue_repo.get_project_issues(
            project_id,
            filters=filters,
            cursor=cursor,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order,
        )

        return ListIssuesResult(
            items=list(page.items),
            total=page.total,
            next_cursor=page.next_cursor,
            prev_cursor=page.prev_cursor,
            has_next=page.has_next,
            has_prev=page.has_prev,
            page_size=page.page_size,
        )

    async def execute_for_assignee(
        self,
        assignee_id: UUID,
        workspace_id: UUID,
        *,
        include_completed: bool = False,
    ) -> ListIssuesResult:
        """Get issues assigned to a user.

        Args:
            assignee_id: User UUID.
            workspace_id: Workspace UUID.
            include_completed: Whether to include completed issues.

        Returns:
            ListIssuesResult with assigned issues.
        """
        issues = await self._issue_repo.get_assignee_issues(
            assignee_id,
            workspace_id,
            include_completed=include_completed,
        )

        return ListIssuesResult(
            items=list(issues),
            total=len(issues),
            has_next=False,
            has_prev=False,
            page_size=len(issues),
        )


__all__ = ["ListIssuesPayload", "ListIssuesResult", "ListIssuesService"]
