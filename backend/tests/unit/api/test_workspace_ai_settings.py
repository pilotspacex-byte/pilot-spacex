"""Unit tests for workspace AI settings schemas.

Tests for APIKeyUpdate and ProviderStatus Pydantic schemas covering:
- 3 providers: google, anthropic, ollama
- service_type required field
- base_url/model_name optional fields
- api_key optional for ollama
- base_url/model_name optional fields on ProviderStatus
"""

from __future__ import annotations

import pydantic
import pytest

from pilot_space.api.v1.schemas.workspace import APIKeyUpdate, ProviderStatus


class TestAPIKeyUpdateSchema:
    """Tests for APIKeyUpdate Pydantic schema validation."""

    @pytest.mark.parametrize(
        ("provider", "service_type"),
        [
            ("google", "embedding"),
            ("anthropic", "llm"),
            ("ollama", "llm"),
            ("ollama", "embedding"),
        ],
    )
    def test_valid_provider_service_combos_accepted(self, provider: str, service_type: str) -> None:
        update = APIKeyUpdate(
            provider=provider,
            service_type=service_type,
            api_key="sk-test-1234567890",  # pragma: allowlist secret
        )
        assert update.provider == provider
        assert update.service_type == service_type

    @pytest.mark.parametrize(
        ("provider", "service_type"),
        [
            ("google", "llm"),
            ("anthropic", "embedding"),
        ],
    )
    def test_invalid_provider_service_combos_rejected(
        self, provider: str, service_type: str
    ) -> None:
        with pytest.raises(pydantic.ValidationError, match="Invalid combination"):
            APIKeyUpdate(
                provider=provider,
                service_type=service_type,
                api_key="sk-test-1234567890",  # pragma: allowlist secret
            )

    def test_invalid_provider_rejected(self) -> None:
        with pytest.raises(pydantic.ValidationError, match="provider"):
            APIKeyUpdate(
                provider="openai",
                service_type="llm",
                api_key="sk-test-1234567890",  # pragma: allowlist secret
            )

    def test_invalid_service_type_rejected(self) -> None:
        with pytest.raises(pydantic.ValidationError, match="service_type"):
            APIKeyUpdate(
                provider="anthropic",
                service_type="invalid",
                api_key="sk-test-1234567890",  # pragma: allowlist secret
            )

    def test_service_type_required(self) -> None:
        with pytest.raises(pydantic.ValidationError, match=r"serviceType|service_type"):
            APIKeyUpdate(
                provider="anthropic",
                api_key="sk-test-1234567890",  # pragma: allowlist secret
            )  # type: ignore[call-arg]

    def test_base_url_optional(self) -> None:
        update = APIKeyUpdate(
            provider="google",
            service_type="embedding",
            api_key="AIza-test-key",  # pragma: allowlist secret
            base_url="https://custom.api.com/v1",
        )
        assert update.base_url == "https://custom.api.com/v1"

    def test_model_name_optional(self) -> None:
        update = APIKeyUpdate(
            provider="ollama",
            service_type="llm",
            model_name="qwen2.5",
        )
        assert update.model_name == "qwen2.5"

    def test_base_url_and_model_name_none_by_default(self) -> None:
        update = APIKeyUpdate(
            provider="anthropic",
            service_type="llm",
            api_key="sk-ant-test-key",  # pragma: allowlist secret
        )
        assert update.base_url is None
        assert update.model_name is None

    def test_api_key_none_allowed(self) -> None:
        """Ollama doesn't require API key."""
        update = APIKeyUpdate(
            provider="ollama",
            service_type="llm",
            api_key=None,
        )
        assert update.api_key is None

    def test_base_url_rejects_invalid_url(self) -> None:
        with pytest.raises(pydantic.ValidationError, match="base_url"):
            APIKeyUpdate(
                provider="google",
                service_type="embedding",
                api_key="AIza-test-key",  # pragma: allowlist secret
                base_url="not-a-url",
            )

    def test_base_url_accepts_http(self) -> None:
        update = APIKeyUpdate(
            provider="ollama",
            service_type="llm",
            base_url="http://localhost:11434",
        )
        assert update.base_url == "http://localhost:11434"

    def test_base_url_rejects_bare_scheme(self) -> None:
        """M-2: base_url must have a host, not just 'https://'."""
        with pytest.raises(pydantic.ValidationError, match="base_url"):
            APIKeyUpdate(
                provider="google",
                api_key="AIza-test-key",  # pragma: allowlist secret
                base_url="https://",
            )

    def test_model_name_max_length(self) -> None:
        """M-1: model_name must not exceed 200 chars."""
        with pytest.raises(pydantic.ValidationError, match="model_name"):
            APIKeyUpdate(
                provider="ollama",
                service_type="llm",
                model_name="x" * 201,
            )

    def test_model_name_within_limit_accepted(self) -> None:
        update = APIKeyUpdate(
            provider="ollama",
            service_type="llm",
            model_name="x" * 200,
        )
        assert len(update.model_name or "") == 200

    def test_base_url_max_length(self) -> None:
        with pytest.raises(pydantic.ValidationError, match="base_url"):
            APIKeyUpdate(
                provider="ollama",
                service_type="llm",
                base_url="https://example.com/" + "x" * 2048,
            )


class TestProviderStatusSchema:
    """Tests for ProviderStatus Pydantic schema."""

    def test_service_type_required(self) -> None:
        status = ProviderStatus(
            provider="google",
            service_type="embedding",
            is_configured=True,
        )
        assert status.service_type == "embedding"

    def test_base_url_and_model_name_fields_present(self) -> None:
        status = ProviderStatus(
            provider="google",
            service_type="embedding",
            is_configured=True,
            base_url="https://custom.example.com",
            model_name="gemini-pro",
        )
        assert status.base_url == "https://custom.example.com"
        assert status.model_name == "gemini-pro"

    def test_base_url_model_name_default_none(self) -> None:
        status = ProviderStatus(
            provider="anthropic",
            service_type="llm",
            is_configured=False,
        )
        assert status.base_url is None
        assert status.model_name is None

    @pytest.mark.parametrize("provider", ["google", "anthropic", "ollama"])
    def test_supported_providers_valid(self, provider: str) -> None:
        status = ProviderStatus(
            provider=provider,
            service_type="llm",
            is_configured=False,
        )
        assert status.provider == provider
