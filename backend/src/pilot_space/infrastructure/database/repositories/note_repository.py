"""Note repository for Note data access.

Provides specialized methods for Note-related queries with eager loading support.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import func, select
from sqlalchemy.orm import joinedload, selectinload

from pilot_space.infrastructure.database.models.note import Note
from pilot_space.infrastructure.database.repositories.base import BaseRepository

if TYPE_CHECKING:
    from collections.abc import Sequence
    from uuid import UUID

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

    async def get_by_project(
        self,
        project_id: UUID,
        *,
        include_deleted: bool = False,
        limit: int | None = None,
    ) -> Sequence[Note]:
        """Get all notes in a project.

        Args:
            project_id: The project ID.
            include_deleted: Whether to include soft-deleted notes.
            limit: Maximum number of notes to return.

        Returns:
            List of notes in the project.
        """
        query = select(Note).where(Note.project_id == project_id)
        if not include_deleted:
            query = query.where(Note.is_deleted == False)  # noqa: E712
        query = query.order_by(Note.created_at.desc())
        if limit:
            query = query.limit(limit)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def search_by_title(
        self,
        workspace_id: UUID,
        search_term: str,
        *,
        project_id: UUID | None = None,
        include_deleted: bool = False,
        limit: int = 20,
    ) -> Sequence[Note]:
        """Search notes by title in workspace.

        Uses case-insensitive pattern matching.

        Args:
            workspace_id: The workspace ID.
            search_term: Text to search for in title.
            project_id: Optional project ID to narrow search.
            include_deleted: Whether to include soft-deleted notes.
            limit: Maximum results to return.

        Returns:
            List of matching notes.
        """
        query = select(Note).where(Note.workspace_id == workspace_id)
        if project_id:
            query = query.where(Note.project_id == project_id)
        if not include_deleted:
            query = query.where(Note.is_deleted == False)  # noqa: E712

        safe_term = search_term.replace("%", r"\%").replace("_", r"\_")
        search_pattern = f"%{safe_term}%"
        query = query.where(Note.title.ilike(search_pattern))
        query = query.order_by(Note.created_at.desc()).limit(limit)
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
        from pilot_space.infrastructure.database.models.threaded_discussion import (
            ThreadedDiscussion,
        )

        query = (
            select(Note)
            .options(
                selectinload(Note.annotations),
                selectinload(Note.discussions).selectinload(ThreadedDiscussion.comments),
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

    async def search_full_text(
        self,
        workspace_id: UUID,
        search_term: str,
        *,
        project_id: UUID | None = None,
        include_deleted: bool = False,
        limit: int = 20,
    ) -> Sequence[Note]:
        """Full-text search on notes using PostgreSQL ts_vector.

        Searches title using the full-text index.

        Args:
            workspace_id: The workspace ID.
            search_term: Text to search for.
            project_id: Optional project ID to narrow search.
            include_deleted: Whether to include soft-deleted notes.
            limit: Maximum results to return.

        Returns:
            List of matching notes ordered by relevance.
        """
        from sqlalchemy import text as sql_text

        query = select(Note).where(Note.workspace_id == workspace_id)
        if project_id:
            query = query.where(Note.project_id == project_id)
        if not include_deleted:
            query = query.where(Note.is_deleted == False)  # noqa: E712

        # Use PostgreSQL full-text search
        ts_query = sql_text("to_tsvector('english', title) @@ plainto_tsquery('english', :term)")
        query = query.where(ts_query.bindparams(term=search_term))
        query = query.order_by(Note.created_at.desc()).limit(limit)
        result = await self.session.execute(query)
        return result.scalars().all()
