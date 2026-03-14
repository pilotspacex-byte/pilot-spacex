"""Unit tests for workspace AI settings schemas.

Tests for APIKeyUpdate and ProviderStatus Pydantic schemas covering:
- All 6 providers accepted in APIKeyUpdate
- base_url/model_name optional fields in both schemas
- Invalid provider rejection
- URL validation on base_url
"""

from __future__ import annotations

import pydantic
import pytest

from pilot_space.api.v1.schemas.workspace import APIKeyUpdate, ProviderStatus


class TestAPIKeyUpdateSchema:
    """Tests for APIKeyUpdate Pydantic schema validation."""

    @pytest.mark.parametrize(
        "provider",
        ["anthropic", "openai", "google", "kimi", "glm", "ai_agent"],
    )
    def test_valid_providers_accepted(self, provider: str) -> None:
        update = APIKeyUpdate(
            provider=provider,
            api_key="sk-test-1234567890",  # pragma: allowlist secret
        )
        assert update.provider == provider

    def test_invalid_provider_rejected(self) -> None:
        with pytest.raises(pydantic.ValidationError, match="provider"):
            APIKeyUpdate(
                provider="unsupported",
                api_key="sk-test-1234567890",  # pragma: allowlist secret
            )

    def test_base_url_optional(self) -> None:
        update = APIKeyUpdate(
            provider="google",
            api_key="AIza-test-key",  # pragma: allowlist secret
            base_url="https://custom.api.com/v1",
        )
        assert update.base_url == "https://custom.api.com/v1"

    def test_model_name_optional(self) -> None:
        update = APIKeyUpdate(
            provider="ai_agent",
            api_key="sk-agent-key-1234",  # pragma: allowlist secret
            model_name="claude-3-5-sonnet-20241022",
        )
        assert update.model_name == "claude-3-5-sonnet-20241022"

    def test_base_url_and_model_name_none_by_default(self) -> None:
        update = APIKeyUpdate(
            provider="anthropic",
            api_key="sk-ant-test-key",  # pragma: allowlist secret
        )
        assert update.base_url is None
        assert update.model_name is None

    def test_api_key_none_allowed(self) -> None:
        update = APIKeyUpdate(provider="openai", api_key=None)
        assert update.api_key is None

    def test_base_url_rejects_invalid_url(self) -> None:
        with pytest.raises(pydantic.ValidationError, match="base_url"):
            APIKeyUpdate(
                provider="google",
                api_key="AIza-test-key",  # pragma: allowlist secret
                base_url="not-a-url",
            )

    def test_base_url_accepts_http(self) -> None:
        update = APIKeyUpdate(
            provider="ai_agent",
            api_key="sk-test-1234567890",  # pragma: allowlist secret
            base_url="http://localhost:8080/v1",
        )
        assert update.base_url == "http://localhost:8080/v1"

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
                provider="ai_agent",
                api_key="sk-test-1234567890",  # pragma: allowlist secret
                model_name="x" * 201,
            )

    def test_model_name_within_limit_accepted(self) -> None:
        update = APIKeyUpdate(
            provider="ai_agent",
            api_key="sk-test-1234567890",  # pragma: allowlist secret
            model_name="x" * 200,
        )
        assert len(update.model_name or "") == 200

    def test_base_url_max_length(self) -> None:
        with pytest.raises(pydantic.ValidationError, match="base_url"):
            APIKeyUpdate(
                provider="ai_agent",
                api_key="sk-test-1234567890",  # pragma: allowlist secret
                base_url="https://example.com/" + "x" * 2048,
            )


class TestProviderStatusSchema:
    """Tests for ProviderStatus Pydantic schema."""

    def test_base_url_and_model_name_fields_present(self) -> None:
        status = ProviderStatus(
            provider="google",
            is_configured=True,
            base_url="https://custom.example.com",
            model_name="gemini-pro",
        )
        assert status.base_url == "https://custom.example.com"
        assert status.model_name == "gemini-pro"

    def test_base_url_model_name_default_none(self) -> None:
        status = ProviderStatus(provider="anthropic", is_configured=False)
        assert status.base_url is None
        assert status.model_name is None

    def test_all_six_providers_valid_in_status(self) -> None:
        """ProviderStatus accepts any string for provider field."""
        for provider in ["anthropic", "openai", "google", "kimi", "glm", "ai_agent"]:
            status = ProviderStatus(provider=provider, is_configured=False)
            assert status.provider == provider
