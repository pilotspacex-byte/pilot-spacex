"""Pydantic v2 schemas for the Intent API.

Feature 015: AI Workforce Platform (M2, T-014)
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import Field, field_validator

from pilot_space.api.v1.schemas.base import BaseSchema, EntitySchema


class IntentDetectRequest(BaseSchema):
    """Request to detect intents from text."""

    text: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="Text to analyze for work intents",
    )
    source: str = Field(
        ...,
        description="Source of the text: 'chat' or 'note'",
    )
    source_block_id: UUID | None = Field(
        default=None,
        description="TipTap block UUID that triggered detection (for note source)",
    )

    @field_validator("source")
    @classmethod
    def validate_source(cls, v: str) -> str:
        if v not in ("chat", "note"):
            msg = "source must be 'chat' or 'note'"
            raise ValueError(msg)
        return v


class IntentEditRequest(BaseSchema):
    """Request to edit a detected intent before confirmation."""

    new_what: str | None = Field(
        default=None,
        min_length=1,
        max_length=2000,
        description="Updated intent description",
    )
    new_why: str | None = Field(
        default=None,
        max_length=2000,
        description="Updated motivation/reason",
    )
    new_constraints: list[str] | None = Field(
        default=None,
        description="Updated list of constraints",
    )
    new_acceptance: list[str] | None = Field(
        default=None,
        description="Updated acceptance criteria",
    )


class ConfirmAllRequest(BaseSchema):
    """Request for batch confirmation of top-N detected intents."""

    min_confidence: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Minimum confidence threshold for inclusion",
    )
    max_count: int = Field(
        default=10,
        ge=1,
        le=10,
        description="Maximum intents to confirm (cap=10)",
    )


class IntentResponse(EntitySchema):
    """Response schema for a single WorkIntent."""

    workspace_id: UUID = Field(description="Workspace this intent belongs to")
    what: str = Field(description="Intent description")
    why: str | None = Field(default=None, description="Motivation/reason")
    constraints: list[Any] | None = Field(default=None, description="Constraints")
    acceptance: list[Any] | None = Field(default=None, description="Acceptance criteria")
    status: str = Field(description="Lifecycle status")
    dedup_status: str = Field(description="Deduplication status")
    confidence: float = Field(description="Detection confidence (0.0-1.0)")
    owner: str | None = Field(default=None, description="Owner user ID or 'system'")
    source_block_id: UUID | None = Field(
        default=None,
        description="Source TipTap block UUID",
    )
    parent_intent_id: UUID | None = Field(
        default=None,
        description="Parent intent for sub-intents",
    )
    dedup_hash: str | None = Field(
        default=None,
        description="SHA-256 dedup hash of normalized what",
    )

    @classmethod
    def from_model(cls, model: Any) -> IntentResponse:
        """Build from WorkIntent ORM model."""
        return cls.model_validate(model)


class DetectIntentResponse(BaseSchema):
    """Response from intent detection endpoint."""

    intents: list[IntentResponse] = Field(description="Detected work intents")
    total_detected: int = Field(description="Total intents detected")
    detection_model: str = Field(description="LLM model used for detection")
    chat_lock_was_active: bool = Field(
        default=False,
        description="True if chat-priority lock was active (note source skipped)",
    )


class ConfirmAllResponse(BaseSchema):
    """Response from confirmAll endpoint."""

    confirmed: list[IntentResponse] = Field(description="Intents that were confirmed")
    confirmed_count: int = Field(description="Number of intents confirmed")
    remaining_count: int = Field(description="Detected intents still pending")
    deduplicating_count: int = Field(
        description="Intents excluded because dedup is still pending (C-8)",
    )
