"""Artifact API schemas — request/response models for project_artifacts router.

Provides Pydantic schemas for the artifact upload, listing, and download-URL
endpoints. All schemas inherit from BaseSchema (camelCase JSON serialization).

Feature: v1.1 — Artifacts (ARTF-04, ARTF-05, ARTF-06)
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field

from pilot_space.api.v1.schemas.base import BaseSchema


class ArtifactResponse(BaseSchema):
    """Response schema for a single artifact record.

    Returned by upload and get endpoints. Clients use the /url endpoint
    to get signed download URLs — storage_key is intentionally excluded.
    """

    id: UUID = Field(description="Unique identifier for the artifact")
    project_id: UUID = Field(description="Project owning this artifact")
    user_id: UUID = Field(description="User who uploaded the artifact")
    filename: str = Field(description="Original filename including extension")
    mime_type: str = Field(description="MIME type of the uploaded file")
    size_bytes: int = Field(ge=1, description="File size in bytes")
    status: str = Field(description="Upload lifecycle state: pending_upload or ready")
    created_at: datetime = Field(description="UTC timestamp when the record was created")


class ArtifactListResponse(BaseSchema):
    """Response schema for listing artifacts in a project.

    Only includes ready artifacts (pending_upload excluded).
    """

    artifacts: list[ArtifactResponse] = Field(description="List of ready artifacts for the project")
    total: int = Field(ge=0, description="Total number of ready artifacts")


class ArtifactUrlResponse(BaseSchema):
    """Response schema for a signed download URL.

    Returned by GET /artifacts/{id}/url. URLs expire after `expires_in` seconds.
    """

    url: str = Field(description="Signed download URL for the artifact")
    expires_in: int = Field(
        default=3600,
        description="Seconds until the signed URL expires",
    )


__all__ = ["ArtifactListResponse", "ArtifactResponse", "ArtifactUrlResponse"]
