"""Note repository for Note data access.

Provides specialized methods for Note-related queries with eager loading support.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import func, select, text
from sqlalchemy.orm import joinedload, selectinload

from pilot_space.infrastructure.database.models.note import Note
from pilot_space.infrastructure.database.repositories.base import BaseRepository

if TYPE_CHECKING:
    from collections.abc import Sequence
    from uuid import UUID

    from sqlalchemy import RowMapping
    from sqlalchemy.ext.asyncio import AsyncSession


class NoteRepository(BaseRepository[Note]):
    """Repository for Note entities.

    Extends BaseRepository with note-specific queries.
    Supports eager loading of annotations and discussions.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize NoteRepository.

        Args:
            session: The async database session.
        """
        super().__init__(session, Note)

    async def get_by_workspace(
        self,
        workspace_id: UUID,
        *,
        include_deleted: bool = False,
        limit: int | None = None,
        offset: int | None = None,
    ) -> Sequence[Note]:
        """Get all notes in a workspace.

        Args:
            workspace_id: The workspace ID.
            include_deleted: Whether to include soft-deleted notes.
            limit: Maximum number of notes to return.
            offset: Number of notes to skip.

        Returns:
            List of notes in the workspace.
        """
        query = select(Note).where(Note.workspace_id == workspace_id)
        if not include_deleted:
            query = query.where(Note.is_deleted == False)  # noqa: E712
        query = query.order_by(Note.created_at.desc())
        if limit:
            query = query.limit(limit)
        if offset:
            query = query.offset(offset)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def list_notes(
        self,
        workspace_id: UUID,
        *,
        project_ids: list[UUID] | None = None,
        is_pinned: bool | None = None,
        search: str | None = None,
        include_deleted: bool = False,
        limit: int | None = None,
        offset: int | None = None,
    ) -> Sequence[Note]:
        """List notes in a workspace with optional filters.

        All filters are composable: any combination of project_ids, is_pinned,
        and search can be provided together.

        Args:
            workspace_id: The workspace ID to scope the query.
            project_ids: If provided, only notes belonging to these projects are returned.
            is_pinned: If provided, filters by pinned status.
            search: If provided, performs case-insensitive title matching.
            include_deleted: Whether to include soft-deleted notes.
            limit: Maximum number of notes to return.
            offset: Number of notes to skip (for pagination).

        Returns:
            List of matching notes ordered by updated_at desc.
        """
        query = select(Note).where(Note.workspace_id == workspace_id)

        if project_ids:
            query = query.where(Note.project_id.in_(project_ids))
        if is_pinned is not None:
            query = query.where(Note.is_pinned == is_pinned)  # noqa: E712
        if search:
            safe_term = search.replace("%", r"\%").replace("_", r"\_")
            query = query.where(Note.title.ilike(f"%{safe_term}%"))
        if not include_deleted:
            query = query.where(Note.is_deleted == False)  # noqa: E712

        query = query.order_by(Note.updated_at.desc())
        if limit:
            query = query.limit(limit)
        if offset:
            query = query.offset(offset)

        result = await self.session.execute(query)
        return result.scalars().all()

    async def count_pinned(
        self,
        workspace_id: UUID,
        *,
        project_id: UUID | None = None,
    ) -> int:
        """Count pinned notes in workspace or project.

        Args:
            workspace_id: The workspace ID.
            project_id: Optional project ID to narrow count.

        Returns:
            Count of pinned notes.
        """
        query = (
            select(func.count())
            .select_from(Note)
            .where(
                Note.workspace_id == workspace_id,
                Note.is_pinned == True,  # noqa: E712
                Note.is_deleted == False,  # noqa: E712
            )
        )
        if project_id:
            query = query.where(Note.project_id == project_id)
        result = await self.session.execute(query)
        return result.scalar() or 0

    async def get_with_annotations(
        self,
        note_id: UUID,
        *,
        include_deleted: bool = False,
    ) -> Note | None:
        """Get note with annotations eagerly loaded.

        Args:
            note_id: The note ID.
            include_deleted: Whether to include soft-deleted note.

        Returns:
            Note with annotations loaded, or None if not found.
        """
        query = select(Note).options(selectinload(Note.annotations)).where(Note.id == note_id)
        if not include_deleted:
            query = query.where(Note.is_deleted == False)  # noqa: E712
        result = await self.session.execute(query)
        return result.unique().scalar_one_or_none()

    async def get_with_discussions(
        self,
        note_id: UUID,
        *,
        include_deleted: bool = False,
    ) -> Note | None:
        """Get note with discussions and comments eagerly loaded.

        Args:
            note_id: The note ID.
            include_deleted: Whether to include soft-deleted note.

        Returns:
            Note with discussions and comments loaded, or None if not found.
        """
        from pilot_space.infrastructure.database.models.threaded_discussion import (
            ThreadedDiscussion,
        )

        query = (
            select(Note)
            .options(selectinload(Note.discussions).selectinload(ThreadedDiscussion.comments))
            .where(Note.id == note_id)
        )
        if not include_deleted:
            query = query.where(Note.is_deleted == False)  # noqa: E712
        result = await self.session.execute(query)
        return result.unique().scalar_one_or_none()

    async def get_with_all_relations(
        self,
        note_id: UUID,
        *,
        include_deleted: bool = False,
    ) -> Note | None:
        """Get note with all relations eagerly loaded.

        Loads annotations, discussions with comments, owner, and template.

        Args:
            note_id: The note ID.
            include_deleted: Whether to include soft-deleted note.

        Returns:
            Note with all relations loaded, or None if not found.
        """
        from pilot_space.infrastructure.database.models.note_issue_link import (
            NoteIssueLink,
        )
        from pilot_space.infrastructure.database.models.threaded_discussion import (
            ThreadedDiscussion,
        )

        query = (
            select(Note)
            .options(
                selectinload(Note.annotations),
                selectinload(Note.discussions).selectinload(ThreadedDiscussion.comments),
                selectinload(Note.issue_links).joinedload(NoteIssueLink.issue),
                joinedload(Note.owner),
                joinedload(Note.template),
                joinedload(Note.project),
            )
            .where(Note.id == note_id)
        )
        if not include_deleted:
            query = query.where(Note.is_deleted == False)  # noqa: E712
        result = await self.session.execute(query)
        return result.unique().scalar_one_or_none()

    async def get_pinned_notes(
        self,
        workspace_id: UUID,
        *,
        project_id: UUID | None = None,
        limit: int = 10,
    ) -> Sequence[Note]:
        """Get pinned notes in workspace or project.

        Args:
            workspace_id: The workspace ID.
            project_id: Optional project ID to narrow results.
            limit: Maximum number of notes to return.

        Returns:
            List of pinned notes.
        """
        query = select(Note).where(
            Note.workspace_id == workspace_id,
            Note.is_pinned == True,  # noqa: E712
            Note.is_deleted == False,  # noqa: E712
        )
        if project_id:
            query = query.where(Note.project_id == project_id)
        query = query.order_by(Note.updated_at.desc()).limit(limit)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_by_owner(
        self,
        owner_id: UUID,
        workspace_id: UUID,
        *,
        include_deleted: bool = False,
        limit: int | None = None,
    ) -> Sequence[Note]:
        """Get all notes by a specific owner in workspace.

        Args:
            owner_id: The owner's user ID.
            workspace_id: The workspace ID.
            include_deleted: Whether to include soft-deleted notes.
            limit: Maximum number of notes to return.

        Returns:
            List of notes by the owner.
        """
        query = select(Note).where(
            Note.owner_id == owner_id,
            Note.workspace_id == workspace_id,
        )
        if not include_deleted:
            query = query.where(Note.is_deleted == False)  # noqa: E712
        query = query.order_by(Note.created_at.desc())
        if limit:
            query = query.limit(limit)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def exists_in_workspace(self, note_id: UUID, workspace_id: UUID) -> bool:
        """Check if a note exists in the given workspace without fetching content.

        Selects only the id column to avoid loading the full JSONB content column.

        Args:
            note_id: The note UUID.
            workspace_id: The workspace UUID.

        Returns:
            True if the note exists and is not deleted, False otherwise.
        """
        result = await self.session.execute(
            select(Note.id).where(
                Note.id == note_id,
                Note.workspace_id == workspace_id,
                Note.is_deleted.is_(False),
            )
        )
        return result.scalar() is not None

    async def get_children(self, parent_id: UUID) -> Sequence[Note]:
        """Get direct children of a note ordered by position ascending.

        Args:
            parent_id: The parent note ID.

        Returns:
            Ordered list of direct child notes.
        """
        query = (
            select(Note)
            .where(
                Note.parent_id == parent_id,
                Note.is_deleted == False,  # noqa: E712
            )
            .order_by(Note.position.asc())
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_siblings(
        self,
        parent_id: UUID | None,
        workspace_id: UUID,
        project_id: UUID | None,
        exclude_note_id: UUID,
        for_update: bool = False,
    ) -> Sequence[Note]:
        """Get siblings of a note (notes sharing same parent) ordered by position ASC.

        Args:
            parent_id: The shared parent ID (None for root-level siblings).
            workspace_id: The workspace ID.
            project_id: The project ID (None for personal notes).
            exclude_note_id: Note ID to exclude from results.
            for_update: If True, apply SELECT FOR UPDATE to serialize concurrent writes.
                        This is a no-op in SQLite (used in production PostgreSQL only).

        Returns:
            Ordered list of sibling notes.
        """
        query = select(Note).where(
            Note.workspace_id == workspace_id,
            Note.is_deleted == False,  # noqa: E712
            Note.id != exclude_note_id,
        )
        if parent_id is None:
            query = query.where(Note.parent_id.is_(None))
        else:
            query = query.where(Note.parent_id == parent_id)

        if project_id is None:
            query = query.where(Note.project_id.is_(None))
        else:
            query = query.where(Note.project_id == project_id)

        query = query.order_by(Note.position.asc())
        if for_update:
            query = query.with_for_update()
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_descendants(self, note_id: UUID) -> Sequence[RowMapping]:
        """Get all descendants of a note using a recursive CTE.

        Uses PostgreSQL WITH RECURSIVE to traverse the note tree.
        Unit tests must mock this method since SQLite cannot run this CTE pattern.

        Args:
            note_id: The root note ID whose descendants to retrieve.

        Returns:
            Sequence of row mappings with id, parent_id, depth, position columns.
        """
        cte_sql = text(
            """
            WITH RECURSIVE descendants AS (
                SELECT id, parent_id, depth, position
                FROM notes
                WHERE parent_id = :root_id AND is_deleted = false
                UNION ALL
                SELECT n.id, n.parent_id, n.depth, n.position
                FROM notes n
                JOIN descendants d ON n.parent_id = d.id
                WHERE n.is_deleted = false
            )
            SELECT * FROM descendants
            """
        )
        result = await self.session.execute(cte_sql, {"root_id": str(note_id)})
        return result.mappings().all()

    async def search_full_text(
        self,
        workspace_id: UUID,
        search_term: str,
        *,
        project_ids: list[UUID] | None = None,
        include_deleted: bool = False,
        limit: int = 20,
    ) -> Sequence[Note]:
        """Full-text search on notes using PostgreSQL ts_vector.

        Searches title using the full-text index.

        Args:
            workspace_id: The workspace ID.
            search_term: Text to search for.
            project_ids: Optional list of project IDs to narrow search.
            include_deleted: Whether to include soft-deleted notes.
            limit: Maximum results to return.

        Returns:
            List of matching notes ordered by relevance.
        """
        from sqlalchemy import text as sql_text

        query = select(Note).where(Note.workspace_id == workspace_id)
        if project_ids:
            query = query.where(Note.project_id.in_(project_ids))
        if not include_deleted:
            query = query.where(Note.is_deleted == False)  # noqa: E712

        # Use PostgreSQL full-text search
        ts_query = sql_text("to_tsvector('english', title) @@ plainto_tsquery('english', :term)")
        query = query.where(ts_query.bindparams(term=search_term))
        query = query.order_by(Note.created_at.desc()).limit(limit)
        result = await self.session.execute(query)
        return result.scalars().all()
