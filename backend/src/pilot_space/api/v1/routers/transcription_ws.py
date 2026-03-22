"""Live speech-to-text WebSocket router.

Thin ASGI shell — delegates all business logic to live_transcription service.
Service exceptions (LiveTranscriptionError hierarchy) carry ws_close_code
and are mapped to WS close frames here.

Routes:
    WS /ai/transcribe/stream  — Stream audio to ElevenLabs Scribe Realtime

Feature: Live voice-to-text input for AI Chat (LIVE-STT-01)
"""

from __future__ import annotations

from fastapi import APIRouter, WebSocket

from pilot_space.application.services.live_transcription import (
    LiveTranscriptionError,
    authenticate_ws_session,
    run_proxy_session,
)
from pilot_space.config import get_settings

router = APIRouter(tags=["ai", "transcription"])


@router.websocket("/transcribe/stream")
async def transcribe_stream(
    websocket: WebSocket,
    token: str | None = None,
    workspace_id: str | None = None,
) -> None:
    """Stream audio to ElevenLabs Scribe v2 Realtime and return live transcripts.

    Query Params:
        token: JWT Bearer token (required — browsers cannot set WS headers).
        workspace_id: Workspace UUID (required for membership check and key lookup).

    Browser sends:
        { message_type: "input_audio_chunk", audio_base_64: "...", commit: false, sample_rate: 16000 }
        { message_type: "input_audio_chunk", audio_base_64: "", commit: true, sample_rate: 16000 }

    Browser receives:
        { type: "partial", text: "..." }
        { type: "committed", text: "..." }
        { type: "error", message: "..." }

    Close codes:
        4001 (WSUnauthorizedError): Authentication failed
        4003 (WSForbiddenError): Workspace access denied
        4022 (WSKeyNotConfiguredError): ElevenLabs API key not configured
    """
    await websocket.accept()

    try:
        session = await authenticate_ws_session(
            token=token,
            workspace_id=workspace_id,
            encryption_key=get_settings().encryption_key.get_secret_value(),
        )
    except LiveTranscriptionError as exc:
        await websocket.close(code=exc.ws_close_code, reason=exc.message)
        return

    await run_proxy_session(websocket, session)


__all__ = ["router"]
