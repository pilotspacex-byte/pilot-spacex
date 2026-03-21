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

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

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
    # Validate MIME type
    content_type = (file.content_type or "application/octet-stream").split(";")[0].strip()
    if content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Unsupported audio type '{content_type}'. "
                f"Allowed: {', '.join(sorted(ALLOWED_MIME_TYPES))}"
            ),
        )

    # Read and validate file bytes
    audio_bytes = await file.read()

    if not audio_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Audio file is empty",
        )

    if len(audio_bytes) > MAX_FILE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Audio file exceeds maximum size of {MAX_FILE_BYTES // (1024 * 1024)} MB",
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
