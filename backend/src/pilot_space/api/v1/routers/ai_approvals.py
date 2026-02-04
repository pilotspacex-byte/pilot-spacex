"""AI approval queue endpoints.

Approval queue management for AI-suggested actions.

T073-T075: Approval queue endpoints.
"""

from __future__ import annotations

import logging
import uuid
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Path, Query, status

from pilot_space.api.middleware.request_context import WorkspaceId
from pilot_space.api.v1.schemas.approval import (
    ApprovalDetailResponse,
    ApprovalListResponse,
    ApprovalRequestResponse,
    ApprovalResolution,
    ApprovalResolutionResponse,
    ApprovalStatus as ApprovalStatusSchema,
)
from pilot_space.dependencies import (
    CurrentUserId,
    DbSession,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/approvals", tags=["AI Approvals"])


def _get_context_preview(payload: dict[str, Any]) -> str:
    """Generate brief context from payload.

    Args:
        payload: Action payload dictionary.

    Returns:
        Brief preview string.
    """
    if "title" in payload:
        return payload["title"][:100]
    if "issues" in payload:
        issue_count = len(payload["issues"])
        return f"{issue_count} issue{'s' if issue_count != 1 else ''} to create"
    if "issue_id" in payload:
        return f"Action on issue {payload['issue_id']}"
    return "Action pending approval"


async def verify_workspace_admin(
    current_user_id: uuid.UUID,
    workspace_id: uuid.UUID,
    session: DbSession,
) -> None:
    """Verify user is workspace admin.

    Args:
        current_user_id: User to verify.
        workspace_id: Workspace to check.
        session: Database session.

    Raises:
        HTTPException: 403 if user is not an admin/owner.
    """
    from pilot_space.config import get_settings

    settings = get_settings()

    # Skip in demo mode
    if settings.app_env in ("development", "test") and current_user_id == UUID(
        "00000000-0000-0000-0000-000000000001"
    ):
        return

    from sqlalchemy import select

    from pilot_space.infrastructure.database.models.workspace_member import (
        WorkspaceMember,
        WorkspaceRole,
    )

    stmt = select(WorkspaceMember.role).where(
        WorkspaceMember.workspace_id == workspace_id,
        WorkspaceMember.user_id == current_user_id,
    )
    result = await session.execute(stmt)
    role = result.scalar()

    if role not in (WorkspaceRole.OWNER, WorkspaceRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )


@router.get(
    "",
    response_model=ApprovalListResponse,
    summary="List approval requests",
    description="List approval requests for workspace with optional status filter (DD-003).",
)
async def list_approvals(
    workspace_id: WorkspaceId,
    current_user_id: CurrentUserId,
    session: DbSession,
    status: Annotated[ApprovalStatusSchema | None, Query(description="Filter by status")] = None,
    limit: Annotated[int, Query(ge=1, le=100, description="Maximum results")] = 20,
    offset: Annotated[int, Query(ge=0, description="Results to skip")] = 0,
) -> ApprovalListResponse:
    """List approval requests for workspace.

    Filters:
    - status: Filter by status (pending, approved, rejected, expired)

    Returns paginated list of approval requests.
    Requires workspace admin permission.

    Args:
        workspace_id: Workspace UUID from request context.
        current_user_id: Current user ID.
        session: Database session.
        status: Optional status filter.
        limit: Maximum results.
        offset: Results to skip.

    Returns:
        List of approval requests with pagination.
    """

    # Verify user is workspace admin
    await verify_workspace_admin(current_user_id, workspace_id, session)

    # Get approval service
    from pilot_space.ai.infrastructure.approval import ApprovalService

    approval_service = ApprovalService(session)

    # List requests
    requests, total = await approval_service.list_requests(
        workspace_id=workspace_id,
        status=status.value if status else None,
        limit=limit,
        offset=offset,
    )

    # Count pending
    pending_count = await approval_service.count_pending(workspace_id)

    # Build response
    return ApprovalListResponse(
        requests=[
            ApprovalRequestResponse(
                id=str(r.id),
                agent_name=r.agent_name,
                action_type=r.action_type,
                status=ApprovalStatusSchema(r.status),
                created_at=r.created_at,
                expires_at=r.expires_at,
                requested_by=r.user.name if r.user else "Unknown",
                context_preview=_get_context_preview(r.payload),
            )
            for r in requests
        ],
        total=total,
        pending_count=pending_count,
    )


@router.get(
    "/{approval_id}",
    response_model=ApprovalDetailResponse,
    summary="Get approval request details",
    description="Get full details of an approval request including payload.",
)
async def get_approval(
    workspace_id: WorkspaceId,
    approval_id: Annotated[uuid.UUID, Path(description="Approval request ID")],
    current_user_id: CurrentUserId,
    session: DbSession,
) -> ApprovalDetailResponse:
    """Get approval request details including payload.

    Args:
        workspace_id: Workspace UUID from request context.
        approval_id: Approval request ID.
        current_user_id: Current user ID.
        session: Database session.

    Returns:
        Full approval request details.

    Raises:
        HTTPException: If request not found or unauthorized.
    """

    from pilot_space.ai.infrastructure.approval import ApprovalService

    approval_service = ApprovalService(session)

    # Get request
    approval_request = await approval_service.get_request(approval_id)

    if not approval_request or approval_request.workspace_id != workspace_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Approval request not found",
        )

    return ApprovalDetailResponse(
        id=str(approval_request.id),
        agent_name=approval_request.agent_name,
        action_type=approval_request.action_type,
        status=ApprovalStatusSchema(approval_request.status),
        payload=approval_request.payload,
        context=approval_request.context,
        created_at=approval_request.created_at,
        expires_at=approval_request.expires_at,
        resolved_at=approval_request.resolved_at,
        resolved_by=approval_request.resolver.name if approval_request.resolver else None,
        resolution_note=approval_request.resolution_note,
    )


@router.post(
    "/{approval_id}/resolve",
    response_model=ApprovalResolutionResponse,
    summary="Resolve approval request",
    description="Approve or reject an approval request. If approved, executes the pending action.",
)
async def resolve_approval(
    workspace_id: WorkspaceId,
    approval_id: Annotated[uuid.UUID, Path(description="Approval request ID")],
    body: ApprovalResolution,
    current_user_id: CurrentUserId,
    session: DbSession,
) -> ApprovalResolutionResponse:
    """Resolve an approval request.

    If approved, executes the pending action.
    If rejected, discards the action.

    Args:
        workspace_id: Workspace UUID from request context.
        approval_id: Approval request ID.
        body: Resolution decision.
        current_user_id: Current user ID.
        session: Database session.

    Returns:
        Resolution result with action outcome.

    Raises:
        HTTPException: If request not found, unauthorized, or already resolved.
    """

    # Verify user is workspace admin
    await verify_workspace_admin(current_user_id, workspace_id, session)

    from pilot_space.ai.infrastructure.approval import ApprovalService

    approval_service = ApprovalService(session)

    # Get request
    approval_request = await approval_service.get_request(approval_id)

    if not approval_request or approval_request.workspace_id != workspace_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Approval request not found",
        )

    if approval_request.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Request already {approval_request.status}",
        )

    # Resolve the request
    await approval_service.resolve(
        request_id=approval_id,
        resolved_by=current_user_id,
        approved=body.approved,
        resolution_note=body.note,
    )

    result: dict[str, Any] = {"approved": body.approved, "action_result": None}

    # If approved, execute the action
    if body.approved:
        try:
            action_result = await _execute_approved_action(
                approval_request.agent_name,
                approval_request.action_type,
                approval_request.payload,
                current_user_id,
                session,
            )
            result["action_result"] = action_result
        except Exception as e:
            logger.exception("Failed to execute approved action")
            result["action_error"] = str(e)

    return ApprovalResolutionResponse(**result)


async def _execute_approved_action(
    agent_name: str,
    action_type: str,
    payload: dict[str, Any],
    current_user_id: uuid.UUID,
    session: Any,
) -> dict[str, Any]:
    """Execute the approved action.

    Args:
        agent_name: Name of the requesting agent.
        action_type: Type of action to execute.
        payload: Action payload.
        current_user_id: User who approved.
        session: Database session.

    Returns:
        Execution result.
    """
    raise NotImplementedError(
        f"Action execution for '{action_type}' not yet integrated with service layer. "
        "Approval recorded but action must be executed manually."
    )


__all__ = ["router"]
