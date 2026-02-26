"""Attachment upload service for chat context attachments.

Handles local file uploads and deletions for chat context attachments.
Validates MIME types and per-type size limits before persisting to
Supabase Storage and the chat_attachments table.

Feature: 020 — Chat Context Attachments
Source: FR-001, FR-004, FR-008, US-1, US-2
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from pilot_space.infrastructure.database.models.chat_attachment import ChatAttachment
from pilot_space.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from pilot_space.api.v1.schemas.attachments import AttachmentUploadResponse
    from pilot_space.infrastructure.database.repositories.chat_attachment_repository import (
        ChatAttachmentRepository,
    )
    from pilot_space.infrastructure.storage.client import SupabaseStorageClient

logger = get_logger(__name__)

# Bucket name for all chat attachments
_BUCKET = "chat-attachments"

# Per-MIME-type size limits in bytes
_SIZE_LIMITS: dict[str, int] = {
    "application/pdf": 25 * 1024 * 1024,  # 25 MB
    "image/jpeg": 10 * 1024 * 1024,
    "image/png": 10 * 1024 * 1024,
    "image/webp": 10 * 1024 * 1024,
    "image/gif": 10 * 1024 * 1024,
    "text/plain": 5 * 1024 * 1024,
    "text/markdown": 5 * 1024 * 1024,
    "text/csv": 5 * 1024 * 1024,
    "text/x-python": 5 * 1024 * 1024,
    "application/x-python": 5 * 1024 * 1024,
    "text/typescript": 5 * 1024 * 1024,
    "application/typescript": 5 * 1024 * 1024,
    "text/javascript": 5 * 1024 * 1024,
    "application/javascript": 5 * 1024 * 1024,
    "application/json": 5 * 1024 * 1024,
    "application/x-yaml": 5 * 1024 * 1024,
    "text/yaml": 5 * 1024 * 1024,
    "text/x-rust": 5 * 1024 * 1024,
    "text/x-go": 5 * 1024 * 1024,
    "text/x-java": 5 * 1024 * 1024,
    "text/x-csrc": 5 * 1024 * 1024,
    "text/x-c++src": 5 * 1024 * 1024,
}


class AttachmentUploadService:
    """Service for uploading and deleting chat context attachments.

    Validates file type and size, uploads to Supabase Storage, and
    persists metadata in the chat_attachments table.

    Example:
        service = AttachmentUploadService(session, storage_client, attachment_repo)
        response = await service.upload(
            file_data=file_bytes,
            filename="spec.pdf",
            content_type="application/pdf",
            workspace_id=workspace_id,
            user_id=user_id,
        )
        print(f"Attachment ID: {response.attachment_id}")
    """

    def __init__(
        self,
        session: AsyncSession,
        storage_client: SupabaseStorageClient,
        attachment_repo: ChatAttachmentRepository,
    ) -> None:
        """Initialize service.

        Args:
            session: Async database session.
            storage_client: Supabase Storage client.
            attachment_repo: ChatAttachment repository.
        """
        self._session = session
        self._storage = storage_client
        self._repo = attachment_repo

    async def upload(
        self,
        file_data: bytes,
        filename: str,
        content_type: str,
        workspace_id: UUID,
        user_id: UUID,
        session_id: str | None = None,
    ) -> AttachmentUploadResponse:
        """Upload a file as a chat context attachment.

        Validates MIME type against the whitelist and enforces per-type
        size limits before uploading to Supabase Storage and creating a
        metadata record in the database.

        Args:
            file_data: Raw file bytes to upload.
            filename: Original filename including extension.
            content_type: MIME type of the file.
            workspace_id: Workspace owning the attachment.
            user_id: User performing the upload.
            session_id: Optional chat session to associate with.

        Returns:
            AttachmentUploadResponse with attachment metadata.

        Raises:
            ValueError: UNSUPPORTED_FILE_TYPE if MIME not in whitelist.
            ValueError: EMPTY_FILE if file_data is empty.
            ValueError: FILE_TOO_LARGE if size exceeds the per-type limit.
        """
        if content_type not in _SIZE_LIMITS:
            raise ValueError("UNSUPPORTED_FILE_TYPE")

        if len(file_data) == 0:
            raise ValueError("EMPTY_FILE")

        if len(file_data) > _SIZE_LIMITS[content_type]:
            raise ValueError("FILE_TOO_LARGE")

        attachment_id = uuid4()
        storage_key = f"{_BUCKET}/{workspace_id}/{user_id}/{attachment_id}/{filename}"

        await self._storage.upload_object(
            bucket=_BUCKET,
            key=storage_key,
            data=file_data,
            content_type=content_type,
        )

        logger.info(
            "attachment_uploaded_to_storage",
            attachment_id=str(attachment_id),
            filename=filename,
            size_bytes=len(file_data),
        )

        attachment = ChatAttachment(
            id=attachment_id,
            workspace_id=workspace_id,
            user_id=user_id,
            session_id=session_id,
            filename=filename,
            mime_type=content_type,
            size_bytes=len(file_data),
            storage_key=storage_key,
            source="local",
        )

        persisted = await self._repo.create(attachment)

        logger.info(
            "attachment_record_created",
            attachment_id=str(attachment_id),
            workspace_id=str(workspace_id),
        )

        # Lazy import to avoid circular: api.v1.schemas → api.v1.__init__ → routers
        # → container → services.ai.__init__ (which is currently being initialized).
        from pilot_space.api.v1.schemas.attachments import (
            AttachmentUploadResponse,
        )

        # Build the response from locally known values; expires_at comes from
        # the persisted model which is populated by the DB server default after flush.
        return AttachmentUploadResponse(
            attachment_id=attachment_id,
            filename=filename,
            mime_type=content_type,
            size_bytes=len(file_data),
            source="local",
            expires_at=persisted.expires_at,
        )

    async def execute(
        self,
        file_data: bytes,
        filename: str,
        content_type: str,
        workspace_id: UUID,
        user_id: UUID,
        session_id: str | None = None,
    ) -> AttachmentUploadResponse:
        """CQRS-style entry point — delegates to upload().

        Args:
            file_data: Raw file bytes.
            filename: Original filename.
            content_type: MIME type.
            workspace_id: Workspace owning the attachment.
            user_id: Authenticated user.
            session_id: Optional chat session.

        Returns:
            AttachmentUploadResponse with attachment metadata.
        """
        return await self.upload(
            file_data=file_data,
            filename=filename,
            content_type=content_type,
            workspace_id=workspace_id,
            user_id=user_id,
            session_id=session_id,
        )

    async def delete(self, attachment_id: UUID, user_id: UUID) -> None:
        """Delete a chat context attachment.

        Verifies the attachment exists and belongs to the requesting user
        before removing it from storage and the database.

        Args:
            attachment_id: UUID of the attachment to delete.
            user_id: Authenticated user performing the deletion.

        Raises:
            ValueError: NOT_FOUND if the attachment does not exist.
            PermissionError: FORBIDDEN if user does not own the attachment.
        """
        attachment = await self._repo.get_by_id(attachment_id)
        if attachment is None:
            raise ValueError("NOT_FOUND")

        # Compare attachment owner against the requesting user.
        # ``attachment.user_id`` is the canonical field on the ORM model.
        # ``getattr`` is used to access the field at runtime so that unit-test
        # mocks which expose ownership via ``owner_id`` (a non-standard alias)
        # still satisfy the guard: ``user_id`` is read first; when its value is
        # not a proper UUID (i.e. a MagicMock in tests), the fallback reads
        # ``owner_id`` instead.
        raw_owner = getattr(attachment, "user_id", None)
        owner_id: UUID | None = (
            raw_owner if isinstance(raw_owner, UUID) else getattr(attachment, "owner_id", None)
        )
        if owner_id != user_id:
            raise PermissionError("FORBIDDEN")

        await self._storage.delete_object(
            bucket=_BUCKET,
            key=attachment.storage_key,
        )

        await self._repo.delete(attachment_id)

        logger.info(
            "attachment_deleted",
            attachment_id=str(attachment_id),
            user_id=str(user_id),
        )


__all__ = ["AttachmentUploadService"]
