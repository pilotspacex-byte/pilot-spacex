"""Secure API key storage using encryption (DD-002).

Implements BYOK (Bring Your Own Key) model for AI provider API keys.
Keys are encrypted at rest and never logged or exposed in error messages.

References:
- T011: Implement SecureKeyStorage class (DD-002)
- docs/DESIGN_DECISIONS.md#DD-002
- specs/004-mvp-agents-build/tasks/P3-T011-T016.md
"""

from __future__ import annotations

import base64
import hashlib
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID

from cryptography.fernet import Fernet
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


@dataclass
class APIKeyInfo:
    """API key metadata (without the actual key)."""

    workspace_id: UUID
    provider: str
    is_valid: bool
    last_validated_at: datetime | None
    validation_error: str | None
    created_at: datetime
    updated_at: datetime


class SecureKeyStorage:
    """Secure API key storage with encryption (DD-002).

    All keys are encrypted at rest using Fernet symmetric encryption.
    The encryption key is derived from a master secret.

    Security guarantees:
    - Keys are never logged or exposed in error messages
    - Keys are encrypted at rest in the database
    - Only masked versions are shown in logs (first 4 + last 4 chars)

    Usage:
        storage = SecureKeyStorage(db_session, master_secret="...")
        await storage.store_api_key(workspace_id, "anthropic", "sk-ant-...")
        key = await storage.get_api_key(workspace_id, "anthropic")
    """

    VALID_PROVIDERS = frozenset({"anthropic", "openai", "google"})

    def __init__(
        self,
        db: AsyncSession,
        master_secret: str,
    ) -> None:
        """Initialize secure key storage.

        Args:
            db: Async database session.
            master_secret: Master secret for key derivation.
        """
        self.db = db
        self._fernet = self._create_fernet(master_secret)

    def _create_fernet(self, master_secret: str) -> Fernet:
        """Create Fernet cipher from master secret."""
        # Derive a 32-byte key from the master secret
        key = hashlib.sha256(master_secret.encode()).digest()
        # Fernet requires URL-safe base64 encoded key
        return Fernet(base64.urlsafe_b64encode(key))

    def _encrypt(self, value: str) -> str:
        """Encrypt a value."""
        return self._fernet.encrypt(value.encode()).decode()

    def _decrypt(self, encrypted_value: str) -> str:
        """Decrypt a value."""
        return self._fernet.decrypt(encrypted_value.encode()).decode()

    @staticmethod
    def _mask_key(key: str) -> str:
        """Create a masked version of the key for logging."""
        if len(key) <= 8:
            return "*" * len(key)
        return f"{key[:4]}...{key[-4:]}"

    async def store_api_key(
        self,
        workspace_id: UUID,
        provider: str,
        api_key: str,
    ) -> None:
        """Store encrypted API key for workspace.

        Args:
            workspace_id: Workspace UUID.
            provider: Provider name (anthropic, openai, google).
            api_key: Raw API key to encrypt and store.

        Raises:
            ValueError: If provider is not valid.
        """
        if provider not in self.VALID_PROVIDERS:
            raise ValueError(f"Invalid provider: {provider}")

        encrypted = self._encrypt(api_key)

        # Use PostgreSQL upsert
        from pilot_space.infrastructure.database.models import WorkspaceAPIKey

        stmt = insert(WorkspaceAPIKey).values(
            workspace_id=workspace_id,
            provider=provider,
            encrypted_key=encrypted,
            is_valid=True,
            last_validated_at=None,
            validation_error=None,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["workspace_id", "provider"],
            set_={
                "encrypted_key": encrypted,
                "is_valid": True,
                "validation_error": None,
                "updated_at": datetime.now(UTC),
            },
        )

        await self.db.execute(stmt)
        await self.db.commit()

        logger.info(
            "API key stored",
            extra={
                "workspace_id": str(workspace_id),
                "provider": provider,
                "key_preview": self._mask_key(api_key),
            },
        )

    async def get_api_key(
        self,
        workspace_id: UUID,
        provider: str,
    ) -> str | None:
        """Retrieve and decrypt API key.

        Args:
            workspace_id: Workspace UUID.
            provider: Provider name.

        Returns:
            Decrypted API key or None if not found.
        """
        from pilot_space.infrastructure.database.models import WorkspaceAPIKey

        stmt = select(WorkspaceAPIKey.encrypted_key).where(
            WorkspaceAPIKey.workspace_id == workspace_id,
            WorkspaceAPIKey.provider == provider,
        )

        result = await self.db.execute(stmt)
        row = result.scalar_one_or_none()

        if row is None:
            return None

        return self._decrypt(row)

    async def delete_api_key(
        self,
        workspace_id: UUID,
        provider: str,
    ) -> bool:
        """Delete API key for workspace/provider.

        Args:
            workspace_id: Workspace UUID.
            provider: Provider name.

        Returns:
            True if key was deleted, False if not found.
        """
        from pilot_space.infrastructure.database.models import WorkspaceAPIKey

        stmt = select(WorkspaceAPIKey).where(
            WorkspaceAPIKey.workspace_id == workspace_id,
            WorkspaceAPIKey.provider == provider,
        )

        result = await self.db.execute(stmt)
        row = result.scalar_one_or_none()

        if row is None:
            return False

        await self.db.delete(row)
        await self.db.commit()

        logger.info(
            "API key deleted",
            extra={
                "workspace_id": str(workspace_id),
                "provider": provider,
            },
        )

        return True

    async def validate_api_key(
        self,
        provider: str,
        api_key: str,
    ) -> bool:
        """Validate API key by making test call to provider.

        Args:
            provider: Provider name.
            api_key: API key to validate.

        Returns:
            True if key is valid, False otherwise.
        """
        try:
            if provider == "anthropic":
                from anthropic import AsyncAnthropic

                client = AsyncAnthropic(api_key=api_key)
                # Use minimal tokens to validate
                await client.messages.create(
                    model="claude-3-5-haiku-20241022",
                    max_tokens=1,
                    messages=[{"role": "user", "content": "ping"}],
                )
            elif provider == "openai":
                from openai import AsyncOpenAI

                client = AsyncOpenAI(api_key=api_key)
                # List models is a cheap validation
                await client.models.list()
            elif provider == "google":
                import google.generativeai as genai  # type: ignore[import-untyped]

                genai.configure(api_key=api_key)  # type: ignore[attr-defined]
                model = genai.GenerativeModel("gemini-2.0-flash")  # type: ignore[attr-defined]
                await model.generate_content_async("ping")
            else:
                logger.warning(
                    "Unknown provider for validation",
                    extra={"provider": provider},
                )
                return False

            return True

        except Exception as e:
            logger.warning(
                "API key validation failed",
                extra={
                    "provider": provider,
                    "error": str(e),
                    "key_preview": self._mask_key(api_key),
                },
            )
            return False

    async def validate_and_update(
        self,
        workspace_id: UUID,
        provider: str,
    ) -> bool:
        """Validate stored key and update validation status.

        Args:
            workspace_id: Workspace UUID.
            provider: Provider name.

        Returns:
            True if key is valid, False otherwise.
        """
        from pilot_space.infrastructure.database.models import WorkspaceAPIKey

        api_key = await self.get_api_key(workspace_id, provider)
        if api_key is None:
            return False

        is_valid = await self.validate_api_key(provider, api_key)

        # Update validation status
        stmt = select(WorkspaceAPIKey).where(
            WorkspaceAPIKey.workspace_id == workspace_id,
            WorkspaceAPIKey.provider == provider,
        )

        result = await self.db.execute(stmt)
        row = result.scalar_one_or_none()

        if row:
            row.is_valid = is_valid
            row.last_validated_at = datetime.now(UTC)
            row.validation_error = None if is_valid else "Validation failed"
            await self.db.commit()

        return is_valid

    async def list_providers(
        self,
        workspace_id: UUID,
    ) -> list[str]:
        """List configured providers for workspace.

        Args:
            workspace_id: Workspace UUID.

        Returns:
            List of provider names with stored keys.
        """
        from pilot_space.infrastructure.database.models import WorkspaceAPIKey

        stmt = select(WorkspaceAPIKey.provider).where(
            WorkspaceAPIKey.workspace_id == workspace_id,
        )

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_key_info(
        self,
        workspace_id: UUID,
        provider: str,
    ) -> APIKeyInfo | None:
        """Get API key metadata (without actual key).

        Args:
            workspace_id: Workspace UUID.
            provider: Provider name.

        Returns:
            APIKeyInfo or None if not found.
        """
        from pilot_space.infrastructure.database.models import WorkspaceAPIKey

        stmt = select(WorkspaceAPIKey).where(
            WorkspaceAPIKey.workspace_id == workspace_id,
            WorkspaceAPIKey.provider == provider,
        )

        result = await self.db.execute(stmt)
        row = result.scalar_one_or_none()

        if row is None:
            return None

        return APIKeyInfo(
            workspace_id=row.workspace_id,
            provider=row.provider,
            is_valid=row.is_valid,
            last_validated_at=row.last_validated_at,
            validation_error=row.validation_error,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )


__all__ = ["APIKeyInfo", "SecureKeyStorage"]
