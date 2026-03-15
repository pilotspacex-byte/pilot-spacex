"""Shared provider-service mapping constants."""

# Canonical provider -> service_type mapping.
# Each tuple: (provider, service_type, supports_both)
PROVIDER_SERVICE_SLOTS: list[tuple[str, str, bool]] = [
    ("google", "embedding", False),
    ("ollama", "embedding", True),
    ("anthropic", "llm", False),
    ("ollama", "llm", True),
]

# Valid provider -> allowed service_types
VALID_PROVIDER_SERVICES: dict[str, set[str]] = {
    "google": {"embedding"},
    "anthropic": {"llm"},
    "ollama": {"embedding", "llm"},
}

# All valid provider names
VALID_PROVIDERS: frozenset[str] = frozenset(VALID_PROVIDER_SERVICES.keys())
