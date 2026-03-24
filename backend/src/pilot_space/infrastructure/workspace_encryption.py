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

import json
import logging
from typing import TYPE_CHECKING, Any
from uuid import UUID

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import select

from pilot_space.domain.exceptions import ConflictError, NotFoundError, ValidationError
from pilot_space.infrastructure.encryption import get_encryption_service

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


def validate_workspace_key(raw_key: str) -> None:
    """Validate that raw_key is a valid 32-byte URL-safe base64 Fernet key.

    Args:
        raw_key: Key string to validate.

    Raises:
        ValueError: If the key is not a valid Fernet key, with an actionable
            message directing the user to use the Generate Key button.
    """
    if not raw_key:
        raise ValidationError(
            "Key must be a 32-byte URL-safe base64 string. "
            "Use the Generate Key button to create a valid key."
        )
    try:
        Fernet(raw_key.encode())
    except Exception as exc:
        raise ValidationError(
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


def decrypt_content_with_fallback(
    ciphertext: str,
    primary_key: str,
    fallback_key: str | None,
) -> str:
    """Decrypt content trying primary key first, falling back to old key.

    Used during key rotation window: content encrypted with the old key
    can still be read using the fallback while re-encryption is in progress.

    Args:
        ciphertext: Fernet-encrypted ciphertext string.
        primary_key: Current (new) workspace Fernet key.
        fallback_key: Previous workspace Fernet key, or None.

    Returns:
        Decrypted plaintext.

    Raises:
        cryptography.fernet.InvalidToken: If neither key can decrypt.
    """
    try:
        return decrypt_content(ciphertext, primary_key)
    except InvalidToken:
        if fallback_key is not None:
            return decrypt_content(ciphertext, fallback_key)
        raise


async def _get_encrypted_notes(
    session: AsyncSession,
    workspace_id: UUID,
) -> list[Any]:
    """Fetch notes with content in the workspace.

    Args:
        session: Async database session.
        workspace_id: Workspace UUID.

    Returns:
        List of Note model instances.
    """
    from pilot_space.infrastructure.database.models.note import Note

    result = await session.execute(
        select(Note).where(
            Note.workspace_id == workspace_id,
            Note.is_deleted.is_(False),
        )
    )
    return list(result.scalars().all())


async def _get_encrypted_issues(
    session: AsyncSession,
    workspace_id: UUID,
) -> list[Any]:
    """Fetch issues with non-null description in the workspace.

    Args:
        session: Async database session.
        workspace_id: Workspace UUID.

    Returns:
        List of Issue model instances with encrypted description.
    """
    from pilot_space.infrastructure.database.models.issue import Issue

    result = await session.execute(
        select(Issue).where(
            Issue.workspace_id == workspace_id,
            Issue.description.isnot(None),
            Issue.is_deleted.is_(False),
        )
    )
    return list(result.scalars().all())


def _re_encrypt_string(value: str, old_key: str, new_key: str) -> str | None:
    """Re-encrypt a single string value from old key to new key.

    Returns None if the value cannot be decrypted (not encrypted or corrupt).
    Callers MUST track None returns and raise before clearing the previous key.
    """
    try:
        plaintext = decrypt_content_with_fallback(value, new_key, old_key)
        return encrypt_content(plaintext, new_key)
    except InvalidToken:
        logger.warning("Skipped re-encryption for undecryptable content (not encrypted or corrupt)")
        return None


async def rotate_workspace_key(
    session: AsyncSession,
    workspace_id: UUID,
    new_raw_key: str,
    batch_size: int = 100,
) -> dict[str, int]:
    """Rotate workspace encryption key with batch re-encryption.

    Performs a full key rotation:
    1. Retrieves old key from DB
    2. Validates new key format
    3. Upserts new key (saves old to previous_encrypted_key)
    4. Re-encrypts all note content and issue descriptions
    5. Clears previous_encrypted_key after completion

    Args:
        session: Async database session.
        workspace_id: Workspace UUID.
        new_raw_key: New Fernet key to rotate to.
        batch_size: Number of rows to process per commit batch.

    Returns:
        Dict with counts: {"notes": N, "issues": M}

    Raises:
        ValueError: If new_raw_key is not a valid Fernet key.
        ValueError: If no existing key is configured for the workspace.
        ValueError: If any records could not be re-encrypted (previous key preserved).
    """
    from pilot_space.infrastructure.database.repositories.workspace_encryption_repository import (
        WorkspaceEncryptionRepository,
    )

    validate_workspace_key(new_raw_key)

    repo = WorkspaceEncryptionRepository(session)
    key_record = await repo.get_key_record(workspace_id)

    if key_record is None:
        msg = "No encryption key configured for this workspace. Cannot rotate."
        raise NotFoundError(msg)

    # Retrieve old raw key before upsert overwrites it
    old_raw_key = retrieve_workspace_key(key_record.encrypted_workspace_key)

    # Upsert saves current key to previous_encrypted_key, stores new key
    await repo.upsert_key(workspace_id, new_raw_key)
    await session.flush()

    # Re-encrypt notes
    notes = await _get_encrypted_notes(session, workspace_id)
    notes_count = 0
    notes_skipped = 0
    for i, note in enumerate(notes):
        if note.content:
            content_str = (
                json.dumps(note.content) if isinstance(note.content, dict) else str(note.content)
            )
            re_encrypted = _re_encrypt_string(content_str, old_raw_key, new_raw_key)
            if re_encrypted is not None:
                try:
                    note.content = json.loads(re_encrypted)
                except json.JSONDecodeError:
                    note.content = re_encrypted  # type: ignore[assignment]
                notes_count += 1
            else:
                notes_skipped += 1
        if (i + 1) % batch_size == 0:
            await session.flush()

    # Re-encrypt issue descriptions
    issues = await _get_encrypted_issues(session, workspace_id)
    issues_count = 0
    issues_skipped = 0
    for i, issue in enumerate(issues):
        if issue.description:
            re_encrypted = _re_encrypt_string(issue.description, old_raw_key, new_raw_key)
            if re_encrypted is not None:
                issue.description = re_encrypted
                issues_count += 1
            else:
                issues_skipped += 1
        if (i + 1) % batch_size == 0:
            await session.flush()

    await session.flush()

    # Abort if any records could not be re-encrypted — clearing the previous key
    # would make those records permanently unreadable.
    total_skipped = notes_skipped + issues_skipped
    if total_skipped > 0:
        msg = (
            f"Key rotation aborted: {total_skipped} record(s) could not be re-encrypted "
            f"({notes_skipped} note(s), {issues_skipped} issue(s)). "
            "Previous key has NOT been cleared. Investigate undecryptable content before retrying."
        )
        logger.error(msg)
        raise ConflictError(msg)

    # Clear previous key -- rotation complete
    await repo.clear_previous_key(workspace_id)
    await session.flush()

    logger.info(
        "Key rotation complete for workspace %s: %d notes, %d issues re-encrypted",
        workspace_id,
        notes_count,
        issues_count,
    )

    return {"notes": notes_count, "issues": issues_count}
