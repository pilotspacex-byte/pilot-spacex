"""Pydantic v2 schemas for note templates (T-144, Feature 016 M8)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class NoteTemplateBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Template name")
    description: str | None = Field(None, max_length=1000, description="Template description")
    content: dict[str, Any] = Field(..., description="TipTap document JSON")


class NoteTemplateCreate(NoteTemplateBase):
    """Payload for creating a custom workspace template (admin only)."""


class NoteTemplateUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    content: dict[str, Any] | None = None


class NoteTemplateResponse(NoteTemplateBase):
    id: uuid.UUID
    workspace_id: uuid.UUID | None
    is_system: bool
    created_by: uuid.UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class NoteTemplateListResponse(BaseModel):
    templates: list[NoteTemplateResponse]
    total: int
