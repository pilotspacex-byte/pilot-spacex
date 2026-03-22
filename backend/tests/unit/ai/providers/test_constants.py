"""Unit tests for shared provider-service mapping constants."""

from __future__ import annotations

import pytest

from pilot_space.ai.providers.constants import (
    PROVIDER_SERVICE_SLOTS,
    VALID_PROVIDER_SERVICES,
    VALID_PROVIDERS,
    validate_ollama_base_url,
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
        """Slots should contain google, anthropic, ollama, elevenlabs entries."""
        slot_providers = {p for p, _, _ in PROVIDER_SERVICE_SLOTS}
        assert slot_providers == {"google", "anthropic", "ollama", "elevenlabs"}

    def test_ollama_supports_both(self) -> None:
        """Ollama slots should have supports_both=True."""
        for provider, _st, supports_both in PROVIDER_SERVICE_SLOTS:
            if provider == "ollama":
                assert supports_both is True


class TestValidateOllamaBaseUrl:
    """SSRF protection tests for Ollama base_url validation."""

    def test_allows_localhost(self) -> None:
        assert validate_ollama_base_url("http://localhost:11434") == "http://localhost:11434"

    def test_allows_private_ip(self) -> None:
        assert (
            validate_ollama_base_url("http://192.168.1.100:11434") == "http://192.168.1.100:11434"
        )

    def test_allows_https(self) -> None:
        assert (
            validate_ollama_base_url("https://ollama.example.com") == "https://ollama.example.com"
        )

    def test_allows_hostname(self) -> None:
        assert (
            validate_ollama_base_url("http://ollama.internal:11434")
            == "http://ollama.internal:11434"
        )

    def test_blocks_cloud_metadata_ip(self) -> None:
        with pytest.raises(ValueError, match="cloud metadata"):
            validate_ollama_base_url("http://169.254.169.254")

    def test_blocks_cloud_metadata_hostname(self) -> None:
        with pytest.raises(ValueError, match="cloud metadata"):
            validate_ollama_base_url("http://metadata.google.internal")

    def test_blocks_link_local_ip(self) -> None:
        with pytest.raises(ValueError, match="link-local"):
            validate_ollama_base_url("http://169.254.1.1")

    def test_blocks_invalid_scheme(self) -> None:
        with pytest.raises(ValueError, match="HTTP or HTTPS"):
            validate_ollama_base_url("ftp://ollama.example.com")

    def test_blocks_no_hostname(self) -> None:
        with pytest.raises(ValueError, match="no hostname"):
            validate_ollama_base_url("http://")

    def test_blocks_metadata_with_path(self) -> None:
        with pytest.raises(ValueError, match="cloud metadata"):
            validate_ollama_base_url("http://169.254.169.254/latest/meta-data/")
