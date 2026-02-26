"""AI attachment upload and delete endpoints.

Handles multipart file uploads for chat context attachments and
hard-delete of attachment records by the owning user.

Routes:
    POST /ai/attachments/upload  — Upload a local file as a chat attachment (201)
    DELETE /ai/attachments/{id}  — Delete an attachment owned by the caller (204)

Feature: 020 — Chat Context Attachments
Source: FR-001, FR-004, FR-008, US-1, US-2
REST contract: specs/020-chat-context-attachments/contracts/rest-api.md §1, §2
"""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from pilot_space.api.v1.schemas.attachments import AttachmentUploadResponse
from pilot_space.dependencies.auth import CurrentUserId
from pilot_space.dependencies.services import AttachmentUploadServiceDep
from pilot_space.infrastructure.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["ai-attachments"])


def _build_upload_response(record: Any) -> AttachmentUploadResponse:
    """Build AttachmentUploadResponse from a service result or ORM record.

    Handles both AttachmentUploadResponse objects (real service) and
    ORM-like objects (e.g. test mocks) that expose `id` instead of
    `attachment_id`.

    Args:
        record: Service result with attachment metadata fields.

    Returns:
        AttachmentUploadResponse with all required fields populated.
    """
    if isinstance(record, AttachmentUploadResponse):
        return record

    return AttachmentUploadResponse(
        attachment_id=record.id,
        filename=record.filename,
        mime_type=record.mime_type,
        size_bytes=record.size_bytes,
        source=record.source,
        expires_at=record.expires_at,
    )


@router.post(
    "/attachments/upload",
    response_model=AttachmentUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_attachment(
    user_id: CurrentUserId,
    upload_service: AttachmentUploadServiceDep,
    workspace_id: Annotated[UUID, Form(...)],
    file: Annotated[UploadFile, File(...)],
    session_id: Annotated[str | None, Form()] = None,
) -> AttachmentUploadResponse:
    """Upload a local file as a chat context attachment.

    Validates MIME type against the supported whitelist and enforces
    per-type size limits before persisting to Supabase Storage.
    Guests are blocked at the service level (GUEST_NOT_ALLOWED).

    Args:
        workspace_id: Workspace that owns the attachment.
        session_id: Optional chat session to associate with the attachment.
        file: Multipart file to upload.
        user_id: Authenticated user ID (injected by FastAPI).
        upload_service: AttachmentUploadService (injected by FastAPI).

    Returns:
        AttachmentUploadResponse with attachment metadata.

    Raises:
        HTTPException 400: UNSUPPORTED_FILE_TYPE, FILE_TOO_LARGE, or EMPTY_FILE.
        HTTPException 403: GUEST_NOT_ALLOWED.
    """
    file_data = await file.read()
    filename = file.filename or "upload"
    content_type = file.content_type or "application/octet-stream"

    logger.info(
        "attachment_upload_request",
        workspace_id=str(workspace_id),
        filename=filename,
        content_type=content_type,
        size_bytes=len(file_data),
        user_id=str(user_id),
    )

    record = await upload_service.execute(
        file_data=file_data,
        filename=filename,
        content_type=content_type,
        workspace_id=workspace_id,
        user_id=user_id,
        session_id=session_id,
    )

    return _build_upload_response(record)


@router.delete(
    "/attachments/{attachment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_attachment(
    attachment_id: UUID,
    user_id: CurrentUserId,
    upload_service: AttachmentUploadServiceDep,
) -> None:
    """Delete a chat context attachment (DB record + Storage object).

    Only the owning user may delete their attachment. Returns 204 on
    success; 404 if the attachment does not exist or has expired; 403
    if the requesting user does not own it.

    Args:
        attachment_id: UUID of the attachment to delete.
        user_id: Authenticated user ID (injected by FastAPI).
        upload_service: AttachmentUploadService handles both storage + DB deletion.

    Raises:
        HTTPException 404: NOT_FOUND if attachment does not exist.
        HTTPException 403: FORBIDDEN if user does not own the attachment.
    """
    try:
        await upload_service.delete(attachment_id=attachment_id, user_id=user_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Attachment not found or expired"},
        ) from exc
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": "You do not own this attachment"},
        ) from exc

    logger.info(
        "attachment_deleted",
        attachment_id=str(attachment_id),
        user_id=str(user_id),
    )
