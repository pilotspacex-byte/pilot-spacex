"""Transcription schemas for API responses.

Pydantic models for voice-to-text transcription via ElevenLabs STT.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import Field

from pilot_space.api.v1.schemas.base import BaseSchema


class TranscribeResponse(BaseSchema):
    """Response for a transcription request.

    Attributes:
        transcript_id: UUID of the persisted transcript cache record.
        text: The transcribed text.
        language_code: Detected or requested language code.
        duration_seconds: Audio duration in seconds.
        cached: True if result was served from cache (identical audio submitted before).
        audio_url: Signed URL for audio playback (1 hour expiry). None if storage upload
            failed (non-blocking) or for cached responses where audio was already stored.
        audio_storage_key: Raw storage key in the voice-recordings bucket. None if
            upload failed or not applicable (cached responses).
    """

    transcript_id: UUID = Field(description="UUID of the transcript cache record")
    text: str = Field(description="Transcribed text")
    language_code: str | None = Field(default=None, description="Detected language code")
    duration_seconds: float | None = Field(default=None, description="Audio duration in seconds")
    cached: bool = Field(
        default=False,
        description="True if result was served from cache",
    )
    audio_url: str | None = Field(
        default=None,
        description="Signed URL for audio playback (1h expiry). None if storage unavailable.",
    )
    audio_storage_key: str | None = Field(
        default=None,
        description="Raw storage key in voice-recordings bucket for future signed URL generation.",
    )


__all__ = ["TranscribeResponse"]
