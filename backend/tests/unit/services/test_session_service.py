"""Tests for SessionService — AUTH-06.

Covers session recording, throttling, force-revocation, and UA parsing.

Requirements: AUTH-06: Session tracking, last_seen throttling, and force-revocation
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from pilot_space.application.services.session_service import SessionService
from pilot_space.infrastructure.database.repositories.workspace_session_repository import (
    WorkspaceSessionRepository,
)


def _make_session_row(
    *,
    session_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
    workspace_id: uuid.UUID | None = None,
    session_token_hash: str = "abc123",
    ip_address: str | None = "1.2.3.4",
    user_agent: str | None = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    revoked_at: datetime | None = None,
) -> MagicMock:
    row = MagicMock()
    row.id = session_id or uuid.uuid4()
    row.user_id = user_id or uuid.uuid4()
    row.workspace_id = workspace_id or uuid.uuid4()
    row.session_token_hash = session_token_hash
    row.ip_address = ip_address
    row.user_agent = user_agent
    row.last_seen_at = datetime.now(UTC)
    row.created_at = datetime.now(UTC)
    row.revoked_at = revoked_at
    row.is_active = revoked_at is None
    row.user = MagicMock()
    row.user.display_name = "Test User"
    row.user.avatar_url = "https://example.com/avatar.png"
    return row


def _make_service() -> tuple[SessionService, MagicMock, MagicMock, MagicMock]:
    """Create SessionService with mocked dependencies."""
    repo = AsyncMock(spec=WorkspaceSessionRepository)
    redis = AsyncMock()
    admin_client = MagicMock()
    admin_client.auth = MagicMock()
    admin_client.auth.admin = MagicMock()
    admin_client.auth.admin.sign_out = MagicMock()
    service = SessionService(
        session_repo=repo,
        redis=redis,
        supabase_admin_client=admin_client,
    )
    return service, repo, redis, admin_client


@pytest.mark.asyncio
async def test_session_recorded_on_first_auth() -> None:
    """Upsert is called when no throttle key is present in Redis."""
    service, repo, redis, _ = _make_service()
    redis.get_raw.return_value = None
    user_id = uuid.uuid4()
    workspace_id = uuid.uuid4()
    token_hash = hashlib.sha256(b"mytoken").hexdigest()
    db = AsyncMock()

    await service.record_session(
        token_hash=token_hash,
        user_id=user_id,
        workspace_id=workspace_id,
        ip_address="1.2.3.4",
        user_agent="TestAgent/1.0",
        db=db,
    )

    repo.upsert_session.assert_called_once_with(
        user_id=user_id,
        workspace_id=workspace_id,
        token_hash=token_hash,
        ip_address="1.2.3.4",
        user_agent="TestAgent/1.0",
        db=db,
    )


@pytest.mark.asyncio
async def test_session_not_recorded_within_throttle_window() -> None:
    """No DB write when throttle key is present within the 60s window."""
    service, repo, redis, _ = _make_service()
    redis.get_raw.return_value = b"1"

    await service.record_session(
        token_hash="deadbeef" * 8,
        user_id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        ip_address="1.2.3.4",
        user_agent="TestAgent/1.0",
        db=AsyncMock(),
    )

    repo.upsert_session.assert_not_called()


@pytest.mark.asyncio
async def test_last_seen_redis_key_set_after_update() -> None:
    """After successful upsert, LASTSEEN_KEY is set with 60s TTL."""
    service, repo, redis, _ = _make_service()
    redis.get_raw.return_value = None
    token_hash = "cafebabe" * 8

    await service.record_session(
        token_hash=token_hash,
        user_id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        ip_address=None,
        user_agent=None,
        db=AsyncMock(),
    )

    redis.setex.assert_called_once_with(f"session:lastseen:{token_hash}", 60, "1")


@pytest.mark.asyncio
async def test_force_terminate_sets_revoked_at() -> None:
    """force_terminate calls repo.revoke with correct session_id and workspace_id."""
    service, repo, redis, _ = _make_service()
    session_id = uuid.uuid4()
    workspace_id = uuid.uuid4()
    token_hash = "deadbeef" * 8
    repo.get_session_by_id.return_value = _make_session_row(
        session_id=session_id,
        workspace_id=workspace_id,
        session_token_hash=token_hash,
    )
    db = AsyncMock()

    await service.force_terminate(session_id=session_id, workspace_id=workspace_id, db=db)

    repo.revoke.assert_called_once_with(
        session_id=session_id,
        workspace_id=workspace_id,
        db=db,
    )


@pytest.mark.asyncio
async def test_force_terminate_sets_redis_revoked_key() -> None:
    """force_terminate sets REVOKED_KEY in Redis with 1800s TTL."""
    service, repo, redis, _ = _make_service()
    session_id = uuid.uuid4()
    workspace_id = uuid.uuid4()
    token_hash = "cafecafe" * 8
    repo.get_session_by_id.return_value = _make_session_row(
        session_id=session_id,
        workspace_id=workspace_id,
        session_token_hash=token_hash,
    )

    await service.force_terminate(
        session_id=session_id,
        workspace_id=workspace_id,
        db=AsyncMock(),
    )

    redis.setex.assert_called_once_with(f"session:revoked:{workspace_id}:{token_hash}", 1800, "1")


@pytest.mark.asyncio
async def test_terminate_all_calls_supabase_sign_out() -> None:
    """terminate_all_for_user calls Supabase admin.sign_out with global scope."""
    service, repo, redis, admin_client = _make_service()
    user_id = uuid.uuid4()
    workspace_id = uuid.uuid4()
    repo.revoke_all_for_user.return_value = 2

    await service.terminate_all_for_user(
        user_id=user_id,
        workspace_id=workspace_id,
        db=AsyncMock(),
    )

    admin_client.auth.admin.sign_out.assert_called_once_with(str(user_id), scope="global")


@pytest.mark.asyncio
async def test_list_sessions_parses_user_agent() -> None:
    """list_sessions extracts browser and OS from Chrome/macOS User-Agent string."""
    service, repo, redis, _ = _make_service()
    chrome_ua = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    repo.list_active_for_workspace.return_value = [_make_session_row(user_agent=chrome_ua)]

    result = await service.list_sessions(workspace_id=uuid.uuid4(), db=AsyncMock())

    assert len(result) == 1
    assert result[0].browser is not None
    assert "Chrome" in result[0].browser
    assert result[0].os is not None
    assert "Mac" in result[0].os or "macOS" in result[0].os


def test_revoked_key_format() -> None:
    """REVOKED_KEY matches pattern session:revoked:{workspace_id}:{token_hash}."""
    from pilot_space.application.services.session_service import REVOKED_KEY_TEMPLATE

    workspace_id = uuid.UUID("12345678-1234-1234-1234-123456789012")
    token_hash = "abc" * 21 + "d"

    key = REVOKED_KEY_TEMPLATE.format(workspace_id=workspace_id, token_hash=token_hash)
    assert key.startswith("session:revoked:")
    assert str(workspace_id) in key
    assert token_hash in key
