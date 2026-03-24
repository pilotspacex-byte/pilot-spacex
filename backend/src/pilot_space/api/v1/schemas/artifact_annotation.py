"""Artifact annotation API schemas.

Request and response models for artifact annotation CRUD endpoints.
The frontend consumes snake_case field names directly (no camelCase aliases).
"""

from __future__ import annotations

from uuid import UUID

from pydantic import ConfigDict, Field

from pilot_space.api.v1.schemas.base import BaseSchema


class _SnakeCaseSchema(BaseSchema):
    """Override BaseSchema alias generator to use snake_case for these endpoints.

    The frontend artifact-annotations.ts client uses snake_case keys directly
    (artifact_id, slide_index, user_id, etc.) so we must not emit camelCase.
    """

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        alias_generator=None,  # type: ignore[arg-type]
    )


class ArtifactAnnotationResponse(_SnakeCaseSchema):
    """Response body for a single artifact annotation.

    Shape matches the frontend AnnotationResponse interface in
    frontend/src/services/api/artifact-annotations.ts.
    """

    id: UUID = Field(description="Annotation unique identifier")
    artifact_id: UUID = Field(description="Artifact this annotation belongs to")
    slide_index: int | None = Field(
        default=None,
        description="Zero-based slide/page index (null = not slide-specific)",
    )
    content: str = Field(description="Annotation text content")
    user_id: UUID = Field(description="User who created the annotation")
    created_at: str = Field(description="ISO-8601 creation timestamp")
    updated_at: str = Field(description="ISO-8601 last-update timestamp")


class ArtifactAnnotationListResponse(_SnakeCaseSchema):
    """Response body for annotation list endpoint."""

    annotations: list[ArtifactAnnotationResponse] = Field(
        description="Annotations for the artifact"
    )
    total: int = Field(ge=0, description="Total annotation count")


class ArtifactAnnotationCreate(_SnakeCaseSchema):
    """Request body for creating an annotation."""

    slide_index: int = Field(
        ge=0,
        description="Zero-based slide/page index",
    )
    content: str = Field(
        min_length=1,
        max_length=4000,
        description="Annotation text (1–4000 chars)",
    )


class ArtifactAnnotationUpdate(_SnakeCaseSchema):
    """Request body for updating an annotation's content."""

    content: str = Field(
        min_length=1,
        max_length=4000,
        description="Updated annotation text (1–4000 chars)",
    )


__all__ = [
    "ArtifactAnnotationCreate",
    "ArtifactAnnotationListResponse",
    "ArtifactAnnotationResponse",
    "ArtifactAnnotationUpdate",
]
