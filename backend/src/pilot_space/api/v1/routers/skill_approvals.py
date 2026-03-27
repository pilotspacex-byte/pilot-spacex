"""Skill approval API endpoints (T-046).

Approve or reject pending skill executions.
- GET  /{workspace_id}/skill-approvals/pending        -> List pending approval executions.
- POST /{workspace_id}/skill-approvals/{execution_id}/approve
  -> Persist skill output to note, mark execution approved.
- POST /{workspace_id}/skill-approvals/{execution_id}/reject
  -> Discard skill output, mark execution rejected.

Approval expires after 24 hours (T-070 pg_cron job).
Admin approval required for destructive skills (C-7).

Feature 015: AI Workforce Platform -- Sprint 2
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Path, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from pilot_space.api.middleware.request_context import WorkspaceId
from pilot_space.api.v1.schemas.skill_approvals import (
    PendingApprovalsResponse,
    PendingSkillExecutionItem,
    SkillApprovalResponse,
    SkillApproveRequest,
)
from pilot_space.dependencies import CurrentUserId, DbSession
from pilot_space.domain.exceptions import ForbiddenError, NotFoundError, ValidationError
from pilot_space.infrastructure.database.models.skill_execution import (
    SkillApprovalStatus,
    SkillExecution,
)
from pilot_space.infrastructure.database.models.work_intent import WorkIntent
from pilot_space.infrastructure.database.models.workspace_member import (
    WorkspaceMember,
    WorkspaceRole,
)
from pilot_space.infrastructure.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(
    prefix="/{workspace_id}/skill-approvals",
    tags=["Skill Approvals"],
)

ExecutionIdPath = Path(..., description="SkillExecution UUID to approve/reject")


async def _verify_workspace_membership(
    user_id: UUID,
    workspace_id: UUID,
    session: AsyncSession,
    required_role: str | None = None,
) -> str:
    """Verify user is a workspace member and optionally check their role.

    Args:
        user_id: User UUID to verify.
        workspace_id: Workspace UUID to check.
        session: Database session.
        required_role: If 'admin', user must be admin or owner.

    Returns:
        User's role in the workspace.

    Raises:
        HTTPException: 403 if user is not a member, or insufficient role.
    """
    stmt = select(WorkspaceMember.role).where(
        WorkspaceMember.workspace_id == workspace_id,
        WorkspaceMember.user_id == user_id,
    )
    result = await session.execute(stmt)
    row = result.scalar()

    if row is None:
        raise ForbiddenError("Not a member of this workspace")

    role = row.value if hasattr(row, "value") else str(row)

    if required_role == "admin" and role not in (
        WorkspaceRole.ADMIN.value,
        WorkspaceRole.OWNER.value,
    ):
        raise ForbiddenError("Admin or owner role required to approve this skill execution")

    return role


async def _get_execution_or_404(
    execution_id: UUID,
    workspace_id: UUID,
    session: AsyncSession,
) -> SkillExecution:
    """Fetch SkillExecution by ID, verify it belongs to the workspace, and it is pending.

    Args:
        execution_id: SkillExecution UUID.
        workspace_id: Expected workspace for RLS check.
        session: Database session.

    Returns:
        SkillExecution ORM record in pending_approval state.

    Raises:
        HTTPException: 404 if not found, 422 if not in pending_approval state.
    """
    stmt = (
        select(SkillExecution)
        .join(WorkIntent, SkillExecution.intent_id == WorkIntent.id)
        .where(
            SkillExecution.id == execution_id,
            WorkIntent.workspace_id == workspace_id,
            SkillExecution.is_deleted == False,  # noqa: E712
        )
    )
    result = await session.execute(stmt)
    execution = result.scalar_one_or_none()

    if execution is None:
        raise NotFoundError(f"Skill execution {execution_id} not found in this workspace")

    if execution.approval_status != SkillApprovalStatus.PENDING_APPROVAL:
        raise ValidationError(
            f"Execution is in '{execution.approval_status.value}' state, not pending_approval"
        )

    return execution


@router.get(
    "/pending",
    response_model=PendingApprovalsResponse,
    status_code=status.HTTP_200_OK,
    summary="List pending skill executions",
    description=(
        "Return all skill executions in pending_approval state for the workspace. "
        "Paginated by limit/offset."
    ),
)
async def list_pending_approvals(
    workspace_id: WorkspaceId,
    session: DbSession,
    current_user_id: CurrentUserId,
    limit: Annotated[int, Query(ge=1, le=100, description="Page size")] = 20,
    offset: Annotated[int, Query(ge=0, description="Page offset")] = 0,
) -> PendingApprovalsResponse:
    """List pending skill executions for workspace.

    Returns executions in pending_approval state, joined to their work intent
    for workspace-level RLS enforcement.  Any workspace member may view pending
    approvals; role enforcement happens at the approve step.

    Args:
        workspace_id: Workspace UUID from request context.
        session: Database session.
        current_user_id: Authenticated user ID.
        limit: Maximum items to return (1-100).
        offset: Items to skip for pagination.

    Returns:
        PendingApprovalsResponse with paginated items and total count.
    """
    await _verify_workspace_membership(current_user_id, workspace_id, session)

    base_filter = (
        SkillExecution.approval_status == SkillApprovalStatus.PENDING_APPROVAL,
        WorkIntent.workspace_id == workspace_id,
        SkillExecution.is_deleted == False,  # noqa: E712
    )

    count_stmt = (
        select(func.count(SkillExecution.id))
        .join(WorkIntent, SkillExecution.intent_id == WorkIntent.id)
        .where(*base_filter)
    )
    total: int = (await session.execute(count_stmt)).scalar_one()

    page_stmt = (
        select(SkillExecution)
        .join(WorkIntent, SkillExecution.intent_id == WorkIntent.id)
        .where(*base_filter)
        .order_by(SkillExecution.created_at.asc())
        .limit(limit)
        .offset(offset)
    )
    rows = (await session.execute(page_stmt)).scalars().all()

    items = [
        PendingSkillExecutionItem(
            execution_id=row.id,
            skill_name=row.skill_name,
            intent_id=row.intent_id,
            required_approval_role=(
                row.required_approval_role.value if row.required_approval_role else None
            ),
            created_at=row.created_at.isoformat(),
        )
        for row in rows
    ]

    logger.debug(
        "[SkillApprovals] Listed pending workspace=%s total=%d limit=%d offset=%d",
        workspace_id,
        total,
        limit,
        offset,
    )

    return PendingApprovalsResponse(items=items, total=total, limit=limit, offset=offset)


@router.post(
    "/{execution_id}/approve",
    response_model=SkillApprovalResponse,
    status_code=status.HTTP_200_OK,
    summary="Approve a pending skill execution",
    description=(
        "Approve a skill execution in pending_approval state. "
        "Persists skill output to the note. "
        "Admin role required for destructive skills (C-7)."
    ),
)
async def approve_skill_execution(
    workspace_id: WorkspaceId,
    execution_id: UUID = ExecutionIdPath,
    request: SkillApproveRequest | None = None,
    session: DbSession = ...,  # type: ignore[assignment]
    current_user_id: CurrentUserId = ...,  # type: ignore[assignment]
) -> SkillApprovalResponse:
    """Approve a skill execution, writing output to the note.

    Args:
        workspace_id: Workspace UUID from request context.
        execution_id: SkillExecution UUID to approve.
        request: Optional note_id and output_override for applying output.
        session: Database session.
        current_user_id: Authenticated user ID.

    Returns:
        SkillApprovalResponse with execution_id and 'approved' status.

    Raises:
        HTTPException: 403 if insufficient role, 404 if not found, 422 if not pending.
    """
    execution = await _get_execution_or_404(execution_id, workspace_id, session)

    # C-7: Admin approval required for destructive skills
    required_role: str | None = None
    if execution.required_approval_role:
        required_role = execution.required_approval_role.value

    await _verify_workspace_membership(
        current_user_id, workspace_id, session, required_role=required_role
    )

    from pilot_space.ai.skills.skill_executor import SkillExecutor
    from pilot_space.config import get_settings
    from pilot_space.container import get_container

    settings = get_settings()
    container = get_container()
    redis = container.redis_client()
    executor = SkillExecutor(
        session=session,
        redis=redis,  # type: ignore[arg-type]
        skills_dir=settings.system_templates_dir / "skills",
    )

    note_id = request.note_id if request else None
    output_override = request.output_override if request else None

    await executor.approve_execution(
        execution_id=execution_id,
        approved_by=current_user_id,
        note_id=note_id,
        output_override=output_override,
    )

    logger.info(
        "[SkillApprovals] Approved execution_id=%s workspace=%s user=%s",
        execution_id,
        workspace_id,
        current_user_id,
    )

    return SkillApprovalResponse(execution_id=execution_id, status="approved")


@router.post(
    "/{execution_id}/reject",
    response_model=SkillApprovalResponse,
    status_code=status.HTTP_200_OK,
    summary="Reject a pending skill execution",
    description=(
        "Reject a skill execution in pending_approval state, discarding output. "
        "Any workspace member can reject."
    ),
)
async def reject_skill_execution(
    workspace_id: WorkspaceId,
    execution_id: UUID = ExecutionIdPath,
    session: DbSession = ...,  # type: ignore[assignment]
    current_user_id: CurrentUserId = ...,  # type: ignore[assignment]
) -> SkillApprovalResponse:
    """Reject a skill execution, discarding the pending output.

    Args:
        workspace_id: Workspace UUID from request context.
        execution_id: SkillExecution UUID to reject.
        session: Database session.
        current_user_id: Authenticated user ID.

    Returns:
        SkillApprovalResponse with execution_id and 'rejected' status.

    Raises:
        HTTPException: 403 if not workspace member, 404 if not found, 422 if not pending.
    """
    await _get_execution_or_404(execution_id, workspace_id, session)
    await _verify_workspace_membership(current_user_id, workspace_id, session)

    from pilot_space.ai.skills.skill_executor import SkillExecutor
    from pilot_space.config import get_settings
    from pilot_space.container import get_container

    settings = get_settings()
    container = get_container()
    redis = container.redis_client()
    executor = SkillExecutor(
        session=session,
        redis=redis,  # type: ignore[arg-type]
        skills_dir=settings.system_templates_dir / "skills",
    )

    await executor.reject_execution(
        execution_id=execution_id,
        rejected_by=current_user_id,
    )

    logger.info(
        "[SkillApprovals] Rejected execution_id=%s workspace=%s user=%s",
        execution_id,
        workspace_id,
        current_user_id,
    )

    return SkillApprovalResponse(execution_id=execution_id, status="rejected")
