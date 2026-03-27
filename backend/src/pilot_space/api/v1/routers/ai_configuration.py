"""AI Configuration router for workspace-level LLM provider management (FR-022).

Thin HTTP shell delegating to AIConfigurationService.
API keys are encrypted before storage and never returned in responses.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, status

from pilot_space.api.v1.dependencies import AIConfigurationServiceDep
from pilot_space.api.v1.schemas.ai_configuration import (
    AIConfigurationCreate,
    AIConfigurationListResponse,
    AIConfigurationResponse,
    AIConfigurationTestResponse,
    AIConfigurationUpdate,
    ModelListResponse,
    ProviderModelItem,
)
from pilot_space.api.v1.schemas.base import DeleteResponse
from pilot_space.dependencies import CurrentUser, DbSession
from pilot_space.infrastructure.database.models.ai_configuration import AIConfiguration

router = APIRouter(prefix="/ai/configurations", tags=["ai-configuration"])


def _config_to_response(config: AIConfiguration) -> AIConfigurationResponse:
    """Convert AIConfiguration model to response schema.

    Security: Never exposes the actual API key.
    """
    return AIConfigurationResponse(
        id=config.id,
        workspace_id=config.workspace_id,
        provider=config.provider,
        is_active=config.is_active,
        has_api_key=bool(config.api_key_encrypted),
        settings=config.settings,
        usage_limits=config.usage_limits,
        base_url=config.base_url,
        display_name=config.display_name,
        created_at=config.created_at,
        updated_at=config.updated_at,
    )


@router.get(
    "",
    response_model=AIConfigurationListResponse,
    summary="List AI configurations",
    description="List all AI configurations for the workspace. Requires workspace membership.",
)
async def list_ai_configurations(
    workspace_id: UUID,
    current_user: CurrentUser,
    session: DbSession,
    service: AIConfigurationServiceDep,
) -> AIConfigurationListResponse:
    """List AI configurations for a workspace."""
    configs = await service.list_configurations(workspace_id, current_user.user_id)
    items = [_config_to_response(c) for c in configs]
    return AIConfigurationListResponse(items=items, total=len(items))


@router.post(
    "",
    response_model=AIConfigurationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create AI configuration",
    description="Create a new AI configuration. Requires admin role. API key is encrypted.",
)
async def create_ai_configuration(
    workspace_id: UUID,
    request: AIConfigurationCreate,
    current_user: CurrentUser,
    session: DbSession,
    service: AIConfigurationServiceDep,
) -> AIConfigurationResponse:
    """Create an AI configuration for a workspace."""
    config = await service.create_configuration(
        workspace_id,
        current_user.user_id,
        provider=request.provider,
        api_key=request.api_key,
        settings=request.settings,
        usage_limits=request.usage_limits,
        base_url=request.base_url,
        display_name=request.display_name,
    )
    return _config_to_response(config)


@router.get(
    "/models",
    response_model=ModelListResponse,
    summary="List available models",
    description=(
        "List models from all active, configured providers. "
        "Unreachable providers return fallback models with is_selectable=False. "
        "Requires workspace membership."
    ),
)
async def list_available_models(
    workspace_id: UUID,
    current_user: CurrentUser,
    session: DbSession,
    service: AIConfigurationServiceDep,
) -> ModelListResponse:
    """List all models available from active provider configurations."""
    models = await service.list_available_models(workspace_id, current_user.user_id)
    return ModelListResponse(
        items=[
            ProviderModelItem(
                provider_config_id=str(m.provider_config_id),
                provider=m.provider,
                model_id=m.model_id,
                display_name=m.display_name,
                is_selectable=m.is_selectable,
            )
            for m in models
        ],
        total=len(models),
    )


@router.get(
    "/{config_id}",
    response_model=AIConfigurationResponse,
    summary="Get AI configuration",
    description="Get a specific AI configuration. Requires workspace membership.",
)
async def get_ai_configuration(
    workspace_id: UUID,
    config_id: UUID,
    current_user: CurrentUser,
    session: DbSession,
    service: AIConfigurationServiceDep,
) -> AIConfigurationResponse:
    """Get a specific AI configuration."""
    config = await service.get_configuration(workspace_id, config_id, current_user.user_id)
    return _config_to_response(config)


@router.patch(
    "/{config_id}",
    response_model=AIConfigurationResponse,
    summary="Update AI configuration",
    description="Update an AI configuration. Requires admin role.",
)
async def update_ai_configuration(
    workspace_id: UUID,
    config_id: UUID,
    request: AIConfigurationUpdate,
    current_user: CurrentUser,
    session: DbSession,
    service: AIConfigurationServiceDep,
) -> AIConfigurationResponse:
    """Update an AI configuration."""
    update_data = request.model_dump(exclude_unset=True)
    config = await service.update_configuration(
        workspace_id, config_id, current_user.user_id, update_data
    )
    return _config_to_response(config)


@router.delete(
    "/{config_id}",
    response_model=DeleteResponse,
    summary="Delete AI configuration",
    description="Delete an AI configuration. Requires admin role.",
)
async def delete_ai_configuration(
    workspace_id: UUID,
    config_id: UUID,
    current_user: CurrentUser,
    session: DbSession,
    service: AIConfigurationServiceDep,
) -> DeleteResponse:
    """Delete an AI configuration."""
    await service.delete_configuration(workspace_id, config_id, current_user.user_id)
    return DeleteResponse(id=config_id, message="AI configuration deleted successfully")


@router.post(
    "/{config_id}/test",
    response_model=AIConfigurationTestResponse,
    summary="Test AI configuration",
    description="Test if the configured API key is valid. Requires workspace membership.",
)
async def test_ai_configuration(
    workspace_id: UUID,
    config_id: UUID,
    current_user: CurrentUser,
    session: DbSession,
    service: AIConfigurationServiceDep,
) -> AIConfigurationTestResponse:
    """Test an AI configuration by validating the API key."""
    result = await service.test_configuration(workspace_id, config_id, current_user.user_id)
    return AIConfigurationTestResponse(
        success=result.success,
        provider=result.provider,
        message=result.message,
        latency_ms=result.latency_ms,
    )


__all__ = ["router"]
