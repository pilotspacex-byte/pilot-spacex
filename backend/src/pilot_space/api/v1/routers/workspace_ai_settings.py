"""Workspace AI settings router for Pilot Space API.

Provides endpoints for managing workspace AI provider configuration,
API key validation, and feature toggles (T062-T066).
Routes are mounted under /workspaces/{workspace_id}/ai/settings.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, status

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
    """Extract feature toggles from workspace settings.

    Args:
        workspace: Workspace model.

    Returns:
        AI feature toggles (defaults if not configured).
    """
    if not workspace.settings or "ai_features" not in workspace.settings:
        return AIFeatureToggles()

    features_data = workspace.settings["ai_features"]
    return AIFeatureToggles(**features_data)


async def _get_admin_workspace(
    workspace_id: UUID,
    current_user: CurrentUser,
    session: DbSession,
) -> Workspace:
    """Resolve workspace and verify admin access.

    Args:
        workspace_id: Workspace identifier.
        current_user: Authenticated user.
        session: Database session.

    Returns:
        Workspace model.

    Raises:
        HTTPException: If workspace not found or user not admin.
    """
    # H-4 fix: use get_with_members to eagerly load members (avoids MissingGreenlet)
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
    """Get workspace AI settings (T062).

    Returns configured providers (not keys) and feature toggles.
    Requires workspace admin permission.

    Args:
        workspace_id: Workspace identifier.
        current_user: Authenticated user.
        session: Database session.

    Returns:
        Current AI settings.

    Raises:
        HTTPException: If workspace not found or user not admin.
    """
    workspace = await _get_admin_workspace(workspace_id, current_user, session)

    # Import here to avoid circular dependencies
    from pilot_space.ai.infrastructure.key_storage import SecureKeyStorage
    from pilot_space.config import get_settings

    settings = get_settings()
    key_storage = SecureKeyStorage(
        db=session, master_secret=settings.encryption_key.get_secret_value()
    )

    # Get provider statuses
    providers = []
    for provider in ["anthropic", "openai", "google"]:
        key_info = await key_storage.get_key_info(workspace_id, provider)
        providers.append(
            ProviderStatus(
                provider=provider,
                is_configured=key_info is not None,
                is_valid=key_info.is_valid if key_info else None,
                last_validated_at=key_info.last_validated_at if key_info else None,
            )
        )

    # Get feature toggles from workspace settings
    features = _get_workspace_features(workspace)

    return WorkspaceAISettingsResponse(
        workspace_id=workspace_id,
        providers=providers,
        features=features,
        default_provider=workspace.settings.get("default_ai_provider", "anthropic")
        if workspace.settings
        else "anthropic",
        cost_limit_usd=workspace.settings.get("ai_cost_limit_usd") if workspace.settings else None,
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
    """Update workspace AI settings (T063).

    Validates API keys before saving. Keys are encrypted with Fernet.
    Requires workspace admin permission.

    Args:
        workspace_id: Workspace identifier.
        body: Settings update data.
        current_user: Authenticated user.
        session: Database session.

    Returns:
        Update results with validation feedback.

    Raises:
        HTTPException: If workspace not found or user not admin.
    """
    workspace = await _get_admin_workspace(workspace_id, current_user, session)

    # Import here to avoid circular dependencies
    from pilot_space.ai.infrastructure.key_storage import SecureKeyStorage
    from pilot_space.config import get_settings

    settings = get_settings()
    key_storage = SecureKeyStorage(
        db=session, master_secret=settings.encryption_key.get_secret_value()
    )

    workspace_repo = WorkspaceRepository(session=session)
    validation_results: list[KeyValidationResult] = []
    updated_providers: list[str] = []

    # Process API key updates
    if body.api_keys:
        for key_update in body.api_keys:
            if key_update.api_key:
                # Validate key before storing
                is_valid = await key_storage.validate_api_key(
                    key_update.provider,
                    key_update.api_key,
                )
                error_message = None if is_valid else "API key validation failed"

                validation_results.append(
                    KeyValidationResult(
                        provider=key_update.provider,
                        is_valid=is_valid,
                        error_message=error_message,
                    )
                )

                if is_valid:
                    # Store encrypted key
                    await key_storage.store_api_key(
                        workspace_id=workspace_id,
                        provider=key_update.provider,
                        api_key=key_update.api_key,
                    )
                    updated_providers.append(key_update.provider)
            else:
                # Remove key
                await key_storage.delete_api_key(workspace_id, key_update.provider)
                updated_providers.append(key_update.provider)
                validation_results.append(
                    KeyValidationResult(
                        provider=key_update.provider,
                        is_valid=True,
                        error_message=None,
                    )
                )

    # Update feature toggles
    updated_features = False
    if body.features or body.cost_limit_usd is not None:
        workspace_settings = workspace.settings or {}

        if body.features:
            workspace_settings["ai_features"] = body.features.model_dump()
            updated_features = True

        if body.cost_limit_usd is not None:
            workspace_settings["ai_cost_limit_usd"] = body.cost_limit_usd
            updated_features = True

        workspace.settings = workspace_settings
        await workspace_repo.update(workspace)

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
