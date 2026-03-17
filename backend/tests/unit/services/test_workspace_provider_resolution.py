"""Tests for resolve_workspace_llm_config helper and ProviderSelector workspace_override.

Tests the shared workspace LLM resolution helper extracted from GenerateRoleSkillService,
and the workspace_override parameter on ProviderSelector.select_with_config().
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest

from pilot_space.ai.providers.provider_selector import (
    ProviderSelector,
    TaskType,
    WorkspaceLLMConfig,
    resolve_workspace_llm_config,
)

WORKSPACE_ID = UUID("12345678-1234-5678-1234-567812345678")

_NOW = datetime(2026, 1, 1, tzinfo=UTC)


@pytest.fixture
def mock_session() -> AsyncMock:
    """Create a mock AsyncSession."""
    return AsyncMock()


@pytest.fixture
def mock_key_storage() -> MagicMock:
    """Create a mock SecureKeyStorage."""
    return MagicMock()


class TestResolveWorkspaceLLMConfig:
    """Tests for resolve_workspace_llm_config helper function."""

    async def test_returns_config_when_default_provider_has_key(
        self, mock_session: AsyncMock
    ) -> None:
        """resolve_workspace_llm_config returns WorkspaceLLMConfig when workspace has default LLM config."""
        from pilot_space.ai.infrastructure.key_storage import APIKeyInfo

        key_info = APIKeyInfo(
            workspace_id=WORKSPACE_ID,
            provider="anthropic",
            service_type="llm",
            is_valid=True,
            last_validated_at=None,
            validation_error=None,
            created_at=_NOW,
            updated_at=_NOW,
            base_url=None,
            model_name="claude-sonnet-4",
        )

        mock_storage = AsyncMock()
        mock_storage.get_key_info.return_value = key_info
        mock_storage.get_api_key.return_value = "sk-ant-test-key"  # pragma: allowlist secret

        # Simulate workspace settings query returning default_llm_provider
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = {"default_llm_provider": "anthropic"}
        mock_session.execute.return_value = mock_result

        with (
            patch(
                "pilot_space.ai.infrastructure.key_storage.SecureKeyStorage",
                return_value=mock_storage,
            ),
            patch("pilot_space.config.get_settings") as mock_settings,
        ):
            mock_settings.return_value.encryption_key.get_secret_value.return_value = (
                "test-encryption-key"
            )
            mock_settings.return_value.anthropic_api_key = None

            result = await resolve_workspace_llm_config(mock_session, WORKSPACE_ID)

        assert result is not None
        assert result.provider == "anthropic"
        assert result.api_key == "sk-ant-test-key"  # pragma: allowlist secret
        assert result.model_name == "claude-sonnet-4"

    async def test_returns_none_when_no_key_info_found(self, mock_session: AsyncMock) -> None:
        """resolve_workspace_llm_config returns None when workspace has no config and no app key."""
        mock_storage = AsyncMock()
        mock_storage.get_key_info.return_value = None
        mock_storage.get_all_key_infos.return_value = []

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = {}
        mock_session.execute.return_value = mock_result

        with (
            patch(
                "pilot_space.ai.infrastructure.key_storage.SecureKeyStorage",
                return_value=mock_storage,
            ),
            patch("pilot_space.config.get_settings") as mock_settings,
        ):
            mock_settings.return_value.encryption_key.get_secret_value.return_value = (
                "test-encryption-key"
            )
            mock_settings.return_value.anthropic_api_key = None

            result = await resolve_workspace_llm_config(mock_session, WORKSPACE_ID)

        assert result is None

    async def test_falls_back_to_any_llm_provider_when_default_has_no_key(
        self, mock_session: AsyncMock
    ) -> None:
        """resolve_workspace_llm_config falls back to any configured LLM when default has no key."""
        from pilot_space.ai.infrastructure.key_storage import APIKeyInfo

        fallback_key_info = APIKeyInfo(
            workspace_id=WORKSPACE_ID,
            provider="ollama",
            service_type="llm",
            is_valid=True,
            last_validated_at=None,
            validation_error=None,
            created_at=_NOW,
            updated_at=_NOW,
            base_url="http://localhost:11434",
            model_name="llama3.2",
        )

        mock_storage = AsyncMock()
        mock_storage.get_key_info.return_value = None  # default provider has no key
        mock_storage.get_all_key_infos.return_value = [fallback_key_info]
        mock_storage.get_api_key.return_value = "ollama-key"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = {"default_llm_provider": "anthropic"}
        mock_session.execute.return_value = mock_result

        with (
            patch(
                "pilot_space.ai.infrastructure.key_storage.SecureKeyStorage",
                return_value=mock_storage,
            ),
            patch("pilot_space.config.get_settings") as mock_settings,
        ):
            mock_settings.return_value.encryption_key.get_secret_value.return_value = (
                "test-encryption-key"
            )
            mock_settings.return_value.anthropic_api_key = None

            result = await resolve_workspace_llm_config(mock_session, WORKSPACE_ID)

        assert result is not None
        assert result.provider == "ollama"
        assert result.base_url == "http://localhost:11434"
        assert result.model_name == "llama3.2"

    async def test_falls_back_to_app_level_anthropic_key(self, mock_session: AsyncMock) -> None:
        """resolve_workspace_llm_config falls back to app-level ANTHROPIC_API_KEY as last resort."""
        mock_storage = AsyncMock()
        mock_storage.get_key_info.return_value = None
        mock_storage.get_all_key_infos.return_value = []

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = {}
        mock_session.execute.return_value = mock_result

        with (
            patch(
                "pilot_space.ai.infrastructure.key_storage.SecureKeyStorage",
                return_value=mock_storage,
            ),
            patch("pilot_space.config.get_settings") as mock_settings,
        ):
            mock_settings.return_value.encryption_key.get_secret_value.return_value = (
                "test-encryption-key"
            )
            mock_app_key = MagicMock()
            mock_app_key.get_secret_value.return_value = (
                "sk-ant-app-level-key"  # pragma: allowlist secret
            )
            mock_settings.return_value.anthropic_api_key = mock_app_key

            result = await resolve_workspace_llm_config(mock_session, WORKSPACE_ID)

        assert result is not None
        assert result.provider == "anthropic"
        assert result.api_key == "sk-ant-app-level-key"  # pragma: allowlist secret
        assert result.base_url is None
        assert result.model_name is None

    async def test_returns_none_when_no_config_found_anywhere(
        self, mock_session: AsyncMock
    ) -> None:
        """resolve_workspace_llm_config returns None when no config found at any level."""
        mock_storage = AsyncMock()
        mock_storage.get_key_info.return_value = None
        mock_storage.get_all_key_infos.return_value = []

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = {}
        mock_session.execute.return_value = mock_result

        with (
            patch(
                "pilot_space.ai.infrastructure.key_storage.SecureKeyStorage",
                return_value=mock_storage,
            ),
            patch("pilot_space.config.get_settings") as mock_settings,
        ):
            mock_settings.return_value.encryption_key.get_secret_value.return_value = (
                "test-encryption-key"
            )
            mock_settings.return_value.anthropic_api_key = None

            result = await resolve_workspace_llm_config(mock_session, WORKSPACE_ID)

        assert result is None

    async def test_empty_encryption_key_falls_back_to_app_level_key(
        self, mock_session: AsyncMock
    ) -> None:
        """resolve_workspace_llm_config falls back to app-level key when encryption_key is empty."""
        with (
            patch("pilot_space.config.get_settings") as mock_settings,
        ):
            mock_settings.return_value.encryption_key.get_secret_value.return_value = ""
            mock_app_key = MagicMock()
            mock_app_key.get_secret_value.return_value = (
                "sk-ant-app-fallback"  # pragma: allowlist secret
            )
            mock_settings.return_value.anthropic_api_key = mock_app_key

            result = await resolve_workspace_llm_config(mock_session, WORKSPACE_ID)

        assert result is not None
        assert result.provider == "anthropic"
        assert result.api_key == "sk-ant-app-fallback"  # pragma: allowlist secret
        assert result.base_url is None
        assert result.model_name is None

    async def test_empty_encryption_key_returns_none_when_no_app_key(
        self, mock_session: AsyncMock
    ) -> None:
        """resolve_workspace_llm_config returns None when encryption_key is empty and no app key."""
        with (
            patch("pilot_space.config.get_settings") as mock_settings,
        ):
            mock_settings.return_value.encryption_key.get_secret_value.return_value = ""
            mock_settings.return_value.anthropic_api_key = None

            result = await resolve_workspace_llm_config(mock_session, WORKSPACE_ID)

        assert result is None

    async def test_returns_none_when_workspace_id_is_none(self, mock_session: AsyncMock) -> None:
        """resolve_workspace_llm_config with None workspace_id falls back to app-level key."""
        with (
            patch("pilot_space.config.get_settings") as mock_settings,
        ):
            mock_settings.return_value.anthropic_api_key = None
            result = await resolve_workspace_llm_config(mock_session, None)

        assert result is None

    async def test_returns_app_key_when_workspace_id_is_none(self, mock_session: AsyncMock) -> None:
        """resolve_workspace_llm_config with None workspace_id uses app-level key."""
        with (
            patch("pilot_space.config.get_settings") as mock_settings,
        ):
            mock_app_key = MagicMock()
            mock_app_key.get_secret_value.return_value = (
                "sk-ant-fallback"  # pragma: allowlist secret
            )
            mock_settings.return_value.anthropic_api_key = mock_app_key

            result = await resolve_workspace_llm_config(mock_session, None)

        assert result is not None
        assert result.provider == "anthropic"
        assert result.api_key == "sk-ant-fallback"  # pragma: allowlist secret


class TestProviderSelectorWorkspaceOverride:
    """Tests for workspace_override parameter on ProviderSelector.select_with_config()."""

    def test_workspace_override_replaces_static_model(self) -> None:
        """select_with_config with workspace_override uses workspace model instead of static table."""
        selector = ProviderSelector()
        ws_config = WorkspaceLLMConfig(
            provider="anthropic",
            api_key="sk-ant-test",  # pragma: allowlist secret
            model_name="claude-opus-4-5",
        )
        config = selector.select_with_config(
            TaskType.ISSUE_EXTRACTION, workspace_override=ws_config
        )
        assert config.model == "claude-opus-4-5"
        assert config.provider == "anthropic"

    def test_workspace_override_without_model_name_uses_static_table(self) -> None:
        """select_with_config with workspace_override but no model_name uses static routing table."""
        selector = ProviderSelector()
        ws_config = WorkspaceLLMConfig(
            provider="anthropic",
            api_key="sk-ant-test",  # pragma: allowlist secret
            model_name=None,
        )
        config = selector.select_with_config(
            TaskType.ISSUE_EXTRACTION, workspace_override=ws_config
        )
        # Should fall back to static Sonnet
        assert config.model == ProviderSelector.ANTHROPIC_SONNET

    def test_workspace_override_includes_base_url_in_config(self) -> None:
        """select_with_config with workspace_override includes base_url in ProviderConfig."""
        selector = ProviderSelector()
        ws_config = WorkspaceLLMConfig(
            provider="ollama",
            api_key="ollama-key",  # pragma: allowlist secret
            base_url="http://localhost:11434",
            model_name="llama3.2",
        )
        config = selector.select_with_config(
            TaskType.TEMPLATE_FILLING, workspace_override=ws_config
        )
        assert config.base_url == "http://localhost:11434"
        assert config.model == "llama3.2"
        assert config.provider == "ollama"

    def test_without_workspace_override_returns_static_defaults(self) -> None:
        """select_with_config without workspace_override returns static routing table (backward compat)."""
        selector = ProviderSelector()
        config = selector.select_with_config(TaskType.PR_REVIEW)
        assert config.provider == "anthropic"
        assert config.model == ProviderSelector.ANTHROPIC_OPUS
        assert config.base_url is None

    def test_workspace_override_does_not_affect_select_method(self) -> None:
        """select() method (without workspace_override) still returns static routing table."""
        selector = ProviderSelector()
        provider, model = selector.select(TaskType.ISSUE_EXTRACTION)
        assert provider == "anthropic"
        assert model == ProviderSelector.ANTHROPIC_SONNET

    def test_workspace_override_falls_back_when_provider_unhealthy(self) -> None:
        """select_with_config with unhealthy workspace provider falls back to static routing table."""
        selector = ProviderSelector()
        ws_config = WorkspaceLLMConfig(
            provider="ollama",
            api_key="ollama-key",  # pragma: allowlist secret
            base_url="http://localhost:11434",
            model_name="llama3.2",
        )
        # Force the circuit breaker for ollama to OPEN state
        from pilot_space.ai.circuit_breaker import CircuitBreaker, CircuitState

        breaker = CircuitBreaker.get_or_create("ollama")
        breaker._state.state = CircuitState.OPEN

        try:
            config = selector.select_with_config(
                TaskType.TEMPLATE_FILLING, workspace_override=ws_config
            )
            # Should fall back to static routing table (anthropic)
            assert config.provider == "anthropic"
            assert config.model == ProviderSelector.ANTHROPIC_SONNET
            assert config.base_url is None
        finally:
            breaker.reset()

    def test_provider_config_base_url_defaults_to_none(self) -> None:
        """ProviderConfig has base_url field that defaults to None."""
        from pilot_space.ai.providers.provider_selector import ProviderConfig

        config = ProviderConfig(
            provider="anthropic",
            model="claude-sonnet-4",
            reason="Test",
        )
        assert config.base_url is None
