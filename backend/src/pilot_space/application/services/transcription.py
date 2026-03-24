"""Transcription service for ElevenLabs Speech-to-Text.

Handles audio transcription via ElevenLabs STT with SHA-256 cache dedup
and optional Supabase Storage upload for playback URLs.

BYOK: Workspace admins configure ElevenLabs API key in AI settings.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from pilot_space.ai.infrastructure.cost_tracker import CostTracker
from pilot_space.ai.infrastructure.key_storage import SecureKeyStorage
from pilot_space.ai.infrastructure.stt_pricing import calculate_stt_cost

# TYPE_CHECKING guard: importing schemas.transcription triggers the api.v1.routers
# import chain, which includes repository_deps → container → this module (circular
# import).  At runtime TranscribeResponse is resolved lazily inside transcribe().
if TYPE_CHECKING:
    from pilot_space.api.v1.schemas.transcription import TranscribeResponse

from pilot_space.infrastructure.database.models.transcript_cache import (
    TRANSCRIPT_CACHE_TTL_DAYS,
    TranscriptCache,
)
from pilot_space.infrastructure.logging import get_logger
from pilot_space.infrastructure.storage.client import SupabaseStorageClient

logger = get_logger(__name__)

# Allowed audio MIME types
ALLOWED_MIME_TYPES = frozenset(
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
MAX_FILE_BYTES = 25 * 1024 * 1024

# ElevenLabs STT endpoint
_ELEVENLABS_STT_URL = "https://api.elevenlabs.io/v1/speech-to-text"

# Supabase Storage bucket for voice recordings
_VOICE_RECORDINGS_BUCKET = "voice-recordings"

# MIME type to file extension mapping
_MIME_TO_EXT: dict[str, str] = {
    "audio/webm": "webm",
    "audio/ogg": "ogg",
    "audio/wav": "wav",
    "audio/mp4": "m4a",
    "audio/mpeg": "mp3",
    "audio/x-m4a": "m4a",
    "audio/aac": "aac",
}


class TranscriptionError(Exception):
    """Base error for transcription failures.

    Follows the project AIError pattern (error_code + http_status) so the
    global exception handler can convert these to RFC 7807 responses.
    """

    error_code: str = "transcription_error"
    http_status: int = 500

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        if code:
            self.error_code = code


class ProviderNotConfiguredError(TranscriptionError):
    """ElevenLabs API key not configured for the workspace."""

    error_code = "provider_not_configured"
    http_status = 422


class ProviderAuthError(TranscriptionError):
    """ElevenLabs API key is invalid or expired."""

    error_code = "provider_auth_failed"
    http_status = 422


class ProviderError(TranscriptionError):
    """ElevenLabs API returned an error."""

    error_code = "provider_error"
    http_status = 502


@dataclass
class TranscribePayload:
    """Input for a transcription request."""

    workspace_id: UUID
    user_id: UUID
    audio_bytes: bytes
    content_type: str
    filename: str
    language: str | None = None


class TranscriptionService:
    """Service for transcribing audio via ElevenLabs STT with caching.

    Follows Clean Architecture: router handles HTTP concerns (validation,
    file upload), service handles business logic (caching, provider call,
    storage upload).

    Args:
        session: Async database session (request-scoped).
        storage_client: Supabase Storage client for audio uploads.
        encryption_key: Master secret for decrypting stored API keys.
    """

    def __init__(
        self,
        session: AsyncSession,
        storage_client: SupabaseStorageClient,
        encryption_key: str,
    ) -> None:
        self._session = session
        self._storage_client = storage_client
        self._encryption_key = encryption_key

    async def transcribe(self, payload: TranscribePayload) -> TranscribeResponse:
        """Transcribe audio to text using ElevenLabs STT.

        Checks the transcript cache for a previous result with the same audio
        content, and if not found, proxies the audio to ElevenLabs STT and
        caches the result. Optionally uploads audio to Supabase Storage.

        Args:
            payload: Transcription request data.

        Returns:
            TranscribeResponse with transcript text and optional metadata.

        Raises:
            ProviderNotConfiguredError: If ElevenLabs API key is not configured.
            ProviderAuthError: If ElevenLabs API key is invalid or expired.
            ProviderError: If ElevenLabs API returns an unexpected error.
        """
        # Lazy import to break circular dependency: transcription → schemas.transcription →
        # api.v1.__init__ → routers → repository_deps → container → transcription.
        # The TYPE_CHECKING guard above allows the return annotation; this import
        # provides the class at call time.
        from pilot_space.api.v1.schemas.transcription import (
            TranscribeResponse as _TranscribeResponse,
        )

        audio_hash = hashlib.sha256(payload.audio_bytes).hexdigest()

        # Check transcript cache (skip expired entries)
        cached = await self._check_cache(payload.workspace_id, audio_hash)
        if cached is not None:
            logger.info(
                "transcription_cache_hit",
                workspace_id=str(payload.workspace_id),
                audio_hash=audio_hash[:8],
                user_id=str(payload.user_id),
            )
            return _TranscribeResponse(
                transcript_id=cached.id,
                text=cached.text,
                language_code=cached.language_code,
                duration_seconds=cached.duration_seconds,
                cached=True,
                audio_url=None,
                audio_storage_key=None,
            )

        # Cache miss — retrieve ElevenLabs API key
        api_key = await self._get_api_key(payload.workspace_id)

        # Call ElevenLabs STT API
        logger.info(
            "transcription_elevenlabs_request",
            workspace_id=str(payload.workspace_id),
            audio_hash=audio_hash[:8],
            content_type=payload.content_type,
            size_bytes=len(payload.audio_bytes),
            user_id=str(payload.user_id),
        )

        transcript_text, detected_language, audio_duration = await self._call_elevenlabs(
            api_key=api_key,
            audio_bytes=payload.audio_bytes,
            content_type=payload.content_type,
            filename=payload.filename,
            language=payload.language,
        )

        # Persist to transcript cache
        record_id = await self._upsert_cache(
            workspace_id=payload.workspace_id,
            audio_hash=audio_hash,
            text=transcript_text,
            language_code=detected_language,
            duration_seconds=audio_duration,
        )

        logger.info(
            "transcription_complete",
            workspace_id=str(payload.workspace_id),
            transcript_id=str(record_id),
            audio_hash=audio_hash[:8],
            text_length=len(transcript_text),
            user_id=str(payload.user_id),
        )

        # Track STT cost (non-fatal — never crashes the transcription flow)
        await self._track_stt_cost(
            workspace_id=payload.workspace_id,
            user_id=payload.user_id,
            model="scribe_v2",
            duration_seconds=audio_duration,
        )

        # Upload audio to Supabase Storage (non-blocking)
        audio_url, audio_storage_key = await self._upload_audio(
            workspace_id=payload.workspace_id,
            user_id=payload.user_id,
            record_id=record_id,
            audio_bytes=payload.audio_bytes,
            content_type=payload.content_type,
        )

        return _TranscribeResponse(
            transcript_id=record_id,
            text=transcript_text,
            language_code=detected_language,
            duration_seconds=audio_duration,
            cached=False,
            audio_url=audio_url,
            audio_storage_key=audio_storage_key,
        )

    async def _check_cache(self, workspace_id: UUID, audio_hash: str) -> TranscriptCache | None:
        """Check transcript cache for an existing non-expired entry."""
        now = datetime.now(UTC)
        stmt = select(TranscriptCache).where(
            TranscriptCache.workspace_id == workspace_id,
            TranscriptCache.audio_hash == audio_hash,
            (TranscriptCache.expires_at.is_(None)) | (TranscriptCache.expires_at > now),
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_api_key(self, workspace_id: UUID) -> str:
        """Retrieve the ElevenLabs API key for the workspace.

        Raises:
            ProviderNotConfiguredError: If no key is configured.
        """
        key_storage = SecureKeyStorage(
            db=self._session,
            master_secret=self._encryption_key,
        )
        api_key = await key_storage.get_api_key(workspace_id, "elevenlabs", "stt")
        if not api_key:
            raise ProviderNotConfiguredError("ElevenLabs API key not configured for this workspace")
        return api_key

    async def _call_elevenlabs(
        self,
        api_key: str,
        audio_bytes: bytes,
        content_type: str,
        filename: str,
        language: str | None,
    ) -> tuple[str, str | None, float | None]:
        """Call ElevenLabs STT API and return (text, language_code, duration).

        Raises:
            ProviderAuthError: If API key is invalid.
            ProviderError: On timeout, network, or unexpected API errors.
        """
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                form_fields: dict[str, str] = {"model_id": "scribe_v2"}
                if language:
                    form_fields["language_code"] = language

                files = {"file": (filename or "recording.webm", audio_bytes, content_type)}

                resp = await client.post(
                    _ELEVENLABS_STT_URL,
                    headers={"xi-api-key": api_key},
                    data=form_fields,
                    files=files,
                )
        except httpx.TimeoutException as exc:
            raise ProviderError("ElevenLabs API timed out") from exc
        except httpx.RequestError as exc:
            raise ProviderError(f"Failed to reach ElevenLabs API: {exc}") from exc

        if resp.status_code in (401, 403):
            raise ProviderAuthError("ElevenLabs API key is invalid or expired")
        if resp.status_code != 200:
            raise ProviderError(f"ElevenLabs API returned HTTP {resp.status_code}")

        try:
            el_data = resp.json()
        except Exception as exc:
            raise ProviderError("ElevenLabs returned non-JSON response") from exc

        transcript_text: str = el_data.get("text", "")
        detected_language: str | None = el_data.get("language_code") or el_data.get("language")
        audio_duration: float | None = el_data.get("audio_duration") or el_data.get("duration")

        return transcript_text, detected_language, audio_duration

    async def _upsert_cache(
        self,
        workspace_id: UUID,
        audio_hash: str,
        text: str,
        language_code: str | None,
        duration_seconds: float | None,
    ) -> UUID:
        """Upsert transcript cache record and return its ID."""
        now = datetime.now(UTC)
        expires_at = now + timedelta(days=TRANSCRIPT_CACHE_TTL_DAYS)
        stmt = insert(TranscriptCache).values(
            workspace_id=workspace_id,
            audio_hash=audio_hash,
            text=text,
            language_code=language_code,
            duration_seconds=duration_seconds,
            provider="elevenlabs",
            metadata_json={"model_id": "scribe_v2"},
            expires_at=expires_at,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["workspace_id", "audio_hash"],
            set_={"text": text, "expires_at": expires_at},
        ).returning(TranscriptCache.id)
        result = await self._session.execute(stmt)
        record_id = result.scalar_one()
        await self._session.commit()
        return record_id

    async def _track_stt_cost(
        self,
        workspace_id: UUID,
        user_id: UUID,
        model: str,
        duration_seconds: float | None,
    ) -> None:
        """Track ElevenLabs STT cost. Non-fatal — failures are logged, never raised."""
        try:
            duration = duration_seconds or 0.0
            cost_usd = calculate_stt_cost("elevenlabs", model, duration)
            tracker = CostTracker(self._session)
            await tracker.track(
                workspace_id=workspace_id,
                user_id=user_id,
                agent_name="stt",
                provider="elevenlabs",
                model=model,
                input_tokens=0,
                output_tokens=0,
                operation_type="voice_input",
                cost_usd_override=cost_usd,
            )
            await self._session.commit()
        except Exception:
            logger.warning(
                "stt_cost_tracking_failed",
                workspace_id=str(workspace_id),
                user_id=str(user_id),
                model=model,
                exc_info=True,
            )

    async def _upload_audio(
        self,
        workspace_id: UUID,
        user_id: UUID,
        record_id: UUID,
        audio_bytes: bytes,
        content_type: str,
    ) -> tuple[str | None, str | None]:
        """Upload audio to Supabase Storage. Returns (signed_url, storage_key).

        Failure is non-blocking — returns (None, None) on error.
        """
        ext = _MIME_TO_EXT.get(content_type, "webm")
        storage_key = f"{workspace_id}/{user_id}/{record_id}.{ext}"

        try:
            await self._storage_client.upload_object(
                bucket=_VOICE_RECORDINGS_BUCKET,
                key=storage_key,
                data=audio_bytes,
                content_type=content_type,
            )
            audio_url = await self._storage_client.get_signed_url(
                bucket=_VOICE_RECORDINGS_BUCKET,
                key=storage_key,
                expires_in=3600,
            )
            logger.info(
                "audio_storage_success",
                workspace_id=str(workspace_id),
                transcript_id=str(record_id),
                storage_key=storage_key,
                user_id=str(user_id),
            )
            return audio_url, storage_key
        except Exception:
            logger.warning(
                "audio_storage_failed",
                workspace_id=str(workspace_id),
                transcript_id=str(record_id),
                storage_key=storage_key,
                user_id=str(user_id),
                exc_info=True,
            )
            return None, None


__all__ = [
    "ProviderAuthError",
    "ProviderError",
    "ProviderNotConfiguredError",
    "TranscribePayload",
    "TranscriptionError",
    "TranscriptionService",
]
