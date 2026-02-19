"""Unit tests for AnthropicClientPool.

Tests client caching, API key security (no plaintext in dict keys),
hash usage, and constructor argument forwarding.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from pilot_space.ai.infrastructure.anthropic_client_pool import AnthropicClientPool

TEST_API_KEY = "sk-ant-test-key-12345"  # pragma: allowlist secret
TEST_API_KEY_2 = "sk-ant-other-key-98765"  # pragma: allowlist secret


@pytest.fixture
def pool() -> AnthropicClientPool:
    return AnthropicClientPool()


class TestAnthropicClientPool:
    def test_same_key_returns_same_client(self, pool: AnthropicClientPool) -> None:
        with patch(
            "pilot_space.ai.infrastructure.anthropic_client_pool.anthropic.AsyncAnthropic"
        ) as mock_cls:
            mock_client = MagicMock()
            mock_cls.return_value = mock_client

            client1 = pool.get_client(TEST_API_KEY)
            client2 = pool.get_client(TEST_API_KEY)

        assert client1 is client2
        mock_cls.assert_called_once()

    def test_different_keys_return_different_clients(self, pool: AnthropicClientPool) -> None:
        with patch(
            "pilot_space.ai.infrastructure.anthropic_client_pool.anthropic.AsyncAnthropic"
        ) as mock_cls:
            mock_cls.side_effect = [MagicMock(), MagicMock()]

            client1 = pool.get_client(TEST_API_KEY)
            client2 = pool.get_client(TEST_API_KEY_2)

        assert client1 is not client2
        assert mock_cls.call_count == 2

    def test_raw_key_not_in_dict_keys(self, pool: AnthropicClientPool) -> None:
        """Security: plaintext API keys must never appear as dict keys."""
        with patch("pilot_space.ai.infrastructure.anthropic_client_pool.anthropic.AsyncAnthropic"):
            pool.get_client(TEST_API_KEY)

        assert TEST_API_KEY not in pool._clients

    def test_hash_used_as_dict_key(self, pool: AnthropicClientPool) -> None:
        """Dict key is a 16-char hex string (truncated SHA-256)."""
        with patch("pilot_space.ai.infrastructure.anthropic_client_pool.anthropic.AsyncAnthropic"):
            pool.get_client(TEST_API_KEY)

        assert len(pool._clients) == 1
        key = next(iter(pool._clients))
        assert len(key) == 16
        # Verify it's valid hex
        int(key, 16)

    def test_api_key_passed_to_async_anthropic_constructor(self, pool: AnthropicClientPool) -> None:
        """Raw API key is passed to AsyncAnthropic(api_key=...) only."""
        with patch(
            "pilot_space.ai.infrastructure.anthropic_client_pool.anthropic.AsyncAnthropic"
        ) as mock_cls:
            pool.get_client(TEST_API_KEY)

        mock_cls.assert_called_once_with(api_key=TEST_API_KEY)

    def test_evict_removes_cached_client(self, pool: AnthropicClientPool) -> None:
        """evict() removes the client for the given key."""
        with patch("pilot_space.ai.infrastructure.anthropic_client_pool.anthropic.AsyncAnthropic"):
            pool.get_client(TEST_API_KEY)

        assert len(pool._clients) == 1
        assert pool.evict(TEST_API_KEY) is True
        assert len(pool._clients) == 0

    def test_evict_returns_false_for_unknown_key(self, pool: AnthropicClientPool) -> None:
        """evict() is a no-op and returns False when key is not cached."""
        assert pool.evict("sk-ant-nonexistent") is False  # pragma: allowlist secret

    def test_get_client_after_evict_creates_new_client(self, pool: AnthropicClientPool) -> None:
        """After eviction, the next get_client call creates a fresh client."""
        with patch(
            "pilot_space.ai.infrastructure.anthropic_client_pool.anthropic.AsyncAnthropic"
        ) as mock_cls:
            mock_cls.side_effect = [MagicMock(), MagicMock()]

            client1 = pool.get_client(TEST_API_KEY)
            pool.evict(TEST_API_KEY)
            client2 = pool.get_client(TEST_API_KEY)

        assert client1 is not client2
        assert mock_cls.call_count == 2
