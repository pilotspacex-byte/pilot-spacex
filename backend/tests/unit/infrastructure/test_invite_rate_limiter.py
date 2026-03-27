"""Unit tests for InviteRateLimiter.

Tests: allows first 3 requests, blocks 4th, independent emails,
fail-open on Redis error, correct key format.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from pilot_space.infrastructure.cache.invite_rate_limiter import InviteRateLimiter

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_limiter(incr_return: int = 1) -> tuple[InviteRateLimiter, AsyncMock]:
    """Build an InviteRateLimiter with a mocked Redis client."""
    redis_client = AsyncMock()
    redis_client.incr = AsyncMock(return_value=incr_return)
    redis_client.expire = AsyncMock(return_value=True)
    return InviteRateLimiter(redis_client=redis_client), redis_client


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_allows_first_request() -> None:
    """incr returns 1 → request is allowed."""
    limiter, _ = _make_limiter(incr_return=1)
    result = await limiter.check_and_increment("user@example.com")
    assert result is True


@pytest.mark.asyncio
async def test_allows_third_request() -> None:
    """incr returns 3 (at limit boundary) → request is still allowed."""
    limiter, _ = _make_limiter(incr_return=3)
    result = await limiter.check_and_increment("user@example.com")
    assert result is True


@pytest.mark.asyncio
async def test_blocks_fourth_request() -> None:
    """incr returns 4 (over limit) → request is denied."""
    limiter, _ = _make_limiter(incr_return=4)
    result = await limiter.check_and_increment("user@example.com")
    assert result is False


def test_independent_emails_have_different_keys() -> None:
    """_make_key for two different emails returns distinct strings."""
    redis_client = AsyncMock()
    limiter = InviteRateLimiter(redis_client=redis_client)

    key_a = limiter._make_key("alice@example.com")
    key_b = limiter._make_key("bob@example.com")

    assert key_a != key_b


@pytest.mark.asyncio
async def test_expire_set_on_first_increment() -> None:
    """When incr returns 1 (first increment), expire is called with ttl=7200."""
    limiter, redis_client = _make_limiter(incr_return=1)
    email = "user@example.com"
    key = limiter._make_key(email)

    await limiter.check_and_increment(email)

    redis_client.expire.assert_awaited_once_with(key, 7200)


@pytest.mark.asyncio
async def test_expire_not_set_on_subsequent_increments() -> None:
    """When incr returns 2, expire is not called (TTL already set)."""
    limiter, redis_client = _make_limiter(incr_return=2)
    await limiter.check_and_increment("user@example.com")
    redis_client.expire.assert_not_awaited()


@pytest.mark.asyncio
async def test_fail_open_on_redis_error() -> None:
    """Redis error during incr → returns True (fail-open policy)."""
    redis_client = AsyncMock()
    redis_client.incr = AsyncMock(side_effect=Exception("Redis connection refused"))
    redis_client.expire = AsyncMock(return_value=True)

    limiter = InviteRateLimiter(redis_client=redis_client)
    result = await limiter.check_and_increment("user@example.com")

    assert result is True


def test_key_includes_hour_bucket() -> None:
    """_make_key output starts with 'invite_magiclink:' and has 3 colon-separated parts."""
    redis_client = AsyncMock()
    limiter = InviteRateLimiter(redis_client=redis_client)

    key = limiter._make_key("user@example.com")

    assert key.startswith("invite_magiclink:")
    parts = key.split(":")
    assert len(parts) == 3
    # Middle part is YYYYMMDDHH (10 digits)
    assert len(parts[1]) == 10
    assert parts[1].isdigit()
    # Last part is sha256[:12] (12 hex chars)
    assert len(parts[2]) == 12
