"""Speech-to-text transcription router using ElevenLabs STT.

Thin HTTP layer — delegates business logic to TranscriptionService.
Service exceptions (TranscriptionError hierarchy) are caught by the global
RFC 7807 exception handler registered in error_handler.py.

Routes:
    POST /ai/transcribe  — Transcribe audio to text via ElevenLabs STT

Feature: Voice-to-text input for AI Chat (VOICE-01, VOICE-02, VOICE-03)
BYOK: Workspace admins configure ElevenLabs API key in AI settings.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, File, Form, UploadFile, status

from pilot_space.api.utils.file_validation import read_and_validate
from pilot_space.api.v1.dependencies import TranscriptionServiceDep
from pilot_space.api.v1.schemas.transcription import TranscribeResponse
from pilot_space.application.services.transcription import (
    ALLOWED_MIME_TYPES,
    MAX_FILE_BYTES,
    TranscribePayload,
)
from pilot_space.dependencies.auth import CurrentUserId, DbSession
from pilot_space.dependencies.workspace import HeaderWorkspaceMemberId

router = APIRouter(tags=["ai", "transcription"])


@router.post(
    "/transcribe",
    response_model=TranscribeResponse,
    status_code=status.HTTP_200_OK,
)
async def transcribe_audio(
    user_id: CurrentUserId,
    session: DbSession,
    workspace_id: HeaderWorkspaceMemberId,
    file: Annotated[UploadFile, File(description="Audio file to transcribe")],
    service: TranscriptionServiceDep,
    language: Annotated[str | None, Form()] = None,
) -> TranscribeResponse:
    """Transcribe audio to text using ElevenLabs STT.

    Accepts a multipart audio upload, validates the file, and delegates to
    TranscriptionService for caching, provider call, and storage upload.

    Workspace membership and RLS context are enforced by the
    HeaderWorkspaceMemberId dependency.

    Service-layer errors (ProviderNotConfiguredError, ProviderAuthError,
    ProviderError) propagate to the global transcription_error_handler
    which returns RFC 7807 application/problem+json responses.
    """
    # Validate MIME type, emptiness, and size in one call
    audio_bytes, content_type = await read_and_validate(
        file,
        allowed_mime_types=ALLOWED_MIME_TYPES,
        max_bytes=MAX_FILE_BYTES,
        file_label="Audio file",
    )

    # Service exceptions propagate to global handler
    return await service.transcribe(
        TranscribePayload(
            workspace_id=workspace_id,
            user_id=user_id,
            audio_bytes=audio_bytes,
            content_type=content_type,
            filename=file.filename or "recording.webm",
            language=language,
        )
    )


__all__ = ["router"]
