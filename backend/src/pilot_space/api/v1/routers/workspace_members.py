"""Workspace member management router for Pilot Space API.

Provides endpoints for listing, adding, updating, and removing workspace members.
Routes are mounted under /workspaces/{workspace_id}/members.
"""

from __future__ import annotations

import re
from uuid import UUID

from fastapi import APIRouter, Query, status

from pilot_space.api.v1.dependencies import MemberProfileServiceDep, WorkspaceMemberServiceDep
from pilot_space.api.v1.schemas.workspace import (
    MemberActivityItem,
    MemberActivityResponse,
    MemberContributionStats,
    MemberProfileResponse,
    WorkspaceMemberAvailabilityUpdate,
    WorkspaceMemberResponse,
    WorkspaceMemberUpdate,
)
from pilot_space.application.services.workspace_member import (
    GetMemberActivityPayload,
    GetMemberProfilePayload,
    ListMembersPayload,
    RemoveMemberPayload,
    UpdateMemberAvailabilityPayload,
    UpdateMemberRolePayload,
)
from pilot_space.dependencies.auth import CurrentUser, CurrentUserId, SessionDep
from pilot_space.infrastructure.database.models.activity import ActivityType
from pilot_space.infrastructure.database.rls import set_rls_context
from pilot_space.infrastructure.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()

_HTML_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(value: str | None) -> str | None:
    """Strip HTML tags from activity old/new values stored by TipTap editor."""
    if value is None:
        return None
    return _HTML_TAG_RE.sub("", value).strip() or None


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
        WorkspaceNotFoundError: If workspace not found.
        MemberNotFoundError: If user not a member.
        UnauthorizedError: If user not authorized.
    """
    await set_rls_context(session, current_user_id, workspace_id)
    result = await service.list_members(
        ListMembersPayload(
            workspace_id=workspace_id,
            requesting_user_id=current_user_id,
        )
    )

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
        WorkspaceNotFoundError: If workspace not found.
        MemberNotFoundError: If member not found.
        UnauthorizedError: If not admin.
    """
    await set_rls_context(session, current_user.user_id, workspace_id)
    result = await service.update_member_role(
        UpdateMemberRolePayload(
            workspace_id=workspace_id,
            target_user_id=user_id,
            new_role=request.role,
            actor_id=current_user.user_id,
        )
    )

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
        WorkspaceNotFoundError: If workspace not found.
        MemberNotFoundError: If member not found.
        UnauthorizedError: If not authorized.
    """
    await set_rls_context(session, current_user.user_id, workspace_id)
    await service.remove_member(
        RemoveMemberPayload(
            workspace_id=workspace_id,
            target_user_id=user_id,
            actor_id=current_user.user_id,
        )
    )


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
    service: WorkspaceMemberServiceDep,
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
        service: Workspace member service.

    Returns:
        Updated member response.

    Raises:
        WorkspaceNotFoundError: If workspace not found.
        MemberNotFoundError: If member not found.
        UnauthorizedError: If not authorized.
    """
    await set_rls_context(session, current_user.user_id, workspace_id)
    result = await service.update_availability(
        UpdateMemberAvailabilityPayload(
            workspace_id=workspace_id,
            user_id=user_id,
            actor_id=current_user.user_id,
            weekly_available_hours=request.weekly_available_hours,
        ),
        session,
    )

    member = result.member
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


@router.get(
    "/{workspace_id}/members/{user_id}",
    response_model=MemberProfileResponse,
    tags=["workspaces"],
)
async def get_workspace_member_profile(
    workspace_id: UUID,
    user_id: UUID,
    session: SessionDep,
    current_user_id: CurrentUserId,
    service: MemberProfileServiceDep,
) -> MemberProfileResponse:
    """Get member profile with contribution stats.

    Args:
        workspace_id: Workspace identifier.
        user_id: Target member user ID.
        session: Database session.
        current_user_id: Authenticated user ID.
        service: Member profile service.

    Returns:
        Member profile with contribution metrics.

    Raises:
        WorkspaceNotFoundError: If workspace not found.
        MemberNotFoundError: If member not found.
        UnauthorizedError: If requester not a member.
    """
    await set_rls_context(session, current_user_id, workspace_id)
    result = await service.get_profile(
        GetMemberProfilePayload(
            workspace_id=workspace_id,
            user_id=user_id,
            requesting_user_id=current_user_id,
        )
    )

    member = result.member
    return MemberProfileResponse(
        user_id=member.user_id,
        email=member.user.email if member.user else "",
        full_name=member.user.full_name if member.user else None,
        avatar_url=member.user.avatar_url if member.user else None,
        role=member.role.value,
        joined_at=member.created_at,
        weekly_available_hours=float(member.weekly_available_hours),
        stats=MemberContributionStats(
            issues_created=result.issues_created,
            issues_assigned=result.issues_assigned,
            cycle_velocity=result.cycle_velocity,
            capacity_utilization_pct=result.capacity_utilization_pct,
            pr_commit_links_count=result.pr_commit_links_count,
        ),
    )


@router.get(
    "/{workspace_id}/members/{user_id}/activity",
    response_model=MemberActivityResponse,
    tags=["workspaces"],
)
async def get_workspace_member_activity(
    workspace_id: UUID,
    user_id: UUID,
    session: SessionDep,
    current_user_id: CurrentUserId,
    service: MemberProfileServiceDep,
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(default=20, ge=1, le=50, description="Items per page (max 50)"),
    type_filter: ActivityType | None = Query(default=None, description="Filter by activity type"),
) -> MemberActivityResponse:
    """Get paginated activity feed for a workspace member.

    Args:
        workspace_id: Workspace identifier.
        user_id: Target member user ID.
        session: Database session.
        current_user_id: Authenticated user ID.
        service: Member profile service.
        page: Page number.
        page_size: Items per page (max 50).
        type_filter: Optional activity type filter.

    Returns:
        Paginated member activity items with issue context.

    Raises:
        WorkspaceNotFoundError: If workspace not found.
        MemberNotFoundError: If member not found.
        UnauthorizedError: If requester not a member.
    """
    await set_rls_context(session, current_user_id, workspace_id)
    result = await service.get_activity(
        GetMemberActivityPayload(
            workspace_id=workspace_id,
            user_id=user_id,
            requesting_user_id=current_user_id,
            page=page,
            page_size=page_size,
            type_filter=type_filter,
        )
    )

    items = []
    for activity in result.items:
        issue = activity.issue
        identifier = None
        title = None
        if issue:
            identifier = issue.identifier if hasattr(issue, "identifier") else None
            title = issue.name if hasattr(issue, "name") else None

        items.append(
            MemberActivityItem(
                id=activity.id,
                activity_type=(
                    activity.activity_type.value
                    if hasattr(activity.activity_type, "value")
                    else str(activity.activity_type)
                ),
                field=activity.field,
                old_value=_strip_html(activity.old_value),
                new_value=_strip_html(activity.new_value),
                comment=activity.comment,
                created_at=activity.created_at,
                issue_id=activity.issue_id,
                issue_identifier=identifier,
                issue_title=title,
            )
        )

    return MemberActivityResponse(
        items=items,
        total=result.total,
        page=result.page,
        page_size=result.page_size,
    )


__all__ = ["router"]
