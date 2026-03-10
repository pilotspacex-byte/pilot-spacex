"""Repository for workspace encryption key records.

Provides upsert and lookup operations for WorkspaceEncryptionKey records.
No DELETE — encryption keys are archived, not deleted (key rotation creates a new version).
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pilot_space.infrastructure.database.models.workspace_encryption_key import (
    WorkspaceEncryptionKey,
)
from pilot_space.infrastructure.workspace_encryption import (
    store_workspace_key,
    validate_workspace_key,
)


class WorkspaceEncryptionRepository:
    """Repository for workspace encryption key CRUD operations.

    Attributes:
        session: Async database session.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with session.

        Args:
            session: Async database session for queries.
        """
        self.session = session

    async def get_key_record(self, workspace_id: str) -> WorkspaceEncryptionKey | None:
        """Fetch the encryption key record for a workspace.

        Args:
            workspace_id: Workspace UUID string.

        Returns:
            WorkspaceEncryptionKey record, or None if not configured.
        """
        result = await self.session.execute(
            select(WorkspaceEncryptionKey).where(
                WorkspaceEncryptionKey.workspace_id == workspace_id
            )
        )
        return result.scalar_one_or_none()

    async def upsert_key(self, workspace_id: str, raw_key: str) -> WorkspaceEncryptionKey:
        """Store or update the workspace encryption key.

        Validates key format, then encrypts with master key before storing.
        Increments key_version on update.

        Args:
            workspace_id: Workspace UUID string.
            raw_key: Raw Fernet key to store.

        Returns:
            Updated or newly created WorkspaceEncryptionKey record.

        Raises:
            ValueError: If raw_key is not a valid Fernet key.
        """
        validate_workspace_key(raw_key)
        encrypted = store_workspace_key(raw_key)
        key_hint = raw_key[-8:]

        existing = await self.get_key_record(workspace_id)
        if existing is not None:
            existing.encrypted_workspace_key = encrypted
            existing.key_hint = key_hint
            existing.key_version = existing.key_version + 1
            await self.session.flush()
            return existing

        record = WorkspaceEncryptionKey(
            workspace_id=workspace_id,
            encrypted_workspace_key=encrypted,
            key_hint=key_hint,
            key_version=1,
        )
        self.session.add(record)
        await self.session.flush()
        return record
