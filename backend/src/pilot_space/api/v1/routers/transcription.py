"""Speech-to-text transcription router using ElevenLabs STT.

Proxies audio uploads to ElevenLabs Speech-to-Text API and caches
results by SHA-256 audio hash to avoid reprocessing identical audio.

Routes:
    POST /ai/transcribe  — Transcribe audio to text via ElevenLabs STT

Feature: Voice-to-text input for AI Chat (VOICE-01, VOICE-02, VOICE-03)
BYOK: Workspace admins configure ElevenLabs API key in AI settings.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from typing import Annotated
from uuid import UUID

import httpx
from fastapi import APIRouter, File, Form, Header, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from pilot_space.api.v1.schemas.transcription import TranscribeResponse
from pilot_space.dependencies.auth import CurrentUserId, DbSession
from pilot_space.infrastructure.database.models.transcript_cache import (
    TRANSCRIPT_CACHE_TTL_DAYS,
    TranscriptCache,
)
from pilot_space.infrastructure.logging import get_logger
from pilot_space.infrastructure.storage.client import SupabaseStorageClient

logger = get_logger(__name__)

router = APIRouter(tags=["ai", "transcription"])

# Allowed audio MIME types
_ALLOWED_MIME_TYPES = frozenset(
    {
        "audio/webm",
        "audio/ogg",
        "audio/wav",
        "audio/mp4",
        "audio/mpeg",
        "audio/x-m4a",
        "audio/aac",
    }
)

# Maximum file size: 25 MB
_MAX_FILE_BYTES = 25 * 1024 * 1024

# ElevenLabs STT endpoint
_ELEVENLABS_STT_URL = "https://api.elevenlabs.io/v1/speech-to-text"

# Supabase Storage bucket for voice recordings.
# NOTE: This bucket must be created via Supabase dashboard or a storage migration
# before audio uploads will succeed. Storage failures are non-blocking.
_VOICE_RECORDINGS_BUCKET = "voice-recordings"


@router.post(
    "/transcribe",
    response_model=TranscribeResponse,
    status_code=status.HTTP_200_OK,
)
async def transcribe_audio(
    user_id: CurrentUserId,
    session: DbSession,
    file: Annotated[UploadFile, File(description="Audio file to transcribe")],
    x_workspace_id: Annotated[UUID, Header(description="Workspace UUID")],
    language: Annotated[str | None, Form()] = None,
) -> TranscribeResponse:
    """Transcribe audio to text using ElevenLabs STT.

    Accepts a multipart audio upload, checks the transcript cache for a
    previous result with the same audio content, and if not found, proxies
    the audio to ElevenLabs Speech-to-Text API and caches the result.

    Args:
        user_id: Authenticated user ID (injected by FastAPI).
        session: Database session (injected by FastAPI).
        file: Audio file to transcribe (audio/webm, audio/ogg, etc.).
        x_workspace_id: Workspace UUID from X-Workspace-Id header.
        language: Optional ISO 639-1 language code hint (e.g. 'en').

    Returns:
        TranscribeResponse with transcript text and optional metadata.

    Raises:
        HTTPException 400: Invalid file type or file too large.
        HTTPException 422: ElevenLabs API key not configured.
        HTTPException 502: ElevenLabs API error.
    """
    workspace_id = x_workspace_id

    # Validate MIME type
    content_type = (file.content_type or "application/octet-stream").split(";")[0].strip()
    if content_type not in _ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "UNSUPPORTED_AUDIO_TYPE",
                "message": (
                    f"Unsupported audio type '{content_type}'. "
                    f"Allowed: {', '.join(sorted(_ALLOWED_MIME_TYPES))}"
                ),
            },
        )

    # Read file bytes
    audio_bytes = await file.read()

    if not audio_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "EMPTY_FILE", "message": "Audio file is empty"},
        )

    if len(audio_bytes) > _MAX_FILE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "FILE_TOO_LARGE",
                "message": f"Audio file exceeds maximum size of {_MAX_FILE_BYTES // (1024 * 1024)} MB",
            },
        )

    # Compute SHA-256 hash for cache lookup
    audio_hash = hashlib.sha256(audio_bytes).hexdigest()

    # Check transcript cache (skip expired entries)
    now = datetime.now(UTC)
    cache_stmt = select(TranscriptCache).where(
        TranscriptCache.workspace_id == workspace_id,
        TranscriptCache.audio_hash == audio_hash,
        (TranscriptCache.expires_at.is_(None)) | (TranscriptCache.expires_at > now),
    )
    cache_result = await session.execute(cache_stmt)
    cached = cache_result.scalar_one_or_none()

    if cached is not None:
        logger.info(
            "transcription_cache_hit",
            workspace_id=str(workspace_id),
            audio_hash=audio_hash[:8],
            user_id=str(user_id),
        )
        # For cached responses, audio was already stored on the original transcription.
        # The TranscriptCache model does not yet carry a storage_key column — a future
        # task can add it to enable signed URL regeneration from cache hits.
        return TranscribeResponse(
            transcript_id=cached.id,
            text=cached.text,
            language_code=cached.language_code,
            duration_seconds=cached.duration_seconds,
            cached=True,
            audio_url=None,
            audio_storage_key=None,
        )

    # Cache miss — retrieve ElevenLabs API key
    from pilot_space.ai.infrastructure.key_storage import SecureKeyStorage
    from pilot_space.config import get_settings

    settings = get_settings()
    key_storage = SecureKeyStorage(
        db=session,
        master_secret=settings.encryption_key.get_secret_value(),
    )
    api_key = await key_storage.get_api_key(workspace_id, "elevenlabs", "stt")

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "PROVIDER_NOT_CONFIGURED",
                "message": "ElevenLabs API key not configured for this workspace",
            },
        )

    # Call ElevenLabs STT API
    logger.info(
        "transcription_elevenlabs_request",
        workspace_id=str(workspace_id),
        audio_hash=audio_hash[:8],
        content_type=content_type,
        size_bytes=len(audio_bytes),
        user_id=str(user_id),
    )

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            form_fields: dict[str, str] = {"model_id": "scribe_v1"}
            if language:
                form_fields["language_code"] = language

            files = {"file": (file.filename or "recording.webm", audio_bytes, content_type)}

            resp = await client.post(
                _ELEVENLABS_STT_URL,
                headers={"xi-api-key": api_key},
                data=form_fields,
                files=files,
            )
    except httpx.TimeoutException as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "code": "PROVIDER_TIMEOUT",
                "message": "ElevenLabs API timed out",
            },
        ) from exc
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "code": "PROVIDER_ERROR",
                "message": f"Failed to reach ElevenLabs API: {exc}",
            },
        ) from exc

    if resp.status_code in (401, 403):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "PROVIDER_AUTH_FAILED",
                "message": "ElevenLabs API key is invalid or expired",
            },
        )
    if resp.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "code": "PROVIDER_ERROR",
                "message": f"ElevenLabs API returned HTTP {resp.status_code}",
            },
        )

    try:
        el_data = resp.json()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "code": "PROVIDER_INVALID_RESPONSE",
                "message": "ElevenLabs returned non-JSON response",
            },
        ) from exc

    transcript_text: str = el_data.get("text", "")
    detected_language: str | None = el_data.get("language_code") or el_data.get("language")
    audio_duration: float | None = el_data.get("audio_duration") or el_data.get("duration")

    # Persist to transcript cache (upsert with TTL, RETURNING id)
    expires_at = now + timedelta(days=TRANSCRIPT_CACHE_TTL_DAYS)
    cache_insert = insert(TranscriptCache).values(
        workspace_id=workspace_id,
        audio_hash=audio_hash,
        text=transcript_text,
        language_code=detected_language,
        duration_seconds=audio_duration,
        provider="elevenlabs",
        metadata_json={"model_id": "scribe_v1"},
        expires_at=expires_at,
    )
    cache_insert = cache_insert.on_conflict_do_update(
        index_elements=["workspace_id", "audio_hash"],
        set_={"text": transcript_text, "expires_at": expires_at},
    ).returning(TranscriptCache.id)
    result = await session.execute(cache_insert)
    record_id = result.scalar_one()
    await session.commit()

    logger.info(
        "transcription_complete",
        workspace_id=str(workspace_id),
        transcript_id=str(record_id),
        audio_hash=audio_hash[:8],
        text_length=len(transcript_text),
        user_id=str(user_id),
    )

    # Upload audio to Supabase Storage for future playback.
    # Storage key is scoped by workspace + user + transcript record ID.
    # Failure is non-blocking: transcription result is always returned.
    audio_url: str | None = None
    audio_storage_key: str | None = None
    # Derive file extension from MIME type
    _MIME_TO_EXT: dict[str, str] = {
        "audio/webm": "webm",
        "audio/ogg": "ogg",
        "audio/wav": "wav",
        "audio/mp4": "m4a",
        "audio/mpeg": "mp3",
        "audio/x-m4a": "m4a",
        "audio/aac": "aac",
    }
    ext = _MIME_TO_EXT.get(content_type, "webm")
    storage_key = f"{workspace_id}/{user_id}/{record_id}.{ext}"

    try:
        storage_client = SupabaseStorageClient()
        await storage_client.upload_object(
            bucket=_VOICE_RECORDINGS_BUCKET,
            key=storage_key,
            data=audio_bytes,
            content_type=content_type,
        )
        audio_url = await storage_client.get_signed_url(
            bucket=_VOICE_RECORDINGS_BUCKET,
            key=storage_key,
            expires_in=3600,
        )
        audio_storage_key = storage_key
        logger.info(
            "audio_storage_success",
            workspace_id=str(workspace_id),
            transcript_id=str(record_id),
            storage_key=storage_key,
            user_id=str(user_id),
        )
    except Exception:
        logger.warning(
            "audio_storage_failed",
            workspace_id=str(workspace_id),
            transcript_id=str(record_id),
            storage_key=storage_key,
            user_id=str(user_id),
            exc_info=True,
        )

    return TranscribeResponse(
        transcript_id=record_id,
        text=transcript_text,
        language_code=detected_language,
        duration_seconds=audio_duration,
        cached=False,
        audio_url=audio_url,
        audio_storage_key=audio_storage_key,
    )


__all__ = ["router"]
