"""Unit tests for SecureKeyStorage (T065).

Tests encryption, decryption, validation, and key info retrieval.
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

        # Mock the execute to simulate successful insert
        mock_session.execute.return_value = None

        await key_storage.store_api_key(
            workspace_id=workspace_id,
            provider="anthropic",
            api_key=api_key,
        )

        # Verify session methods were called
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
                api_key="test-key",  # pragma: allowlist secret
            )

        # Should not call database
        mock_session.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_key_decrypts_from_storage(
        self, key_storage: SecureKeyStorage, mock_session: MagicMock
    ) -> None:
        """Verify key is decrypted when retrieved."""
        workspace_id = uuid4()
        original_key = "sk-ant-test-key-12345"  # pragma: allowlist secret

        # First store the key to get encrypted version
        encrypted = key_storage._encrypt(original_key)

        # Mock the execute to return encrypted key
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = encrypted
        mock_session.execute.return_value = mock_result

        retrieved_key = await key_storage.get_api_key(workspace_id, "anthropic")

        assert retrieved_key == original_key
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_key_returns_none_if_not_found(
        self, key_storage: SecureKeyStorage, mock_session: MagicMock
    ) -> None:
        """Verify None returned when key doesn't exist."""
        workspace_id = uuid4()

        # Mock empty result
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        key = await key_storage.get_api_key(workspace_id, "anthropic")

        assert key is None

    @pytest.mark.asyncio
    async def test_delete_key_removes_from_storage(
        self, key_storage: SecureKeyStorage, mock_session: MagicMock
    ) -> None:
        """Verify key deletion."""
        workspace_id = uuid4()

        # Mock existing key
        mock_row = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_row
        mock_session.execute.return_value = mock_result

        deleted = await key_storage.delete_api_key(workspace_id, "anthropic")

        assert deleted is True
        mock_session.delete.assert_called_once_with(mock_row)
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_key_returns_false_if_not_found(
        self, key_storage: SecureKeyStorage, mock_session: MagicMock
    ) -> None:
        """Verify False returned when key doesn't exist."""
        workspace_id = uuid4()

        # Mock empty result
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        deleted = await key_storage.delete_api_key(workspace_id, "anthropic")

        assert deleted is False
        mock_session.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_key_info_returns_metadata(
        self, key_storage: SecureKeyStorage, mock_session: MagicMock
    ) -> None:
        """Verify key info returns metadata without actual key."""
        workspace_id = uuid4()

        # Mock key info
        mock_row = MagicMock()
        mock_row.workspace_id = workspace_id
        mock_row.provider = "anthropic"
        mock_row.is_valid = True
        mock_row.last_validated_at = datetime.now(UTC)
        mock_row.validation_error = None
        mock_row.created_at = datetime.now(UTC)
        mock_row.updated_at = datetime.now(UTC)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_row
        mock_session.execute.return_value = mock_result

        key_info = await key_storage.get_key_info(workspace_id, "anthropic")

        assert key_info is not None
        assert key_info.workspace_id == workspace_id
        assert key_info.provider == "anthropic"
        assert key_info.is_valid is True
        assert key_info.validation_error is None

    @pytest.mark.asyncio
    async def test_get_key_info_returns_none_if_not_found(
        self, key_storage: SecureKeyStorage, mock_session: MagicMock
    ) -> None:
        """Verify None returned when key info doesn't exist."""
        workspace_id = uuid4()

        # Mock empty result
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        key_info = await key_storage.get_key_info(workspace_id, "anthropic")

        assert key_info is None

    @pytest.mark.asyncio
    async def test_list_providers_returns_configured_providers(
        self, key_storage: SecureKeyStorage, mock_session: MagicMock
    ) -> None:
        """Verify list of configured providers."""
        workspace_id = uuid4()

        # Mock providers
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = ["anthropic", "openai"]
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        providers = await key_storage.list_providers(workspace_id)

        assert providers == ["anthropic", "openai"]

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
        # Mock successful API call
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock()
        mock_anthropic.return_value = mock_client

        is_valid = await key_storage.validate_api_key("anthropic", "sk-ant-test")

        assert is_valid is True
        mock_client.messages.create.assert_called_once()

    @pytest.mark.asyncio
    @patch("anthropic.AsyncAnthropic")
    async def test_validate_api_key_anthropic_failure(
        self,
        mock_anthropic: MagicMock,
        key_storage: SecureKeyStorage,
    ) -> None:
        """Verify failed Anthropic key validation."""
        # Mock failed API call
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(side_effect=Exception("Invalid API key"))
        mock_anthropic.return_value = mock_client

        is_valid = await key_storage.validate_api_key("anthropic", "sk-ant-invalid")

        assert is_valid is False

    @pytest.mark.asyncio
    @patch("openai.AsyncOpenAI")
    async def test_validate_api_key_openai_success(
        self,
        mock_openai: MagicMock,
        key_storage: SecureKeyStorage,
    ) -> None:
        """Verify OpenAI key validation."""
        # Mock successful API call
        mock_client = AsyncMock()
        mock_client.models.list = AsyncMock()
        mock_openai.return_value = mock_client

        is_valid = await key_storage.validate_api_key("openai", "sk-test")

        assert is_valid is True
        mock_client.models.list.assert_called_once()

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
        # Mock successful API call
        mock_model = AsyncMock()
        mock_model.generate_content_async = AsyncMock()
        mock_model_class.return_value = mock_model

        is_valid = await key_storage.validate_api_key(
            "google", "test-key"
        )  # pragma: allowlist secret

        assert is_valid is True
        mock_configure.assert_called_once_with(api_key="test-key")  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_validate_api_key_unknown_provider(self, key_storage: SecureKeyStorage) -> None:
        """Verify unknown provider returns False."""
        is_valid = await key_storage.validate_api_key("unknown", "test-key")

        assert is_valid is False

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

        # Mock get_api_key to return a key
        encrypted = key_storage._encrypt("sk-ant-test")
        mock_result_get = MagicMock()
        mock_result_get.scalar_one_or_none.return_value = encrypted

        # Mock the row for update
        mock_row = MagicMock()
        mock_row.is_valid = False
        mock_result_update = MagicMock()
        mock_result_update.scalar_one_or_none.return_value = mock_row

        mock_session.execute.side_effect = [mock_result_get, mock_result_update]

        # Mock successful validation
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock()
        mock_anthropic.return_value = mock_client

        is_valid = await key_storage.validate_and_update(workspace_id, "anthropic")

        assert is_valid is True
        assert mock_row.is_valid is True
        assert mock_row.last_validated_at is not None
        assert mock_row.validation_error is None
        mock_session.commit.assert_called()
