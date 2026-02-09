"""AI Configuration router for workspace-level LLM provider management (FR-022).

Provides endpoints for managing workspace AI configurations with BYOK (Bring Your Own Key).
API keys are encrypted before storage and never returned in responses.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from pilot_space.api.v1.schemas.ai_configuration import (
    AIConfigurationCreate,
    AIConfigurationListResponse,
    AIConfigurationResponse,
    AIConfigurationTestResponse,
    AIConfigurationUpdate,
)
from pilot_space.api.v1.schemas.base import DeleteResponse
from pilot_space.dependencies import CurrentUser, DbSession
from pilot_space.infrastructure.database.models.ai_configuration import (
    AIConfiguration,
    LLMProvider,
)
from pilot_space.infrastructure.database.models.workspace_member import WorkspaceRole
from pilot_space.infrastructure.database.repositories.ai_configuration_repository import (
    AIConfigurationRepository,
)
from pilot_space.infrastructure.database.repositories.workspace_repository import (
    WorkspaceRepository,
)
from pilot_space.infrastructure.encryption import (
    EncryptionError,
    decrypt_api_key,
    encrypt_api_key,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai/configurations", tags=["ai-configuration"])

# Lock to protect genai.configure() global state mutation from race conditions
_google_api_lock = asyncio.Lock()


def get_ai_config_repository(session: DbSession) -> AIConfigurationRepository:
    """Get AI configuration repository with session."""
    return AIConfigurationRepository(session=session)


def get_workspace_repository(session: DbSession) -> WorkspaceRepository:
    """Get workspace repository with session."""
    return WorkspaceRepository(session=session)


AIConfigRepo = Annotated[AIConfigurationRepository, Depends(get_ai_config_repository)]
WorkspaceRepo = Annotated[WorkspaceRepository, Depends(get_workspace_repository)]


async def _verify_workspace_membership(
    workspace_id: UUID,
    user_id: UUID,
    workspace_repo: WorkspaceRepository,
    *,
    require_admin: bool = False,
) -> WorkspaceRole:
    """Verify user is a member of the workspace.

    Args:
        workspace_id: Workspace UUID.
        user_id: User UUID.
        workspace_repo: Workspace repository instance.
        require_admin: If True, require admin or owner role.

    Returns:
        User's role in the workspace.

    Raises:
        HTTPException: If workspace not found or user lacks required access.
    """
    # H-4 fix: Use get_with_members to eagerly load members and avoid
    # MissingGreenlet errors when iterating workspace.members in async context.
    workspace = await workspace_repo.get_with_members(workspace_id)
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )

    member = next(
        (m for m in (workspace.members or []) if m.user_id == user_id),
        None,
    )
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this workspace",
        )

    if require_admin and member.role not in (WorkspaceRole.ADMIN, WorkspaceRole.OWNER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required for this operation",
        )

    return member.role


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
    ai_config_repo: AIConfigRepo,
    workspace_repo: WorkspaceRepo,
) -> AIConfigurationListResponse:
    """List AI configurations for a workspace.

    Args:
        workspace_id: Workspace identifier.
        current_user: Authenticated user.
        ai_config_repo: AI configuration repository.
        workspace_repo: Workspace repository.

    Returns:
        List of AI configurations (without API keys).
    """
    await _verify_workspace_membership(workspace_id, current_user.user_id, workspace_repo)

    configs = await ai_config_repo.get_by_workspace(workspace_id, include_inactive=True)
    items = [_config_to_response(config) for config in configs]

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
    ai_config_repo: AIConfigRepo,
    workspace_repo: WorkspaceRepo,
    session: DbSession,
) -> AIConfigurationResponse:
    """Create an AI configuration for a workspace.

    Args:
        workspace_id: Workspace identifier.
        request: Configuration creation data.
        current_user: Authenticated user.
        ai_config_repo: AI configuration repository.
        workspace_repo: Workspace repository.
        session: Database session for transaction.

    Returns:
        Created AI configuration (without API key).

    Raises:
        HTTPException: If not admin or provider already configured.
    """
    await _verify_workspace_membership(
        workspace_id, current_user.user_id, workspace_repo, require_admin=True
    )

    # Check if provider already exists for this workspace
    existing = await ai_config_repo.get_by_workspace_and_provider(workspace_id, request.provider)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Configuration for provider '{request.provider.value}' already exists",
        )

    # Encrypt the API key
    try:
        encrypted_key = encrypt_api_key(request.api_key)
    except EncryptionError as e:
        logger.exception("Failed to encrypt API key")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to securely store API key",
        ) from e

    # Create configuration
    config = AIConfiguration(
        workspace_id=workspace_id,
        provider=request.provider,
        api_key_encrypted=encrypted_key,
        is_active=True,
        settings=request.settings,
        usage_limits=request.usage_limits,
    )
    config = await ai_config_repo.create(config)
    await session.commit()

    logger.info(
        "AI configuration created",
        extra={
            "workspace_id": str(workspace_id),
            "provider": request.provider.value,
            "config_id": str(config.id),
        },
    )

    return _config_to_response(config)


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
    ai_config_repo: AIConfigRepo,
    workspace_repo: WorkspaceRepo,
) -> AIConfigurationResponse:
    """Get a specific AI configuration.

    Args:
        workspace_id: Workspace identifier.
        config_id: Configuration identifier.
        current_user: Authenticated user.
        ai_config_repo: AI configuration repository.
        workspace_repo: Workspace repository.

    Returns:
        AI configuration (without API key).

    Raises:
        HTTPException: If not found or not a member.
    """
    await _verify_workspace_membership(workspace_id, current_user.user_id, workspace_repo)

    config = await ai_config_repo.get_by_workspace_and_id(workspace_id, config_id)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="AI configuration not found",
        )

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
    ai_config_repo: AIConfigRepo,
    workspace_repo: WorkspaceRepo,
    session: DbSession,
) -> AIConfigurationResponse:
    """Update an AI configuration.

    Args:
        workspace_id: Workspace identifier.
        config_id: Configuration identifier.
        request: Update data.
        current_user: Authenticated user.
        ai_config_repo: AI configuration repository.
        workspace_repo: Workspace repository.
        session: Database session for transaction.

    Returns:
        Updated AI configuration (without API key).

    Raises:
        HTTPException: If not found or not admin.
    """
    await _verify_workspace_membership(
        workspace_id, current_user.user_id, workspace_repo, require_admin=True
    )

    config = await ai_config_repo.get_by_workspace_and_id(workspace_id, config_id)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="AI configuration not found",
        )

    # Apply updates
    update_data = request.model_dump(exclude_unset=True)

    # Handle API key update separately (needs encryption)
    if "api_key" in update_data:
        api_key = update_data.pop("api_key")
        if api_key:
            try:
                config.api_key_encrypted = encrypt_api_key(api_key)
            except EncryptionError as e:
                logger.exception("Failed to encrypt API key")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to securely store API key",
                ) from e

    # Apply remaining updates
    for key, value in update_data.items():
        setattr(config, key, value)

    config = await ai_config_repo.update(config)
    await session.commit()

    logger.info(
        "AI configuration updated",
        extra={
            "workspace_id": str(workspace_id),
            "config_id": str(config_id),
        },
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
    ai_config_repo: AIConfigRepo,
    workspace_repo: WorkspaceRepo,
    session: DbSession,
) -> DeleteResponse:
    """Delete an AI configuration.

    Args:
        workspace_id: Workspace identifier.
        config_id: Configuration identifier.
        current_user: Authenticated user.
        ai_config_repo: AI configuration repository.
        workspace_repo: Workspace repository.
        session: Database session for transaction.

    Returns:
        Delete confirmation.

    Raises:
        HTTPException: If not found or not admin.
    """
    await _verify_workspace_membership(
        workspace_id, current_user.user_id, workspace_repo, require_admin=True
    )

    config = await ai_config_repo.get_by_workspace_and_id(workspace_id, config_id)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="AI configuration not found",
        )

    await ai_config_repo.delete(config)
    await session.commit()

    logger.info(
        "AI configuration deleted",
        extra={
            "workspace_id": str(workspace_id),
            "config_id": str(config_id),
            "provider": config.provider.value,
        },
    )

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
    ai_config_repo: AIConfigRepo,
    workspace_repo: WorkspaceRepo,
) -> AIConfigurationTestResponse:
    """Test an AI configuration by validating the API key.

    Makes a minimal API call to the provider to verify the key is valid.

    Args:
        workspace_id: Workspace identifier.
        config_id: Configuration identifier.
        current_user: Authenticated user.
        ai_config_repo: AI configuration repository.
        workspace_repo: Workspace repository.

    Returns:
        Test result with success status and latency.

    Raises:
        HTTPException: If configuration not found.
    """
    await _verify_workspace_membership(workspace_id, current_user.user_id, workspace_repo)

    config = await ai_config_repo.get_by_workspace_and_id(workspace_id, config_id)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="AI configuration not found",
        )

    # Decrypt API key for testing
    try:
        api_key = decrypt_api_key(config.api_key_encrypted)
    except EncryptionError:
        logger.exception("Failed to decrypt API key for testing")
        return AIConfigurationTestResponse(
            success=False,
            provider=config.provider,
            message="Failed to decrypt API key. Configuration may be corrupted.",
            latency_ms=None,
        )

    # Test the API key with the provider
    start_time = time.perf_counter()
    success, message = await _test_provider_api_key(config.provider, api_key)
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

    return AIConfigurationTestResponse(
        success=success,
        provider=config.provider,
        message=message,
        latency_ms=latency_ms if success else None,
    )


async def _test_provider_api_key(provider: LLMProvider, api_key: str) -> tuple[bool, str]:
    """Test an API key with the specified provider.

    Makes a minimal API call to verify the key is valid.

    Args:
        provider: The LLM provider.
        api_key: The decrypted API key.

    Returns:
        Tuple of (success, message).
    """
    if provider == LLMProvider.ANTHROPIC:
        return await _test_anthropic_key(api_key)
    if provider == LLMProvider.OPENAI:
        return await _test_openai_key(api_key)
    if provider == LLMProvider.GOOGLE:
        return await _test_google_key(api_key)
    return False, f"Unknown provider: {provider}"


async def _test_anthropic_key(api_key: str) -> tuple[bool, str]:
    """Test Anthropic API key validity.

    Uses a minimal messages API call with max_tokens=1.
    """
    import anthropic

    try:
        client = anthropic.AsyncAnthropic(api_key=api_key)
        # Minimal request to validate the key
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
        # Rate limited but key is valid
        return True, "API key is valid (rate limited)"
    except anthropic.APIError as e:
        return False, f"API error: {e.message}"
    else:
        return True, "API key is valid"


async def _test_openai_key(api_key: str) -> tuple[bool, str]:
    """Test OpenAI API key validity.

    Uses a minimal models list API call.
    """
    import openai

    try:
        client = openai.AsyncOpenAI(api_key=api_key)
        # List models is a lightweight call to validate the key
        await client.models.list()
    except openai.AuthenticationError:
        return False, "Invalid API key"
    except openai.PermissionDeniedError:
        return False, "API key lacks required permissions"
    except openai.RateLimitError:
        # Rate limited but key is valid
        return True, "API key is valid (rate limited)"
    except openai.APIError as e:
        return False, f"API error: {e.message}"
    else:
        return True, "API key is valid"


async def _test_google_key(api_key: str) -> tuple[bool, str]:
    """Test Google AI API key validity.

    Uses a minimal models list API call. Protected by lock to prevent
    race conditions from genai.configure() global state mutation.
    """
    import google.generativeai as genai

    try:
        # Lock protects genai.configure() global state from concurrent access
        async with _google_api_lock:
            genai.configure(api_key=api_key)  # pyright: ignore[reportPrivateImportUsage,reportUnknownMemberType]
            # List models is a lightweight call to validate the key
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


__all__ = ["router"]
