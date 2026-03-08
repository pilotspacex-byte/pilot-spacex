"""TENANT-02: Workspace encryption key management and content encrypt/decrypt.

Unit tests for per-workspace encryption using a workspace-specific Fernet key
wrapped by a master key (envelope encryption pattern).
"""

from __future__ import annotations

import pytest
from cryptography.fernet import Fernet


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
    """Non-Fernet key format raises ValueError with actionable message.

    Valid Fernet key: URL-safe base64, 32 bytes when decoded.
    Invalid examples: "not-a-key", "deadbeef" * 8, empty string.
    Expected: ValueError with "invalid_key_format" or descriptive message.
    """
    from pilot_space.infrastructure.workspace_encryption import validate_workspace_key

    with pytest.raises(ValueError, match="32-byte"):
        validate_workspace_key("not-a-valid-key")

    with pytest.raises(ValueError, match="32-byte"):
        validate_workspace_key("deadbeef" * 8)

    with pytest.raises(ValueError, match="32-byte"):
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


@pytest.mark.xfail(strict=False, reason="TENANT-02: key rotation re-encrypt not in this plan scope")
async def test_key_rotation_re_encrypts_existing_content() -> None:
    """Rotating workspace key re-encrypts all existing encrypted content.

    Scenario:
    1. Create workspace with key v1, encrypt 3 notes.
    2. Rotate to key v2.
    3. Decrypt all notes with key v2 — plaintext must match original.
    4. Decrypting with key v1 must fail (InvalidToken).
    """
    raise NotImplementedError
