"""Shared provider-service mapping constants."""

from __future__ import annotations

import ipaddress
from urllib.parse import urlparse

# Canonical provider -> service_type mapping.
# Each tuple: (provider, service_type, supports_both)
PROVIDER_SERVICE_SLOTS: list[tuple[str, str, bool]] = [
    ("google", "embedding", False),
    ("ollama", "embedding", True),
    ("anthropic", "llm", False),
    ("ollama", "llm", True),
    ("elevenlabs", "stt", False),
]

# Valid provider -> allowed service_types
VALID_PROVIDER_SERVICES: dict[str, set[str]] = {
    "google": {"embedding"},
    "anthropic": {"llm"},
    "ollama": {"embedding", "llm"},
    "elevenlabs": {"stt"},
}

# All valid provider names
VALID_PROVIDERS: frozenset[str] = frozenset(VALID_PROVIDER_SERVICES.keys())


def validate_ollama_base_url(url: str) -> str:
    """Validate Ollama base URL — allows HTTP but blocks private/reserved IPs.

    Ollama typically runs on localhost in dev, but in production the base_url
    must not point to cloud metadata endpoints or internal services.

    Raises:
        ValueError: If URL points to a private, reserved, or link-local address.
    """
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"base_url must use HTTP or HTTPS, got: {parsed.scheme!r}")
    hostname = parsed.hostname
    if not hostname:
        raise ValueError("base_url has no hostname")

    # Block cloud metadata and link-local endpoints
    _metadata_blocked = {"169.254.169.254", "metadata.google.internal"}
    if hostname.lower() in _metadata_blocked:
        raise ValueError("base_url must not point to cloud metadata endpoints")

    try:
        addr = ipaddress.ip_address(hostname)
    except ValueError:
        return url  # Not a bare IP — hostname like "ollama.internal" is fine

    if addr.is_link_local:
        raise ValueError("base_url must not point to a link-local address")
    # Allow localhost (127.x) and private IPs (10.x, 172.16-31.x, 192.168.x)
    # for local/on-prem Ollama deployments
    return url
