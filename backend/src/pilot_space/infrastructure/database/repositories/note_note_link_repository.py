"""Repository for NoteNoteLink entity.

Provides CRUD + query methods for Note-to-Note relationships.
Supports workspace-scoped operations with RLS enforcement.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from pilot_space.infrastructure.database.models.note_note_link import (
    NoteNoteLink,
    NoteNoteLinkType,
)
from pilot_space.infrastructure.database.repositories.base import BaseRepository


class NoteNoteLinkRepository(BaseRepository[NoteNoteLink]):
    """Repository for NoteNoteLink entities."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with session and NoteNoteLink model."""
        super().__init__(session=session, model_class=NoteNoteLink)

    async def find_by_source(
        self,
        source_note_id: UUID,
        workspace_id: UUID,
    ) -> list[NoteNoteLink]:
        """Get all outgoing links from a note.

        Args:
            source_note_id: Source note UUID.
            workspace_id: Workspace UUID for RLS scoping.

        Returns:
            List of NoteNoteLink records.
        """
        query = (
            select(NoteNoteLink)
            .where(
                and_(
                    NoteNoteLink.source_note_id == source_note_id,
                    NoteNoteLink.workspace_id == workspace_id,
                    NoteNoteLink.is_deleted == False,  # noqa: E712
                )
            )
            .options(selectinload(NoteNoteLink.target_note))
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def find_by_target(
        self,
        target_note_id: UUID,
        workspace_id: UUID,
    ) -> list[NoteNoteLink]:
        """Get all incoming links (backlinks) to a note.

        Args:
            target_note_id: Target note UUID.
            workspace_id: Workspace UUID for RLS scoping.

        Returns:
            List of NoteNoteLink records.
        """
        query = (
            select(NoteNoteLink)
            .where(
                and_(
                    NoteNoteLink.target_note_id == target_note_id,
                    NoteNoteLink.workspace_id == workspace_id,
                    NoteNoteLink.is_deleted == False,  # noqa: E712
                )
            )
            .options(selectinload(NoteNoteLink.source_note))
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def find_existing(
        self,
        source_note_id: UUID,
        target_note_id: UUID,
        block_id: str | None,
        workspace_id: UUID,
    ) -> NoteNoteLink | None:
        """Find existing link by source+target+block_id (unique constraint).

        Args:
            source_note_id: Source note UUID.
            target_note_id: Target note UUID.
            block_id: Block ID (None for unanchored links).
            workspace_id: Workspace UUID for RLS scoping.

        Returns:
            Existing NoteNoteLink or None.
        """
        conditions = [
            NoteNoteLink.source_note_id == source_note_id,
            NoteNoteLink.target_note_id == target_note_id,
            NoteNoteLink.workspace_id == workspace_id,
            NoteNoteLink.is_deleted == False,  # noqa: E712
        ]
        if block_id is None:
            conditions.append(NoteNoteLink.block_id.is_(None))
        else:
            conditions.append(NoteNoteLink.block_id == block_id)

        query = select(NoteNoteLink).where(and_(*conditions))
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def create_link(
        self,
        source_note_id: UUID,
        target_note_id: UUID,
        link_type: NoteNoteLinkType,
        workspace_id: UUID,
        block_id: str | None = None,
    ) -> NoteNoteLink:
        """Create a new note-to-note link.

        Args:
            source_note_id: Source note UUID.
            target_note_id: Target note UUID.
            link_type: Link type (inline/embed).
            workspace_id: Workspace UUID.
            block_id: Optional block ID.

        Returns:
            Created NoteNoteLink.
        """
        link = NoteNoteLink(
            source_note_id=source_note_id,
            target_note_id=target_note_id,
            link_type=link_type,
            block_id=block_id,
            workspace_id=workspace_id,
        )
        return await self.create(link)

    async def delete_link(
        self,
        source_note_id: UUID,
        target_note_id: UUID,
        workspace_id: UUID,
    ) -> int:
        """Soft-delete all links between source and target notes.

        Uses a single batch UPDATE for efficiency (avoids N+1).

        Args:
            source_note_id: Source note UUID.
            target_note_id: Target note UUID.
            workspace_id: Workspace UUID for RLS scoping.

        Returns:
            Number of links soft-deleted.
        """
        stmt = (
            update(NoteNoteLink)
            .where(
                and_(
                    NoteNoteLink.source_note_id == source_note_id,
                    NoteNoteLink.target_note_id == target_note_id,
                    NoteNoteLink.workspace_id == workspace_id,
                    NoteNoteLink.is_deleted == False,  # noqa: E712
                )
            )
            .values(is_deleted=True, deleted_at=func.now())
        )
        result = await self.session.execute(stmt)
        return result.rowcount  # type: ignore[return-value]
