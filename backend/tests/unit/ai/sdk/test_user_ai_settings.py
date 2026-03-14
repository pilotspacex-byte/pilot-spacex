"""Tests for user AI settings resolution.

Verifies that per-user ai_settings overrides work correctly for:
- Model tier resolution (user > env > hardcoded default)
- SDK env base_url override
- Auth schema serialization
"""

from __future__ import annotations

import os
from datetime import UTC
from typing import Any
from unittest.mock import patch

import pytest

from pilot_space.ai.sdk.config import build_sdk_env, validate_base_url
from pilot_space.ai.sdk.sandbox_config import ModelTier, resolve_model
from pilot_space.api.v1.schemas.auth import UserProfileResponse, UserProfileUpdateRequest
from pilot_space.config import get_settings


@pytest.fixture(autouse=True)
def _clear_settings_cache() -> Any:
    """Clear lru_cache on get_settings between tests (Gotcha #3)."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


class TestResolveModelForUser:
    """Tests for resolve_model function."""

    def test_user_override_sonnet(self) -> None:
        """User ai_settings model_sonnet overrides default."""
        settings: dict[str, Any] = {"model_sonnet": "claude-sonnet-4-20250514-custom"}
        result = resolve_model(ModelTier.SONNET, user_ai_settings=settings)
        assert result == "claude-sonnet-4-20250514-custom"

    def test_user_override_haiku_leaves_others_default(self) -> None:
        """User haiku override doesn't affect sonnet/opus."""
        settings: dict[str, Any] = {"model_haiku": "custom-haiku"}
        haiku = resolve_model(ModelTier.HAIKU, user_ai_settings=settings)
        assert haiku == "custom-haiku"

        # Sonnet and Opus should fall back to defaults (no env set)
        with patch.dict(os.environ, {}, clear=False):
            # Remove env vars if they exist
            env = {
                k: v
                for k, v in os.environ.items()
                if k not in ("PILOTSPACE_MODEL_SONNET_DEFAULT", "PILOTSPACE_MODEL_OPUS_DEFAULT")
            }
            with patch.dict(os.environ, env, clear=True):
                sonnet = resolve_model(ModelTier.SONNET, user_ai_settings=settings)
                opus = resolve_model(ModelTier.OPUS, user_ai_settings=settings)
                assert sonnet == "claude-sonnet-4-20250514"
                assert opus == "claude-opus-4-5-20251101"

    def test_empty_settings_falls_back_to_env(self) -> None:
        """Empty ai_settings falls back to env var."""
        with patch.dict(
            os.environ,
            {"PILOTSPACE_MODEL_SONNET_DEFAULT": "env-sonnet-model"},
        ):
            result = resolve_model(ModelTier.SONNET, user_ai_settings={})
            assert result == "env-sonnet-model"

    def test_none_settings_falls_back_to_env(self) -> None:
        """None ai_settings falls back to env var."""
        with patch.dict(
            os.environ,
            {"PILOTSPACE_MODEL_OPUS_DEFAULT": "env-opus-model"},
        ):
            result = resolve_model(ModelTier.OPUS, user_ai_settings=None)
            assert result == "env-opus-model"

    def test_no_env_falls_back_to_hardcoded(self) -> None:
        """No env var falls back to hardcoded default."""
        env = {k: v for k, v in os.environ.items() if k not in ("PILOTSPACE_MODEL_HAIKU_DEFAULT",)}
        with patch.dict(os.environ, env, clear=True):
            result = resolve_model(ModelTier.HAIKU, user_ai_settings=None)
            assert result == "claude-haiku-4-5-20251001"

    def test_user_override_takes_priority_over_env(self) -> None:
        """User override beats env var."""
        settings: dict[str, Any] = {"model_sonnet": "user-sonnet"}
        with patch.dict(
            os.environ,
            {"PILOTSPACE_MODEL_SONNET_DEFAULT": "env-sonnet"},
        ):
            result = resolve_model(ModelTier.SONNET, user_ai_settings=settings)
            assert result == "user-sonnet"


class TestBuildSdkEnvForUser:
    """Tests for build_sdk_env function."""

    def test_user_base_url_override(self) -> None:
        """User ai_settings base_url overrides system default."""
        settings: dict[str, Any] = {"base_url": "https://proxy.example.com"}
        env = build_sdk_env("test-key", user_ai_settings=settings)  # pragma: allowlist secret
        assert env["ANTHROPIC_BASE_URL"] == "https://proxy.example.com"

    def test_no_user_base_url_uses_system(self) -> None:
        """Without user base_url, falls back to Settings().anthropic_base_url."""
        env = build_sdk_env("test-key", user_ai_settings={})  # pragma: allowlist secret
        # Should have same behavior as build_sdk_env
        assert env["ANTHROPIC_API_KEY"] == "test-key"  # pragma: allowlist secret

    def test_none_settings_uses_system(self) -> None:
        """None ai_settings falls back to system default."""
        env = build_sdk_env("test-key", user_ai_settings=None)  # pragma: allowlist secret
        assert env["ANTHROPIC_API_KEY"] == "test-key"  # pragma: allowlist secret


class TestValidateBaseUrl:
    """Tests for validate_base_url SSRF prevention."""

    def test_valid_https_url(self) -> None:
        """Accepts valid HTTPS URL with public hostname."""
        result = validate_base_url("https://proxy.example.com/v1")
        assert result == "https://proxy.example.com/v1"

    def test_rejects_http(self) -> None:
        """Rejects non-HTTPS scheme."""
        with pytest.raises(ValueError, match="must use HTTPS"):
            validate_base_url("http://proxy.example.com")

    def test_rejects_localhost(self) -> None:
        """Rejects localhost."""
        with pytest.raises(ValueError, match="must not point to localhost"):
            validate_base_url("https://localhost:8080")

    def test_rejects_127_0_0_1(self) -> None:
        """Rejects loopback IP."""
        with pytest.raises(ValueError, match="must not point to localhost"):
            validate_base_url("https://127.0.0.1:8080")

    def test_rejects_private_ip(self) -> None:
        """Rejects private network IPs (e.g., 10.x, 192.168.x)."""
        with pytest.raises(ValueError, match="private or reserved"):
            validate_base_url("https://10.0.0.5:8080")

    def test_rejects_link_local_ip(self) -> None:
        """Rejects link-local IPs (169.254.x.x)."""
        with pytest.raises(ValueError, match="private or reserved"):
            validate_base_url("https://169.254.1.1")

    def test_rejects_no_hostname(self) -> None:
        """Rejects URL with no hostname."""
        with pytest.raises(ValueError, match="no hostname"):
            validate_base_url("https://")

    def test_rejects_ftp_scheme(self) -> None:
        """Rejects non-HTTP schemes like ftp."""
        with pytest.raises(ValueError, match="must use HTTPS"):
            validate_base_url("ftp://files.example.com")

    def test_build_sdk_env_rejects_bad_user_url(self) -> None:
        """build_sdk_env raises ValueError for non-HTTPS user base_url."""
        with pytest.raises(ValueError, match="must use HTTPS"):
            build_sdk_env(
                "test-key",  # pragma: allowlist secret
                user_ai_settings={"base_url": "http://evil.com"},
            )


class TestAuthSchemas:
    """Tests for ai_settings in auth schemas."""

    def test_update_request_accepts_ai_settings(self) -> None:
        """UserProfileUpdateRequest accepts AiSettingsSchema dict."""
        req = UserProfileUpdateRequest(
            ai_settings={"model_sonnet": "custom-sonnet", "base_url": "https://proxy.example.com"}
        )
        assert req.ai_settings is not None
        assert req.ai_settings.model_sonnet == "custom-sonnet"
        assert req.ai_settings.base_url == "https://proxy.example.com"

    def test_update_request_rejects_http_base_url(self) -> None:
        """UserProfileUpdateRequest rejects non-HTTPS base_url."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError, match="base_url"):
            UserProfileUpdateRequest(ai_settings={"base_url": "http://evil.com"})

    def test_update_request_rejects_private_ip_base_url(self) -> None:
        """UserProfileUpdateRequest rejects private IP base_url."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError, match="base_url"):
            UserProfileUpdateRequest(ai_settings={"base_url": "https://192.168.1.1"})

    def test_update_request_ai_settings_default_none(self) -> None:
        """UserProfileUpdateRequest ai_settings defaults to None."""
        req = UserProfileUpdateRequest()
        assert req.ai_settings is None

    def test_response_includes_ai_settings(self) -> None:
        """UserProfileResponse includes ai_settings field."""
        from datetime import datetime
        from uuid import uuid4

        resp = UserProfileResponse(
            id=uuid4(),
            email="test@example.com",
            created_at=datetime.now(tz=UTC),
            ai_settings={"model_haiku": "custom-haiku"},
        )
        assert resp.ai_settings is not None
        assert resp.ai_settings.model_haiku == "custom-haiku"

    def test_response_ai_settings_default_none(self) -> None:
        """UserProfileResponse ai_settings defaults to None."""
        from datetime import datetime
        from uuid import uuid4

        resp = UserProfileResponse(
            id=uuid4(),
            email="test@example.com",
            created_at=datetime.now(tz=UTC),
        )
        assert resp.ai_settings is None

    def test_ai_settings_ignores_unknown_fields(self) -> None:
        """AiSettingsSchema silently ignores unknown fields."""
        from pilot_space.api.v1.schemas.auth import AiSettingsSchema

        settings = AiSettingsSchema.model_validate(
            {"model_sonnet": "custom", "unknown_field": "value"}
        )
        assert settings.model_sonnet == "custom"
        assert not hasattr(settings, "unknown_field")


class TestUpdateProfilePayloadSentinel:
    """Tests for the UNSET sentinel in UpdateProfilePayload."""

    def test_default_ai_settings_is_unset(self) -> None:
        """ai_settings defaults to UNSET sentinel, not None."""
        from uuid import uuid4

        from pilot_space.application.services.auth import UNSET, UpdateProfilePayload

        payload = UpdateProfilePayload(user_id=uuid4())
        assert payload.ai_settings is UNSET

    def test_explicit_none_is_not_unset(self) -> None:
        """Explicitly passing None is distinguishable from not provided."""
        from uuid import uuid4

        from pilot_space.application.services.auth import UNSET, UpdateProfilePayload

        payload = UpdateProfilePayload(user_id=uuid4(), ai_settings=None)
        assert payload.ai_settings is None
        assert payload.ai_settings is not UNSET

    def test_explicit_dict_is_not_unset(self) -> None:
        """Explicitly passing a dict is distinguishable from not provided."""
        from uuid import uuid4

        from pilot_space.application.services.auth import UNSET, UpdateProfilePayload

        payload = UpdateProfilePayload(user_id=uuid4(), ai_settings={"model_sonnet": "custom"})
        assert payload.ai_settings is not UNSET
        assert payload.ai_settings == {"model_sonnet": "custom"}
