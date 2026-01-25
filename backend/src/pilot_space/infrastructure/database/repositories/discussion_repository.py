"""Discussion repository for ThreadedDiscussion and DiscussionComment data access.

Provides specialized methods for discussion-related queries.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from pilot_space.infrastructure.database.models.discussion_comment import (
    DiscussionComment,
)
from pilot_space.infrastructure.database.models.threaded_discussion import (
    DiscussionStatus,
    ThreadedDiscussion,
)
from pilot_space.infrastructure.database.repositories.base import BaseRepository

if TYPE_CHECKING:
    from collections.abc import Sequence
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession


class DiscussionRepository(BaseRepository[ThreadedDiscussion]):
    """Repository for ThreadedDiscussion entities.

    Extends BaseRepository with discussion-specific queries.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize DiscussionRepository.

        Args:
            session: The async database session.
        """
        super().__init__(session, ThreadedDiscussion)

    async def get_by_note(
        self,
        note_id: UUID,
        *,
        include_deleted: bool = False,
        include_comments: bool = True,
    ) -> Sequence[ThreadedDiscussion]:
        """Get all discussions for a note.

        Args:
            note_id: The note ID.
            include_deleted: Whether to include soft-deleted discussions.
            include_comments: Whether to eagerly load comments.

        Returns:
            List of discussions for the note.
        """
        query = select(ThreadedDiscussion).where(ThreadedDiscussion.note_id == note_id)
        if include_comments:
            query = query.options(selectinload(ThreadedDiscussion.comments))
        if not include_deleted:
            query = query.where(ThreadedDiscussion.is_deleted == False)  # noqa: E712
        query = query.order_by(ThreadedDiscussion.created_at.desc())
        result = await self.session.execute(query)
        return result.unique().scalars().all()

    async def get_open_discussions(
        self,
        note_id: UUID,
        *,
        include_comments: bool = True,
    ) -> Sequence[ThreadedDiscussion]:
        """Get all open discussions for a note.

        Args:
            note_id: The note ID.
            include_comments: Whether to eagerly load comments.

        Returns:
            List of open discussions.
        """
        query = select(ThreadedDiscussion).where(
            ThreadedDiscussion.note_id == note_id,
            ThreadedDiscussion.status == DiscussionStatus.OPEN,
            ThreadedDiscussion.is_deleted == False,  # noqa: E712
        )
        if include_comments:
            query = query.options(selectinload(ThreadedDiscussion.comments))
        query = query.order_by(ThreadedDiscussion.created_at.desc())
        result = await self.session.execute(query)
        return result.unique().scalars().all()

    async def get_by_block(
        self,
        note_id: UUID,
        block_id: str,
        *,
        include_deleted: bool = False,
        include_comments: bool = True,
    ) -> Sequence[ThreadedDiscussion]:
        """Get discussions for a specific block in a note.

        Args:
            note_id: The note ID.
            block_id: The TipTap block ID.
            include_deleted: Whether to include soft-deleted discussions.
            include_comments: Whether to eagerly load comments.

        Returns:
            List of discussions for the block.
        """
        query = select(ThreadedDiscussion).where(
            ThreadedDiscussion.note_id == note_id,
            ThreadedDiscussion.block_id == block_id,
        )
        if include_comments:
            query = query.options(selectinload(ThreadedDiscussion.comments))
        if not include_deleted:
            query = query.where(ThreadedDiscussion.is_deleted == False)  # noqa: E712
        query = query.order_by(ThreadedDiscussion.created_at.desc())
        result = await self.session.execute(query)
        return result.unique().scalars().all()

    async def get_with_comments(
        self,
        discussion_id: UUID,
        *,
        include_deleted: bool = False,
    ) -> ThreadedDiscussion | None:
        """Get a discussion with comments eagerly loaded.

        Args:
            discussion_id: The discussion ID.
            include_deleted: Whether to include soft-deleted discussion.

        Returns:
            Discussion with comments loaded, or None if not found.
        """
        query = (
            select(ThreadedDiscussion)
            .options(selectinload(ThreadedDiscussion.comments))
            .where(ThreadedDiscussion.id == discussion_id)
        )
        if not include_deleted:
            query = query.where(ThreadedDiscussion.is_deleted == False)  # noqa: E712
        result = await self.session.execute(query)
        return result.unique().scalar_one_or_none()

    async def count_open_discussions(
        self,
        note_id: UUID,
    ) -> int:
        """Count open discussions for a note.

        Args:
            note_id: The note ID.

        Returns:
            Count of open discussions.
        """
        query = (
            select(func.count())
            .select_from(ThreadedDiscussion)
            .where(
                ThreadedDiscussion.note_id == note_id,
                ThreadedDiscussion.status == DiscussionStatus.OPEN,
                ThreadedDiscussion.is_deleted == False,  # noqa: E712
            )
        )
        result = await self.session.execute(query)
        return result.scalar() or 0

    async def get_resolved_discussions(
        self,
        note_id: UUID,
        *,
        limit: int = 20,
    ) -> Sequence[ThreadedDiscussion]:
        """Get resolved discussions for a note.

        Args:
            note_id: The note ID.
            limit: Maximum number of discussions to return.

        Returns:
            List of resolved discussions.
        """
        query = (
            select(ThreadedDiscussion)
            .options(selectinload(ThreadedDiscussion.comments))
            .where(
                ThreadedDiscussion.note_id == note_id,
                ThreadedDiscussion.status == DiscussionStatus.RESOLVED,
                ThreadedDiscussion.is_deleted == False,  # noqa: E712
            )
            .order_by(ThreadedDiscussion.updated_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(query)
        return result.unique().scalars().all()


class DiscussionCommentRepository(BaseRepository[DiscussionComment]):
    """Repository for DiscussionComment entities.

    Extends BaseRepository with comment-specific queries.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize DiscussionCommentRepository.

        Args:
            session: The async database session.
        """
        super().__init__(session, DiscussionComment)

    async def get_by_discussion(
        self,
        discussion_id: UUID,
        *,
        include_deleted: bool = False,
    ) -> Sequence[DiscussionComment]:
        """Get all comments for a discussion.

        Args:
            discussion_id: The discussion ID.
            include_deleted: Whether to include soft-deleted comments.

        Returns:
            List of comments for the discussion, ordered by creation time.
        """
        query = select(DiscussionComment).where(DiscussionComment.discussion_id == discussion_id)
        if not include_deleted:
            query = query.where(DiscussionComment.is_deleted == False)  # noqa: E712
        query = query.order_by(DiscussionComment.created_at.asc())
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_ai_generated(
        self,
        discussion_id: UUID,
    ) -> Sequence[DiscussionComment]:
        """Get AI-generated comments for a discussion.

        Args:
            discussion_id: The discussion ID.

        Returns:
            List of AI-generated comments.
        """
        query = (
            select(DiscussionComment)
            .where(
                DiscussionComment.discussion_id == discussion_id,
                DiscussionComment.is_ai_generated == True,  # noqa: E712
                DiscussionComment.is_deleted == False,  # noqa: E712
            )
            .order_by(DiscussionComment.created_at.asc())
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def count_by_discussion(
        self,
        discussion_id: UUID,
    ) -> int:
        """Count comments in a discussion.

        Args:
            discussion_id: The discussion ID.

        Returns:
            Count of comments.
        """
        query = (
            select(func.count())
            .select_from(DiscussionComment)
            .where(
                DiscussionComment.discussion_id == discussion_id,
                DiscussionComment.is_deleted == False,  # noqa: E712
            )
        )
        result = await self.session.execute(query)
        return result.scalar() or 0

    async def get_by_author(
        self,
        author_id: UUID,
        workspace_id: UUID,
        *,
        include_deleted: bool = False,
        limit: int = 50,
    ) -> Sequence[DiscussionComment]:
        """Get comments by a specific author.

        Args:
            author_id: The author's user ID.
            workspace_id: The workspace ID.
            include_deleted: Whether to include soft-deleted comments.
            limit: Maximum number of comments to return.

        Returns:
            List of comments by the author.
        """
        query = select(DiscussionComment).where(
            DiscussionComment.author_id == author_id,
            DiscussionComment.workspace_id == workspace_id,
        )
        if not include_deleted:
            query = query.where(DiscussionComment.is_deleted == False)  # noqa: E712
        query = query.order_by(DiscussionComment.created_at.desc()).limit(limit)
        result = await self.session.execute(query)
        return result.scalars().all()
