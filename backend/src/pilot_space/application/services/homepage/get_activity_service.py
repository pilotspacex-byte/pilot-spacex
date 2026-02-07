"""Service for fetching homepage activity feed.

Queries recent notes and issues, groups them by time period
(today / yesterday / this_week), and returns cursor-paginated results.

References:
- specs/012-homepage-note/spec.md Activity Feed Endpoint
- US-19: Homepage Hub feature
"""

from __future__ import annotations

import base64
import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from uuid import UUID

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class GetActivityPayload:
    """Payload for fetching activity feed.

    Attributes:
        workspace_id: Workspace to query.
        cursor: Opaque pagination cursor (base64-encoded JSON).
        limit: Max items per page (default 20, max 50).
    """

    workspace_id: UUID
    cursor: str | None = None
    limit: int = 20


@dataclass
class ActivityItem:
    """Unified activity item for grouping.

    Wraps either a note or issue row with its type discriminator
    so the grouping logic can work with a single sorted list.
    """

    type: str  # "note" or "issue"
    id: UUID
    updated_at: datetime
    data: object  # NoteActivityRow | IssueActivityRow


@dataclass
class GroupedActivity:
    """Activity items grouped by time period."""

    today: list[ActivityItem] = field(default_factory=list)
    yesterday: list[ActivityItem] = field(default_factory=list)
    this_week: list[ActivityItem] = field(default_factory=list)


@dataclass
class GetActivityResult:
    """Result from fetching activity feed.

    Attributes:
        grouped: Items grouped into today/yesterday/this_week.
        total: Total number of items returned.
        cursor: Next pagination cursor (None if no more).
        has_more: Whether more items exist beyond this page.
    """

    grouped: GroupedActivity
    total: int = 0
    cursor: str | None = None
    has_more: bool = False


class GetActivityService:
    """Service for querying the homepage activity feed.

    Fetches recent notes (with latest annotation preview) and recent
    issues (with state, priority, assignee, last activity) from the
    HomepageRepository, merges them by updated_at desc, groups into
    today / yesterday / this_week buckets, and returns cursor-paginated
    results.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize GetActivityService.

        Args:
            session: The async database session.
        """
        self._session = session

    async def execute(self, payload: GetActivityPayload) -> GetActivityResult:
        """Execute activity feed query.

        Args:
            payload: The activity feed payload.

        Returns:
            GetActivityResult with grouped items and pagination metadata.
        """
        from pilot_space.infrastructure.database.repositories.homepage_repository import (
            HomepageRepository,
        )

        repo = HomepageRepository(self._session)
        limit = min(payload.limit, 50)

        # Decode cursor → updated_at timestamp for keyset pagination
        cursor_dt = self._decode_cursor(payload.cursor)

        # Fetch one extra to detect has_more
        fetch_limit = limit + 1

        notes = await repo.get_recent_notes_with_annotations(
            payload.workspace_id,
            limit=fetch_limit,
            cursor_updated_at=cursor_dt,
        )
        issues = await repo.get_recent_issues_with_activity(
            payload.workspace_id,
            limit=fetch_limit,
            cursor_updated_at=cursor_dt,
        )

        # Merge into unified list sorted by updated_at desc
        items: list[ActivityItem] = []
        for n in notes:
            items.append(ActivityItem(type="note", id=n.id, updated_at=n.updated_at, data=n))
        for i in issues:
            items.append(ActivityItem(type="issue", id=i.id, updated_at=i.updated_at, data=i))
        items.sort(key=lambda x: x.updated_at, reverse=True)

        # Trim to limit; check has_more
        has_more = len(items) > limit
        items = items[:limit]

        # Build next cursor from last item's updated_at
        next_cursor: str | None = None
        if has_more and items:
            next_cursor = self._encode_cursor(items[-1].updated_at)

        # Group by time period
        grouped = self._group_by_period(items)

        return GetActivityResult(
            grouped=grouped,
            total=len(items),
            cursor=next_cursor,
            has_more=has_more,
        )

    def _group_by_period(self, items: list[ActivityItem]) -> GroupedActivity:
        """Group activity items into today/yesterday/this_week buckets.

        Uses UTC dates for boundary calculations.

        Args:
            items: Sorted list of activity items (desc by updated_at).

        Returns:
            GroupedActivity with items in each bucket.
        """
        now = datetime.now(tz=UTC)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        yesterday_start = today_start - timedelta(days=1)

        grouped = GroupedActivity()

        for item in items:
            ts = item.updated_at
            # Ensure timezone-aware comparison
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=UTC)

            if ts >= today_start:
                grouped.today.append(item)
            elif ts >= yesterday_start:
                grouped.yesterday.append(item)
            else:
                grouped.this_week.append(item)

        return grouped

    @staticmethod
    def _decode_cursor(cursor: str | None) -> datetime | None:
        """Decode opaque cursor to datetime.

        Cursor format: base64({"t": "2026-02-05T10:00:00Z"})

        Args:
            cursor: Base64-encoded cursor string.

        Returns:
            Parsed datetime or None.
        """
        if not cursor:
            return None
        try:
            decoded = base64.b64decode(cursor).decode("utf-8")
            data = json.loads(decoded)
            return datetime.fromisoformat(data["t"])
        except (ValueError, KeyError, json.JSONDecodeError):
            logger.warning("Invalid activity cursor: %s", cursor)
            return None

    @staticmethod
    def _encode_cursor(dt: datetime) -> str:
        """Encode datetime to opaque cursor.

        Args:
            dt: Datetime value to encode.

        Returns:
            Base64-encoded cursor string.
        """
        payload = json.dumps({"t": dt.isoformat()})
        return base64.b64encode(payload.encode("utf-8")).decode("ascii")


__all__ = [
    "ActivityItem",
    "GetActivityPayload",
    "GetActivityResult",
    "GetActivityService",
    "GroupedActivity",
]
