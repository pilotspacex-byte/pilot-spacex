"""AI attachment upload, delete, and signed URL endpoints.

Thin HTTP shell -- all business logic delegated to AttachmentManagementService
and AttachmentUploadService. Router handles only file upload parsing, MIME
validation, and HTTP response/header construction.

Routes:
    POST /ai/attachments/upload  -- Upload a local file as a chat attachment (201)
    GET  /ai/attachments/{id}/url -- Get a signed download URL for preview (200)
    DELETE /ai/attachments/{id}  -- Delete an attachment owned by the caller (204)

Feature: 020 -- Chat Context Attachments
Source: FR-001, FR-004, FR-008, US-1, US-2
REST contract: specs/020-chat-context-attachments/contracts/rest-api.md
"""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, File, Form, Response, UploadFile, status

from pilot_space.api.v1.dependencies import AttachmentManagementServiceDep
from pilot_space.api.v1.schemas.attachments import (
    AttachmentUploadResponse,
    DocumentIngestRequest,
    ExtractionResultResponse,
)
from pilot_space.dependencies.ai import QueueClientDep
from pilot_space.dependencies.auth import CurrentUserId, DbSession
from pilot_space.dependencies.services import (
    AttachmentUploadServiceDep,
    ChatAttachmentRepositoryDep,
)
from pilot_space.dependencies.workspace import HeaderWorkspaceMemberId
from pilot_space.infrastructure.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["ai-attachments"])


def _build_upload_response(record: Any) -> AttachmentUploadResponse:
    """Build AttachmentUploadResponse from a service result or ORM record."""
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
    db: DbSession,
    workspace_id: HeaderWorkspaceMemberId,
    svc: AttachmentManagementServiceDep,
    file: Annotated[UploadFile, File(...)],
    session_id: Annotated[str | None, Form()] = None,
    response: Response = Response(),
) -> AttachmentUploadResponse:
    """Upload a local file as a chat context attachment.

    Validates MIME type, enforces size limits, checks quota. Guests blocked.
    """

    # Guest check
    await svc.check_guest_restriction(workspace_id, user_id)

    # Read file data (HTTP concern: file parsing)
    file_data = await file.read()
    filename = file.filename or "upload"
    content_type = file.content_type or "application/octet-stream"
    file_bytes = len(file_data)

    # Quota check
    warning_pct = await svc.check_storage_quota(workspace_id, file_bytes)

    logger.info(
        "attachment_upload_request",
        workspace_id=str(workspace_id),
        filename=filename,
        content_type=content_type,
        size_bytes=file_bytes,
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

    # Update usage counters (non-fatal)
    await svc.update_storage_usage(workspace_id, file_bytes)

    if warning_pct is not None:
        response.headers["X-Storage-Warning"] = str(round(warning_pct, 4))

    return _build_upload_response(record)


@router.get("/attachments/{attachment_id}/url")
async def get_attachment_url(
    attachment_id: UUID,
    user_id: CurrentUserId,
    db: DbSession,
    _workspace_id: HeaderWorkspaceMemberId,
    svc: AttachmentManagementServiceDep,
) -> dict[str, str | int]:
    """Get a 1-hour signed download URL for a chat attachment."""
    result = await svc.get_signed_url(attachment_id, user_id)
    return {"url": result.url, "expiresIn": result.expires_in}


@router.delete(
    "/attachments/{attachment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_attachment(
    attachment_id: UUID,
    user_id: CurrentUserId,
    upload_service: AttachmentUploadServiceDep,
) -> None:
    """Delete a chat context attachment (DB record + Storage object)."""
    await upload_service.delete(attachment_id=attachment_id, user_id=user_id)

    logger.info(
        "attachment_deleted",
        attachment_id=str(attachment_id),
        user_id=str(user_id),
    )


@router.get(
    "/attachments/{attachment_id}/extraction",
    response_model=ExtractionResultResponse,
    status_code=status.HTTP_200_OK,
)
async def get_extraction_result(
    attachment_id: UUID,
    user_id: CurrentUserId,
    db: DbSession,
    attachment_repo: ChatAttachmentRepositoryDep,
    svc: AttachmentManagementServiceDep,
) -> ExtractionResultResponse:
    """Return extraction metadata and pre-chunked content for an attachment."""
    return await svc.get_extraction_result(attachment_id, attachment_repo)


@router.post(
    "/attachments/{attachment_id}/ingest",
    status_code=status.HTTP_202_ACCEPTED,
)
async def ingest_document(
    attachment_id: UUID,
    user_id: CurrentUserId,
    body: DocumentIngestRequest,
    db: DbSession,
    attachment_repo: ChatAttachmentRepositoryDep,
    queue_client: QueueClientDep,
    svc: AttachmentManagementServiceDep,
) -> dict[str, str]:
    """Enqueue the document for KG ingestion with optional chunk adjustments."""
    excluded_indices = [adj.chunk_index for adj in body.chunk_adjustments if adj.excluded]

    result = await svc.ingest_document(
        attachment_id=attachment_id,
        workspace_id=body.workspace_id,
        project_id=body.project_id,
        excluded_chunk_indices=excluded_indices,
        attachment_repo=attachment_repo,
        queue_client=queue_client,
    )
    return {"status": result.status, "attachment_id": str(result.attachment_id)}
