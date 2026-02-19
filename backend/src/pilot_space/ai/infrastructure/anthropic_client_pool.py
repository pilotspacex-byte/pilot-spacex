"""Singleton pool of AsyncAnthropic clients keyed by hashed API key.

Managed by the DI container (providers.Singleton). Each distinct API key
gets its own AsyncAnthropic (and httpx connection pool), reused across
requests. This avoids allocating a new TCP connection pool on every
ghost text call under 500ms polling load.

Security: Dict keys are truncated SHA-256 hashes — plaintext API keys
never appear as dictionary keys. The raw key is passed to AsyncAnthropic()
only and is not stored anywhere else.
"""

from __future__ import annotations

import hashlib

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

    Security: API keys are hashed before use as dict keys. The truncated
    SHA-256 prefix probabilistically identifies the key without exposing
    its value (collision probability ~1 in 2^64).
    """

    def __init__(self) -> None:
        """Initialize empty client pool."""
        self._clients: dict[str, anthropic.AsyncAnthropic] = {}

    def get_client(self, api_key: str) -> anthropic.AsyncAnthropic:
        """Return cached client for api_key, creating one if absent.

        Args:
            api_key: Workspace-specific Anthropic API key.

        Returns:
            Reusable AsyncAnthropic client for that key.
        """
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()[:16]
        if key_hash not in self._clients:
            self._clients[key_hash] = anthropic.AsyncAnthropic(api_key=api_key)
        return self._clients[key_hash]

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
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()[:16]
        return self._clients.pop(key_hash, None) is not None


__all__ = ["AnthropicClientPool"]
