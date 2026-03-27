"""AI Configuration service for workspace-level LLM provider management (FR-022).

Handles provider key testing, workspace config CRUD, and model listing.
API keys are encrypted before storage and never returned in responses.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from pilot_space.domain.exceptions import ConflictError, ForbiddenError, NotFoundError
from pilot_space.infrastructure.database.models.ai_configuration import (
    AIConfiguration,
    LLMProvider,
)
from pilot_space.infrastructure.database.models.workspace_member import WorkspaceRole
from pilot_space.infrastructure.database.repositories.ai_configuration_repository import (
    AIConfigurationRepository,
)
from pilot_space.infrastructure.database.rls import set_rls_context
from pilot_space.infrastructure.encryption import decrypt_api_key, encrypt_api_key
from pilot_space.infrastructure.logging import get_logger

logger = get_logger(__name__)

# Lock to protect genai.configure() global state mutation from race conditions
google_api_lock = asyncio.Lock()

# Default base URLs for OpenAI-compatible providers
_OPENAI_COMPATIBLE_DEFAULTS: dict[LLMProvider, str] = {
    LLMProvider.KIMI: "https://api.moonshot.cn/v1",
    LLMProvider.GLM: "https://open.bigmodel.cn/api/paas/v4",
}


@dataclass
class TestKeyResult:
    """Result of testing a provider API key."""

    success: bool
    provider: LLMProvider
    message: str
    latency_ms: int | None


@dataclass
class AvailableModel:
    """A model available from a provider configuration."""

    provider_config_id: UUID
    provider: str
    model_id: str
    display_name: str
    is_selectable: bool


class AIConfigurationService:
    """Workspace-level AI configuration management.

    Args:
        session: Request-scoped async database session.
        workspace_repository: Workspace repository for membership checks.
    """

    def __init__(
        self,
        session: AsyncSession,
        workspace_repository: object,
    ) -> None:
        self._session = session
        self._workspace_repo = workspace_repository
        self._ai_config_repo = AIConfigurationRepository(session=session)

    async def _verify_workspace_membership(
        self,
        workspace_id: UUID,
        user_id: UUID,
        *,
        require_admin: bool = False,
    ) -> WorkspaceRole:
        """Verify user is a member of the workspace.

        Returns:
            User's role in the workspace.

        Raises:
            NotFoundError: If workspace not found.
            ForbiddenError: If user lacks required access.
        """
        workspace = await self._workspace_repo.get_with_members(workspace_id)  # type: ignore[union-attr]
        if not workspace:
            raise NotFoundError("Workspace not found")

        member = next(
            (m for m in (workspace.members or []) if m.user_id == user_id and not m.is_deleted),
            None,
        )
        if not member:
            raise ForbiddenError("Not a member of this workspace")

        if require_admin and member.role not in (WorkspaceRole.ADMIN, WorkspaceRole.OWNER):
            raise ForbiddenError("Admin role required for this operation")

        return member.role

    async def list_configurations(self, workspace_id: UUID, user_id: UUID) -> list[AIConfiguration]:
        """List AI configurations for a workspace."""
        await set_rls_context(self._session, user_id, workspace_id)
        await self._verify_workspace_membership(workspace_id, user_id)

        return list(
            await self._ai_config_repo.get_by_workspace(workspace_id, include_inactive=True)
        )

    async def create_configuration(
        self,
        workspace_id: UUID,
        user_id: UUID,
        *,
        provider: LLMProvider,
        api_key: str,
        settings: dict[str, Any] | None = None,
        usage_limits: dict[str, Any] | None = None,
        base_url: str | None = None,
        display_name: str | None = None,
    ) -> AIConfiguration:
        """Create an AI configuration for a workspace.

        Raises:
            ConflictError: If provider already configured.
            ForbiddenError: If not admin.
        """
        await set_rls_context(self._session, user_id, workspace_id)
        await self._verify_workspace_membership(workspace_id, user_id, require_admin=True)

        existing = await self._ai_config_repo.get_by_workspace_and_provider(workspace_id, provider)
        if existing:
            raise ConflictError(f"Configuration for provider '{provider.value}' already exists")

        encrypted_key = encrypt_api_key(api_key)

        config = AIConfiguration(
            workspace_id=workspace_id,
            provider=provider,
            api_key_encrypted=encrypted_key,
            is_active=True,
            settings=settings,
            usage_limits=usage_limits,
            base_url=base_url,
            display_name=display_name,
        )
        config = await self._ai_config_repo.create(config)
        await self._session.commit()

        logger.info(
            "AI configuration created",
            extra={
                "workspace_id": str(workspace_id),
                "provider": provider.value,
                "config_id": str(config.id),
            },
        )

        return config

    async def get_configuration(
        self, workspace_id: UUID, config_id: UUID, user_id: UUID
    ) -> AIConfiguration:
        """Get a specific AI configuration.

        Raises:
            NotFoundError: If not found.
        """
        await set_rls_context(self._session, user_id, workspace_id)
        await self._verify_workspace_membership(workspace_id, user_id)

        config = await self._ai_config_repo.get_by_workspace_and_id(workspace_id, config_id)
        if not config:
            raise NotFoundError("AI configuration not found")

        return config

    async def update_configuration(
        self,
        workspace_id: UUID,
        config_id: UUID,
        user_id: UUID,
        update_data: dict[str, Any],
    ) -> AIConfiguration:
        """Update an AI configuration.

        Args:
            workspace_id: Workspace UUID.
            config_id: Configuration UUID.
            user_id: Requesting user UUID.
            update_data: Dict of fields to update (from model_dump(exclude_unset=True)).

        Raises:
            NotFoundError: If not found.
            ForbiddenError: If not admin.
        """
        await set_rls_context(self._session, user_id, workspace_id)
        await self._verify_workspace_membership(workspace_id, user_id, require_admin=True)

        config = await self._ai_config_repo.get_by_workspace_and_id(workspace_id, config_id)
        if not config:
            raise NotFoundError("AI configuration not found")

        # Handle API key update separately (needs encryption)
        if "api_key" in update_data:
            api_key = update_data.pop("api_key")
            if api_key:
                config.api_key_encrypted = encrypt_api_key(api_key)

        for key, value in update_data.items():
            setattr(config, key, value)

        config = await self._ai_config_repo.update(config)
        await self._session.commit()

        logger.info(
            "AI configuration updated",
            extra={
                "workspace_id": str(workspace_id),
                "config_id": str(config_id),
            },
        )

        return config

    async def delete_configuration(
        self, workspace_id: UUID, config_id: UUID, user_id: UUID
    ) -> AIConfiguration:
        """Delete an AI configuration.

        Returns:
            The deleted configuration (for response metadata).

        Raises:
            NotFoundError: If not found.
            ForbiddenError: If not admin.
        """
        await set_rls_context(self._session, user_id, workspace_id)
        await self._verify_workspace_membership(workspace_id, user_id, require_admin=True)

        config = await self._ai_config_repo.get_by_workspace_and_id(workspace_id, config_id)
        if not config:
            raise NotFoundError("AI configuration not found")

        await self._ai_config_repo.delete(config)
        await self._session.commit()

        logger.info(
            "AI configuration deleted",
            extra={
                "workspace_id": str(workspace_id),
                "config_id": str(config_id),
                "provider": config.provider.value,
            },
        )

        return config

    async def test_configuration(
        self, workspace_id: UUID, config_id: UUID, user_id: UUID
    ) -> TestKeyResult:
        """Test an AI configuration by validating the API key.

        Makes a minimal API call to the provider to verify the key is valid.
        """
        await set_rls_context(self._session, user_id, workspace_id)
        await self._verify_workspace_membership(workspace_id, user_id)

        config = await self._ai_config_repo.get_by_workspace_and_id(workspace_id, config_id)
        if not config:
            raise NotFoundError("AI configuration not found")

        from pilot_space.infrastructure.encryption import EncryptionError

        try:
            api_key = decrypt_api_key(config.api_key_encrypted)
        except EncryptionError:
            logger.exception("Failed to decrypt API key for testing")
            return TestKeyResult(
                success=False,
                provider=config.provider,
                message="Failed to decrypt API key. Configuration may be corrupted.",
                latency_ms=None,
            )

        start_time = time.perf_counter()
        success, message = await self._test_provider_api_key(
            config.provider, api_key, config.base_url
        )
        latency_ms = int((time.perf_counter() - start_time) * 1000)

        logger.info(
            "AI configuration test completed",
            extra={
                "workspace_id": str(workspace_id),
                "config_id": str(config_id),
                "provider": config.provider.value,
                "success": success,
                "latency_ms": latency_ms,
            },
        )

        return TestKeyResult(
            success=success,
            provider=config.provider,
            message=message,
            latency_ms=latency_ms if success else None,
        )

    async def list_available_models(
        self, workspace_id: UUID, user_id: UUID
    ) -> list[AvailableModel]:
        """List all models available from active provider configurations."""
        await set_rls_context(self._session, user_id, workspace_id)
        await self._verify_workspace_membership(workspace_id, user_id)

        from pilot_space.ai.providers.model_listing import ModelListingService

        listing_service = ModelListingService()
        models = await listing_service.list_models_for_workspace(workspace_id, self._session)

        return [
            AvailableModel(
                provider_config_id=UUID(m.provider_config_id),
                provider=m.provider,
                model_id=m.model_id,
                display_name=m.display_name,
                is_selectable=m.is_selectable,
            )
            for m in models
        ]

    # -----------------------------------------------------------------------
    # Provider key testing
    # -----------------------------------------------------------------------

    @staticmethod
    async def _test_provider_api_key(  # noqa: PLR0911
        provider: LLMProvider, api_key: str, base_url: str | None = None
    ) -> tuple[bool, str]:
        """Test an API key with the specified provider."""
        if provider == LLMProvider.ANTHROPIC:
            return await AIConfigurationService._test_anthropic_key(api_key)
        if provider == LLMProvider.OPENAI:
            return await AIConfigurationService._test_openai_key(api_key)
        if provider == LLMProvider.GOOGLE:
            return await AIConfigurationService._test_google_key(api_key)
        if provider in _OPENAI_COMPATIBLE_DEFAULTS:
            resolved_url = base_url or _OPENAI_COMPATIBLE_DEFAULTS[provider]
            return await AIConfigurationService._test_openai_compatible_key(api_key, resolved_url)
        if provider == LLMProvider.CUSTOM:
            if not base_url:
                return False, "Custom provider requires a base_url"
            return await AIConfigurationService._test_openai_compatible_key(api_key, base_url)
        return False, f"Unknown provider: {provider}"

    @staticmethod
    async def _test_anthropic_key(api_key: str) -> tuple[bool, str]:
        """Test Anthropic API key validity."""
        import anthropic

        try:
            client = anthropic.AsyncAnthropic(api_key=api_key)
            await client.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=1,
                messages=[{"role": "user", "content": "test"}],
            )
        except anthropic.AuthenticationError:
            return False, "Invalid API key"
        except anthropic.PermissionDeniedError:
            return False, "API key lacks required permissions"
        except anthropic.RateLimitError:
            return True, "API key is valid (rate limited)"
        except anthropic.APIError as e:
            return False, f"API error: {e.message}"
        else:
            return True, "API key is valid"

    @staticmethod
    async def _test_openai_key(api_key: str) -> tuple[bool, str]:
        """Test OpenAI API key validity."""
        import openai

        try:
            client = openai.AsyncOpenAI(api_key=api_key)
            await client.models.list()
        except openai.AuthenticationError:
            return False, "Invalid API key"
        except openai.PermissionDeniedError:
            return False, "API key lacks required permissions"
        except openai.RateLimitError:
            return True, "API key is valid (rate limited)"
        except openai.APIError as e:
            return False, f"API error: {e.message}"
        else:
            return True, "API key is valid"

    @staticmethod
    async def _test_google_key(api_key: str) -> tuple[bool, str]:
        """Test Google AI API key validity."""
        import google.generativeai as genai  # type: ignore[import-untyped]

        try:
            async with google_api_lock:
                genai.configure(api_key=api_key)  # pyright: ignore[reportPrivateImportUsage,reportUnknownMemberType]
                list(genai.list_models())  # pyright: ignore[reportPrivateImportUsage,reportUnknownMemberType,reportUnknownArgumentType]
        except Exception as e:
            error_str = str(e).lower()
            if "invalid" in error_str or "api key" in error_str:
                return False, "Invalid API key"
            if "permission" in error_str:
                return False, "API key lacks required permissions"
            return False, f"API error: {e!s}"
        else:
            return True, "API key is valid"

    @staticmethod
    async def _test_openai_compatible_key(api_key: str, base_url: str) -> tuple[bool, str]:
        """Test an OpenAI-compatible API key by listing models at the given base_url."""
        import openai

        try:
            client = openai.AsyncOpenAI(api_key=api_key, base_url=base_url)
            await client.models.list()
        except openai.AuthenticationError:
            return False, "Invalid API key"
        except openai.PermissionDeniedError:
            return False, "API key lacks required permissions"
        except openai.RateLimitError:
            return True, "API key is valid (rate limited)"
        except openai.APIError as e:
            return False, f"API error: {e.message}"
        else:
            return True, "API key is valid"
