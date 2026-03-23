"""Model override resolution for per-session model selection (AIPR-04).

Provides ModelOverride schema, ResolvedModelConfig dataclass, and
resolve_model_override() function used by the chat endpoint to route
a user-selected provider/model to the correct API key and base URL.

Flow:
    ChatRequest.model_override (ModelOverride)
        -> resolve_model_override()
        -> AIConfigurationRepository.get_by_workspace_and_id()
        -> decrypt_api_key()
        -> ResolvedModelConfig

Fallback: if config not found or decryption fails, returns None so the
agent falls back to the workspace's default Anthropic configuration.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from pydantic import Field

from pilot_space.api.v1.schemas.base import BaseSchema
from pilot_space.infrastructure.logging import get_logger

logger = get_logger(__name__)


class ModelOverride(BaseSchema):
    """User-selected model for a chat session.

    Sent by the frontend when the user picks a specific provider/model
    from the AI model picker. The config_id links to an AIConfiguration
    row which holds the encrypted API key and optional base_url.
    """

    provider: str = Field(
        ...,
        description="Provider name, e.g. 'anthropic', 'kimi', 'custom'",
    )
    model: str = Field(
        ...,
        description="Model ID, e.g. 'claude-sonnet-4'",
    )
    config_id: str = Field(
        ...,
        description="AIConfiguration.id — used to look up api_key + base_url",
    )


@dataclass
class ResolvedModelConfig:
    """Resolved provider credentials for a user-selected model.

    Produced by resolve_model_override() and passed through ChatInput
    so PilotSpaceAgent can use the correct API key and model ID.
    """

    api_key: str
    model: str
    provider: str
    base_url: str | None = None


async def resolve_model_override(
    model_override: ModelOverride,
    workspace_id: UUID,
    db: object,  # AsyncSession — typed as object to avoid circular import
) -> ResolvedModelConfig | None:
    """Resolve a ModelOverride to decrypted credentials.

    Looks up the AIConfiguration row identified by model_override.config_id,
    verifies it belongs to the workspace and is active, then decrypts the
    stored API key.

    Returns:
        ResolvedModelConfig with decrypted credentials, or None if the
        config is not found, inactive, or decryption fails. None causes
        the agent to fall back to the workspace's default configuration.

    Never raises — failures are logged and treated as graceful fallback.
    """
    from pilot_space.infrastructure.database.repositories.ai_configuration_repository import (
        AIConfigurationRepository,
    )
    from pilot_space.infrastructure.encryption import decrypt_api_key

    try:
        config_id = UUID(model_override.config_id)
    except ValueError:
        logger.warning(
            "model_override_invalid_config_id",
            config_id=model_override.config_id,
        )
        return None

    try:
        repo = AIConfigurationRepository(session=db)  # type: ignore[arg-type]
        config = await repo.get_by_workspace_and_id(workspace_id, config_id)
        if config is None or not config.is_active:
            logger.warning(
                "model_override_config_not_found",
                config_id=str(config_id),
                workspace_id=str(workspace_id),
            )
            return None

        api_key = decrypt_api_key(config.api_key_encrypted)

        # base_url may live in the settings JSON field (not a top-level column)
        base_url: str | None = None
        if config.settings:
            base_url = config.settings.get("base_url")

        return ResolvedModelConfig(
            api_key=api_key,
            model=model_override.model,
            provider=model_override.provider,
            base_url=base_url,
        )

    except Exception as exc:
        logger.warning(
            "model_override_resolution_failed",
            config_id=str(model_override.config_id),
            error=str(exc),
        )
        return None


__all__ = ["ModelOverride", "ResolvedModelConfig", "resolve_model_override"]
