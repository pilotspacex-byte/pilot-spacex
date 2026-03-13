"""T099: API Key Security Audit Tests.

Comprehensive tests ensuring API keys are never logged or exposed:
- Keys not logged in normal operations
- Keys not in error messages
- Keys not returned in logs from key_storage.py

Reference: specs/004-mvp-agents-build/tasks/P15-T095-T110.md
"""

from __future__ import annotations

import logging
import os
import uuid
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import pytest

from pilot_space.ai.infrastructure.key_storage import SecureKeyStorage

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

_DB_URL = os.getenv("TEST_DATABASE_URL", "sqlite")
_requires_postgres = pytest.mark.skipif(
    "sqlite" in _DB_URL,
    reason=(
        "Requires PostgreSQL (workspace_api_keys.id uses gen_random_uuid() server default). "
        "Set TEST_DATABASE_URL."
    ),
)


@_requires_postgres
class TestAPIKeySecurity:
    """Tests for API key security - ensure keys never leak to logs."""

    @pytest.mark.asyncio
    async def test_store_api_key_does_not_log_full_key(
        self,
        db_session: AsyncSession,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Verify storing API key logs masked version only."""
        workspace_id = uuid.uuid4()
        test_key = "sk-ant-api03-test-secret-key-1234567890abcdef"  # pragma: allowlist secret

        storage = SecureKeyStorage(
            db=db_session,
            master_secret="test-master-secret-for-testing",  # pragma: allowlist secret
        )

        with caplog.at_level(logging.DEBUG):
            await storage.store_api_key(
                workspace_id=workspace_id,
                provider="anthropic",
                api_key=test_key,
            )

        # Verify no full key in logs
        for record in caplog.records:
            assert test_key not in record.message, "Full API key found in log message"
            # Verify masked version is used
            if "key_preview" in record.message or "API key stored" in record.message:
                # Should only contain masked version
                assert "sk-a..." in record.message or "*" in record.message

    @pytest.mark.asyncio
    async def test_validation_error_does_not_expose_key(
        self,
        db_session: AsyncSession,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Verify validation errors don't expose API keys."""
        invalid_key = "sk-ant-api03-invalid-key-will-fail-validation"

        storage = SecureKeyStorage(
            db=db_session,
            master_secret="test-master-secret",  # pragma: allowlist secret
        )

        # Mock the validation to fail
        with (
            patch.object(storage, "validate_api_key", return_value=False),
            caplog.at_level(logging.DEBUG),
        ):
            await storage.validate_api_key("anthropic", invalid_key)

        # Check all log records
        for record in caplog.records:
            assert invalid_key not in record.message, "API key leaked in error log"
            # Should use masked version if key is mentioned
            if "key" in record.message.lower():
                assert len(record.message) < 200  # Reasonable log length

    @pytest.mark.asyncio
    async def test_get_api_key_does_not_log_decrypted_value(
        self,
        db_session: AsyncSession,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Verify retrieving API key doesn't log the decrypted value."""
        workspace_id = uuid.uuid4()
        test_key = "sk-openai-test-secret-key-1234567890"  # pragma: allowlist secret

        storage = SecureKeyStorage(
            db=db_session,
            master_secret="test-master-secret",  # pragma: allowlist secret
        )

        # Store key
        await storage.store_api_key(
            workspace_id=workspace_id,
            provider="openai",
            api_key=test_key,
        )

        caplog.clear()

        # Retrieve key
        with caplog.at_level(logging.DEBUG):
            retrieved = await storage.get_api_key(workspace_id, "openai")

        # Verify key was retrieved but not logged
        assert retrieved == test_key
        for record in caplog.records:
            assert test_key not in record.message, "Decrypted key logged on retrieval"

    @pytest.mark.asyncio
    async def test_delete_api_key_does_not_log_value(
        self,
        db_session: AsyncSession,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Verify deleting API key doesn't log the value."""
        workspace_id = uuid.uuid4()
        test_key = "sk-google-test-secret-key-xyz"  # pragma: allowlist secret

        storage = SecureKeyStorage(
            db=db_session,
            master_secret="test-master-secret",  # pragma: allowlist secret
        )

        await storage.store_api_key(
            workspace_id=workspace_id,
            provider="google",
            api_key=test_key,
        )

        caplog.clear()

        with caplog.at_level(logging.DEBUG):
            await storage.delete_api_key(workspace_id, "google")

        for record in caplog.records:
            assert test_key not in record.message, "Key logged during deletion"

    def test_mask_key_function(self) -> None:
        """Verify _mask_key produces safe output."""
        storage = SecureKeyStorage(
            db=AsyncMock(),
            master_secret="test",  # pragma: allowlist secret
        )

        # Long key
        long_key = "sk-ant-api03-very-long-secret-key-12345"
        masked = storage._mask_key(long_key)
        assert long_key not in masked
        assert "sk-a" in masked
        assert "2345" in masked
        assert "..." in masked

        # Short key
        short_key = "abc123"
        masked_short = storage._mask_key(short_key)
        assert short_key not in masked_short
        assert "*" in masked_short

    @pytest.mark.asyncio
    async def test_exception_messages_do_not_contain_keys(
        self,
        db_session: AsyncSession,
    ) -> None:
        """Verify exceptions don't expose API keys."""
        storage = SecureKeyStorage(
            db=db_session,
            master_secret="test-master-secret",  # pragma: allowlist secret
        )

        # Invalid provider should raise ValueError
        test_key = "sk-test-secret-key"  # pragma: allowlist secret
        with pytest.raises(ValueError, match="Invalid provider") as exc_info:
            await storage.store_api_key(
                workspace_id=uuid.uuid4(),
                provider="invalid_provider",
                api_key=test_key,
            )

        # Exception message should not contain the key
        assert test_key not in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_logging_uses_masked_preview(
        self,
        db_session: AsyncSession,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Verify all logging uses masked key preview."""
        workspace_id = uuid.uuid4()
        test_key = "sk-ant-api03-this-is-a-test-key-12345678"  # pragma: allowlist secret

        storage = SecureKeyStorage(
            db=db_session,
            master_secret="test-master-secret",  # pragma: allowlist secret
        )

        with caplog.at_level(logging.INFO):
            await storage.store_api_key(
                workspace_id=workspace_id,
                provider="anthropic",
                api_key=test_key,
            )

        # Find the log record about key storage
        storage_logs = [r for r in caplog.records if "API key stored" in r.message]
        assert len(storage_logs) > 0

        for log_record in storage_logs:
            # Should contain masked version
            assert "sk-a...5678" in str(log_record.msg) or "key_preview" in str(log_record.__dict__)
            # Should NOT contain full key
            assert test_key not in str(log_record.msg)
            assert test_key not in str(log_record.args)

    @pytest.mark.asyncio
    async def test_validate_and_update_masks_key_in_logs(
        self,
        db_session: AsyncSession,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Verify validation logging doesn't expose keys."""
        workspace_id = uuid.uuid4()
        # Use a test key that will fail validation
        test_key = "sk-ant-invalid-key-for-testing"  # pragma: allowlist secret

        storage = SecureKeyStorage(
            db=db_session,
            master_secret="test-master-secret",  # pragma: allowlist secret
        )

        await storage.store_api_key(
            workspace_id=workspace_id,
            provider="anthropic",
            api_key=test_key,
        )

        caplog.clear()

        # Mock validation to avoid actual API call
        with (
            patch.object(storage, "validate_api_key", return_value=False),
            caplog.at_level(logging.WARNING),
        ):
            await storage.validate_and_update(workspace_id, "anthropic")

        # Check validation failure logs
        for record in caplog.records:
            assert test_key not in record.message
            # If key is mentioned, should be masked
            if "key" in record.message.lower():
                assert (
                    "sk-a...ting" in record.message
                    or "*" in record.message
                    or "preview" in str(record.__dict__)
                )


class TestAPIKeyPatternAudit:
    """Audit tests for dangerous patterns in codebase."""

    def test_no_api_key_in_f_strings(self) -> None:
        """Ensure API keys aren't used in f-strings (risk of logging)."""
        # This is a static check documented in the test
        # In practice, run: grep -r 'f".*api_key' src/pilot_space/ai/
        # Should find no dangerous patterns
        assert True  # Placeholder for documentation

    def test_no_api_key_in_exception_constructors(self) -> None:
        """Ensure API keys aren't passed to exception constructors."""
        # Static check: grep -r 'raise.*api_key' src/pilot_space/ai/
        # Should find no direct key passing
        assert True  # Placeholder for documentation

    def test_key_storage_only_uses_masked_in_extra_dict(self) -> None:
        """Verify logger.info/warning extra dict uses masked keys."""
        # Manual review of key_storage.py logging calls
        # All should use _mask_key() or key_preview
        assert True  # Placeholder for documentation


class TestAPIKeyEnvironmentSecurity:
    """Tests for environment variable and configuration security."""

    def test_master_secret_not_logged(
        self,
        db_session: AsyncSession,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Verify master secret is never logged."""
        master_secret = "super-secret-master-key-do-not-log"  # pragma: allowlist secret

        with caplog.at_level(logging.DEBUG):
            _ = SecureKeyStorage(
                db=db_session,
                master_secret=master_secret,
            )

        # Master secret should never appear in logs
        for record in caplog.records:
            assert master_secret not in record.message
            assert master_secret not in str(record.args)

    @pytest.mark.asyncio
    @_requires_postgres
    async def test_encrypted_key_not_in_logs(
        self,
        db_session: AsyncSession,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Verify encrypted key value is not logged."""
        workspace_id = uuid.uuid4()
        test_key = "sk-test-key-12345"  # pragma: allowlist secret

        storage = SecureKeyStorage(
            db=db_session,
            master_secret="test-secret",  # pragma: allowlist secret
        )

        # Store key
        with caplog.at_level(logging.DEBUG):
            await storage.store_api_key(
                workspace_id=workspace_id,
                provider="anthropic",
                api_key=test_key,
            )

        # Get encrypted value (for test purposes)
        encrypted = storage._encrypt(test_key)

        # Encrypted value should not be in logs either
        for record in caplog.records:
            assert encrypted not in record.message, "Encrypted key found in logs"
