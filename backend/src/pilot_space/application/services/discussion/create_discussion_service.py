"""CreateDiscussionService for creating threaded discussions.

Implements CQRS-lite command pattern for discussion creation.
Creates discussion and first comment atomically.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pilot_space.domain.exceptions import NotFoundError, ValidationError
from pilot_space.infrastructure.database.models.threaded_discussion import (
    DiscussionStatus,
)

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from pilot_space.infrastructure.database.models.discussion_comment import (
        DiscussionComment,
    )
    from pilot_space.infrastructure.database.models.threaded_discussion import (
        ThreadedDiscussion,
    )
    from pilot_space.infrastructure.database.repositories.discussion_repository import (
        DiscussionCommentRepository,
        DiscussionRepository,
    )
    from pilot_space.infrastructure.database.repositories.note_repository import (
        NoteRepository,
    )


@dataclass(frozen=True, slots=True)
class CreateDiscussionPayload:
    """Payload for creating a discussion with first comment.

    Attributes:
        workspace_id: The workspace ID.
        note_id: The note ID to discuss.
        author_id: The user ID starting the discussion.
        initial_comment: The first comment content.
        title: Optional discussion title.
        block_id: Optional TipTap block ID this discussion refers to.
        is_ai_generated: Whether the initial comment is AI-generated.
    """

    workspace_id: UUID
    note_id: UUID
    author_id: UUID
    initial_comment: str
    title: str | None = None
    block_id: str | None = None
    is_ai_generated: bool = False


@dataclass(frozen=True, slots=True)
class CreateDiscussionResult:
    """Result from discussion creation.

    Attributes:
        discussion: The created discussion.
        first_comment: The initial comment.
    """

    discussion: ThreadedDiscussion
    first_comment: DiscussionComment


class CreateDiscussionService:
    """Service for creating discussions.

    Handles atomic creation of discussion thread with initial comment.
    Supports both human and AI-generated discussions.
    """

    def __init__(
        self,
        session: AsyncSession,
        note_repository: NoteRepository,
        discussion_repository: DiscussionRepository,
        comment_repository: DiscussionCommentRepository,
    ) -> None:
        """Initialize CreateDiscussionService.

        Args:
            session: The async database session.
            note_repository: Repository for note queries.
            discussion_repository: Repository for discussion persistence.
            comment_repository: Repository for comment persistence.
        """
        self._session = session
        self._note_repo = note_repository
        self._discussion_repo = discussion_repository
        self._comment_repo = comment_repository

    async def execute(self, payload: CreateDiscussionPayload) -> CreateDiscussionResult:
        """Execute discussion creation.

        Creates discussion and first comment atomically.

        Args:
            payload: The creation payload.

        Returns:
            CreateDiscussionResult with discussion and first comment.

        Raises:
            ValidationError: If validation fails.
            NotFoundError: If note/discussion not found.
        """
        from pilot_space.infrastructure.database.models.discussion_comment import (
            DiscussionComment,
        )
        from pilot_space.infrastructure.database.models.threaded_discussion import (
            ThreadedDiscussion,
        )

        # Validate initial comment
        if not payload.initial_comment or not payload.initial_comment.strip():
            msg = "Initial comment is required"
            raise ValidationError(msg)

        # Verify note exists
        note = await self._note_repo.get_by_id(payload.note_id)
        if not note:
            msg = f"Note with ID {payload.note_id} not found"
            raise NotFoundError(msg)

        # Verify note belongs to workspace
        if note.workspace_id != payload.workspace_id:
            msg = "Note does not belong to the specified workspace"
            raise ValidationError(msg)

        # Create discussion
        discussion = ThreadedDiscussion(
            workspace_id=payload.workspace_id,
            note_id=payload.note_id,
            block_id=payload.block_id,
            title=payload.title.strip() if payload.title else None,
            status=DiscussionStatus.OPEN,
        )

        created_discussion = await self._discussion_repo.create(discussion)

        # Create first comment
        comment = DiscussionComment(
            workspace_id=payload.workspace_id,
            discussion_id=created_discussion.id,
            author_id=payload.author_id,
            content=payload.initial_comment.strip(),
            is_ai_generated=payload.is_ai_generated,
        )

        created_comment = await self._comment_repo.create(comment)

        return CreateDiscussionResult(
            discussion=created_discussion,
            first_comment=created_comment,
        )

    async def add_comment(
        self,
        *,
        workspace_id: UUID,
        discussion_id: UUID,
        author_id: UUID,
        content: str,
        is_ai_generated: bool = False,
    ) -> DiscussionComment:
        """Add a comment to an existing discussion.

        Args:
            workspace_id: The workspace ID.
            discussion_id: The discussion ID.
            author_id: The comment author's user ID.
            content: The comment content.
            is_ai_generated: Whether this is an AI-generated comment.

        Returns:
            The created comment.

        Raises:
            ValidationError: If validation fails.
            NotFoundError: If discussion not found.
        """
        from pilot_space.infrastructure.database.models.discussion_comment import (
            DiscussionComment,
        )

        # Validate content
        if not content or not content.strip():
            msg = "Comment content is required"
            raise ValidationError(msg)

        # Verify discussion exists and is open
        discussion = await self._discussion_repo.get_by_id(discussion_id)
        if not discussion:
            msg = f"Discussion with ID {discussion_id} not found"
            raise NotFoundError(msg)

        if discussion.workspace_id != workspace_id:
            msg = "Discussion does not belong to the specified workspace"
            raise ValidationError(msg)

        if discussion.status != DiscussionStatus.OPEN:
            msg = "Cannot add comment to resolved discussion"
            raise ValidationError(msg)

        # Create comment
        comment = DiscussionComment(
            workspace_id=workspace_id,
            discussion_id=discussion_id,
            author_id=author_id,
            content=content.strip(),
            is_ai_generated=is_ai_generated,
        )

        return await self._comment_repo.create(comment)

    async def resolve_discussion(
        self,
        *,
        discussion_id: UUID,
        resolved_by_id: UUID,
    ) -> ThreadedDiscussion:
        """Resolve a discussion.

        Args:
            discussion_id: The discussion ID.
            resolved_by_id: The user ID resolving the discussion.

        Returns:
            The resolved discussion.

        Raises:
            NotFoundError: If discussion not found.
            ValidationError: If discussion already resolved.
        """
        discussion = await self._discussion_repo.get_by_id(discussion_id)
        if not discussion:
            msg = f"Discussion with ID {discussion_id} not found"
            raise NotFoundError(msg)

        if discussion.status == DiscussionStatus.RESOLVED:
            msg = "Discussion is already resolved"
            raise ValidationError(msg)

        discussion.status = DiscussionStatus.RESOLVED
        discussion.resolved_by_id = resolved_by_id

        return await self._discussion_repo.update(discussion)
