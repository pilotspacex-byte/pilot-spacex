"""Test session expiration handling.

T322: Tests session TTL expiration and touch/refresh behavior.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import pytest

from pilot_space.ai.session.session_manager import (
    AIMessage,
    SessionExpiredError,
    SessionManager,
    SessionNotFoundError,
)


class MockRedisClient:
    """Mock Redis client for session testing."""

    def __init__(self) -> None:
        """Initialize mock Redis with TTL tracking."""
        self._data: dict[str, tuple[Any, float | None]] = {}  # key -> (value, expires_at)

    async def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        """Set key with optional TTL.

        Args:
            key: Redis key.
            value: Value to store.
            ttl: TTL in seconds.

        Returns:
            True if set successfully.
        """
        import time

        expires_at = time.time() + ttl if ttl else None
        self._data[key] = (value, expires_at)
        return True

    async def get(self, key: str) -> Any | None:
        """Get key value if not expired.

        Args:
            key: Redis key.

        Returns:
            Value if exists and not expired, None otherwise.
        """
        import time

        if key not in self._data:
            return None

        value, expires_at = self._data[key]

        if expires_at is not None and time.time() > expires_at:
            # Key expired
            del self._data[key]
            return None

        return value

    async def delete(self, key: str) -> int:
        """Delete key.

        Args:
            key: Redis key.

        Returns:
            Number of keys deleted.
        """
        if key in self._data:
            del self._data[key]
            return 1
        return 0

    async def expire(self, key: str, seconds: int) -> bool:
        """Update TTL on existing key.

        Args:
            key: Redis key.
            seconds: New TTL in seconds.

        Returns:
            True if TTL was updated.
        """
        import time

        if key not in self._data:
            return False

        value, _ = self._data[key]
        expires_at = time.time() + seconds
        self._data[key] = (value, expires_at)
        return True

    async def scan_keys(self, pattern: str, max_keys: int = 1000) -> list[str]:
        """Scan for keys matching pattern.

        Args:
            pattern: Key pattern (supports * wildcard).
            max_keys: Maximum keys to return.

        Returns:
            List of matching keys.
        """
        import re

        # Convert Redis pattern to regex
        regex_pattern = pattern.replace("*", ".*")
        regex = re.compile(regex_pattern)

        return [k for k in self._data if regex.match(k)][:max_keys]


class TestSessionExpiration:
    """Test session TTL and expiration behavior."""

    @pytest.mark.asyncio
    async def test_session_expires_after_ttl(self) -> None:
        """Verify session expires after TTL period."""
        redis = MockRedisClient()
        session_manager = SessionManager(redis)

        # Create session with 1-second TTL
        # We'll manually set a short TTL by creating the session
        # and then manipulating the expires_at time
        session = await session_manager.create_session(
            user_id=uuid4(),
            workspace_id=uuid4(),
            agent_name="conversation",
        )

        # Session exists immediately
        retrieved = await session_manager.get_session(session.id)
        assert retrieved is not None
        assert retrieved.id == session.id

        # Manually set session to expire in 1 second for testing
        session_key = session_manager._session_key(session.id)
        session_data = session.to_dict()
        session_data["expires_at"] = (datetime.now(UTC) + timedelta(seconds=1)).isoformat()
        await redis.set(session_key, session_data, ttl=1)

        # Wait for expiration (both Redis TTL and session logic)
        await asyncio.sleep(1.5)

        # Session should be gone (Redis TTL expired)
        with pytest.raises(SessionNotFoundError):
            await session_manager.get_session(session.id)

    @pytest.mark.asyncio
    async def test_touch_extends_ttl(self) -> None:
        """Verify updating session extends TTL."""
        redis = MockRedisClient()
        session_manager = SessionManager(redis)

        # Create session with short TTL for testing
        session = await session_manager.create_session(
            user_id=uuid4(),
            workspace_id=uuid4(),
            agent_name="conversation",
        )

        # Manually set Redis TTL to 2 seconds
        session_key = session_manager._session_key(session.id)
        initial_data = session.to_dict()
        await redis.set(session_key, initial_data, ttl=2)

        # Wait 1 second
        await asyncio.sleep(1)

        # Update session (should extend TTL)
        message = AIMessage(role="user", content="Continue session")
        await session_manager.update_session(
            session.id,
            message=message,
        )

        # Wait another 1.5 seconds (would have expired without update)
        await asyncio.sleep(1.5)

        # Should still exist due to touch
        retrieved = await session_manager.get_session(session.id)
        assert retrieved is not None
        assert len(retrieved.messages) == 1
        assert retrieved.messages[0].content == "Continue session"

    @pytest.mark.asyncio
    async def test_session_expired_error_when_timestamp_passed(self) -> None:
        """Verify SessionExpiredError raised when session timestamp is past."""
        redis = MockRedisClient()
        session_manager = SessionManager(redis)

        # Create session
        session = await session_manager.create_session(
            user_id=uuid4(),
            workspace_id=uuid4(),
            agent_name="test",
        )

        # Manually set expires_at to past
        session_key = session_manager._session_key(session.id)
        session_data = session.to_dict()
        past_time = datetime.now(UTC) - timedelta(seconds=10)
        session_data["expires_at"] = past_time.isoformat()
        # Keep Redis data alive but set session logic expiration
        await redis.set(session_key, session_data, ttl=60)

        # Should raise SessionExpiredError (session logic detects expiration)
        with pytest.raises(SessionExpiredError) as exc_info:
            await session_manager.get_session(session.id)

        assert exc_info.value.session_id == session.id

    @pytest.mark.asyncio
    async def test_cleanup_expired_sessions(self) -> None:
        """Verify cleanup removes expired sessions."""
        redis = MockRedisClient()
        session_manager = SessionManager(redis)

        # Create multiple sessions
        session1 = await session_manager.create_session(
            user_id=uuid4(),
            workspace_id=uuid4(),
            agent_name="test1",
        )

        session2 = await session_manager.create_session(
            user_id=uuid4(),
            workspace_id=uuid4(),
            agent_name="test2",
        )

        # Expire session1 manually
        session_key1 = session_manager._session_key(session1.id)
        session_data1 = session1.to_dict()
        past_time = datetime.now(UTC) - timedelta(seconds=10)
        session_data1["expires_at"] = past_time.isoformat()
        await redis.set(session_key1, session_data1, ttl=60)

        # Run cleanup
        cleaned = await session_manager.cleanup_expired_sessions()

        # Should have cleaned 1 session
        assert cleaned == 1

        # session1 should be gone
        with pytest.raises(SessionNotFoundError):
            await session_manager.get_session(session1.id)

        # session2 should still exist
        retrieved = await session_manager.get_session(session2.id)
        assert retrieved.id == session2.id

    @pytest.mark.asyncio
    async def test_update_nonexistent_session_raises_error(self) -> None:
        """Verify updating non-existent session raises error."""
        redis = MockRedisClient()
        session_manager = SessionManager(redis)

        fake_session_id = uuid4()

        with pytest.raises(SessionNotFoundError):
            await session_manager.update_session(
                fake_session_id,
                message=AIMessage(role="user", content="test"),
            )

    @pytest.mark.asyncio
    async def test_multiple_updates_maintain_session(self) -> None:
        """Verify multiple updates keep session alive."""
        redis = MockRedisClient()
        session_manager = SessionManager(redis)

        session = await session_manager.create_session(
            user_id=uuid4(),
            workspace_id=uuid4(),
            agent_name="conversation",
        )

        # Perform multiple updates with delays
        for i in range(3):
            await asyncio.sleep(0.5)
            await session_manager.update_session(
                session.id,
                message=AIMessage(role="user", content=f"Message {i + 1}"),
            )

        # Session should still be active
        retrieved = await session_manager.get_session(session.id)
        assert len(retrieved.messages) == 3
        assert retrieved.turn_count == 3

    @pytest.mark.asyncio
    async def test_end_session_removes_session(self) -> None:
        """Verify ending session removes it from storage."""
        redis = MockRedisClient()
        session_manager = SessionManager(redis)

        session = await session_manager.create_session(
            user_id=uuid4(),
            workspace_id=uuid4(),
            agent_name="test",
        )

        # End session
        deleted = await session_manager.end_session(session.id)
        assert deleted is True

        # Session should be gone
        with pytest.raises(SessionNotFoundError):
            await session_manager.get_session(session.id)

        # Ending again should return False
        deleted_again = await session_manager.end_session(session.id)
        assert deleted_again is False


@pytest.fixture
def mock_redis() -> MockRedisClient:
    """Provide mock Redis client."""
    return MockRedisClient()
