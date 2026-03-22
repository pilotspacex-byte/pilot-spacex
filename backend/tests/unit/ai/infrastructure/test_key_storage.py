"""Unit tests for SecureKeyStorage.

Tests encryption, decryption, validation, service_type support, and key info retrieval.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

if TYPE_CHECKING:
    from pilot_space.ai.infrastructure.key_storage import SecureKeyStorage


@pytest.fixture
def mock_session() -> MagicMock:
    """Mock async database session."""
    session = MagicMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.delete = AsyncMock()
    return session


@pytest.fixture
def key_storage(mock_session: MagicMock) -> SecureKeyStorage:
    """Create SecureKeyStorage instance with mock session."""
    from pilot_space.ai.infrastructure.key_storage import SecureKeyStorage

    return SecureKeyStorage(
        db=mock_session,
        master_secret="test-master-secret-32-bytes-long!",  # pragma: allowlist secret
    )


class TestSecureKeyStorage:
    """Test suite for SecureKeyStorage."""

    @pytest.mark.asyncio
    async def test_store_key_encrypts_and_saves(
        self, key_storage: SecureKeyStorage, mock_session: MagicMock
    ) -> None:
        """Verify key is encrypted before storage."""
        workspace_id = uuid4()
        api_key = "sk-ant-test-key-12345"  # pragma: allowlist secret

        mock_session.execute.return_value = None

        await key_storage.store_api_key(
            workspace_id=workspace_id,
            provider="anthropic",
            service_type="llm",
            api_key=api_key,
        )

        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_store_key_validates_provider(
        self, key_storage: SecureKeyStorage, mock_session: MagicMock
    ) -> None:
        """Verify invalid provider raises ValueError."""
        workspace_id = uuid4()

        with pytest.raises(ValueError, match="Invalid provider"):
            await key_storage.store_api_key(
                workspace_id=workspace_id,
                provider="invalid-provider",
                service_type="llm",
                api_key="test-key",  # pragma: allowlist secret
            )

        mock_session.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_store_key_validates_service_type(
        self, key_storage: SecureKeyStorage, mock_session: MagicMock
    ) -> None:
        """Verify invalid service_type raises ValueError."""
        workspace_id = uuid4()

        with pytest.raises(ValueError, match="Invalid service_type"):
            await key_storage.store_api_key(
                workspace_id=workspace_id,
                provider="anthropic",
                service_type="invalid",
                api_key="test-key",  # pragma: allowlist secret
            )

        mock_session.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_store_key_without_api_key_for_ollama(
        self, key_storage: SecureKeyStorage, mock_session: MagicMock
    ) -> None:
        """Verify Ollama can be stored without API key."""
        workspace_id = uuid4()

        mock_session.execute.return_value = None

        await key_storage.store_api_key(
            workspace_id=workspace_id,
            provider="ollama",
            service_type="llm",
            api_key=None,
            base_url="http://localhost:11434",
        )

        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_store_ollama_for_embedding(
        self, key_storage: SecureKeyStorage, mock_session: MagicMock
    ) -> None:
        """Verify Ollama can be stored as embedding service."""
        workspace_id = uuid4()

        mock_session.execute.return_value = None

        await key_storage.store_api_key(
            workspace_id=workspace_id,
            provider="ollama",
            service_type="embedding",
            base_url="http://localhost:11434",
            model_name="nomic-embed-text",
        )

        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_key_decrypts_from_storage(
        self, key_storage: SecureKeyStorage, mock_session: MagicMock
    ) -> None:
        """Verify key is decrypted when retrieved."""
        workspace_id = uuid4()
        original_key = "sk-ant-test-key-12345"  # pragma: allowlist secret

        encrypted = key_storage._encrypt(original_key)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = encrypted
        mock_session.execute.return_value = mock_result

        retrieved_key = await key_storage.get_api_key(workspace_id, "anthropic", "llm")

        assert retrieved_key == original_key
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_key_returns_none_if_not_found(
        self, key_storage: SecureKeyStorage, mock_session: MagicMock
    ) -> None:
        """Verify None returned when key doesn't exist."""
        workspace_id = uuid4()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        key = await key_storage.get_api_key(workspace_id, "anthropic", "llm")

        assert key is None

    @pytest.mark.asyncio
    async def test_delete_key_removes_from_storage(
        self, key_storage: SecureKeyStorage, mock_session: MagicMock
    ) -> None:
        """Verify key deletion with service_type."""
        workspace_id = uuid4()

        mock_row = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_row
        mock_session.execute.return_value = mock_result

        deleted = await key_storage.delete_api_key(workspace_id, "anthropic", "llm")

        assert deleted is True
        mock_session.delete.assert_called_once_with(mock_row)
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_key_returns_false_if_not_found(
        self, key_storage: SecureKeyStorage, mock_session: MagicMock
    ) -> None:
        """Verify False returned when key doesn't exist."""
        workspace_id = uuid4()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        deleted = await key_storage.delete_api_key(workspace_id, "anthropic", "llm")

        assert deleted is False
        mock_session.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_key_info_returns_metadata(
        self, key_storage: SecureKeyStorage, mock_session: MagicMock
    ) -> None:
        """Verify key info returns metadata including service_type."""
        workspace_id = uuid4()

        mock_row = MagicMock()
        mock_row.workspace_id = workspace_id
        mock_row.provider = "anthropic"
        mock_row.service_type = "llm"
        mock_row.is_valid = True
        mock_row.last_validated_at = datetime.now(UTC)
        mock_row.validation_error = None
        mock_row.created_at = datetime.now(UTC)
        mock_row.updated_at = datetime.now(UTC)
        mock_row.base_url = None
        mock_row.model_name = None

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_row
        mock_session.execute.return_value = mock_result

        key_info = await key_storage.get_key_info(workspace_id, "anthropic", "llm")

        assert key_info is not None
        assert key_info.workspace_id == workspace_id
        assert key_info.provider == "anthropic"
        assert key_info.service_type == "llm"
        assert key_info.is_valid is True

    @pytest.mark.asyncio
    async def test_get_key_info_returns_none_if_not_found(
        self, key_storage: SecureKeyStorage, mock_session: MagicMock
    ) -> None:
        """Verify None returned when key info doesn't exist."""
        workspace_id = uuid4()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        key_info = await key_storage.get_key_info(workspace_id, "anthropic", "llm")

        assert key_info is None

    @pytest.mark.asyncio
    async def test_list_providers_returns_configured_providers(
        self, key_storage: SecureKeyStorage, mock_session: MagicMock
    ) -> None:
        """Verify list of configured providers."""
        workspace_id = uuid4()

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = ["anthropic", "google"]
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        providers = await key_storage.list_providers(workspace_id)

        assert providers == ["anthropic", "google"]

    @pytest.mark.asyncio
    async def test_list_providers_filters_by_service_type(
        self, key_storage: SecureKeyStorage, mock_session: MagicMock
    ) -> None:
        """Verify list_providers filters by service_type."""
        workspace_id = uuid4()

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = ["google"]
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        providers = await key_storage.list_providers(workspace_id, service_type="embedding")

        assert providers == ["google"]

    @pytest.mark.asyncio
    async def test_mask_key_hides_middle_characters(self, key_storage: SecureKeyStorage) -> None:
        """Verify key masking for logging."""
        api_key = "sk-ant-api01-test-key-12345"  # pragma: allowlist secret
        masked = key_storage._mask_key(api_key)

        assert masked.startswith("sk-a")
        assert masked.endswith("2345")
        assert "..." in masked
        assert len(masked) < len(api_key)

    @pytest.mark.asyncio
    async def test_mask_short_key_all_asterisks(self, key_storage: SecureKeyStorage) -> None:
        """Verify short keys are fully masked."""
        api_key = "short"  # pragma: allowlist secret
        masked = key_storage._mask_key(api_key)

        assert masked == "*****"

    @pytest.mark.asyncio
    @patch("anthropic.AsyncAnthropic")
    async def test_validate_api_key_anthropic_success(
        self,
        mock_anthropic: MagicMock,
        key_storage: SecureKeyStorage,
    ) -> None:
        """Verify Anthropic key validation."""
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock()
        mock_anthropic.return_value = mock_client

        is_valid, error = await key_storage.validate_api_key("anthropic", "sk-ant-test")

        assert is_valid is True
        assert error is None
        mock_client.messages.create.assert_called_once()

    @pytest.mark.asyncio
    @patch("anthropic.AsyncAnthropic")
    async def test_validate_api_key_anthropic_failure(
        self,
        mock_anthropic: MagicMock,
        key_storage: SecureKeyStorage,
    ) -> None:
        """Verify failed Anthropic key validation."""
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(side_effect=Exception("Invalid API key"))
        mock_anthropic.return_value = mock_client

        is_valid, error = await key_storage.validate_api_key("anthropic", "sk-ant-invalid")

        assert is_valid is False
        assert error is not None

    @pytest.mark.asyncio
    @patch("google.generativeai.GenerativeModel")
    @patch("google.generativeai.configure")
    async def test_validate_api_key_google_success(
        self,
        mock_configure: MagicMock,
        mock_model_class: MagicMock,
        key_storage: SecureKeyStorage,
    ) -> None:
        """Verify Google key validation."""
        mock_model = AsyncMock()
        mock_model.generate_content_async = AsyncMock()
        mock_model_class.return_value = mock_model

        is_valid, error = await key_storage.validate_api_key(
            "google", "test-key"
        )  # pragma: allowlist secret

        assert is_valid is True
        assert error is None
        mock_configure.assert_called_once_with(api_key="test-key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient")
    async def test_validate_ollama_success(
        self,
        mock_httpx_client: MagicMock,
        key_storage: SecureKeyStorage,
    ) -> None:
        """Verify Ollama validation via /api/tags health check."""
        mock_response = MagicMock()
        mock_response.status_code = 200

        mock_client_instance = AsyncMock()
        mock_client_instance.get = AsyncMock(return_value=mock_response)
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=False)
        mock_httpx_client.return_value = mock_client_instance

        is_valid, error = await key_storage.validate_api_key(
            "ollama", None, base_url="http://localhost:11434"
        )

        assert is_valid is True
        assert error is None

    @pytest.mark.asyncio
    async def test_validate_api_key_unknown_provider(self, key_storage: SecureKeyStorage) -> None:
        """Verify unknown provider returns False."""
        is_valid, error = await key_storage.validate_api_key("unknown", "test-key")

        assert is_valid is False
        assert error is not None

    @pytest.mark.asyncio
    async def test_validate_anthropic_without_key_returns_false(
        self, key_storage: SecureKeyStorage
    ) -> None:
        """Verify Anthropic validation fails without API key."""
        is_valid, error = await key_storage.validate_api_key("anthropic", None)

        assert is_valid is False
        assert error is not None

    @pytest.mark.asyncio
    async def test_valid_providers_set(self, key_storage: SecureKeyStorage) -> None:
        """Verify google, anthropic, ollama, elevenlabs are valid."""
        assert (
            frozenset({"google", "anthropic", "ollama", "elevenlabs"})
            == key_storage.VALID_PROVIDERS
        )

    @pytest.mark.asyncio
    async def test_valid_service_types_set(self, key_storage: SecureKeyStorage) -> None:
        """Verify embedding, llm, and stt are valid service types."""
        assert frozenset({"embedding", "llm", "stt"}) == key_storage.VALID_SERVICE_TYPES

    @pytest.mark.asyncio
    @patch("anthropic.AsyncAnthropic")
    async def test_validate_and_update_success(
        self,
        mock_anthropic: MagicMock,
        key_storage: SecureKeyStorage,
        mock_session: MagicMock,
    ) -> None:
        """Verify validate_and_update marks key as valid."""
        workspace_id = uuid4()

        # Mock get_api_key
        encrypted = key_storage._encrypt("sk-ant-test")
        mock_result_get = MagicMock()
        mock_result_get.scalar_one_or_none.return_value = encrypted

        # Mock get_key_info (for base_url)
        mock_info_row = MagicMock()
        mock_info_row.workspace_id = workspace_id
        mock_info_row.provider = "anthropic"
        mock_info_row.service_type = "llm"
        mock_info_row.is_valid = False
        mock_info_row.last_validated_at = None
        mock_info_row.validation_error = None
        mock_info_row.created_at = datetime.now(UTC)
        mock_info_row.updated_at = datetime.now(UTC)
        mock_info_row.base_url = None
        mock_info_row.model_name = None
        mock_result_info = MagicMock()
        mock_result_info.scalar_one_or_none.return_value = mock_info_row

        # Mock the row for update
        mock_row = MagicMock()
        mock_row.is_valid = False
        mock_result_update = MagicMock()
        mock_result_update.scalar_one_or_none.return_value = mock_row

        mock_session.execute.side_effect = [
            mock_result_get,
            mock_result_info,
            mock_result_update,
        ]

        # Mock successful validation
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock()
        mock_anthropic.return_value = mock_client

        is_valid = await key_storage.validate_and_update(workspace_id, "anthropic", "llm")

        assert is_valid is True
        assert mock_row.is_valid is True
        assert mock_row.last_validated_at is not None
        assert mock_row.validation_error is None
        mock_session.commit.assert_called()

    @pytest.mark.asyncio
    async def test_get_all_key_infos_returns_all_rows(
        self, key_storage: SecureKeyStorage, mock_session: MagicMock
    ) -> None:
        """Verify get_all_key_infos returns all configured keys for a workspace."""
        workspace_id = uuid4()
        now = datetime.now(UTC)

        mock_row_1 = MagicMock()
        mock_row_1.workspace_id = workspace_id
        mock_row_1.provider = "anthropic"
        mock_row_1.service_type = "llm"
        mock_row_1.is_valid = True
        mock_row_1.last_validated_at = now
        mock_row_1.validation_error = None
        mock_row_1.created_at = now
        mock_row_1.updated_at = now
        mock_row_1.base_url = None
        mock_row_1.model_name = None

        mock_row_2 = MagicMock()
        mock_row_2.workspace_id = workspace_id
        mock_row_2.provider = "google"
        mock_row_2.service_type = "embedding"
        mock_row_2.is_valid = True
        mock_row_2.last_validated_at = now
        mock_row_2.validation_error = None
        mock_row_2.created_at = now
        mock_row_2.updated_at = now
        mock_row_2.base_url = None
        mock_row_2.model_name = None

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_row_1, mock_row_2]
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        infos = await key_storage.get_all_key_infos(workspace_id)

        assert len(infos) == 2
        assert infos[0].provider == "anthropic"
        assert infos[0].service_type == "llm"
        assert infos[1].provider == "google"
        assert infos[1].service_type == "embedding"

    @pytest.mark.asyncio
    async def test_get_all_key_infos_returns_empty_list(
        self, key_storage: SecureKeyStorage, mock_session: MagicMock
    ) -> None:
        """Verify get_all_key_infos returns empty list when no keys configured."""
        workspace_id = uuid4()

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        infos = await key_storage.get_all_key_infos(workspace_id)

        assert infos == []
