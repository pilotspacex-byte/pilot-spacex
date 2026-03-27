"""Singleton pool of AsyncAnthropic clients keyed by API key identity.

Managed by the DI container (providers.Singleton). Each distinct API key
gets its own AsyncAnthropic (and httpx connection pool), reused across
requests. This avoids allocating a new TCP connection pool on every
ghost text call under 500ms polling load.

Security: Plaintext API keys are NOT used as dict keys. Each unique
(api_key, base_url) pair is assigned a monotonic integer index on first
access. The raw key is passed to AsyncAnthropic() only and is not stored
in the cache key namespace.
"""

from __future__ import annotations

from typing import Any

import anthropic


class AnthropicClientPool:
    """Per-API-key AsyncAnthropic client cache.

    Each distinct API key gets its own AsyncAnthropic instance, which
    internally holds an httpx.AsyncClient with its own connection pool.
    Reusing the same client across requests for the same key avoids
    allocating a new TCP connection pool on every call.

    Thread safety: dict assignment is atomic in CPython. At worst, two
    clients are created simultaneously on first access for a key — both
    are valid; one is discarded. Self-healing on the next request.
    """

    def __init__(self) -> None:
        """Initialize empty client pool."""
        self._clients: dict[int, anthropic.AsyncAnthropic] = {}
        # Maps (api_key, base_url) identity to integer index.
        # Uses id() of interned key strings to avoid storing plaintext
        # keys as dict keys while still deduplicating correctly.
        self._key_index: dict[tuple[str, str | None], int] = {}
        self._next_id: int = 0

    def _get_slot(self, api_key: str, base_url: str | None = None) -> int:
        """Get or assign an integer slot for this (api_key, base_url) pair."""
        identity = (api_key, base_url)
        if identity not in self._key_index:
            self._key_index[identity] = self._next_id
            self._next_id += 1
        return self._key_index[identity]

    def get_client(
        self,
        api_key: str,
        base_url: str | None = None,
    ) -> anthropic.AsyncAnthropic:
        """Return cached client for api_key + base_url, creating one if absent.

        Args:
            api_key: Workspace-specific API key.
            base_url: Optional base URL for Ollama/proxy endpoints.

        Returns:
            Reusable AsyncAnthropic client for that key + base_url combo.
        """
        slot = self._get_slot(api_key, base_url)
        if slot not in self._clients:
            kwargs: dict[str, Any] = {"api_key": api_key}
            if base_url:
                kwargs["base_url"] = base_url
            self._clients[slot] = anthropic.AsyncAnthropic(**kwargs)
        return self._clients[slot]

    def evict(self, api_key: str) -> bool:
        """Remove cached client for an API key.

        Call after key rotation to ensure the old client (and its httpx
        connection pool) is garbage-collected on next GC cycle.

        Args:
            api_key: The API key whose client should be evicted.

        Returns:
            True if a client was found and removed, False if the key was
            not cached (already evicted or never used).
        """
        # Find all slots matching this api_key (any base_url)
        removed = False
        keys_to_remove = [k for k in self._key_index if k[0] == api_key]
        for key in keys_to_remove:
            slot = self._key_index.pop(key)
            if self._clients.pop(slot, None) is not None:
                removed = True
        return removed


__all__ = ["AnthropicClientPool"]
