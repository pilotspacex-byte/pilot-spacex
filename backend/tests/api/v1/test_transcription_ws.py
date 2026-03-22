"""Tests for live STT WebSocket proxy endpoint (LIVE-STT-01).

Tests cover the authentication and authorization rejection cases at the WS
handshake stage, before any ElevenLabs connection is attempted. No external
calls are made.

Routes under test:
    WS /api/v1/ai/transcribe/stream

These tests use the Starlette TestClient's websocket_connect() which
exercises the ASGI layer without a live server.

The FastAPI WebSocket pattern is: accept() first, then validate, then close().
This means the client-side connect() call succeeds, but the server immediately
closes the socket with a close code.
"""

from __future__ import annotations

from unittest.mock import patch
from uuid import UUID

import pytest
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from pilot_space.infrastructure.auth import TokenPayload
from pilot_space.main import app

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_FAKE_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJpbnZhbGlkIn0.bad_signature"  # pragma: allowlist secret
_FAKE_WORKSPACE_ID = "00000000-0000-0000-0000-000000000001"
_FAKE_USER_ID = UUID("00000000-0000-0000-0000-000000000099")
_VERIFY_TOKEN_PATH = "pilot_space.application.services.live_transcription.verify_token"
_WS_BASE = "/api/v1/ai/transcribe/stream"


# ---------------------------------------------------------------------------
# Shared fixture — single TestClient lifespan for all tests
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def client() -> TestClient:
    """Create a single TestClient for the module to avoid repeated lifespan startup."""
    return TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_transcribe_stream_missing_token_closes_4001(client: TestClient) -> None:
    """WS connection without a token query param must be closed with 4001."""
    with (
        client.websocket_connect(_WS_BASE) as ws,
        pytest.raises(WebSocketDisconnect) as exc_info,
    ):
        ws.receive_text()

    assert exc_info.value.code == 4001


def test_transcribe_stream_invalid_token_closes_4001(client: TestClient) -> None:
    """WS connection with a malformed/invalid JWT must be closed with 4001."""
    from pilot_space.dependencies.jwt_providers import JWTValidationError

    with (
        patch(_VERIFY_TOKEN_PATH, side_effect=JWTValidationError("Invalid token")),
        client.websocket_connect(
            f"{_WS_BASE}?token={_FAKE_TOKEN}&workspace_id={_FAKE_WORKSPACE_ID}"
        ) as ws,
        pytest.raises(WebSocketDisconnect) as exc_info,
    ):
        ws.receive_text()

    assert exc_info.value.code == 4001


def test_transcribe_stream_expired_token_closes_4001(client: TestClient) -> None:
    """WS connection with an expired JWT must be closed with 4001."""
    from pilot_space.dependencies.jwt_providers import JWTExpiredError

    with (
        patch(_VERIFY_TOKEN_PATH, side_effect=JWTExpiredError("Token expired")),
        client.websocket_connect(
            f"{_WS_BASE}?token={_FAKE_TOKEN}&workspace_id={_FAKE_WORKSPACE_ID}"
        ) as ws,
        pytest.raises(WebSocketDisconnect) as exc_info,
    ):
        ws.receive_text()

    assert exc_info.value.code == 4001


def test_transcribe_stream_missing_workspace_id_closes_4003(client: TestClient) -> None:
    """WS connection with valid token but no workspace_id must close with 4003."""
    with (
        patch(
            _VERIFY_TOKEN_PATH,
            return_value=TokenPayload(sub=str(_FAKE_USER_ID), exp=9999999999, iat=0),
        ),
        client.websocket_connect(f"{_WS_BASE}?token={_FAKE_TOKEN}") as ws,
        pytest.raises(WebSocketDisconnect) as exc_info,
    ):
        ws.receive_text()

    assert exc_info.value.code == 4003
