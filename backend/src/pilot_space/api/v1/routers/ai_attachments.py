"""AI attachment upload, delete, and signed URL endpoints.

Handles multipart file uploads for chat context attachments,
hard-delete of attachment records, and signed URL generation for preview.

Routes:
    POST /ai/attachments/upload  — Upload a local file as a chat attachment (201)
    GET  /ai/attachments/{id}/url — Get a signed download URL for preview (200)
    DELETE /ai/attachments/{id}  — Delete an attachment owned by the caller (204)

Feature: 020 — Chat Context Attachments
Source: FR-001, FR-004, FR-008, US-1, US-2
REST contract: specs/020-chat-context-attachments/contracts/rest-api.md §1, §2
"""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, File, Form, HTTPException, Request, Response, UploadFile, status
from sqlalchemy import select

from pilot_space.api.v1.routers.workspace_quota import (
    _check_storage_quota,  # pyright: ignore[reportPrivateUsage]
    _update_storage_usage,  # pyright: ignore[reportPrivateUsage]
)
from pilot_space.api.v1.schemas.attachments import (
    AttachmentUploadResponse,
    DocumentIngestRequest,
    ExtractionChunk,
    ExtractionMetadata,
    ExtractionResultResponse,
)
from pilot_space.dependencies.ai import QueueClientDep
from pilot_space.dependencies.auth import CurrentUserId, DbSession
from pilot_space.dependencies.services import (
    AttachmentUploadServiceDep,
    ChatAttachmentRepositoryDep,
)
from pilot_space.dependencies.workspace import HeaderWorkspaceMemberId
from pilot_space.domain.exceptions import ForbiddenError, NotFoundError
from pilot_space.infrastructure.database.models.chat_attachment import ChatAttachment
from pilot_space.infrastructure.database.models.workspace_member import (
    WorkspaceMember,
    WorkspaceRole,
)
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
    db: DbSession,
    workspace_id: HeaderWorkspaceMemberId,
    file: Annotated[UploadFile, File(...)],
    session_id: Annotated[str | None, Form()] = None,
    response: Response = Response(),
) -> AttachmentUploadResponse:
    """Upload a local file as a chat context attachment.

    Validates MIME type against the supported whitelist and enforces
    per-type size limits before persisting to Supabase Storage.
    Guests are blocked at the router level (GUEST_NOT_ALLOWED).

    Workspace membership is enforced by HeaderWorkspaceMemberId
    (X-Workspace-Id header), which also sets RLS context.

    Args:
        workspace_id: Workspace UUID from X-Workspace-Id header (membership verified).
        file: Multipart file to upload.
        user_id: Authenticated user ID (injected by FastAPI).
        upload_service: AttachmentUploadService (injected by FastAPI).
        db: Database session (injected by FastAPI).
        session_id: Optional chat session to associate with the attachment.

    Returns:
        AttachmentUploadResponse with attachment metadata.

    Raises:
        HTTPException 400: UNSUPPORTED_FILE_TYPE, FILE_TOO_LARGE, or EMPTY_FILE.
        HTTPException 403: NOT_A_MEMBER or GUEST_NOT_ALLOWED.
    """
    # Guest check — membership already verified by HeaderWorkspaceMemberId
    result = await db.execute(
        select(WorkspaceMember.role).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user_id,
        )
    )
    role = result.scalar()
    if role == WorkspaceRole.GUEST:
        raise ForbiddenError("Guests cannot upload attachments", error_code="GUEST_NOT_ALLOWED")

    file_data = await file.read()
    filename = file.filename or "upload"
    content_type = file.content_type or "application/octet-stream"
    _file_bytes = len(file_data)

    _quota_ok, _warning_pct = await _check_storage_quota(db, workspace_id, _file_bytes)
    if not _quota_ok:
        raise HTTPException(
            status_code=status.HTTP_507_INSUFFICIENT_STORAGE,
            detail="Storage quota exceeded",
        )

    logger.info(
        "attachment_upload_request",
        workspace_id=str(workspace_id),
        filename=filename,
        content_type=content_type,
        size_bytes=_file_bytes,
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

    try:
        await _update_storage_usage(db, workspace_id, _file_bytes)
    except Exception:
        logger.warning("storage_usage_update_failed", workspace_id=str(workspace_id))
    if _warning_pct is not None:
        response.headers["X-Storage-Warning"] = str(round(_warning_pct, 4))

    return _build_upload_response(record)


@router.get("/attachments/{attachment_id}/url")
async def get_attachment_url(
    attachment_id: UUID,
    user_id: CurrentUserId,
    db: DbSession,
    request: Request,
    _workspace_id: HeaderWorkspaceMemberId,
) -> dict[str, str | int]:
    """Get a 1-hour signed download URL for a chat attachment.

    Only the owning user can generate signed URLs for their attachments.
    Workspace membership is enforced by HeaderWorkspaceMemberId.

    Args:
        attachment_id: UUID of the attachment.
        user_id: Authenticated user ID.
        db: Async DB session.
        request: FastAPI request (used to access the DI container).
        _workspace_id: Workspace UUID (membership verified by dependency).

    Returns:
        dict with url and expiresIn fields.
    """
    result = await db.execute(select(ChatAttachment).where(ChatAttachment.id == attachment_id))
    attachment = result.scalar_one_or_none()
    if attachment is None:
        raise NotFoundError("Attachment not found")
    if attachment.user_id != user_id:
        raise ForbiddenError("Not your attachment")

    storage = request.app.state.container.storage_client()
    signed_url = await storage.get_signed_url(
        bucket="chat-attachments",
        key=attachment.storage_key,
        expires_in=3600,
    )
    return {"url": signed_url, "expiresIn": 3600}


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
) -> ExtractionResultResponse:
    """Return extraction metadata and pre-chunked content for an attachment.

    Reads from OCR results and Office extraction cache. Returns 200 with
    extraction_source="none" when extraction has not yet run.
    """
    from pilot_space.application.services.note.markdown_chunker import (
        chunk_markdown_by_headings,
    )
    from pilot_space.infrastructure.database.models.ocr_result import OcrResultModel

    attachment = await attachment_repo.get_by_id(attachment_id)
    if attachment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Attachment not found or expired"},
        )

    extracted_text: str | None = None
    extraction_source = "none"
    confidence: float | None = None
    language: str | None = None
    provider_name: str | None = None
    tables: list[str] = []

    ocr_row = await db.execute(
        select(OcrResultModel)
        .where(OcrResultModel.attachment_id == attachment_id)
        .order_by(OcrResultModel.created_at.desc())
        .limit(1)
    )
    ocr_result = ocr_row.scalar()
    if ocr_result and ocr_result.extracted_text:
        extracted_text = ocr_result.extracted_text
        extraction_source = "ocr"
        confidence = ocr_result.confidence
        language = ocr_result.language
        provider_name = ocr_result.provider_used
        if ocr_result.tables_json:
            raw_tables = ocr_result.tables_json.get("tables")
            if isinstance(raw_tables, list):
                tables = [str(t) for t in raw_tables]
    elif attachment.extracted_text:
        extracted_text = attachment.extracted_text
        extraction_source = "office"

    extraction_chunks: list[ExtractionChunk] = []
    word_count: int | None = None
    if extracted_text:
        word_count = len(extracted_text.split())
        raw_chunks = chunk_markdown_by_headings(
            extracted_text, min_chunk_chars=50, max_chunk_chars=2000, overlap_chars=100
        )
        extraction_chunks = [
            ExtractionChunk(
                chunk_index=c.chunk_index,
                heading=c.heading or "",
                content=c.content,
                char_count=len(c.content),
                token_count=c.token_count,
                heading_hierarchy=list(c.heading_hierarchy) if c.heading_hierarchy else [],
            )
            for c in raw_chunks
        ]

    return ExtractionResultResponse(
        attachment_id=attachment_id,
        extracted_text=extracted_text,
        metadata=ExtractionMetadata(
            extraction_source=extraction_source,
            confidence=confidence,
            language=language,
            word_count=word_count,
            provider_name=provider_name,
        ),
        chunks=extraction_chunks,
        tables=tables,
    )


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
) -> dict[str, str]:
    """Enqueue the document for KG ingestion with optional chunk adjustments."""
    from pilot_space.ai.workers.memory_worker import TASK_DOCUMENT_INGESTION
    from pilot_space.infrastructure.queue.models import QueueName

    attachment = await attachment_repo.get_by_id(attachment_id)
    if attachment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Attachment not found or expired"},
        )

    excluded_indices = [adj.chunk_index for adj in body.chunk_adjustments if adj.excluded]
    payload = {
        "task_type": TASK_DOCUMENT_INGESTION,
        "workspace_id": str(body.workspace_id),
        "project_id": str(body.project_id),
        "attachment_id": str(attachment_id),
        "excluded_chunk_indices": excluded_indices,
    }

    try:
        if queue_client:
            await queue_client.enqueue(QueueName.AI_NORMAL, payload)
            logger.info(
                "document_ingest_enqueued",
                attachment_id=str(attachment_id),
                workspace_id=str(body.workspace_id),
                excluded_chunks=len(excluded_indices),
            )
        else:
            logger.warning("document_ingest_queue_unavailable", attachment_id=str(attachment_id))
    except Exception:
        logger.warning(
            "document_ingest_enqueue_failed",
            attachment_id=str(attachment_id),
            exc_info=True,
        )

    return {"status": "queued", "attachment_id": str(attachment_id)}
