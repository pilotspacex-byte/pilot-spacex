"""Onboarding API schemas.

Request and response schemas for onboarding endpoints.
FR-001, FR-002, FR-003, FR-005, FR-011 support.

T003: Onboarding schemas.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import Field, field_validator

from pilot_space.api.v1.schemas.base import BaseSchema, EntitySchema


class OnboardingStep(str, Enum):
    """Valid onboarding step names."""

    AI_PROVIDERS = "ai_providers"
    INVITE_MEMBERS = "invite_members"
    FIRST_NOTE = "first_note"
    ROLE_SETUP = "role_setup"


class OnboardingSteps(BaseSchema):
    """Schema for onboarding steps status.

    Tracks completion of each step in the onboarding flow.
    """

    ai_providers: bool = Field(default=False, description="AI provider configured")
    invite_members: bool = Field(default=False, description="Team members invited")
    first_note: bool = Field(default=False, description="First note written")
    role_setup: bool = Field(default=False, description="SDLC role configured")


class OnboardingResponse(EntitySchema):
    """Schema for onboarding state response.

    Source: FR-001, FR-002, US1
    GET /api/v1/workspaces/{id}/onboarding

    Attributes:
        workspace_id: Workspace this belongs to.
        steps: Step completion status.
        guided_note_id: ID of guided note if created.
        dismissed_at: When dismissed.
        completed_at: When all steps completed.
        completion_percentage: 0-100 calculated from steps.
    """

    workspace_id: UUID = Field(description="Workspace ID")
    steps: OnboardingSteps = Field(description="Step completion status")
    guided_note_id: UUID | None = Field(default=None, description="Guided note ID")
    dismissed_at: datetime | None = Field(default=None, description="Dismiss timestamp")
    completed_at: datetime | None = Field(default=None, description="Completion timestamp")
    completion_percentage: int = Field(
        default=0,
        ge=0,
        le=100,
        description="Completion percentage (0-100)",
    )


class OnboardingUpdateRequest(BaseSchema):
    """Schema for updating onboarding state.

    Source: FR-002, FR-003, US1
    PATCH /api/v1/workspaces/{id}/onboarding

    Attributes:
        step: Step to update (ai_providers, invite_members, first_note).
        completed: Whether step is completed.
        dismissed: Set dismissed_at to now if true.
    """

    step: OnboardingStep | None = Field(
        default=None,
        description="Step to mark complete",
    )
    completed: bool | None = Field(
        default=None,
        description="Step completion status",
    )
    dismissed: bool | None = Field(
        default=None,
        description="Set dismissed_at to now if true",
    )

    @field_validator("completed")
    @classmethod
    def validate_completed_requires_step(cls, v: bool | None) -> bool | None:
        """Validate completed requires step to be set."""
        # Validation happens in endpoint since we need both fields
        return v


class AIProviderType(str, Enum):
    """Supported AI provider types."""

    ANTHROPIC = "anthropic"


class ValidateKeyRequest(BaseSchema):
    """Schema for validating AI provider key.

    Source: FR-005, US2
    POST /api/v1/workspaces/{id}/ai-providers/validate

    Attributes:
        provider: Provider name (anthropic only for MVP).
        api_key: API key to validate.
    """

    provider: AIProviderType = Field(
        description="Provider to validate (anthropic)",
    )
    api_key: str = Field(
        min_length=1,
        description="API key to validate",
    )

    @field_validator("api_key")
    @classmethod
    def validate_anthropic_key_format(cls, v: str) -> str:
        """Validate Anthropic key format."""
        # Note: Pydantic v2 field validators run before model is fully built
        # so we validate format in endpoint after both fields are available
        return v.strip()


class ValidateKeyResponse(BaseSchema):
    """Schema for key validation response.

    Source: FR-005, FR-006, US2

    Attributes:
        provider: Provider name.
        valid: Whether key authenticated successfully.
        error_message: Human-readable error if invalid.
        models_available: List of models accessible with key.
    """

    provider: AIProviderType = Field(description="Provider name")
    valid: bool = Field(description="Key validation result")
    error_message: str | None = Field(
        default=None,
        description="Error message if invalid",
    )
    models_available: list[str] = Field(
        default_factory=list,
        description="Available models",
    )


class GuidedNoteResponse(BaseSchema):
    """Schema for guided note creation response.

    Source: FR-011, US4
    POST /api/v1/workspaces/{id}/onboarding/guided-note

    Attributes:
        note_id: ID of the created guided note.
        title: Note title.
        redirect_url: URL to navigate to note editor.
    """

    note_id: UUID = Field(description="Created note ID")
    title: str = Field(description="Note title")
    redirect_url: str = Field(description="URL to note editor")


__all__ = [
    "AIProviderType",
    "GuidedNoteResponse",
    "OnboardingResponse",
    "OnboardingStep",
    "OnboardingSteps",
    "OnboardingUpdateRequest",
    "ValidateKeyRequest",
    "ValidateKeyResponse",
]
