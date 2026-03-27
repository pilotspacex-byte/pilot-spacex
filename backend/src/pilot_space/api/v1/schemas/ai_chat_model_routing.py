"""Pydantic schemas for AI chat model routing (AIPR-04).

Provides ModelOverride schema and ResolvedModelConfig dataclass used by
the chat endpoint to route a user-selected provider/model to the correct
API key and base URL.

Flow:
    ChatRequest.model_override (ModelOverride)
        -> resolve_model_override()
        -> AIConfigurationRepository.get_by_workspace_and_id()
        -> decrypt_api_key()
        -> ResolvedModelConfig
"""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import Field

from pilot_space.api.v1.schemas.base import BaseSchema


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


__all__ = ["ModelOverride", "ResolvedModelConfig"]
