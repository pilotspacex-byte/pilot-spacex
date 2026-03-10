"""Notification router for in-app notification management.

T-030: REST Router for notifications.

Endpoints:
- GET  /workspaces/{workspace_id}/notifications              — paginated list
- GET  /workspaces/{workspace_id}/notifications/unread-count — bell badge count
- PATCH /workspaces/{workspace_id}/notifications/{id}/read   — mark single read
- POST /workspaces/{workspace_id}/notifications/read-all     — mark all read
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

from pilot_space.application.services.notification.notification_service import (
    NotificationNotFoundError,
    NotificationService,
)
from pilot_space.dependencies.auth import CurrentUserId, SessionDep
from pilot_space.infrastructure.database.models.notification import (
    NotificationPriority,
    NotificationType,
)
from pilot_space.infrastructure.database.repositories.notification_repository import (
    NotificationRepository,
)
from pilot_space.infrastructure.database.rls import set_rls_context
from pilot_space.infrastructure.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Dependency helpers
# ---------------------------------------------------------------------------


def _get_notification_service(session: SessionDep) -> NotificationService:
    """Build NotificationService for the current request session.

    The session is explicitly passed so the ContextVar is set before the
    repository is instantiated — matching the pattern in all other routers.
    """
    repo = NotificationRepository(session)
    return NotificationService(session=session, notification_repository=repo)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/{workspace_id}/notifications/unread-count",
    response_model=UnreadCountResponse,
    tags=["notifications"],
    summary="Get unread notification count",
)
async def get_unread_count(
    workspace_id: UUID,
    session: SessionDep,
    current_user_id: CurrentUserId,
) -> UnreadCountResponse:
    """Return the number of unread notifications for the authenticated user.

    Used to drive the bell badge in the UI.

    Args:
        workspace_id: Workspace UUID.
        session: Database session (triggers ContextVar).
        current_user_id: Authenticated user UUID.

    Returns:
        Unread notification count.
    """
    await set_rls_context(session, current_user_id, workspace_id)
    service = _get_notification_service(session)
    count = await service.count_unread(workspace_id, current_user_id)
    return UnreadCountResponse(count=count)


@router.get(
    "/{workspace_id}/notifications",
    response_model=NotificationListResponse,
    tags=["notifications"],
    summary="List notifications for the authenticated user",
)
async def list_notifications(
    workspace_id: UUID,
    session: SessionDep,
    current_user_id: CurrentUserId,
    page: Annotated[int, Query(ge=1, description="Page number (1-based)")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 20,
    unread_only: Annotated[bool, Query(description="Return only unread notifications")] = False,
) -> NotificationListResponse:
    """Return paginated notifications for the authenticated user in a workspace.

    Results are ordered newest-first. Use ``unread_only=true`` to filter
    to only unread items (null read_at).

    Args:
        workspace_id: Workspace UUID.
        session: Database session.
        current_user_id: Authenticated user UUID.
        page: 1-based page number.
        page_size: Items per page (1-100).
        unread_only: Filter to unread only when True.

    Returns:
        Paginated notification list.
    """
    await set_rls_context(session, current_user_id, workspace_id)
    service = _get_notification_service(session)
    result = await service.list_for_user(
        workspace_id=workspace_id,
        user_id=current_user_id,
        page=page,
        page_size=page_size,
        unread_only=unread_only,
    )
    return NotificationListResponse(
        items=[NotificationResponse.model_validate(n) for n in result.items],
        total=result.total,
        page=result.page,
        page_size=result.page_size,
        total_pages=result.total_pages,
    )


@router.patch(
    "/{workspace_id}/notifications/{notification_id}/read",
    response_model=NotificationResponse,
    tags=["notifications"],
    summary="Mark a single notification as read",
)
async def mark_notification_read(
    workspace_id: UUID,
    notification_id: UUID,
    session: SessionDep,
    current_user_id: CurrentUserId,
) -> NotificationResponse:
    """Mark a specific notification as read.

    Only the owning user may mark their own notification as read.
    Returns 404 if the notification does not exist or belongs to a different user.

    Args:
        workspace_id: Workspace UUID.
        notification_id: Notification UUID.
        session: Database session.
        current_user_id: Authenticated user UUID.

    Returns:
        Updated notification.

    Raises:
        HTTPException 404: If notification not found or not owned by the user.
    """
    await set_rls_context(session, current_user_id, workspace_id)
    service = _get_notification_service(session)
    try:
        notification = await service.mark_read(notification_id, current_user_id)
    except NotificationNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return NotificationResponse.model_validate(notification)


@router.post(
    "/{workspace_id}/notifications/read-all",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["notifications"],
    summary="Mark all notifications as read",
)
async def mark_all_notifications_read(
    workspace_id: UUID,
    session: SessionDep,
    current_user_id: CurrentUserId,
) -> None:
    """Mark all unread notifications as read for the authenticated user.

    Args:
        workspace_id: Workspace UUID.
        session: Database session.
        current_user_id: Authenticated user UUID.
    """
    await set_rls_context(session, current_user_id, workspace_id)
    service = _get_notification_service(session)
    count = await service.mark_all_read(workspace_id, current_user_id)
    logger.debug(
        "mark_all_read_completed",
        workspace_id=str(workspace_id),
        user_id=str(current_user_id),
        updated=count,
    )
