"""Domain schema for NoteTemplateService return type.

NoteTemplateResponse already exists in ``api/v1/schemas/note_template.py``
as an API-level DTO.  This thin domain schema mirrors those fields but lives
at the service boundary so services stay decoupled from the API layer.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class NoteTemplateResult(BaseModel):
    """Template CRUD result returned by NoteTemplateService.

    Matches the fields produced by ``NoteTemplateService._to_dict()``.
    """

    model_config = ConfigDict(from_attributes=True, frozen=True)

    id: UUID
    workspace_id: UUID | None
    name: str
    description: str | None
    content: dict[str, Any]
    is_system: bool
    created_by: UUID | None
    created_at: datetime
    updated_at: datetime


__all__ = ["NoteTemplateResult"]
