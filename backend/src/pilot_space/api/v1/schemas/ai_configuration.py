"""Pydantic schemas for AI Configuration API (FR-022).

Provides request/response models for workspace-level LLM provider configuration.
API keys are write-only and never returned in responses.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

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


__all__ = [
    "AIConfigurationCreate",
    "AIConfigurationListResponse",
    "AIConfigurationResponse",
    "AIConfigurationTestRequest",
    "AIConfigurationTestResponse",
    "AIConfigurationUpdate",
    "LLMProvider",
]
