"""Unit tests for shared provider-service mapping constants."""

from __future__ import annotations

from pilot_space.ai.providers.constants import (
    PROVIDER_SERVICE_SLOTS,
    VALID_PROVIDER_SERVICES,
    VALID_PROVIDERS,
)


class TestProviderConstants:
    """Verify consistency of provider constant definitions."""

    def test_valid_providers_matches_service_map_keys(self) -> None:
        """VALID_PROVIDERS must equal the keys of VALID_PROVIDER_SERVICES."""
        assert frozenset(VALID_PROVIDER_SERVICES.keys()) == VALID_PROVIDERS

    def test_slots_only_contain_valid_providers(self) -> None:
        """Every provider in PROVIDER_SERVICE_SLOTS must be in VALID_PROVIDERS."""
        for provider, _service_type, _both in PROVIDER_SERVICE_SLOTS:
            assert provider in VALID_PROVIDERS, f"{provider} not in VALID_PROVIDERS"

    def test_slots_only_contain_valid_service_types(self) -> None:
        """Every service_type in PROVIDER_SERVICE_SLOTS must be allowed for that provider."""
        for provider, service_type, _both in PROVIDER_SERVICE_SLOTS:
            allowed = VALID_PROVIDER_SERVICES[provider]
            assert service_type in allowed, (
                f"{provider}:{service_type} not in allowed set {allowed}"
            )

    def test_openai_not_in_valid_providers(self) -> None:
        """openai must not be in the valid provider set (removed)."""
        assert "openai" not in VALID_PROVIDERS

    def test_slots_have_expected_providers(self) -> None:
        """Slots should contain google, anthropic, ollama entries."""
        slot_providers = {p for p, _, _ in PROVIDER_SERVICE_SLOTS}
        assert slot_providers == {"google", "anthropic", "ollama"}

    def test_ollama_supports_both(self) -> None:
        """Ollama slots should have supports_both=True."""
        for provider, _st, supports_both in PROVIDER_SERVICE_SLOTS:
            if provider == "ollama":
                assert supports_both is True
