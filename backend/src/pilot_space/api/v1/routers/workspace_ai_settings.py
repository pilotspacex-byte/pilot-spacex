"""Workspace AI settings router for Pilot Space API.

Provides endpoints for managing workspace AI provider configuration,
API key validation, and feature toggles (T062-T066).
Routes are mounted under /workspaces/{workspace_id}/ai/settings.

Service-based architecture: 2 service slots (embedding + llm).
Supported providers: google (embedding), anthropic (llm), ollama (both).
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy.orm.attributes import flag_modified

from pilot_space.ai.providers.constants import PROVIDER_SERVICE_SLOTS
from pilot_space.api.v1.schemas.workspace import (
    AIFeatureToggles,
    KeyValidationResult,
    ProviderStatus,
    WorkspaceAISettingsResponse,
    WorkspaceAISettingsUpdate,
    WorkspaceAISettingsUpdateResponse,
)
from pilot_space.dependencies import (
    CurrentUser,
    DbSession,
)
from pilot_space.infrastructure.database.models.workspace import Workspace
from pilot_space.infrastructure.database.repositories.workspace_repository import (
    WorkspaceRepository,
)
from pilot_space.infrastructure.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


def _get_workspace_features(workspace: Workspace) -> AIFeatureToggles:
    """Extract feature toggles from workspace settings."""
    if not workspace.settings or "ai_features" not in workspace.settings:
        return AIFeatureToggles()

    features_data = workspace.settings["ai_features"]
    return AIFeatureToggles(**features_data)


async def _get_admin_workspace(
    workspace_id: UUID,
    current_user: CurrentUser,
    session: DbSession,
) -> Workspace:
    """Resolve workspace and verify admin access."""
    workspace_repo = WorkspaceRepository(session=session)
    workspace = await workspace_repo.get_with_members(workspace_id)
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )

    member = next(
        (m for m in (workspace.members or []) if m.user_id == current_user.user_id),
        None,
    )
    if not member or not member.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )

    return workspace


@router.get(
    "/{workspace_id}/ai/settings",
    response_model=WorkspaceAISettingsResponse,
    tags=["workspaces", "ai"],
)
async def get_ai_settings(
    workspace_id: UUID,
    current_user: CurrentUser,
    session: DbSession,
) -> WorkspaceAISettingsResponse:
    """Get workspace AI settings.

    Returns provider statuses grouped by service type and feature toggles.
    Requires workspace admin permission.
    """
    workspace = await _get_admin_workspace(workspace_id, current_user, session)

    from pilot_space.ai.infrastructure.key_storage import SecureKeyStorage
    from pilot_space.config import get_settings

    settings = get_settings()
    key_storage = SecureKeyStorage(
        db=session, master_secret=settings.encryption_key.get_secret_value()
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

    features = _get_workspace_features(workspace)

    ws_settings = workspace.settings or {}

    return WorkspaceAISettingsResponse(
        workspace_id=workspace_id,
        providers=providers,
        features=features,
        default_llm_provider=ws_settings.get("default_llm_provider", "anthropic"),
        default_embedding_provider=ws_settings.get("default_embedding_provider", "google"),
        cost_limit_usd=ws_settings.get("ai_cost_limit_usd"),
    )


@router.patch(
    "/{workspace_id}/ai/settings",
    response_model=WorkspaceAISettingsUpdateResponse,
    tags=["workspaces", "ai"],
)
async def update_ai_settings(
    workspace_id: UUID,
    body: WorkspaceAISettingsUpdate,
    current_user: CurrentUser,
    session: DbSession,
) -> WorkspaceAISettingsUpdateResponse:
    """Update workspace AI settings.

    Stores API keys (encrypted with Fernet) and feature toggles.
    Requires workspace admin permission.
    """
    workspace = await _get_admin_workspace(workspace_id, current_user, session)

    from pilot_space.ai.infrastructure.key_storage import SecureKeyStorage
    from pilot_space.config import get_settings

    settings = get_settings()
    key_storage = SecureKeyStorage(
        db=session, master_secret=settings.encryption_key.get_secret_value()
    )

    workspace_repo = WorkspaceRepository(session=session)
    validation_results: list[KeyValidationResult] = []
    updated_providers: list[str] = []

    if body.api_keys:
        for key_update in body.api_keys:
            provider = key_update.provider
            service_type = key_update.service_type
            provider_label = f"{provider}:{service_type}"

            existing_info = await key_storage.get_key_info(workspace_id, provider, service_type)

            has_new_key = key_update.api_key is not None
            has_metadata_change = (
                key_update.base_url is not None or key_update.model_name is not None
            )

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
                    validation_results.append(
                        KeyValidationResult(
                            provider=provider_label,
                            is_valid=False,
                            error_message=str(e),
                        )
                    )
                    continue

            if has_new_key:
                # For Ollama, base_url is required when storing a new key
                if provider == "ollama" and not base_url:
                    validation_results.append(
                        KeyValidationResult(
                            provider=provider_label,
                            is_valid=False,
                            error_message="Base URL is required for Ollama",
                        )
                    )
                    continue

                await key_storage.store_api_key(
                    workspace_id=workspace_id,
                    provider=provider,
                    service_type=service_type,
                    api_key=key_update.api_key,  # type: ignore[arg-type]
                    base_url=base_url,
                    model_name=model_name,
                )
                updated_providers.append(provider_label)

                # Validate the stored key
                is_valid, val_error = await key_storage.validate_api_key(
                    provider=provider,
                    api_key=key_update.api_key,
                    base_url=base_url,
                )

                validation_results.append(
                    KeyValidationResult(
                        provider=provider_label,
                        is_valid=is_valid,
                        error_message=val_error,
                    )
                )
            elif has_metadata_change and existing_info is not None:
                # Only metadata changed — update without touching encrypted key
                await key_storage.update_metadata(
                    workspace_id=workspace_id,
                    provider=provider,
                    service_type=service_type,
                    base_url=base_url,
                    model_name=model_name,
                )
                updated_providers.append(provider_label)
                validation_results.append(
                    KeyValidationResult(
                        provider=provider_label,
                        is_valid=True,
                        error_message=None,
                    )
                )
            elif has_metadata_change and existing_info is None:
                # Ollama can be configured with just base_url (no API key required)
                if provider == "ollama":
                    await key_storage.store_api_key(
                        workspace_id=workspace_id,
                        provider=provider,
                        service_type=service_type,
                        api_key=None,
                        base_url=base_url,
                        model_name=model_name,
                    )
                    updated_providers.append(provider_label)

                    # Validate connectivity
                    is_valid, val_error = await key_storage.validate_api_key(
                        provider=provider,
                        api_key=None,
                        base_url=base_url,
                    )

                    validation_results.append(
                        KeyValidationResult(
                            provider=provider_label,
                            is_valid=is_valid,
                            error_message=val_error,
                        )
                    )
                else:
                    validation_results.append(
                        KeyValidationResult(
                            provider=provider_label,
                            is_valid=False,
                            error_message="API key required before updating provider metadata",
                        )
                    )
            elif not has_new_key and not has_metadata_change and existing_info is not None:
                # Explicit None api_key with no metadata changes — delete the key
                await key_storage.delete_api_key(workspace_id, provider, service_type)
                updated_providers.append(provider_label)
                validation_results.append(
                    KeyValidationResult(
                        provider=provider_label,
                        is_valid=True,
                        error_message=None,
                    )
                )

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
        await session.commit()

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


__all__ = ["router"]
