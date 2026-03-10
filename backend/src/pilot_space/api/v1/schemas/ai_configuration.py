"""Pydantic schemas for AI Configuration API (FR-022).

Provides request/response models for workspace-level LLM provider configuration.
API keys are write-only and never returned in responses.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from pilot_space.infrastructure.database.models.ai_configuration import LLMProvider


class AIConfigurationBase(BaseModel):
    """Base schema with shared AI configuration fields."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class AIConfigurationCreate(AIConfigurationBase):
    """Schema for creating an AI configuration.

    Attributes:
        provider: LLM provider (anthropic, openai, google).
        api_key: Provider API key (write-only, encrypted before storage).
        settings: Optional provider-specific settings.
        usage_limits: Optional usage limits and quotas.
    """

    provider: Annotated[
        LLMProvider,
        Field(description="LLM provider (anthropic, openai, google)"),
    ]
    api_key: Annotated[
        str,
        Field(
            min_length=10,
            max_length=200,
            description="Provider API key (write-only, never returned)",
        ),
    ]
    settings: Annotated[
        dict[str, Any] | None,
        Field(
            default=None,
            description="Provider-specific settings (default_model, temperature, etc.)",
            examples=[{"default_model": "claude-3-5-sonnet-20241022", "max_tokens": 4096}],
        ),
    ]
    usage_limits: Annotated[
        dict[str, Any] | None,
        Field(
            default=None,
            description="Optional usage limits (daily_tokens, monthly_budget, etc.)",
            examples=[{"daily_tokens": 1000000, "monthly_budget_usd": 100}],
        ),
    ]
    base_url: Annotated[
        str | None,
        Field(
            default=None,
            max_length=512,
            description="OpenAI-compatible API base URL. Required when provider=custom.",
        ),
    ]
    display_name: Annotated[
        str | None,
        Field(
            default=None,
            max_length=128,
            description="Human-readable provider name shown in UI.",
        ),
    ]

    @field_validator("api_key")
    @classmethod
    def validate_api_key_format(cls, v: str) -> str:
        """Validate API key format based on common provider patterns."""
        v = v.strip()
        if not v:
            raise ValueError("API key cannot be empty")
        return v

    @field_validator("settings", "usage_limits", mode="before")
    @classmethod
    def normalize_empty_dict(cls, v: dict[str, Any] | None) -> dict[str, Any] | None:
        """Convert empty dicts to None for cleaner storage."""
        if v is not None and len(v) == 0:
            return None
        return v

    @model_validator(mode="after")
    def validate_custom_provider_requires_base_url(self) -> AIConfigurationCreate:
        """Require base_url when provider is CUSTOM."""
        if self.provider == LLMProvider.CUSTOM and not self.base_url:
            raise ValueError("base_url is required when provider is 'custom'")
        return self


class AIConfigurationUpdate(AIConfigurationBase):
    """Schema for updating an AI configuration.

    All fields are optional to support partial updates (PATCH semantics).
    """

    api_key: Annotated[
        str | None,
        Field(
            default=None,
            min_length=10,
            max_length=200,
            description="New provider API key (write-only)",
        ),
    ]
    is_active: Annotated[
        bool | None,
        Field(default=None, description="Activate or deactivate this configuration"),
    ]
    settings: Annotated[
        dict[str, Any] | None,
        Field(
            default=None,
            description="Updated provider-specific settings",
        ),
    ]
    usage_limits: Annotated[
        dict[str, Any] | None,
        Field(
            default=None,
            description="Updated usage limits",
        ),
    ]

    @field_validator("api_key")
    @classmethod
    def validate_api_key_format(cls, v: str | None) -> str | None:
        """Validate API key format if provided."""
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("API key cannot be empty")
        return v


class AIConfigurationResponse(AIConfigurationBase):
    """Response schema for AI configuration.

    Security: API keys are NEVER included in responses.
    """

    id: Annotated[UUID, Field(description="Unique configuration identifier")]
    workspace_id: Annotated[UUID, Field(description="Parent workspace ID")]
    provider: Annotated[LLMProvider, Field(description="LLM provider")]
    is_active: Annotated[bool, Field(description="Whether this configuration is active")]
    has_api_key: Annotated[
        bool,
        Field(
            default=True,
            description="Indicates if an API key is configured (never exposes the key itself)",
        ),
    ]
    settings: Annotated[
        dict[str, Any] | None,
        Field(description="Provider-specific settings"),
    ]
    usage_limits: Annotated[
        dict[str, Any] | None,
        Field(description="Usage limits and quotas"),
    ]
    base_url: Annotated[
        str | None,
        Field(description="OpenAI-compatible API base URL (custom providers)"),
    ]
    display_name: Annotated[
        str | None,
        Field(description="Human-readable provider name"),
    ]
    created_at: Annotated[datetime, Field(description="Creation timestamp")]
    updated_at: Annotated[datetime, Field(description="Last update timestamp")]


class AIConfigurationTestRequest(AIConfigurationBase):
    """Request schema for testing an existing configuration."""

    # No additional fields needed - config_id is in URL path


class AIConfigurationTestResponse(AIConfigurationBase):
    """Response schema for API key validation test.

    Attributes:
        success: Whether the API key is valid.
        provider: The tested provider.
        message: Human-readable result message.
        latency_ms: Response time from provider (if successful).
    """

    success: Annotated[bool, Field(description="Whether the API key is valid")]
    provider: Annotated[LLMProvider, Field(description="Tested provider")]
    message: Annotated[str, Field(description="Human-readable result message")]
    latency_ms: Annotated[
        int | None,
        Field(default=None, description="Provider response latency in milliseconds"),
    ]


class AIConfigurationListResponse(AIConfigurationBase):
    """Response schema for listing AI configurations."""

    items: Annotated[
        list[AIConfigurationResponse],
        Field(description="List of AI configurations"),
    ]
    total: Annotated[int, Field(ge=0, description="Total count of configurations")]


class ProviderModelItem(AIConfigurationBase):
    """A single model available from a configured provider."""

    provider_config_id: Annotated[
        str,
        Field(description="ID of the AIConfiguration that provides this model"),
    ]
    provider: Annotated[str, Field(description="Provider name (anthropic, openai, etc.)")]
    model_id: Annotated[str, Field(description="Provider-assigned model identifier")]
    display_name: Annotated[str, Field(description="Human-readable model name")]
    is_selectable: Annotated[
        bool,
        Field(
            description=(
                "True when live API confirmed availability. "
                "False when provider was unreachable and fallback list is used."
            )
        ),
    ]


class ModelListResponse(AIConfigurationBase):
    """Response schema for listing models across all active providers."""

    items: Annotated[
        list[ProviderModelItem],
        Field(description="Models from all active, reachable providers"),
    ]
    total: Annotated[int, Field(ge=0, description="Total model count")]


__all__ = [
    "AIConfigurationCreate",
    "AIConfigurationListResponse",
    "AIConfigurationResponse",
    "AIConfigurationTestRequest",
    "AIConfigurationTestResponse",
    "AIConfigurationUpdate",
    "LLMProvider",
    "ModelListResponse",
    "ProviderModelItem",
]
