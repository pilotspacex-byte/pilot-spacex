"""Test scaffolds for SessionService — AUTH-06.

These tests define the expected contract for the session tracking service
before implementation begins. All tests are marked xfail(strict=False) so
they are collected by pytest and run, but do not block the suite.

Requirements covered:
  AUTH-06: Session tracking, last_seen throttling, and force-revocation
"""

from __future__ import annotations

import pytest

# ---------------------------------------------------------------------------
# AUTH-06: Session lifecycle
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.xfail(
    strict=False,
    reason="SessionService.record_session not yet implemented (AUTH-06)",
)
async def test_session_recorded_on_first_auth() -> None:
    """A WorkspaceSession row is created when a user authenticates.

    Scenario:
        Given a user authenticates to a workspace with a new token
        When SessionService.record_session(user_id, workspace_id, token, ip, ua) is called
        Then a WorkspaceSession row exists with:
          - session_token_hash == sha256(token)
          - ip_address == ip
          - user_agent == ua
          - revoked_at is None
    """
    raise NotImplementedError("AUTH-06: SessionService.record_session not implemented")


@pytest.mark.asyncio
@pytest.mark.xfail(
    strict=False,
    reason="SessionService.update_last_seen throttle not yet implemented (AUTH-06)",
)
async def test_last_seen_throttled_within_60s() -> None:
    """last_seen_at is NOT updated if updated within the last 60 seconds.

    Scenario:
        Given a session with last_seen_at = now()
        When SessionService.update_last_seen(session_id) is called again within 60s
        Then last_seen_at is NOT updated (write is skipped)
        And the Redis TTL key for throttle is still set
    """
    raise NotImplementedError("AUTH-06: last_seen_at throttle (60s window) not implemented")


@pytest.mark.asyncio
@pytest.mark.xfail(
    strict=False,
    reason="SessionService.force_terminate not yet implemented (AUTH-06)",
)
async def test_force_terminate_sets_revoked_at() -> None:
    """force_terminate sets revoked_at timestamp on the session row.

    Scenario:
        Given an active session (revoked_at is None)
        When SessionService.force_terminate(session_id) is called
        Then session.revoked_at is set to a non-null datetime
        And session.is_active == False
    """
    raise NotImplementedError(
        "AUTH-06: SessionService.force_terminate (revoked_at) not implemented"
    )


@pytest.mark.asyncio
@pytest.mark.xfail(
    strict=False,
    reason="SessionService.force_terminate Redis cleanup not yet implemented (AUTH-06)",
)
async def test_force_terminate_deletes_redis_key() -> None:
    """force_terminate removes the session's Redis key to prevent cache use.

    Scenario:
        Given an active session with a cached Redis key for last_seen throttle
        When SessionService.force_terminate(session_id) is called
        Then the corresponding Redis key is deleted
        And subsequent requests with this token receive 401
    """
    raise NotImplementedError(
        "AUTH-06: SessionService.force_terminate Redis key deletion not implemented"
    )


@pytest.mark.asyncio
@pytest.mark.xfail(
    strict=False,
    reason="SessionService.terminate_all_user_sessions not yet implemented (AUTH-06)",
)
async def test_terminate_all_user_sessions() -> None:
    """terminate_all_user_sessions revokes all active sessions for a user.

    Scenario:
        Given user has 3 active sessions across 2 workspaces
        When SessionService.terminate_all_user_sessions(user_id) is called
        Then all 3 sessions have revoked_at set
        And all corresponding Redis keys are deleted
        And the method returns the count of revoked sessions (3)
    """
    raise NotImplementedError("AUTH-06: SessionService.terminate_all_user_sessions not implemented")
