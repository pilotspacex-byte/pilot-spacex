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
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID

from cryptography.fernet import Fernet
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from pilot_space.ai.providers.constants import VALID_PROVIDERS
from pilot_space.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)


@dataclass
class APIKeyInfo:
    """API key metadata (without the actual key)."""

    workspace_id: UUID
    provider: str
    service_type: str
    is_valid: bool
    last_validated_at: datetime | None
    validation_error: str | None
    created_at: datetime
    updated_at: datetime
    base_url: str | None = None
    model_name: str | None = None


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
        await storage.store_api_key(workspace_id, "anthropic", "llm", "sk-ant-...")
        key = await storage.get_api_key(workspace_id, "anthropic", "llm")
    """

    VALID_PROVIDERS = VALID_PROVIDERS
    VALID_SERVICE_TYPES = frozenset({"embedding", "llm", "stt"})

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
        """Create Fernet cipher from master secret using secure KDF.

        Uses PBKDF2-HMAC-SHA256 with 600,000 iterations per OWASP recommendations.
        A fixed salt is acceptable here since master_secret is per-deployment.
        """
        salt = b"pilotspace_fernet_kdf_v1"
        key = hashlib.pbkdf2_hmac(
            "sha256",
            master_secret.encode(),
            salt,
            iterations=600_000,
            dklen=32,
        )
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
        service_type: str,
        api_key: str | None = None,
        base_url: str | None = None,
        model_name: str | None = None,
    ) -> None:
        """Store encrypted API key for workspace.

        Resets validation status since the key changed.

        Args:
            workspace_id: Workspace UUID.
            provider: Provider name (google, anthropic, ollama).
            service_type: Service category ('embedding' or 'llm').
            api_key: Raw API key to encrypt and store (optional for ollama).
            base_url: Custom base URL for provider API.
            model_name: Default model name override.

        Raises:
            ValueError: If provider or service_type is not valid.
        """
        if provider not in self.VALID_PROVIDERS:
            raise ValueError(f"Invalid provider: {provider}")
        if service_type not in self.VALID_SERVICE_TYPES:
            raise ValueError(f"Invalid service_type: {service_type}")

        encrypted = self._encrypt(api_key) if api_key else None

        from pilot_space.infrastructure.database.models import WorkspaceAPIKey

        stmt = insert(WorkspaceAPIKey).values(
            workspace_id=workspace_id,
            provider=provider,
            service_type=service_type,
            encrypted_key=encrypted,
            is_valid=True,
            last_validated_at=None,
            validation_error=None,
            base_url=base_url,
            model_name=model_name,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["workspace_id", "provider", "service_type"],
            set_={
                "encrypted_key": encrypted,
                "is_valid": True,
                "validation_error": None,
                "last_validated_at": None,
                "base_url": base_url,
                "model_name": model_name,
                "updated_at": datetime.now(UTC),
            },
        )

        await self.db.execute(stmt)
        await self.db.commit()

        logger.info(
            "key_storage_api_key_stored",
            workspace_id=str(workspace_id),
            provider=provider,
            service_type=service_type,
            key_preview=self._mask_key(api_key) if api_key else "none",
        )

    async def update_metadata(
        self,
        workspace_id: UUID,
        provider: str,
        service_type: str,
        base_url: str | None = None,
        model_name: str | None = None,
    ) -> bool:
        """Update only metadata (base_url/model_name) without touching the encrypted key.

        Preserves existing validation status and encrypted key.

        Args:
            workspace_id: Workspace UUID.
            provider: Provider name.
            service_type: Service category ('embedding' or 'llm').
            base_url: New base URL (None keeps existing).
            model_name: New model name (None keeps existing).

        Returns:
            True if row was updated, False if no existing key found.
        """
        from pilot_space.infrastructure.database.models import WorkspaceAPIKey

        stmt = select(WorkspaceAPIKey).where(
            WorkspaceAPIKey.workspace_id == workspace_id,
            WorkspaceAPIKey.provider == provider,
            WorkspaceAPIKey.service_type == service_type,
        )

        result = await self.db.execute(stmt)
        row = result.scalar_one_or_none()

        if row is None:
            return False

        if base_url is not None:
            row.base_url = base_url
        if model_name is not None:
            row.model_name = model_name
        row.updated_at = datetime.now(UTC)  # type: ignore[assignment]
        await self.db.commit()

        logger.info(
            "key_storage_metadata_updated",
            workspace_id=str(workspace_id),
            provider=provider,
        )
        return True

    async def get_api_key(
        self,
        workspace_id: UUID,
        provider: str,
        service_type: str,
    ) -> str | None:
        """Retrieve and decrypt API key.

        Args:
            workspace_id: Workspace UUID.
            provider: Provider name.
            service_type: Service category.

        Returns:
            Decrypted API key or None if not found or not set.
        """
        from pilot_space.infrastructure.database.models import WorkspaceAPIKey

        stmt = select(WorkspaceAPIKey.encrypted_key).where(
            WorkspaceAPIKey.workspace_id == workspace_id,
            WorkspaceAPIKey.provider == provider,
            WorkspaceAPIKey.service_type == service_type,
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
        service_type: str,
    ) -> bool:
        """Delete API key for workspace/provider/service_type.

        Args:
            workspace_id: Workspace UUID.
            provider: Provider name.
            service_type: Service category.

        Returns:
            True if key was deleted, False if not found.
        """
        from pilot_space.infrastructure.database.models import WorkspaceAPIKey

        stmt = select(WorkspaceAPIKey).where(
            WorkspaceAPIKey.workspace_id == workspace_id,
            WorkspaceAPIKey.provider == provider,
            WorkspaceAPIKey.service_type == service_type,
        )

        result = await self.db.execute(stmt)
        row = result.scalar_one_or_none()

        if row is None:
            return False

        await self.db.delete(row)
        await self.db.commit()

        logger.info(
            "key_storage_api_key_deleted",
            workspace_id=str(workspace_id),
            provider=provider,
            service_type=service_type,
        )

        return True

    async def validate_api_key(  # noqa: PLR0911
        self,
        provider: str,
        api_key: str | None,
        base_url: str | None = None,
    ) -> tuple[bool, str | None]:
        """Validate API key by making test call to provider.

        Args:
            provider: Provider name.
            api_key: API key to validate (None for keyless providers).
            base_url: Custom base URL (for Ollama).

        Returns:
            Tuple of (is_valid, error_message). error_message is None on success.
        """
        try:
            if provider == "anthropic":
                if not api_key:
                    return False, "API key is required"
                from anthropic import AsyncAnthropic

                client = AsyncAnthropic(
                    api_key=api_key,
                    base_url=base_url or None,
                )
                await client.messages.create(
                    model="claude-3-5-haiku-20241022",
                    max_tokens=1,
                    messages=[{"role": "user", "content": "ping"}],
                )
            elif provider == "google":
                if not api_key:
                    return False, "API key is required"
                import google.generativeai as genai  # type: ignore[import-untyped]

                genai.configure(api_key=api_key)  # type: ignore[attr-defined]
                model = genai.GenerativeModel("gemini-2.0-flash")  # type: ignore[attr-defined]
                await model.generate_content_async("ping")
            elif provider == "ollama":
                import httpx

                from pilot_space.ai.providers.constants import validate_ollama_base_url

                url = (base_url or "http://localhost:11434").rstrip("/")
                validate_ollama_base_url(url)
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.get(f"{url}/api/tags")
                    if resp.status_code != 200:
                        return False, f"Ollama returned HTTP {resp.status_code}"
            elif provider == "elevenlabs":
                if not api_key:
                    return False, "API key is required"
                import httpx

                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.get(
                        "https://api.elevenlabs.io/v1/models",
                        headers={"xi-api-key": api_key},
                    )
                    if resp.status_code in (401, 403):
                        return False, "Invalid ElevenLabs API key"
                    if resp.status_code != 200:
                        return False, f"ElevenLabs returned HTTP {resp.status_code}"
            else:
                logger.warning("key_storage_unknown_provider", provider=provider)
                return False, f"Unknown provider: {provider}"

            return True, None

        except Exception as e:
            error_msg = str(e)
            logger.warning(
                "key_storage_validation_failed",
                provider=provider,
                error=error_msg,
                key_preview=self._mask_key(api_key) if api_key else "none",
            )
            return False, error_msg

    async def validate_and_update(
        self,
        workspace_id: UUID,
        provider: str,
        service_type: str,
    ) -> bool:
        """Validate stored key and update validation status.

        Args:
            workspace_id: Workspace UUID.
            provider: Provider name.
            service_type: Service category.

        Returns:
            True if key is valid, False otherwise.
        """
        from pilot_space.infrastructure.database.models import WorkspaceAPIKey

        api_key = await self.get_api_key(workspace_id, provider, service_type)

        # Get key info for base_url (needed for Ollama validation)
        key_info = await self.get_key_info(workspace_id, provider, service_type)
        base_url = key_info.base_url if key_info else None

        is_valid, error_msg = await self.validate_api_key(provider, api_key, base_url)

        stmt = select(WorkspaceAPIKey).where(
            WorkspaceAPIKey.workspace_id == workspace_id,
            WorkspaceAPIKey.provider == provider,
            WorkspaceAPIKey.service_type == service_type,
        )

        result = await self.db.execute(stmt)
        row = result.scalar_one_or_none()

        if row:
            row.is_valid = is_valid
            row.last_validated_at = datetime.now(UTC)
            row.validation_error = error_msg
            await self.db.commit()

        return is_valid

    async def list_providers(
        self,
        workspace_id: UUID,
        service_type: str | None = None,
    ) -> list[str]:
        """List configured providers for workspace.

        Args:
            workspace_id: Workspace UUID.
            service_type: Optional filter by service category.

        Returns:
            List of provider names with stored keys.
        """
        from pilot_space.infrastructure.database.models import WorkspaceAPIKey

        stmt = select(WorkspaceAPIKey.provider).where(
            WorkspaceAPIKey.workspace_id == workspace_id,
        )
        if service_type:
            stmt = stmt.where(WorkspaceAPIKey.service_type == service_type)

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_key_info(
        self,
        workspace_id: UUID,
        provider: str,
        service_type: str,
    ) -> APIKeyInfo | None:
        """Get API key metadata (without actual key).

        Args:
            workspace_id: Workspace UUID.
            provider: Provider name.
            service_type: Service category.

        Returns:
            APIKeyInfo or None if not found.
        """
        from pilot_space.infrastructure.database.models import WorkspaceAPIKey

        stmt = select(WorkspaceAPIKey).where(
            WorkspaceAPIKey.workspace_id == workspace_id,
            WorkspaceAPIKey.provider == provider,
            WorkspaceAPIKey.service_type == service_type,
        )

        result = await self.db.execute(stmt)
        row = result.scalar_one_or_none()

        if row is None:
            return None

        return APIKeyInfo(
            workspace_id=row.workspace_id,
            provider=row.provider,
            service_type=row.service_type,
            is_valid=row.is_valid,
            last_validated_at=row.last_validated_at,
            validation_error=row.validation_error,
            created_at=row.created_at,
            updated_at=row.updated_at,
            base_url=row.base_url,
            model_name=row.model_name,
        )

    async def get_all_key_infos(self, workspace_id: UUID) -> list[APIKeyInfo]:
        """Get all API key metadata for a workspace in a single query.

        Args:
            workspace_id: Workspace UUID.

        Returns:
            List of APIKeyInfo for all configured providers.
        """
        from pilot_space.infrastructure.database.models import WorkspaceAPIKey

        stmt = select(WorkspaceAPIKey).where(
            WorkspaceAPIKey.workspace_id == workspace_id,
        )
        result = await self.db.execute(stmt)
        rows = result.scalars().all()
        return [
            APIKeyInfo(
                workspace_id=r.workspace_id,
                provider=r.provider,
                service_type=r.service_type,
                is_valid=r.is_valid,
                last_validated_at=r.last_validated_at,
                validation_error=r.validation_error,
                created_at=r.created_at,
                updated_at=r.updated_at,
                base_url=r.base_url,
                model_name=r.model_name,
            )
            for r in rows
        ]


__all__ = ["APIKeyInfo", "SecureKeyStorage"]
