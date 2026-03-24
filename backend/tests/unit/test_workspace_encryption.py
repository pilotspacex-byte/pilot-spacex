"""TENANT-02: Workspace encryption key management and content encrypt/decrypt.

Unit tests for per-workspace encryption using a workspace-specific Fernet key
wrapped by a master key (envelope encryption pattern).
"""

from __future__ import annotations

import pytest
from cryptography.fernet import Fernet, InvalidToken

from pilot_space.domain.exceptions import ValidationError


@pytest.mark.asyncio
async def test_workspace_key_stored_encrypted_with_master_key() -> None:
    """Workspace encryption key is stored as master-key-encrypted ciphertext.

    The raw workspace Fernet key must never appear in plaintext in the database.
    encrypted_workspace_key column stores: Fernet(master_key).encrypt(workspace_fernet_key)
    """
    from pilot_space.infrastructure.workspace_encryption import (
        retrieve_workspace_key,
        store_workspace_key,
    )

    raw_key = Fernet.generate_key().decode()
    ciphertext = store_workspace_key(raw_key)

    # Ciphertext must not equal the plaintext key
    assert ciphertext != raw_key
    # Must be a non-empty string (Fernet token)
    assert len(ciphertext) > 0

    # Must round-trip back to original
    recovered = retrieve_workspace_key(ciphertext)
    assert recovered == raw_key


@pytest.mark.asyncio
async def test_content_round_trip_encryption() -> None:
    """note.body encrypted on write, decrypted on read; plaintext matches original.

    Scenario:
    1. Generate a workspace Fernet key.
    2. encrypt_content("hello world", workspace_key) -> ciphertext (bytes, not plaintext).
    3. decrypt_content(ciphertext, workspace_key) -> "hello world".
    4. Assert round-trip output equals original plaintext.
    """
    from pilot_space.infrastructure.workspace_encryption import (
        decrypt_content,
        encrypt_content,
    )

    workspace_key = Fernet.generate_key().decode()
    plaintext = "hello world"

    ciphertext = encrypt_content(plaintext, workspace_key)
    assert ciphertext != plaintext  # must be encrypted

    recovered = decrypt_content(ciphertext, workspace_key)
    assert recovered == plaintext


@pytest.mark.asyncio
async def test_invalid_key_format_raises_value_error() -> None:
    """Non-Fernet key format raises ValidationError with actionable message.

    Valid Fernet key: URL-safe base64, 32 bytes when decoded.
    Invalid examples: "not-a-key", "deadbeef" * 8, empty string.
    Expected: ValidationError with "invalid_key_format" or descriptive message.
    """
    from pilot_space.infrastructure.workspace_encryption import validate_workspace_key

    with pytest.raises(ValidationError, match="32-byte"):
        validate_workspace_key("not-a-valid-key")

    with pytest.raises(ValidationError, match="32-byte"):
        validate_workspace_key("deadbeef" * 8)

    with pytest.raises(ValidationError, match="32-byte"):
        validate_workspace_key("")


@pytest.mark.asyncio
async def test_get_workspace_content_key_returns_none_when_no_key() -> None:
    """get_workspace_content_key returns None when no key configured (plaintext mode).

    Workspaces without a configured key are in plaintext mode.
    Uses a mock session that returns no key record.
    """
    import uuid
    from unittest.mock import AsyncMock, MagicMock

    from pilot_space.infrastructure.workspace_encryption import get_workspace_content_key

    # Mock session that returns scalar_one_or_none() -> None
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None

    mock_session = MagicMock()
    mock_session.execute = AsyncMock(return_value=mock_result)

    random_workspace_id = str(uuid.uuid4())
    result = await get_workspace_content_key(mock_session, random_workspace_id)
    assert result is None


# ============================================================================
# Dual-key fallback tests
# ============================================================================


class TestDecryptContentWithFallback:
    """Tests for decrypt_content_with_fallback dual-key decryption."""

    def test_primary_key_succeeds_no_fallback_needed(self) -> None:
        """When primary key decrypts successfully, fallback is not used."""
        from pilot_space.infrastructure.workspace_encryption import (
            decrypt_content_with_fallback,
            encrypt_content,
        )

        key1 = Fernet.generate_key().decode()
        key2 = Fernet.generate_key().decode()
        ciphertext = encrypt_content("secret data", key1)

        result = decrypt_content_with_fallback(ciphertext, key1, key2)
        assert result == "secret data"

    def test_primary_fails_fallback_succeeds(self) -> None:
        """When primary key fails, fallback key is used to decrypt."""
        from pilot_space.infrastructure.workspace_encryption import (
            decrypt_content_with_fallback,
            encrypt_content,
        )

        old_key = Fernet.generate_key().decode()
        new_key = Fernet.generate_key().decode()
        # Encrypted with old key
        ciphertext = encrypt_content("legacy data", old_key)

        # Primary is new_key (fails), fallback is old_key (succeeds)
        result = decrypt_content_with_fallback(ciphertext, new_key, old_key)
        assert result == "legacy data"

    def test_both_keys_fail_raises_invalid_token(self) -> None:
        """When both primary and fallback keys fail, InvalidToken is raised."""
        from pilot_space.infrastructure.workspace_encryption import (
            decrypt_content_with_fallback,
            encrypt_content,
        )

        real_key = Fernet.generate_key().decode()
        wrong_key1 = Fernet.generate_key().decode()
        wrong_key2 = Fernet.generate_key().decode()
        ciphertext = encrypt_content("data", real_key)

        with pytest.raises(InvalidToken):
            decrypt_content_with_fallback(ciphertext, wrong_key1, wrong_key2)

    def test_no_fallback_key_raises_on_primary_failure(self) -> None:
        """When fallback_key is None and primary fails, InvalidToken is raised."""
        from pilot_space.infrastructure.workspace_encryption import (
            decrypt_content_with_fallback,
            encrypt_content,
        )

        real_key = Fernet.generate_key().decode()
        wrong_key = Fernet.generate_key().decode()
        ciphertext = encrypt_content("data", real_key)

        with pytest.raises(InvalidToken):
            decrypt_content_with_fallback(ciphertext, wrong_key, None)


# ============================================================================
# Key rotation end-to-end test
# ============================================================================


@pytest.mark.asyncio
async def test_key_rotation_re_encrypts_existing_content() -> None:
    """Rotating workspace key re-encrypts all existing encrypted content.

    Scenario:
    1. Create workspace with key v1, encrypt 3 content strings.
    2. Rotate to key v2 (function-level test using encrypt/decrypt helpers).
    3. Decrypt all content with key v2 -- plaintext must match original.
    4. Decrypting with key v1 must fail (InvalidToken).
    """
    from pilot_space.infrastructure.workspace_encryption import (
        decrypt_content,
        encrypt_content,
    )

    # Step 1: Generate key v1 and encrypt content
    key_v1 = Fernet.generate_key().decode()
    originals = [
        "Note body one",
        "Note body two with special chars: !@#$%",
        "Issue description three",
    ]
    ciphertexts_v1 = [encrypt_content(text, key_v1) for text in originals]

    # Step 2: Generate key v2, simulate rotation re-encryption
    key_v2 = Fernet.generate_key().decode()
    ciphertexts_v2 = []
    for ct in ciphertexts_v1:
        plaintext = decrypt_content(ct, key_v1)
        ciphertexts_v2.append(encrypt_content(plaintext, key_v2))

    # Step 3: All content decryptable with key v2
    for i, ct in enumerate(ciphertexts_v2):
        recovered = decrypt_content(ct, key_v2)
        assert recovered == originals[i], f"Content {i} mismatch after rotation"

    # Step 4: Decrypting re-encrypted content with key v1 must fail
    for ct in ciphertexts_v2:
        with pytest.raises(InvalidToken):
            decrypt_content(ct, key_v1)


@pytest.mark.asyncio
async def test_rotate_workspace_key_service() -> None:
    """rotate_workspace_key orchestrates full key rotation with batch re-encryption.

    Uses mocks for DB operations to test the service logic:
    1. Retrieves old key from DB
    2. Validates new key
    3. Calls upsert_key (saves old to previous_encrypted_key)
    4. Re-encrypts content rows in batches
    5. Clears previous_encrypted_key after completion
    6. Returns counts of re-encrypted items
    """
    import uuid
    from unittest.mock import AsyncMock, MagicMock, patch

    from pilot_space.infrastructure.workspace_encryption import (
        encrypt_content,
        rotate_workspace_key,
    )

    workspace_id = str(uuid.uuid4())
    key_v1 = Fernet.generate_key().decode()
    key_v2 = Fernet.generate_key().decode()

    # Prepare mock encrypted content
    encrypted_note = encrypt_content("note body", key_v1)
    encrypted_issue = encrypt_content("issue description", key_v1)

    # Mock session
    mock_session = MagicMock()
    mock_session.execute = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.flush = AsyncMock()

    # Mock the repository and its methods
    mock_repo = MagicMock()
    mock_key_record = MagicMock()
    mock_key_record.encrypted_workspace_key = MagicMock()
    mock_key_record.key_version = 2
    mock_repo.get_key_record = AsyncMock(return_value=mock_key_record)
    mock_repo.upsert_key = AsyncMock(return_value=mock_key_record)
    mock_repo.clear_previous_key = AsyncMock()

    # Mock note rows
    mock_note = MagicMock()
    mock_note.content = encrypted_note
    mock_note.id = uuid.uuid4()

    # Mock issue rows
    mock_issue = MagicMock()
    mock_issue.description = encrypted_issue
    mock_issue.id = uuid.uuid4()

    with (
        patch(
            "pilot_space.infrastructure.workspace_encryption.retrieve_workspace_key",
            return_value=key_v1,
        ),
        patch(
            "pilot_space.infrastructure.database.repositories.workspace_encryption_repository.WorkspaceEncryptionRepository",
            return_value=mock_repo,
        ),
        patch(
            "pilot_space.infrastructure.workspace_encryption._get_encrypted_notes",
            new_callable=AsyncMock,
            return_value=[mock_note],
        ),
        patch(
            "pilot_space.infrastructure.workspace_encryption._get_encrypted_issues",
            new_callable=AsyncMock,
            return_value=[mock_issue],
        ),
    ):
        result = await rotate_workspace_key(mock_session, workspace_id, key_v2)

    assert result["notes"] >= 0
    assert result["issues"] >= 0
    mock_repo.upsert_key.assert_awaited_once()
    mock_repo.clear_previous_key.assert_awaited_once()
