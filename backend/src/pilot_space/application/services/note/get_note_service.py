"""GetNoteService for retrieving notes.

Implements CQRS-lite query pattern for note retrieval.
Supports various loading options for related data.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from pilot_space.infrastructure.database.models.note import Note
    from pilot_space.infrastructure.database.repositories.note_repository import (
        NoteRepository,
    )


@dataclass(frozen=True, slots=True)
class GetNoteOptions:
    """Options for note retrieval.

    Attributes:
        include_annotations: Load annotations with note.
        include_discussions: Load discussions with comments.
        include_all_relations: Load all relations (annotations, discussions, owner).
        include_deleted: Include soft-deleted notes.
    """

    include_annotations: bool = False
    include_discussions: bool = False
    include_all_relations: bool = False
    include_deleted: bool = False


class GetNoteService:
    """Service for retrieving notes.

    Handles note queries with configurable relation loading.
    Optimizes queries based on requested data.
    """

    def __init__(
        self,
        session: AsyncSession,
        note_repository: NoteRepository,
    ) -> None:
        """Initialize GetNoteService.

        Args:
            session: The async database session.
            note_repository: Repository for note operations.
        """
        self._session = session
        self._note_repo = note_repository

    async def get_by_id(
        self,
        note_id: UUID,
        options: GetNoteOptions | None = None,
    ) -> Note | None:
        """Get a note by ID with optional relations.

        Args:
            note_id: The note ID.
            options: Loading options for relations.

        Returns:
            The note if found, None otherwise.
        """
        options = options or GetNoteOptions()

        if options.include_all_relations:
            return await self._note_repo.get_with_all_relations(
                note_id,
                include_deleted=options.include_deleted,
            )

        if options.include_discussions:
            return await self._note_repo.get_with_discussions(
                note_id,
                include_deleted=options.include_deleted,
            )

        if options.include_annotations:
            return await self._note_repo.get_with_annotations(
                note_id,
                include_deleted=options.include_deleted,
            )

        return await self._note_repo.get_by_id(
            note_id,
            include_deleted=options.include_deleted,
        )

    async def get_by_workspace(
        self,
        workspace_id: UUID,
        *,
        project_id: UUID | None = None,
        include_deleted: bool = False,
        limit: int | None = None,
        offset: int | None = None,
    ) -> Sequence[Note]:
        """Get notes in a workspace with optional project filter.

        Args:
            workspace_id: The workspace ID.
            project_id: Optional project ID filter.
            include_deleted: Include soft-deleted notes.
            limit: Maximum notes to return.
            offset: Number of notes to skip.

        Returns:
            List of notes.
        """
        
        return await self._note_repo.list_notes(
            workspace_id,
            project_ids=[project_id] if project_id else None,
            include_deleted=include_deleted,
            limit=limit,
            offset=offset,
        )

    async def search(
        self,
        workspace_id: UUID,
        search_term: str,
        *,
        project_id: UUID | None = None,
        use_full_text: bool = False,
        include_deleted: bool = False,
        limit: int = 20,
    ) -> Sequence[Note]:
        """Search notes by title.

        Args:
            workspace_id: The workspace ID.
            search_term: Text to search for.
            project_id: Optional project ID filter.
            use_full_text: Use PostgreSQL full-text search.
            include_deleted: Include soft-deleted notes.
            limit: Maximum results to return.

        Returns:
            List of matching notes.
        """
        if use_full_text:
            return await self._note_repo.search_full_text(
                workspace_id,
                search_term,
                project_ids=[project_id] if project_id else None,
                include_deleted=include_deleted,
                limit=limit,
            )

        return await self._note_repo.list_notes(
            workspace_id,
            project_ids=[project_id] if project_id else None,
            search=search_term,
            include_deleted=include_deleted,
            limit=limit,
        )

    async def get_pinned(
        self,
        workspace_id: UUID,
        *,
        project_id: UUID | None = None,
        limit: int = 10,
    ) -> Sequence[Note]:
        """Get pinned notes in workspace or project.

        Args:
            workspace_id: The workspace ID.
            project_id: Optional project ID filter.
            limit: Maximum notes to return.

        Returns:
            List of pinned notes.
        """
        return await self._note_repo.list_notes(
            workspace_id,
            project_ids=[project_id] if project_id else None,
            is_pinned=True,
            limit=limit,
        )

    async def get_by_owner(
        self,
        owner_id: UUID,
        workspace_id: UUID,
        *,
        include_deleted: bool = False,
        limit: int | None = None,
    ) -> Sequence[Note]:
        """Get notes by a specific owner.

        Args:
            owner_id: The owner's user ID.
            workspace_id: The workspace ID.
            include_deleted: Include soft-deleted notes.
            limit: Maximum notes to return.

        Returns:
            List of notes by the owner.
        """
        return await self._note_repo.get_by_owner(
            owner_id,
            workspace_id,
            include_deleted=include_deleted,
            limit=limit,
        )

    async def count_pinned(
        self,
        workspace_id: UUID,
        *,
        project_id: UUID | None = None,
    ) -> int:
        """Count pinned notes.

        Args:
            workspace_id: The workspace ID.
            project_id: Optional project ID filter.

        Returns:
            Count of pinned notes.
        """
        return await self._note_repo.count_pinned(
            workspace_id,
            project_id=project_id,
        )
