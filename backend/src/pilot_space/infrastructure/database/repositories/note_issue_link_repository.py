"""Repository for NoteIssueLink entity.

Provides CRUD + query methods for Note-Issue relationships.
Supports workspace-scoped operations with RLS enforcement.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from pilot_space.infrastructure.database.models.note_issue_link import (
    NoteIssueLink,
    NoteLinkType,
)
from pilot_space.infrastructure.database.repositories.base import BaseRepository


class NoteIssueLinkRepository(BaseRepository[NoteIssueLink]):
    """Repository for NoteIssueLink entities."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with session and NoteIssueLink model."""
        super().__init__(session=session, model_class=NoteIssueLink)

    async def get_by_note(
        self,
        note_id: UUID,
        workspace_id: UUID,
    ) -> list[NoteIssueLink]:
        """Get all issue links for a note.

        Args:
            note_id: Note UUID.
            workspace_id: Workspace UUID for RLS scoping.

        Returns:
            List of NoteIssueLink records.
        """
        query = select(NoteIssueLink).where(
            and_(
                NoteIssueLink.note_id == note_id,
                NoteIssueLink.workspace_id == workspace_id,
                NoteIssueLink.is_deleted == False,  # noqa: E712
            )
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_issue(
        self,
        issue_id: UUID,
        workspace_id: UUID,
    ) -> list[NoteIssueLink]:
        """Get all note links for an issue.

        Args:
            issue_id: Issue UUID.
            workspace_id: Workspace UUID for RLS scoping.

        Returns:
            List of NoteIssueLink records.
        """
        query = select(NoteIssueLink).where(
            and_(
                NoteIssueLink.issue_id == issue_id,
                NoteIssueLink.workspace_id == workspace_id,
                NoteIssueLink.is_deleted == False,  # noqa: E712
            )
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def find_existing(
        self,
        note_id: UUID,
        issue_id: UUID,
        link_type: NoteLinkType,
        workspace_id: UUID,
    ) -> NoteIssueLink | None:
        """Find existing link by note+issue+type (unique constraint).

        Args:
            note_id: Note UUID.
            issue_id: Issue UUID.
            link_type: Link type.
            workspace_id: Workspace UUID for RLS scoping.

        Returns:
            Existing NoteIssueLink or None.
        """
        query = select(NoteIssueLink).where(
            and_(
                NoteIssueLink.note_id == note_id,
                NoteIssueLink.issue_id == issue_id,
                NoteIssueLink.link_type == link_type,
                NoteIssueLink.workspace_id == workspace_id,
                NoteIssueLink.is_deleted == False,  # noqa: E712
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def soft_delete_by_note_and_issue(
        self,
        note_id: UUID,
        issue_id: UUID,
        workspace_id: UUID,
    ) -> int:
        """Soft-delete all links between a note and issue.

        Args:
            note_id: Note UUID.
            issue_id: Issue UUID.
            workspace_id: Workspace UUID for RLS scoping.

        Returns:
            Number of links soft-deleted.
        """
        links = await self.session.execute(
            select(NoteIssueLink).where(
                and_(
                    NoteIssueLink.note_id == note_id,
                    NoteIssueLink.issue_id == issue_id,
                    NoteIssueLink.workspace_id == workspace_id,
                    NoteIssueLink.is_deleted == False,  # noqa: E712
                )
            )
        )
        count = 0
        for link in links.scalars().all():
            link.is_deleted = True
            count += 1
        return count
