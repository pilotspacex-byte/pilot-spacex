"""Tests for env-based model resolution and SDK env construction.

Covers:
- ModelTier.model_id env var overrides (PILOTSPACE_MODEL_*_DEFAULT)
- get_model_for_task() env-aware routing
- build_sdk_env() helper with ANTHROPIC_BASE_URL forwarding
- Settings.anthropic_base_url field
"""

from __future__ import annotations

import pytest

from pilot_space.ai.sdk.config import MODEL_OPUS, build_sdk_env, get_model_for_task
from pilot_space.ai.sdk.sandbox_config import ModelTier
from pilot_space.config import get_settings


@pytest.fixture(autouse=True)
def _clear_settings_cache() -> None:
    """Prevent stale lru_cache across tests that mutate env vars."""
    get_settings.cache_clear()
    yield  # type: ignore[misc]
    get_settings.cache_clear()


class TestModelTierEnvOverride:
    """ModelTier.model_id reads PILOTSPACE_MODEL_*_DEFAULT env vars."""

    def test_sonnet_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("PILOTSPACE_MODEL_SONNET_DEFAULT", raising=False)
        assert ModelTier.SONNET.model_id == "claude-sonnet-4-20250514"

    def test_sonnet_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PILOTSPACE_MODEL_SONNET_DEFAULT", "kimi-k2.5:cloud")
        assert ModelTier.SONNET.model_id == "kimi-k2.5:cloud"

    def test_opus_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("PILOTSPACE_MODEL_OPUS_DEFAULT", raising=False)
        assert ModelTier.OPUS.model_id == "claude-opus-4-5-20251101"

    def test_opus_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PILOTSPACE_MODEL_OPUS_DEFAULT", "kimi-k2.5:cloud")
        assert ModelTier.OPUS.model_id == "kimi-k2.5:cloud"

    def test_haiku_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("PILOTSPACE_MODEL_HAIKU_DEFAULT", raising=False)
        assert ModelTier.HAIKU.model_id == "claude-haiku-4-5-20251001"

    def test_haiku_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PILOTSPACE_MODEL_HAIKU_DEFAULT", "bjoernb/claude-haiku-4-5")
        assert ModelTier.HAIKU.model_id == "bjoernb/claude-haiku-4-5"


class TestGetModelForTask:
    """get_model_for_task() resolves via ModelTier (env-aware)."""

    def test_code_uses_sonnet(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("PILOTSPACE_MODEL_SONNET_DEFAULT", raising=False)
        result = get_model_for_task("code")
        assert result == ModelTier.SONNET.model_id

    def test_architecture_uses_opus(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("PILOTSPACE_MODEL_OPUS_DEFAULT", raising=False)
        result = get_model_for_task("architecture")
        assert result == MODEL_OPUS

    def test_code_respects_env_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PILOTSPACE_MODEL_SONNET_DEFAULT", "custom-sonnet")
        result = get_model_for_task("code")
        assert result == "custom-sonnet"

    def test_latency_returns_gemini(self) -> None:
        result = get_model_for_task("latency")
        assert result == "gemini-2.0-flash"

    def test_embedding_returns_openai(self) -> None:
        result = get_model_for_task("embedding")
        assert result == "text-embedding-3-large"

    def test_unknown_falls_back_to_sonnet(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("PILOTSPACE_MODEL_SONNET_DEFAULT", raising=False)
        result = get_model_for_task("unknown_task")
        assert result == ModelTier.SONNET.model_id


class TestBuildSdkEnv:
    """build_sdk_env() centralizes SDK subprocess env dict."""

    def test_includes_api_key(self) -> None:
        env = build_sdk_env("sk-test-123")
        assert env["ANTHROPIC_API_KEY"] == "sk-test-123"  # pragma: allowlist secret

    def test_includes_path_and_home(self) -> None:
        env = build_sdk_env("sk-test")
        assert "PATH" in env
        assert "HOME" in env

    def test_forwards_base_url_when_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ANTHROPIC_BASE_URL", "http://localhost:11434")
        env = build_sdk_env("sk-test")
        assert env["ANTHROPIC_BASE_URL"] == "http://localhost:11434"

    def test_omits_base_url_when_unset(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("ANTHROPIC_BASE_URL", raising=False)
        env = build_sdk_env("sk-test")
        assert "ANTHROPIC_BASE_URL" not in env


class TestSettingsAnthropicBaseUrl:
    """Settings.anthropic_base_url field."""

    def test_defaults_to_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from pilot_space.config import Settings

        monkeypatch.delenv("ANTHROPIC_BASE_URL", raising=False)
        settings = Settings()
        assert settings.anthropic_base_url is None

    def test_reads_env_var(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from pilot_space.config import Settings

        monkeypatch.setenv("ANTHROPIC_BASE_URL", "http://localhost:11434")
        settings = Settings()
        assert settings.anthropic_base_url == "http://localhost:11434"
