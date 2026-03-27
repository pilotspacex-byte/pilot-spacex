"""Domain schema for ActionButtonService return types.

The full API-level response schema (``SkillActionButtonResponse``) already
lives in ``api/v1/schemas/skill_action_button.py``.  This thin domain schema
mirrors that contract at the service boundary so the service is not coupled
to the API layer.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from pilot_space.domain.enums import BindingType


class ActionButtonResult(BaseModel):
    """Action button result returned by ActionButtonService.

    Mirrors ``api/v1/schemas/skill_action_button.SkillActionButtonResponse``
    but lives at the domain/service layer boundary.
    """

    model_config = ConfigDict(from_attributes=True, frozen=True)

    id: UUID
    workspace_id: UUID
    name: str
    icon: str | None
    binding_type: BindingType
    binding_id: UUID | None
    binding_metadata: dict[str, Any]
    sort_order: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


__all__ = ["ActionButtonResult"]
