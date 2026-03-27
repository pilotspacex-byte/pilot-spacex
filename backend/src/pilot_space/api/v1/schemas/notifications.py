"""Pydantic schemas for the notifications API.

T-030: In-app notification response schemas.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from pilot_space.infrastructure.database.models.notification import (
    NotificationPriority,
    NotificationType,
)


class NotificationResponse(BaseModel):
    """Notification API response schema."""

    id: UUID
    workspace_id: UUID
    user_id: UUID
    type: NotificationType
    title: str
    body: str
    entity_type: str | None
    entity_id: UUID | None
    priority: NotificationPriority
    read_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class NotificationListResponse(BaseModel):
    """Paginated notification list response."""

    items: list[NotificationResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class UnreadCountResponse(BaseModel):
    """Unread notification count for bell badge."""

    count: int


__all__ = [
    "NotificationListResponse",
    "NotificationResponse",
    "UnreadCountResponse",
]
