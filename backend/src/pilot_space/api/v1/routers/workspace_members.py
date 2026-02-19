"""Workspace member management router for Pilot Space API.

Provides endpoints for listing, adding, updating, and removing workspace members.
Routes are mounted under /workspaces/{workspace_id}/members.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from pilot_space.api.v1.dependencies import WorkspaceMemberServiceDep
from pilot_space.api.v1.schemas.workspace import (
    WorkspaceMemberAvailabilityUpdate,
    WorkspaceMemberResponse,
    WorkspaceMemberUpdate,
)
from pilot_space.application.services.workspace_member import (
    ListMembersPayload,
    RemoveMemberPayload,
    UpdateMemberRolePayload,
)
from pilot_space.dependencies.auth import CurrentUser, CurrentUserId, SessionDep
from pilot_space.infrastructure.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.get(
    "/{workspace_id}/members",
    response_model=list[WorkspaceMemberResponse],
    tags=["workspaces"],
)
async def list_workspace_members(
    workspace_id: UUID,
    session: SessionDep,
    current_user_id: CurrentUserId,
    service: WorkspaceMemberServiceDep,
) -> list[WorkspaceMemberResponse]:
    """List workspace members.

    Args:
        workspace_id: Workspace identifier.
        session: Database session (triggers ContextVar).
        current_user_id: Authenticated user ID.
        service: Workspace member service.

    Returns:
        List of workspace members.

    Raises:
        HTTPException: If workspace not found or user not a member.
    """
    try:
        result = await service.list_members(
            ListMembersPayload(
                workspace_id=workspace_id,
                requesting_user_id=current_user_id,
            )
        )
    except ValueError as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_msg,
            ) from e
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=error_msg,
        ) from e

    return [
        WorkspaceMemberResponse(
            user_id=member.user_id,
            email=member.user.email if member.user else "",
            full_name=member.user.full_name if member.user else None,
            avatar_url=member.user.avatar_url if member.user else None,
            role=member.role.value,
            joined_at=member.created_at,
            weekly_available_hours=float(member.weekly_available_hours),
        )
        for member in result.members
    ]


@router.patch(
    "/{workspace_id}/members/{user_id}",
    response_model=WorkspaceMemberResponse,
    tags=["workspaces"],
)
async def update_workspace_member(
    workspace_id: UUID,
    user_id: UUID,
    request: WorkspaceMemberUpdate,
    session: SessionDep,
    current_user: CurrentUser,
    service: WorkspaceMemberServiceDep,
) -> WorkspaceMemberResponse:
    """Update member role.

    Requires admin role.

    Args:
        workspace_id: Workspace identifier.
        user_id: Member user ID.
        request: Update data.
        session: Database session (triggers ContextVar).
        current_user: Authenticated user.
        service: Workspace member service.

    Returns:
        Updated member.

    Raises:
        HTTPException: If not found or not admin.
    """
    try:
        result = await service.update_member_role(
            UpdateMemberRolePayload(
                workspace_id=workspace_id,
                target_user_id=user_id,
                new_role=request.role,
                actor_id=current_user.user_id,
            )
        )
    except ValueError as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_msg,
            ) from e
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=error_msg,
        ) from e

    updated_member = result.updated_member
    return WorkspaceMemberResponse(
        user_id=updated_member.user_id,
        email=updated_member.user.email if updated_member.user else "",
        full_name=updated_member.user.full_name if updated_member.user else None,
        avatar_url=updated_member.user.avatar_url if updated_member.user else None,
        role=updated_member.role.value,
        joined_at=updated_member.created_at,
        weekly_available_hours=float(updated_member.weekly_available_hours),
    )


@router.delete(
    "/{workspace_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["workspaces"],
)
async def remove_workspace_member(
    workspace_id: UUID,
    user_id: UUID,
    session: SessionDep,
    current_user: CurrentUser,
    service: WorkspaceMemberServiceDep,
) -> None:
    """Remove member from workspace.

    Requires admin role (or self-removal).

    Args:
        workspace_id: Workspace identifier.
        user_id: Member user ID.
        session: Database session (triggers ContextVar).
        current_user: Authenticated user.
        service: Workspace member service.

    Raises:
        HTTPException: If not found or not authorized.
    """
    try:
        await service.remove_member(
            RemoveMemberPayload(
                workspace_id=workspace_id,
                target_user_id=user_id,
                actor_id=current_user.user_id,
            )
        )
    except ValueError as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_msg,
            ) from e
        if "only admin" in error_msg.lower() or "owner cannot remove" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg,
            ) from e
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=error_msg,
        ) from e


@router.patch(
    "/{workspace_id}/members/{user_id}/availability",
    response_model=WorkspaceMemberResponse,
    tags=["workspaces"],
    summary="Update member weekly available hours (T-246)",
)
async def update_member_availability(
    workspace_id: UUID,
    user_id: UUID,
    request: WorkspaceMemberAvailabilityUpdate,
    session: SessionDep,
    current_user: CurrentUser,
) -> WorkspaceMemberResponse:
    """Update a member's weekly available hours for capacity planning.

    Any workspace member can update their own hours.
    Admins can update any member's hours.

    Args:
        workspace_id: Workspace identifier.
        user_id: Member user ID.
        request: New weekly available hours.
        session: Database session.
        current_user: Authenticated user.

    Returns:
        Updated member response.

    Raises:
        HTTPException: If member not found or unauthorized.
    """
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from pilot_space.infrastructure.database.models.workspace_member import WorkspaceMember

    # Only self or admin can update
    is_self = current_user.user_id == user_id
    is_admin = current_user.role in ("owner", "admin") if hasattr(current_user, "role") else False

    if not is_self and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins or the member themselves can update availability",
        )

    result = await session.execute(
        select(WorkspaceMember)
        .options(selectinload(WorkspaceMember.user))
        .where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user_id,
        )
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")

    member.weekly_available_hours = request.weekly_available_hours
    await session.flush()
    await session.refresh(member)

    user = member.user
    display_name = (
        getattr(user, "full_name", None) or getattr(user, "email", None) or str(user_id)
        if user
        else str(user_id)
    )

    return WorkspaceMemberResponse(
        user_id=member.user_id,
        email=getattr(user, "email", "") if user else "",
        full_name=display_name if user else None,
        avatar_url=getattr(user, "avatar_url", None) if user else None,
        role=member.role.value,
        joined_at=member.created_at,
        weekly_available_hours=float(member.weekly_available_hours),
    )


__all__ = ["router"]
