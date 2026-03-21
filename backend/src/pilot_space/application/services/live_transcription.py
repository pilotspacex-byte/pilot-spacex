"""Live speech-to-text service using ElevenLabs Scribe v2 Realtime.

Encapsulates WebSocket authentication, workspace membership verification,
API key retrieval, and bidirectional proxy relay between the browser and
ElevenLabs Scribe v2 Realtime.

Architecture:
    Browser --WS--> FastAPI --WS--> ElevenLabs Scribe Realtime
    Browser <--WS-- FastAPI <--WS-- ElevenLabs

The WS router remains a thin ASGI shell; all business logic lives here.
"""

from __future__ import annotations

import asyncio
import json
import time
from contextlib import suppress
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

import websockets
from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from pilot_space.ai.infrastructure.cost_tracker import CostTracker
from pilot_space.ai.infrastructure.key_storage import SecureKeyStorage
from pilot_space.ai.infrastructure.stt_pricing import calculate_stt_cost
from pilot_space.dependencies.auth import verify_token
from pilot_space.dependencies.jwt_providers import JWTExpiredError, JWTValidationError
from pilot_space.infrastructure.database.engine import get_db_session
from pilot_space.infrastructure.database.models.workspace_member import WorkspaceMember
from pilot_space.infrastructure.database.rls import set_rls_context
from pilot_space.infrastructure.logging import get_logger

logger = get_logger(__name__)

# ElevenLabs Scribe v2 Realtime WebSocket URL
_ELEVENLABS_REALTIME_URL = (
    "wss://api.elevenlabs.io/v1/speech-to-text/realtime?model_id=scribe_v2_realtime"
)

# WebSocket close codes
WS_CLOSE_UNAUTHORIZED = 4001
WS_CLOSE_FORBIDDEN = 4003
WS_CLOSE_KEY_NOT_CONFIGURED = 4022

# Timeout waiting for ElevenLabs committed transcript after browser sends commit
_COMMITTED_TIMEOUT_SECONDS = 15.0


class LiveTranscriptionError(Exception):
    """Base exception for live transcription WS failures.

    Follows the project AIError pattern with error_code + ws_close_code
    so the WS router can close the socket with a structured code/reason.

    Attributes:
        error_code: Machine-readable error identifier.
        ws_close_code: WebSocket close code sent to the browser.
        message: Human-readable description (also used as WS close reason).
    """

    error_code: str = "transcription_ws_error"
    ws_close_code: int = 4000

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class WSUnauthorizedError(LiveTranscriptionError):
    """JWT token is missing, invalid, or expired."""

    error_code = "ws_unauthorized"
    ws_close_code = WS_CLOSE_UNAUTHORIZED


class WSForbiddenError(LiveTranscriptionError):
    """Workspace ID missing/invalid, or user is not a member."""

    error_code = "ws_forbidden"
    ws_close_code = WS_CLOSE_FORBIDDEN


class WSKeyNotConfiguredError(LiveTranscriptionError):
    """ElevenLabs API key is not configured for the workspace."""

    error_code = "ws_key_not_configured"
    ws_close_code = WS_CLOSE_KEY_NOT_CONFIGURED


@dataclass
class AuthenticatedSession:
    """Result of successful WS authentication + authorization."""

    user_id: UUID
    workspace_id: UUID
    api_key: str


@dataclass
class _SessionMetrics:
    """Mutable container for proxy session metrics used by cost tracking."""

    start_time: float = field(default_factory=time.monotonic)
    committed_text: str = ""


async def authenticate_ws_session(
    token: str | None,
    workspace_id: str | None,
    encryption_key: str,
) -> AuthenticatedSession:
    """Validate JWT, verify workspace membership, and retrieve API key.

    Performs the full pre-proxy handshake:
    1. Verify JWT token (browsers cannot set WS headers, so token is a query param)
    2. Parse and validate workspace_id
    3. Check workspace membership + set RLS context
    4. Retrieve ElevenLabs API key from SecureKeyStorage

    Args:
        token: JWT Bearer token from query parameter.
        workspace_id: Workspace UUID string from query parameter.
        encryption_key: Master secret for decrypting stored API keys.

    Returns:
        AuthenticatedSession with user_id, workspace_id, and api_key.

    Raises:
        WSUnauthorizedError: Missing/invalid/expired token.
        WSForbiddenError: Missing workspace_id, invalid UUID, or not a member.
        WSKeyNotConfiguredError: ElevenLabs API key not configured.
    """
    # ------------------------------------------------------------------ Auth
    if not token:
        raise WSUnauthorizedError("Missing token")

    try:
        payload = verify_token(token)
    except (JWTExpiredError, JWTValidationError) as exc:
        logger.warning("transcription_ws_invalid_token", error=str(exc))
        raise WSUnauthorizedError("Invalid or expired token") from exc

    user_id = payload.user_id

    # -------------------------------------------------------- Workspace parse
    if not workspace_id:
        logger.warning("transcription_ws_missing_workspace_id", user_id=str(user_id))
        raise WSForbiddenError("workspace_id required")

    try:
        ws_uuid = UUID(workspace_id)
    except ValueError as exc:
        logger.warning(
            "transcription_ws_invalid_workspace_id",
            workspace_id=workspace_id,
            user_id=str(user_id),
        )
        raise WSForbiddenError("Invalid workspace_id") from exc

    # ------------------------------------------------- Membership + key check
    async with get_db_session() as session:
        await set_rls_context(session, user_id, ws_uuid)

        if not await _is_workspace_member(session, ws_uuid, user_id):
            logger.warning(
                "transcription_ws_not_member",
                user_id=str(user_id),
                workspace_id=str(ws_uuid),
            )
            raise WSForbiddenError("Not a member of this workspace")

        api_key = await _get_elevenlabs_key(session, ws_uuid, encryption_key)

    if not api_key:
        logger.warning(
            "transcription_ws_key_not_configured",
            user_id=str(user_id),
            workspace_id=str(ws_uuid),
        )
        raise WSKeyNotConfiguredError("ElevenLabs API key not configured for this workspace")

    return AuthenticatedSession(user_id=user_id, workspace_id=ws_uuid, api_key=api_key)


async def run_proxy_session(
    ws_browser: WebSocket,
    session: AuthenticatedSession,
) -> None:
    """Open ElevenLabs WS and relay audio/transcripts bidirectionally.

    Browser sends audio chunks; ElevenLabs returns partial and committed
    transcripts. The relay runs two concurrent tasks and coordinates their
    lifecycle: browser→ElevenLabs finishes first (on commit or disconnect),
    then we wait for the committed transcript from ElevenLabs with a timeout.

    Args:
        ws_browser: The accepted browser WebSocket connection.
        session: Authenticated session with user_id, workspace_id, api_key.
    """
    user_id_str = str(session.user_id)
    ws_uuid_str = str(session.workspace_id)
    metrics = _SessionMetrics()

    logger.info(
        "transcription_ws_connected",
        user_id=user_id_str,
        workspace_id=ws_uuid_str,
    )

    try:
        async with websockets.connect(
            _ELEVENLABS_REALTIME_URL,
            additional_headers={"xi-api-key": session.api_key},
        ) as ws_elevenlabs:
            task_browser = asyncio.create_task(_browser_to_elevenlabs(ws_browser, ws_elevenlabs))
            task_elevenlabs = asyncio.create_task(
                _elevenlabs_to_browser(ws_elevenlabs, ws_browser, metrics)
            )

            # Wait for browser relay to finish (commit or disconnect).
            # Do NOT cancel ElevenLabs relay yet — it still needs to send
            # the committed_transcript back after a commit.
            await task_browser

            # Wait for ElevenLabs committed transcript (with timeout)
            try:
                await asyncio.wait_for(task_elevenlabs, timeout=_COMMITTED_TIMEOUT_SECONDS)
            except TimeoutError:
                logger.warning("transcription_ws_committed_timeout", user_id=user_id_str)
                task_elevenlabs.cancel()
                with suppress(asyncio.CancelledError):
                    await task_elevenlabs

            # Log any unhandled task exceptions
            for task in (task_browser, task_elevenlabs):
                if task.done() and not task.cancelled() and task.exception():
                    logger.warning(
                        "transcription_ws_task_error",
                        error=str(task.exception()),
                        user_id=user_id_str,
                    )

    except Exception:
        logger.exception(
            "transcription_ws_elevenlabs_connection_error",
            user_id=user_id_str,
            workspace_id=ws_uuid_str,
        )
        with suppress(Exception):
            await ws_browser.send_text(
                json.dumps({"type": "error", "message": "Speech service temporarily unavailable"})
            )

    finally:
        logger.info(
            "transcription_ws_disconnected",
            user_id=user_id_str,
            workspace_id=ws_uuid_str,
        )
        with suppress(Exception):
            await ws_browser.close()

        # Track STT cost (non-fatal, separate DB session)
        await _track_live_stt_cost(session, metrics)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _is_workspace_member(session: AsyncSession, workspace_id: UUID, user_id: UUID) -> bool:
    """Check if user is an active member of the workspace."""
    result = await session.execute(
        select(
            exists().where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == user_id,
                WorkspaceMember.is_deleted == False,  # noqa: E712
            )
        )
    )
    return bool(result.scalar())


async def _get_elevenlabs_key(
    session: AsyncSession, workspace_id: UUID, encryption_key: str
) -> str | None:
    """Retrieve the ElevenLabs API key for the workspace."""
    key_storage = SecureKeyStorage(
        db=session,
        master_secret=encryption_key,
    )
    return await key_storage.get_api_key(workspace_id, "elevenlabs", "stt")


async def _browser_to_elevenlabs(
    ws_browser: WebSocket,
    ws_elevenlabs: Any,
) -> None:
    """Forward audio chunks from browser WebSocket to ElevenLabs.

    Reads JSON messages from the browser, validates they are input_audio_chunk
    messages, and forwards them to ElevenLabs. Stops when a commit message is
    received or when the browser disconnects.
    """
    try:
        while True:
            try:
                raw = await ws_browser.receive_text()
            except WebSocketDisconnect:
                break
            except Exception:
                break

            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                logger.warning("transcription_ws_invalid_json", raw=raw[:100])
                continue

            if msg.get("message_type") != "input_audio_chunk":
                logger.warning(
                    "transcription_ws_unexpected_message_type",
                    message_type=msg.get("message_type"),
                )
                continue

            await ws_elevenlabs.send(json.dumps(msg))

            if msg.get("commit") is True:
                break
    except Exception as exc:
        logger.warning("transcription_ws_browser_to_elevenlabs_error", error=str(exc))


async def _elevenlabs_to_browser(
    ws_elevenlabs: Any,
    ws_browser: WebSocket,
    metrics: _SessionMetrics | None = None,
) -> None:
    """Forward transcript events from ElevenLabs to the browser.

    Reads messages from ElevenLabs, parses them, and forwards
    partial_transcript and committed_transcript events to the browser as
    normalized ``{ type, text }`` messages.
    """
    try:
        async for raw in ws_elevenlabs:
            try:
                msg = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                continue

            msg_type = msg.get("type") or msg.get("message_type", "")

            if msg_type == "partial_transcript":
                text = msg.get("text", "")
                await ws_browser.send_text(json.dumps({"type": "partial", "text": text}))

            elif msg_type == "committed_transcript":
                text = msg.get("text", "")
                await ws_browser.send_text(json.dumps({"type": "committed", "text": text}))
                if metrics is not None:
                    metrics.committed_text = text
                break

            # session_started and other messages are silently ignored

    except Exception as exc:
        logger.warning("transcription_ws_elevenlabs_to_browser_error", error=str(exc))


async def _track_live_stt_cost(
    session: AuthenticatedSession,
    metrics: _SessionMetrics,
) -> None:
    """Track cost for a completed live STT session. Non-fatal."""
    try:
        duration_seconds = time.monotonic() - metrics.start_time
        if duration_seconds <= 0:
            return

        cost_usd = calculate_stt_cost("elevenlabs", "scribe_v2_realtime", duration_seconds)

        async with get_db_session() as db:
            tracker = CostTracker(db)
            await tracker.track(
                workspace_id=session.workspace_id,
                user_id=session.user_id,
                agent_name="stt_live",
                provider="elevenlabs",
                model="scribe_v2_realtime",
                input_tokens=0,
                output_tokens=0,
                operation_type="voice_input",
                cost_usd_override=cost_usd,
            )
            await db.commit()

        logger.info(
            "stt_live_cost_tracked",
            workspace_id=str(session.workspace_id),
            user_id=str(session.user_id),
            duration_seconds=round(duration_seconds, 2),
            cost_usd=round(cost_usd, 6),
        )
    except Exception:
        logger.warning(
            "stt_live_cost_tracking_failed",
            workspace_id=str(session.workspace_id),
            user_id=str(session.user_id),
            exc_info=True,
        )


__all__ = [
    "AuthenticatedSession",
    "LiveTranscriptionError",
    "WSForbiddenError",
    "WSKeyNotConfiguredError",
    "WSUnauthorizedError",
    "authenticate_ws_session",
    "run_proxy_session",
]
