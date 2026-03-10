"""Workspace-level envelope encryption helpers.

Workspace key is stored encrypted with the system master Fernet key.
Content fields (notes.body, issues.description) are encrypted with the
workspace key when configured.

Encryption is opt-in: get_workspace_content_key() returns None when no key is
configured, and callers must check for None before encrypting/decrypting.

Pattern:
  stored = Fernet(MASTER_KEY).encrypt(raw_workspace_key)
  content = Fernet(raw_workspace_key).encrypt(plaintext)

References:
- TENANT-02: Workspace BYOK encryption
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from cryptography.fernet import Fernet
from sqlalchemy import select

from pilot_space.infrastructure.encryption import get_encryption_service

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


def validate_workspace_key(raw_key: str) -> None:
    """Validate that raw_key is a valid 32-byte URL-safe base64 Fernet key.

    Args:
        raw_key: Key string to validate.

    Raises:
        ValueError: If the key is not a valid Fernet key, with an actionable
            message directing the user to use the Generate Key button.
    """
    if not raw_key:
        raise ValueError(
            "Key must be a 32-byte URL-safe base64 string. "
            "Use the Generate Key button to create a valid key."
        )
    try:
        Fernet(raw_key.encode())
    except Exception as exc:
        raise ValueError(
            "Key must be a 32-byte URL-safe base64 string. "
            "Use the Generate Key button to create a valid key."
        ) from exc


def store_workspace_key(raw_key: str) -> str:
    """Encrypt workspace key with master key for storage.

    Args:
        raw_key: Valid Fernet key string to protect.

    Returns:
        Master-key-encrypted ciphertext suitable for DB storage.

    Raises:
        ValueError: If raw_key is not a valid Fernet key.
    """
    validate_workspace_key(raw_key)
    return get_encryption_service().encrypt(raw_key)


def retrieve_workspace_key(encrypted_key: str) -> str:
    """Decrypt workspace key from storage.

    Args:
        encrypted_key: Master-key-encrypted ciphertext from DB.

    Returns:
        Raw workspace Fernet key.

    Raises:
        EncryptionError: If master key cannot decrypt the stored key.
    """
    return get_encryption_service().decrypt(encrypted_key)


def encrypt_content(content: str, workspace_key: str) -> str:
    """Encrypt a content field with the workspace key.

    Args:
        content: Plaintext content to encrypt.
        workspace_key: Raw workspace Fernet key string.

    Returns:
        Fernet-encrypted ciphertext as a UTF-8 string.
    """
    f = Fernet(workspace_key.encode())
    return f.encrypt(content.encode()).decode()


def decrypt_content(ciphertext: str, workspace_key: str) -> str:
    """Decrypt a content field with the workspace key.

    Args:
        ciphertext: Fernet-encrypted ciphertext string.
        workspace_key: Raw workspace Fernet key string.

    Returns:
        Decrypted plaintext.

    Raises:
        cryptography.fernet.InvalidToken: If key is wrong or data is corrupted.
    """
    f = Fernet(workspace_key.encode())
    return f.decrypt(ciphertext.encode()).decode()


async def get_workspace_content_key(
    session: AsyncSession,
    workspace_id: str,
) -> str | None:
    """Fetch the raw workspace encryption key for content operations.

    Returns None if no key is configured (plaintext mode).
    Callers must check for None before calling encrypt_content/decrypt_content.

    Args:
        session: Async database session.
        workspace_id: Workspace UUID string.

    Returns:
        Raw workspace Fernet key, or None if encryption is not configured.

    Raises:
        EncryptionError: If master key cannot decrypt the stored key.
    """
    from pilot_space.infrastructure.database.models.workspace_encryption_key import (
        WorkspaceEncryptionKey,
    )

    result = await session.execute(
        select(WorkspaceEncryptionKey).where(WorkspaceEncryptionKey.workspace_id == workspace_id)
    )
    key_record = result.scalar_one_or_none()
    if key_record is None:
        return None
    return retrieve_workspace_key(key_record.encrypted_workspace_key)
