"""Artifact annotation API schemas — request/response models for artifact_annotations router.

Provides Pydantic schemas for the annotation create, list, update, and delete endpoints.
All schemas inherit from BaseSchema (camelCase JSON serialization).

Feature: v1.2 — PPTX Annotations
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field

from pilot_space.api.v1.schemas.base import BaseSchema


class CreateAnnotationRequest(BaseSchema):
    """Request body for creating a new annotation on a slide.

    Attributes:
        slide_index: Zero-based index of the slide to annotate.
        content: Text content of the annotation (1-5000 characters).
    """

    slide_index: int = Field(ge=0, description="Zero-based slide index")
    content: str = Field(min_length=1, max_length=5000, description="Annotation text content")


class UpdateAnnotationRequest(BaseSchema):
    """Request body for updating an existing annotation's content.

    Attributes:
        content: New text content (1-5000 characters).
    """

    content: str = Field(
        min_length=1, max_length=5000, description="Updated annotation text content"
    )


class ArtifactAnnotationResponse(BaseSchema):
    """Response schema for a single annotation record.

    Returned by create, update, and get endpoints.
    """

    id: UUID = Field(description="Unique identifier for the annotation")
    artifact_id: UUID = Field(description="Artifact this annotation belongs to")
    slide_index: int = Field(description="Zero-based slide index")
    content: str = Field(description="Text content of the annotation")
    user_id: UUID = Field(description="User who created the annotation")
    workspace_id: UUID = Field(description="Workspace owning this annotation")
    created_at: datetime = Field(description="UTC timestamp when the annotation was created")
    updated_at: datetime = Field(description="UTC timestamp when the annotation was last updated")


class AnnotationListResponse(BaseSchema):
    """Response schema for listing annotations on a slide.

    Attributes:
        annotations: List of annotations for the requested slide.
        total: Total number of annotations for that slide.
    """

    annotations: list[ArtifactAnnotationResponse] = Field(
        description="List of annotations for the slide"
    )
    total: int = Field(ge=0, description="Total number of annotations for the slide")


__all__ = [
    "AnnotationListResponse",
    "ArtifactAnnotationResponse",
    "CreateAnnotationRequest",
    "UpdateAnnotationRequest",
]
