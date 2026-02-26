"""ChatAttachment repository for managing file attachment metadata.

Feature: 020 — Chat Context Attachments
Source: FR-001, FR-004, FR-008, US-1, US-2
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import and_, delete, select
from sqlalchemy.sql import func

from pilot_space.infrastructure.database.models.chat_attachment import ChatAttachment

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sqlalchemy.ext.asyncio import AsyncSession


class ChatAttachmentRepository:
    """Repository for ChatAttachment entities.

    ChatAttachment uses hard delete (TTL-based cleanup) rather than soft
    delete, so it does not extend BaseRepository which assumes SoftDeleteMixin.

    Provides:
    - Ownership-validated batch fetch for chat handler
    - Session-scoped listing
    - TTL-aware hard deletion for pg_cron cleanup
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository.

        Args:
            session: Async database session.
        """
        self.session = session

    async def create(self, attachment: ChatAttachment) -> ChatAttachment:
        """Persist a new attachment record and return it with generated fields.

        Args:
            attachment: The ChatAttachment instance to persist.

        Returns:
            The persisted attachment with id and server defaults populated.
        """
        self.session.add(attachment)
        await self.session.flush()
        await self.session.refresh(attachment)
        return attachment

    async def get_by_id(self, attachment_id: UUID) -> ChatAttachment | None:
        """Fetch a single attachment by primary key.

        Args:
            attachment_id: UUID of the attachment row.

        Returns:
            ChatAttachment if found, None otherwise.
        """
        result = await self.session.execute(
            select(ChatAttachment).where(ChatAttachment.id == attachment_id)
        )
        return result.scalar_one_or_none()

    async def get_by_ids_for_user(
        self,
        attachment_ids: list[UUID],
        user_id: UUID,
    ) -> list[ChatAttachment]:
        """Batch-fetch attachments by IDs, filtered to the given user.

        Validates ownership at the query level: only rows matching both
        ``id IN (...)`` and ``user_id = ?`` are returned. Missing or
        foreign-owned IDs are silently excluded; callers must compare
        counts to detect access violations.

        Args:
            attachment_ids: List of attachment UUIDs to retrieve.
            user_id: The requesting user's UUID; enforces ownership.

        Returns:
            List of ChatAttachment rows owned by the user.
        """
        if not attachment_ids:
            return []

        result = await self.session.execute(
            select(ChatAttachment).where(
                and_(
                    ChatAttachment.id.in_(attachment_ids),
                    ChatAttachment.user_id == user_id,
                )
            )
        )
        return list(result.scalars().all())

    async def list_by_session(self, session_id: str) -> Sequence[ChatAttachment]:
        """List all attachments associated with a chat session.

        Args:
            session_id: The chat session identifier.

        Returns:
            Sequence of attachments ordered by creation time ascending.
        """
        result = await self.session.execute(
            select(ChatAttachment)
            .where(ChatAttachment.session_id == session_id)
            .order_by(ChatAttachment.created_at.asc())
        )
        return result.scalars().all()

    async def delete(self, attachment_id: UUID) -> bool:
        """Hard-delete an attachment row by primary key.

        Args:
            attachment_id: UUID of the attachment to delete.

        Returns:
            True if a row was deleted, False if no matching row existed.
        """
        result = await self.session.execute(
            delete(ChatAttachment)
            .where(ChatAttachment.id == attachment_id)
            .returning(ChatAttachment.id)
        )
        return result.scalar_one_or_none() is not None

    async def delete_expired(self) -> int:
        """Hard-delete all attachment rows whose TTL has elapsed.

        Intended for use by pg_cron or a background cleanup task.

        Returns:
            Number of rows deleted.
        """
        result = await self.session.execute(
            delete(ChatAttachment)
            .where(ChatAttachment.expires_at < func.now())
            .returning(ChatAttachment.id)
        )
        return len(result.scalars().all())


__all__ = ["ChatAttachmentRepository"]
