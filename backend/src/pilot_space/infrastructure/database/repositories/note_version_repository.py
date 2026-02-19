"""NoteVersionRepository for note version snapshots.

Provides paginated queries, trigger-based filtering, pinned-only queries,
and retention queries. All queries enforce workspace-scoped RLS via workspace_id.

Feature 017: Note Versioning + PM Blocks — Sprint 1 (T-204)
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import delete, desc, select

from pilot_space.infrastructure.database.models.note_version import NoteVersion, VersionTrigger
from pilot_space.infrastructure.database.repositories.base import BaseRepository

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sqlalchemy.ext.asyncio import AsyncSession


class NoteVersionRepository(BaseRepository[NoteVersion]):
    """Repository for NoteVersion CRUD and workspace-scoped queries."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session=session, model_class=NoteVersion)

    async def list_by_note(
        self,
        note_id: UUID,
        workspace_id: UUID,
        *,
        limit: int = 20,
        offset: int = 0,
    ) -> Sequence[NoteVersion]:
        """List versions for a note, newest first.

        Args:
            note_id: Note UUID.
            workspace_id: Workspace UUID for RLS enforcement.
            limit: Max results.
            offset: Pagination offset.

        Returns:
            Sequence of NoteVersion models ordered by created_at DESC.
        """
        query = (
            select(NoteVersion)
            .where(
                NoteVersion.note_id == note_id,
                NoteVersion.workspace_id == workspace_id,
            )
            .order_by(desc(NoteVersion.created_at))
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def list_by_trigger(
        self,
        note_id: UUID,
        workspace_id: UUID,
        trigger: VersionTrigger,
    ) -> Sequence[NoteVersion]:
        """List versions for a note filtered by trigger type.

        Args:
            note_id: Note UUID.
            workspace_id: Workspace UUID.
            trigger: Version trigger type to filter by.

        Returns:
            Sequence of NoteVersion models.
        """
        query = (
            select(NoteVersion)
            .where(
                NoteVersion.note_id == note_id,
                NoteVersion.workspace_id == workspace_id,
                NoteVersion.trigger == trigger,
            )
            .order_by(desc(NoteVersion.created_at))
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def list_pinned(
        self,
        note_id: UUID,
        workspace_id: UUID,
    ) -> Sequence[NoteVersion]:
        """List pinned versions for a note.

        Args:
            note_id: Note UUID.
            workspace_id: Workspace UUID.

        Returns:
            Pinned NoteVersion models, newest first.
        """
        query = (
            select(NoteVersion)
            .where(
                NoteVersion.note_id == note_id,
                NoteVersion.workspace_id == workspace_id,
                NoteVersion.pinned == True,  # noqa: E712
            )
            .order_by(desc(NoteVersion.created_at))
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_by_id_for_note(
        self,
        version_id: UUID,
        note_id: UUID,
        workspace_id: UUID,
    ) -> NoteVersion | None:
        """Fetch a single version, verifying note and workspace ownership.

        Args:
            version_id: Version UUID.
            note_id: Note UUID (ownership check).
            workspace_id: Workspace UUID (RLS check).

        Returns:
            NoteVersion if found and owned by note/workspace, else None.
        """
        query = select(NoteVersion).where(
            NoteVersion.id == version_id,
            NoteVersion.note_id == note_id,
            NoteVersion.workspace_id == workspace_id,
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_ai_before_for_after(
        self,
        note_id: UUID,
        workspace_id: UUID,
        ai_after_created_at: datetime,
    ) -> NoteVersion | None:
        """Find the closest ai_before snapshot preceding an ai_after version.

        Used for the "Undo AI Changes" fast path (GAP-04): given an ai_after
        version's timestamp, return the most recent ai_before snapshot that
        was created before it (same AI operation pair).

        Args:
            note_id: Note UUID.
            workspace_id: Workspace UUID.
            ai_after_created_at: Timestamp of the ai_after version to pair against.

        Returns:
            The closest preceding ai_before NoteVersion, or None if not found.
        """
        query = (
            select(NoteVersion)
            .where(
                NoteVersion.note_id == note_id,
                NoteVersion.workspace_id == workspace_id,
                NoteVersion.trigger == VersionTrigger.AI_BEFORE,
                NoteVersion.created_at < ai_after_created_at,
            )
            .order_by(desc(NoteVersion.created_at))
            .limit(1)
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_ai_before_map_for_versions(
        self,
        note_id: UUID,
        workspace_id: UUID,
        ai_after_timestamps: list[datetime],
    ) -> dict[datetime, UUID]:
        """Batch fetch ai_before version IDs for a list of ai_after timestamps.

        Replaces N individual get_ai_before_for_after calls with one query.
        For each ai_after timestamp, finds the most recent ai_before snapshot
        created before that timestamp (same approach as get_ai_before_for_after
        but for multiple timestamps at once).

        Args:
            note_id: Note UUID.
            workspace_id: Workspace UUID.
            ai_after_timestamps: List of ai_after version created_at values.

        Returns:
            Dict mapping ai_after created_at -> ai_before version UUID.
        """
        if not ai_after_timestamps:
            return {}

        max_ts = max(ai_after_timestamps)
        # Single query: fetch all ai_before rows created before the latest ai_after ts.
        all_ai_before_result = await self.session.execute(
            select(NoteVersion)
            .where(
                NoteVersion.note_id == note_id,
                NoteVersion.workspace_id == workspace_id,
                NoteVersion.trigger == VersionTrigger.AI_BEFORE,
                NoteVersion.created_at < max_ts,
            )
            .order_by(desc(NoteVersion.created_at))
        )
        # Sort descending by created_at for efficient greedy pairing
        ai_befores = sorted(
            all_ai_before_result.scalars().all(),
            key=lambda v: v.created_at,
            reverse=True,
        )

        # For each ai_after timestamp, pick the most recent ai_before before it
        result_map: dict[datetime, UUID] = {}
        for ts in ai_after_timestamps:
            for ab in ai_befores:
                if ab.created_at < ts:
                    result_map[ts] = ab.id
                    break

        return result_map

    async def get_latest_ai_before(
        self,
        note_id: UUID,
        workspace_id: UUID,
    ) -> NoteVersion | None:
        """Get the most recent ai_before snapshot for a note.

        Used for the "Undo AI Changes" fast path when no specific ai_after
        version is provided — restores from the latest ai_before checkpoint.

        Args:
            note_id: Note UUID.
            workspace_id: Workspace UUID.

        Returns:
            Most recent ai_before NoteVersion, or None if no AI ops recorded.
        """
        query = (
            select(NoteVersion)
            .where(
                NoteVersion.note_id == note_id,
                NoteVersion.workspace_id == workspace_id,
                NoteVersion.trigger == VersionTrigger.AI_BEFORE,
            )
            .order_by(desc(NoteVersion.created_at))
            .limit(1)
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_latest_for_note(
        self,
        note_id: UUID,
        workspace_id: UUID,
    ) -> NoteVersion | None:
        """Get the most recent version for a note.

        Args:
            note_id: Note UUID.
            workspace_id: Workspace UUID.

        Returns:
            Most recent NoteVersion or None.
        """
        query = (
            select(NoteVersion)
            .where(
                NoteVersion.note_id == note_id,
                NoteVersion.workspace_id == workspace_id,
            )
            .order_by(desc(NoteVersion.created_at))
            .limit(1)
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_max_version_number(
        self,
        note_id: UUID,
        workspace_id: UUID,
    ) -> int:
        """Get the highest version_number for a note within a workspace.

        Used to calculate the next version_number for a new snapshot.
        workspace_id is required for RLS enforcement and cross-tenant safety.

        Args:
            note_id: Note UUID.
            workspace_id: Workspace UUID (scopes query to prevent cross-tenant leaks).

        Returns:
            Max version_number, or 0 if no versions exist.
        """
        from sqlalchemy import func

        query = select(func.max(NoteVersion.version_number)).where(
            NoteVersion.note_id == note_id,
            NoteVersion.workspace_id == workspace_id,
        )
        result = await self.session.execute(query)
        max_num = result.scalar_one_or_none()
        return max_num or 0

    async def find_retention_candidates(
        self,
        note_id: UUID,
        workspace_id: UUID,
        max_count: int,
        max_age_days: int,
    ) -> Sequence[NoteVersion]:
        """Find versions eligible for retention cleanup.

        Returns unpinned versions that are either:
        - Older than max_age_days, OR
        - Beyond the max_count newest versions

        Pinned versions are always excluded (FR-075).

        Args:
            note_id: Note UUID.
            workspace_id: Workspace UUID.
            max_count: Maximum number of versions to keep.
            max_age_days: Maximum age in days to keep.

        Returns:
            Sequence of NoteVersion IDs eligible for deletion.
        """
        cutoff_date = datetime.now(tz=UTC) - timedelta(days=max_age_days)

        # Get all unpinned versions ordered newest first
        all_unpinned_query = (
            select(NoteVersion)
            .where(
                NoteVersion.note_id == note_id,
                NoteVersion.workspace_id == workspace_id,
                NoteVersion.pinned == False,  # noqa: E712
            )
            .order_by(desc(NoteVersion.created_at))
        )
        result = await self.session.execute(all_unpinned_query)
        all_unpinned = list(result.scalars().all())

        candidates = []
        for idx, version in enumerate(all_unpinned):
            # Beyond max_count rank OR older than cutoff
            beyond_count = idx >= max_count
            too_old = version.created_at.replace(tzinfo=UTC) < cutoff_date
            if beyond_count or too_old:
                candidates.append(version)

        return candidates

    async def batch_delete(self, version_ids: list[UUID]) -> int:
        """Delete multiple versions by ID.

        Args:
            version_ids: List of version UUIDs to delete.

        Returns:
            Number of rows deleted.
        """
        if not version_ids:
            return 0
        stmt = delete(NoteVersion).where(NoteVersion.id.in_(version_ids))
        result = await self.session.execute(stmt)
        rowcount: int = result.rowcount  # type: ignore[attr-defined]
        return rowcount

    async def count_by_note(
        self,
        note_id: UUID,
        workspace_id: UUID,
    ) -> int:
        """Count total versions for a note.

        Args:
            note_id: Note UUID.
            workspace_id: Workspace UUID.

        Returns:
            Total version count.
        """
        from sqlalchemy import func

        query = select(func.count()).where(
            NoteVersion.note_id == note_id,
            NoteVersion.workspace_id == workspace_id,
        )
        result = await self.session.execute(query)
        return result.scalar_one()
