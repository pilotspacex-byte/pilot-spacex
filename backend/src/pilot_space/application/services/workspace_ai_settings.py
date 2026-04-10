"""WorkspaceAISettingsService — manage workspace AI provider configuration.

Extracted from workspace_ai_settings router (T062-T066).
Handles provider status lookup, API key management, and feature toggle updates.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy.orm.attributes import flag_modified

from pilot_space.ai.providers.constants import PROVIDER_SERVICE_SLOTS
from pilot_space.application.services.workspace_ai_settings_toggles import (
    ProducerToggles,
    get_producer_toggles,
    set_producer_toggle,
)
from pilot_space.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from pilot_space.infrastructure.database.models.workspace import Workspace
    from pilot_space.infrastructure.database.repositories.workspace_repository import (
        WorkspaceRepository,
    )

logger = get_logger(__name__)


class WorkspaceAISettingsService:
    """Workspace AI settings business logic.

    Provides methods to read and update workspace AI provider configuration,
    API key validation, and feature toggles.
    """

    def __init__(
        self,
        session: AsyncSession,
        workspace_repository: WorkspaceRepository,
    ) -> None:
        self._session = session
        self._workspace_repo = workspace_repository

    async def get_ai_settings(
        self,
        workspace: Workspace,
        workspace_id: UUID,
    ) -> Any:
        """Build AI settings response with provider statuses and feature toggles.

        Args:
            workspace: The resolved workspace model (admin-verified).
            workspace_id: Workspace UUID.

        Returns:
            WorkspaceAISettingsResponse with providers, features, defaults.
        """
        from pilot_space.ai.infrastructure.key_storage import SecureKeyStorage
        from pilot_space.api.v1.schemas.workspace import (
            AIFeatureToggles,
            ProviderStatus,
            WorkspaceAISettingsResponse,
        )
        from pilot_space.config import get_settings

        settings = get_settings()
        key_storage = SecureKeyStorage(
            db=self._session,
            master_secret=settings.encryption_key.get_secret_value(),
        )

        # Batch-fetch all key infos in one query instead of N+1
        all_key_infos = await key_storage.get_all_key_infos(workspace_id)
        key_info_map = {(ki.provider, ki.service_type): ki for ki in all_key_infos}

        providers = []
        for provider, service_type, _supports_both in PROVIDER_SERVICE_SLOTS:
            key_info = key_info_map.get((provider, service_type))
            providers.append(
                ProviderStatus(
                    provider=provider,
                    service_type=service_type,
                    is_configured=key_info is not None,
                    is_valid=key_info.is_valid if key_info else None,
                    last_validated_at=key_info.last_validated_at if key_info else None,
                    base_url=key_info.base_url if key_info else None,
                    model_name=key_info.model_name if key_info else None,
                )
            )

        features = _get_workspace_features(workspace, AIFeatureToggles)
        ws_settings = workspace.settings or {}

        return WorkspaceAISettingsResponse(
            workspace_id=workspace_id,
            providers=providers,
            features=features,
            default_llm_provider=ws_settings.get("default_llm_provider", "anthropic"),
            default_embedding_provider=ws_settings.get("default_embedding_provider", "google"),
            cost_limit_usd=ws_settings.get("ai_cost_limit_usd"),
        )

    async def update_ai_settings(
        self,
        workspace: Workspace,
        workspace_id: UUID,
        body: Any,
    ) -> Any:
        """Process AI settings update: store/validate keys, update features.

        Args:
            workspace: The resolved workspace model (admin-verified).
            workspace_id: Workspace UUID.
            body: WorkspaceAISettingsUpdate request.

        Returns:
            WorkspaceAISettingsUpdateResponse with validation results.
        """
        from pilot_space.ai.infrastructure.key_storage import SecureKeyStorage
        from pilot_space.api.v1.schemas.workspace import (
            KeyValidationResult,
            WorkspaceAISettingsUpdateResponse,
        )
        from pilot_space.config import get_settings

        settings = get_settings()
        key_storage = SecureKeyStorage(
            db=self._session,
            master_secret=settings.encryption_key.get_secret_value(),
        )

        workspace_repo = self._workspace_repo
        validation_results: list[KeyValidationResult] = []
        updated_providers: list[str] = []

        if body.api_keys:
            for key_update in body.api_keys:
                result = await self._process_key_update(
                    key_storage=key_storage,
                    workspace_id=workspace_id,
                    key_update=key_update,
                )
                if result is not None:
                    vr, provider_label = result
                    validation_results.append(vr)
                    if vr.is_valid or provider_label not in updated_providers:
                        updated_providers.append(provider_label)

        # Update feature toggles and default providers
        updated_features = False
        needs_settings_update = (
            body.features
            or body.cost_limit_usd is not None
            or body.default_llm_provider is not None
            or body.default_embedding_provider is not None
        )
        if needs_settings_update:
            workspace_settings = workspace.settings or {}

            if body.features:
                workspace_settings["ai_features"] = body.features.model_dump()
                updated_features = True

            if body.cost_limit_usd is not None:
                workspace_settings["ai_cost_limit_usd"] = body.cost_limit_usd
                updated_features = True

            if body.default_llm_provider is not None:
                workspace_settings["default_llm_provider"] = body.default_llm_provider
                updated_features = True

            if body.default_embedding_provider is not None:
                workspace_settings["default_embedding_provider"] = body.default_embedding_provider
                updated_features = True

            workspace.settings = workspace_settings
            flag_modified(workspace, "settings")
            await workspace_repo.update(workspace)
            await self._session.commit()

        logger.info(
            "Workspace AI settings updated",
            extra={
                "workspace_id": str(workspace_id),
                "updated_providers": updated_providers,
                "updated_features": updated_features,
            },
        )

        return WorkspaceAISettingsUpdateResponse(
            success=all(r.is_valid for r in validation_results),
            validation_results=validation_results,
            updated_providers=updated_providers,
            updated_features=updated_features,
        )

    async def _process_key_update(
        self,
        key_storage: Any,
        workspace_id: UUID,
        key_update: Any,
    ) -> tuple[Any, str] | None:
        """Process a single API key update entry.

        Returns (KeyValidationResult, provider_label) or None if skipped.
        """
        from pilot_space.api.v1.schemas.workspace import KeyValidationResult

        provider = key_update.provider
        service_type = key_update.service_type
        provider_label = f"{provider}:{service_type}"

        existing_info = await key_storage.get_key_info(workspace_id, provider, service_type)

        has_new_key = key_update.api_key is not None
        has_metadata_change = key_update.base_url is not None or key_update.model_name is not None

        # Merge metadata with existing values
        base_url = (
            key_update.base_url
            if key_update.base_url is not None
            else (existing_info.base_url if existing_info else None)
        )
        model_name = (
            key_update.model_name
            if key_update.model_name is not None
            else (existing_info.model_name if existing_info else None)
        )

        # SSRF check for Ollama base_url
        if provider == "ollama" and base_url:
            try:
                from pilot_space.ai.providers.constants import validate_ollama_base_url

                validate_ollama_base_url(base_url)
            except ValueError as e:
                return (
                    KeyValidationResult(
                        provider=provider_label,
                        is_valid=False,
                        error_message=str(e),
                    ),
                    provider_label,
                )

        if has_new_key:
            return await self._handle_new_key(
                key_storage,
                workspace_id,
                provider,
                service_type,
                key_update,
                base_url,
                model_name,
                provider_label,
            )
        if has_metadata_change and existing_info is not None:
            return await self._handle_metadata_update(
                key_storage,
                workspace_id,
                provider,
                service_type,
                base_url,
                model_name,
                provider_label,
            )
        if has_metadata_change and existing_info is None:
            return await self._handle_metadata_no_existing(
                key_storage,
                workspace_id,
                provider,
                service_type,
                base_url,
                model_name,
                provider_label,
            )
        if not has_new_key and not has_metadata_change and existing_info is not None:
            # Explicit None api_key with no metadata changes -- delete the key
            await key_storage.delete_api_key(workspace_id, provider, service_type)
            return (
                KeyValidationResult(
                    provider=provider_label,
                    is_valid=True,
                    error_message=None,
                ),
                provider_label,
            )

        return None

    async def _handle_new_key(
        self,
        ks: Any,
        workspace_id: UUID,
        provider: str,
        service_type: str,
        ku: Any,
        base_url: str | None,
        model_name: str | None,
        provider_label: str,
    ) -> tuple[Any, str]:
        """Store and validate a new API key."""
        from pilot_space.api.v1.schemas.workspace import KeyValidationResult

        if provider == "ollama" and not base_url:
            return (
                KeyValidationResult(
                    provider=provider_label,
                    is_valid=False,
                    error_message="Base URL is required for Ollama",
                ),
                provider_label,
            )

        await ks.store_api_key(
            workspace_id=workspace_id,
            provider=provider,
            service_type=service_type,
            api_key=ku.api_key,
            base_url=base_url,
            model_name=model_name,
        )

        is_valid, val_error = await ks.validate_api_key(
            provider=provider,
            api_key=ku.api_key,
            base_url=base_url,
        )

        return (
            KeyValidationResult(
                provider=provider_label,
                is_valid=is_valid,
                error_message=val_error,
            ),
            provider_label,
        )

    async def _handle_metadata_update(
        self,
        ks: Any,
        workspace_id: UUID,
        provider: str,
        service_type: str,
        base_url: str | None,
        model_name: str | None,
        provider_label: str,
    ) -> tuple[Any, str]:
        """Update metadata on an existing key."""
        from pilot_space.api.v1.schemas.workspace import KeyValidationResult

        await ks.update_metadata(
            workspace_id=workspace_id,
            provider=provider,
            service_type=service_type,
            base_url=base_url,
            model_name=model_name,
        )
        return (
            KeyValidationResult(
                provider=provider_label,
                is_valid=True,
                error_message=None,
            ),
            provider_label,
        )

    async def _handle_metadata_no_existing(
        self,
        ks: Any,
        workspace_id: UUID,
        provider: str,
        service_type: str,
        base_url: str | None,
        model_name: str | None,
        provider_label: str,
    ) -> tuple[Any, str]:
        """Handle metadata change with no existing key (Ollama special case)."""
        from pilot_space.api.v1.schemas.workspace import KeyValidationResult

        if provider == "ollama":
            await ks.store_api_key(
                workspace_id=workspace_id,
                provider=provider,
                service_type=service_type,
                api_key=None,
                base_url=base_url,
                model_name=model_name,
            )

            is_valid, val_error = await ks.validate_api_key(
                provider=provider,
                api_key=None,
                base_url=base_url,
            )

            return (
                KeyValidationResult(
                    provider=provider_label,
                    is_valid=is_valid,
                    error_message=val_error,
                ),
                provider_label,
            )
        return (
            KeyValidationResult(
                provider=provider_label,
                is_valid=False,
                error_message="API key required before updating provider metadata",
            ),
            provider_label,
        )


    # ------------------------------------------------------------------
    # Phase 70-06 — memory producer opt-out toggles
    # ------------------------------------------------------------------

    async def get_producer_toggles(self, workspace_id: UUID) -> ProducerToggles:
        """Return the four Phase 70 memory producer toggles for a workspace.

        Defaults (3x True, summarizer False) are returned when the
        workspace has no explicit configuration or on read failure.
        """
        return await get_producer_toggles(self._session, workspace_id)

    async def set_producer_toggle(
        self,
        workspace_id: UUID,
        producer: str,
        enabled: bool,
    ) -> ProducerToggles:
        """Persist a single producer toggle and commit.

        Raises ``ValidationError`` for unknown producer names.
        """
        toggles = await set_producer_toggle(
            self._session, workspace_id, producer, enabled
        )
        await self._session.commit()
        return toggles


def _get_workspace_features(workspace: Workspace, toggles_cls: type[Any]) -> Any:
    """Extract feature toggles from workspace settings."""
    if not workspace.settings or "ai_features" not in workspace.settings:
        return toggles_cls()

    features_data = workspace.settings["ai_features"]
    return toggles_cls(**features_data)


__all__ = ["WorkspaceAISettingsService"]
