"""Unit tests for SkillConcurrencyManager and NoteWriteLock.

T-047: SkillConcurrencyManager — acquire/release/overflow behaviour.
C-3:  NoteWriteLock — acquire/release/timeout/concurrent behaviour.

Feature 015: AI Workforce Platform — Sprint 2
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from pilot_space.application.services.note_write_lock import (
    NoteLockTimeoutError,
    NoteWriteLock,
)
from pilot_space.application.services.skill.concurrency_manager import (
    MAX_CONCURRENT,
    SkillConcurrencyManager,
)

# ---------------------------------------------------------------------------
# Helpers: fake RedisClient
# ---------------------------------------------------------------------------


def _make_redis(counters: dict | None = None) -> MagicMock:
    """Build a MagicMock mimicking RedisClient's async methods."""
    redis = MagicMock()
    _counters: dict[str, int] = counters or {}

    async def incr(key: str, _amount: int = 1) -> int:
        _counters[key] = _counters.get(key, 0) + 1
        return _counters[key]

    async def decr(key: str, _amount: int = 1) -> int:
        _counters[key] = _counters.get(key, 0) - 1
        return _counters[key]

    async def expire(_key: str, _ttl: int) -> bool:
        return True

    async def get(key: str) -> int | None:
        return _counters.get(key)

    redis.incr = AsyncMock(side_effect=incr)
    redis.decr = AsyncMock(side_effect=decr)
    redis.expire = AsyncMock(side_effect=expire)
    redis.get = AsyncMock(side_effect=get)
    return redis


def _make_lock_redis(
    nx_results: list[bool],
    delete_result: int = 1,
) -> MagicMock:
    """Build a RedisClient mock for lock acquire/release testing.

    Args:
        nx_results: Sequence of booleans for successive set(…, if_not_exists=True) calls.
        delete_result: Value returned by delete().
    """
    redis = MagicMock()
    _nx_iter = iter(nx_results)
    _store: dict[str, str] = {}

    async def mock_set(
        key: str,
        value: str,
        *,
        ttl: int | None = None,
        if_not_exists: bool = False,
        if_exists: bool = False,
    ) -> bool:
        if if_not_exists:
            result = next(_nx_iter, False)
            if result:
                _store[key] = value
            return result
        _store[key] = value
        return True

    async def mock_delete(*keys: str) -> int:
        for k in keys:
            _store.pop(k, None)
        return delete_result

    redis.set = AsyncMock(side_effect=mock_set)
    redis.delete = AsyncMock(side_effect=mock_delete)
    redis._client = None  # trigger plain-delete fallback in release()
    return redis


# ===========================================================================
# SkillConcurrencyManager tests
# ===========================================================================


class TestSkillConcurrencyManager:
    """Tests for SkillConcurrencyManager (T-047)."""

    @pytest.mark.asyncio
    async def test_acquire_first_slot_sets_ttl(self) -> None:
        """First slot acquisition sets safety TTL on the Redis key."""
        redis = _make_redis()
        manager = SkillConcurrencyManager(redis)
        ws = uuid4()

        acquired = await manager.acquire_slot(ws)

        assert acquired is True
        redis.expire.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_acquire_up_to_max(self) -> None:
        """All MAX_CONCURRENT slots can be acquired sequentially."""
        redis = _make_redis()
        manager = SkillConcurrencyManager(redis)
        ws = uuid4()

        results = [await manager.acquire_slot(ws) for _ in range(MAX_CONCURRENT)]

        assert all(results)

    @pytest.mark.asyncio
    async def test_acquire_exceeds_max_returns_false(self) -> None:
        """Acquiring slot beyond MAX_CONCURRENT returns False and decrements counter."""
        redis = _make_redis()
        manager = SkillConcurrencyManager(redis)
        ws = uuid4()

        # Fill all slots
        for _ in range(MAX_CONCURRENT):
            await manager.acquire_slot(ws)

        # One more should fail
        acquired = await manager.acquire_slot(ws)

        assert acquired is False
        # Counter must be decremented back after denial
        redis.decr.assert_awaited()

    @pytest.mark.asyncio
    async def test_release_slot_decrements_counter(self) -> None:
        """release_slot decrements the Redis counter."""
        redis = _make_redis()
        manager = SkillConcurrencyManager(redis)
        ws = uuid4()

        await manager.acquire_slot(ws)
        await manager.release_slot(ws)

        assert redis.decr.await_count == 1

    @pytest.mark.asyncio
    async def test_release_clamps_negative_counter(self) -> None:
        """Releasing an un-held slot (negative counter) clamps to 0."""
        redis = _make_redis()
        manager = SkillConcurrencyManager(redis)
        ws = uuid4()

        # Release without acquire → counter starts at 0, goes to -1
        await manager.release_slot(ws)

        # incr was called to clamp back
        redis.incr.assert_awaited()

    @pytest.mark.asyncio
    async def test_get_queue_depth_zero_within_limit(self) -> None:
        """Queue depth is 0 when within limit."""
        redis = _make_redis()
        manager = SkillConcurrencyManager(redis)
        ws = uuid4()

        await manager.acquire_slot(ws)
        depth = await manager.get_queue_depth(ws)

        assert depth == 0

    @pytest.mark.asyncio
    async def test_get_queue_depth_no_key(self) -> None:
        """Queue depth is 0 when workspace has no counter key."""
        redis = _make_redis()
        manager = SkillConcurrencyManager(redis)
        ws = uuid4()

        depth = await manager.get_queue_depth(ws)

        assert depth == 0

    @pytest.mark.asyncio
    async def test_redis_unavailable_fails_open(self) -> None:
        """When Redis returns None, manager fails open (returns True)."""
        redis = MagicMock()
        redis.incr = AsyncMock(return_value=None)
        redis.expire = AsyncMock(return_value=True)
        manager = SkillConcurrencyManager(redis)

        acquired = await manager.acquire_slot(uuid4())

        assert acquired is True


# ===========================================================================
# NoteWriteLock tests
# ===========================================================================


class TestNoteWriteLock:
    """Tests for NoteWriteLock (C-3)."""

    @pytest.mark.asyncio
    async def test_acquire_success_returns_lock_id(self) -> None:
        """acquire() returns a non-empty lock_id string on success."""
        redis = _make_lock_redis(nx_results=[True])
        lock = NoteWriteLock(redis)
        note_id = uuid4()

        lock_id = await lock.acquire(note_id)

        assert isinstance(lock_id, str)
        assert len(lock_id) > 0

    @pytest.mark.asyncio
    async def test_acquire_calls_set_with_nx(self) -> None:
        """acquire() issues SET with if_not_exists=True."""
        redis = _make_lock_redis(nx_results=[True])
        lock = NoteWriteLock(redis)
        note_id = uuid4()

        await lock.acquire(note_id)

        redis.set.assert_awaited_once()
        _, kwargs = redis.set.await_args
        assert kwargs.get("if_not_exists") is True

    @pytest.mark.asyncio
    async def test_acquire_retries_until_lock_free(self) -> None:
        """acquire() retries after failed NX attempt."""
        # First attempt fails (lock held), second succeeds
        redis = _make_lock_redis(nx_results=[False, True])
        lock = NoteWriteLock(redis)
        note_id = uuid4()

        # Shorten poll interval for fast test
        with patch(
            "pilot_space.application.services.note_write_lock._POLL_INTERVAL_S",
            0.01,
        ):
            lock_id = await lock.acquire(note_id)

        assert isinstance(lock_id, str)
        assert redis.set.await_count == 2

    @pytest.mark.asyncio
    async def test_acquire_raises_on_timeout(self) -> None:
        """acquire() raises NoteLockTimeoutError after ACQUIRE_TIMEOUT_S."""
        # All NX attempts fail (lock never free)
        redis = _make_lock_redis(nx_results=[False] * 100)
        lock = NoteWriteLock(redis)
        note_id = uuid4()

        with (
            patch(
                "pilot_space.application.services.note_write_lock.ACQUIRE_TIMEOUT_S",
                0.05,
            ),
            patch(
                "pilot_space.application.services.note_write_lock._POLL_INTERVAL_S",
                0.01,
            ),
            pytest.raises(NoteLockTimeoutError),
        ):
            await lock.acquire(note_id)

    @pytest.mark.asyncio
    async def test_release_deletes_key(self) -> None:
        """release() calls delete on the lock key."""
        redis = _make_lock_redis(nx_results=[True])
        lock = NoteWriteLock(redis)
        note_id = uuid4()

        lock_id = await lock.acquire(note_id)
        await lock.release(note_id, lock_id)

        redis.delete.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_lock_context_manager_acquires_and_releases(self) -> None:
        """lock() context manager acquires on enter, releases on exit."""
        redis = _make_lock_redis(nx_results=[True])
        lock = NoteWriteLock(redis)
        note_id = uuid4()

        async with lock.lock(note_id) as lock_id:
            assert isinstance(lock_id, str)
            assert redis.set.await_count == 1

        redis.delete.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_lock_releases_on_exception(self) -> None:
        """lock() releases even when the body raises an exception."""
        redis = _make_lock_redis(nx_results=[True])
        lock = NoteWriteLock(redis)
        note_id = uuid4()

        with pytest.raises(ValueError, match="body error"):
            async with lock.lock(note_id):
                raise ValueError("body error")

        # Release must still happen
        redis.delete.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_release_with_lua_script(self) -> None:
        """release() uses Lua script when raw Redis client is available."""
        inner_client = AsyncMock()
        inner_client.eval = AsyncMock(return_value=1)

        redis = MagicMock()
        redis.set = AsyncMock(return_value=True)
        redis.delete = AsyncMock(return_value=1)
        redis._client = inner_client  # expose inner client for Lua path

        lock = NoteWriteLock(redis)
        note_id = uuid4()
        lock_id = str(uuid4())

        await lock.release(note_id, lock_id)

        inner_client.eval.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_release_lua_mismatch_logs_warning(self) -> None:
        """release() logs a warning when Lua script returns 0 (lock_id mismatch)."""
        inner_client = AsyncMock()
        inner_client.eval = AsyncMock(return_value=0)  # 0 = mismatch

        redis = MagicMock()
        redis._client = inner_client

        lock = NoteWriteLock(redis)
        note_id = uuid4()

        # Should complete without raising even on mismatch
        await lock.release(note_id, "wrong-lock-id")

        inner_client.eval.assert_awaited_once()


# ===========================================================================
# Approval router helper tests (role verification logic)
# ===========================================================================


class TestApprovalRoleVerification:
    """Unit tests for approval role enforcement logic (C-7).

    Tests the _verify_workspace_membership helper in skill_approvals router.
    """

    @pytest.mark.asyncio
    async def test_member_approved_when_no_required_role(self) -> None:
        """Any workspace member can approve when no required_role is set."""
        from unittest.mock import AsyncMock

        session = MagicMock()
        result_mock = MagicMock()
        result_mock.scalar.return_value = MagicMock(value="member")
        session.execute = AsyncMock(return_value=result_mock)

        from pilot_space.api.v1.routers.skill_approvals import (
            _verify_workspace_membership,
        )

        role = await _verify_workspace_membership(
            user_id=uuid4(),
            workspace_id=uuid4(),
            session=session,
            required_role=None,
        )

        assert role == "member"

    @pytest.mark.asyncio
    async def test_member_blocked_when_admin_required(self) -> None:
        """Member is blocked with 403 when admin role is required."""
        from fastapi import HTTPException

        session = MagicMock()
        result_mock = MagicMock()
        # Simulate a 'member' role (not admin/owner)
        role_obj = MagicMock()
        role_obj.value = "member"
        result_mock.scalar.return_value = role_obj
        session.execute = AsyncMock(return_value=result_mock)

        # Need WorkspaceRole values to match
        with patch(
            "pilot_space.api.v1.routers.skill_approvals.WorkspaceRole",
            create=True,
        ):
            from pilot_space.infrastructure.database.models.workspace_member import (
                WorkspaceRole,
            )

            # Patch the module-level lookup inside the function
            with patch.dict(
                "sys.modules",
                {
                    "pilot_space.infrastructure.database.models.workspace_member": MagicMock(
                        WorkspaceMember=MagicMock(),
                        WorkspaceRole=WorkspaceRole,
                    )
                },
            ):
                from pilot_space.api.v1.routers.skill_approvals import (
                    _verify_workspace_membership,
                )

                with pytest.raises(HTTPException) as exc_info:
                    await _verify_workspace_membership(
                        user_id=uuid4(),
                        workspace_id=uuid4(),
                        session=session,
                        required_role="admin",
                    )

                assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_non_member_raises_403(self) -> None:
        """Non-member raises 403 Forbidden."""
        from fastapi import HTTPException

        session = MagicMock()
        result_mock = MagicMock()
        result_mock.scalar.return_value = None  # not a member
        session.execute = AsyncMock(return_value=result_mock)

        from pilot_space.api.v1.routers.skill_approvals import (
            _verify_workspace_membership,
        )

        with pytest.raises(HTTPException) as exc_info:
            await _verify_workspace_membership(
                user_id=uuid4(),
                workspace_id=uuid4(),
                session=session,
            )

        assert exc_info.value.status_code == 403
