"""Issue implement-context router.

Provides GET /api/v1/issues/{issue_ref}/implement-context for the
pilot CLI to fetch full implementation context before launching Claude Code.

Accepts both UUID and human-readable identifier formats (e.g., "PS-42").
"""

from __future__ import annotations

import re
from uuid import UUID

from fastapi import APIRouter, Body, HTTPException, status

from pilot_space.api.v1.dependencies import UpdateIssueServiceDep
from pilot_space.api.v1.dependencies_pilot import (
    CLIRequesterContextDep,
    RichContextAssemblerDep,
)
from pilot_space.api.v1.repository_deps import IssueRepositoryDep
from pilot_space.api.v1.schemas.implement_context import ImplementContextResponse
from pilot_space.api.v1.schemas.issue import StateUpdateRequest
from pilot_space.application.services.issue.rich_context_assembler import RichContextPayload
from pilot_space.dependencies.auth import SessionDep
from pilot_space.infrastructure.database.rls import set_rls_context
from pilot_space.infrastructure.logging import get_logger

router = APIRouter(
    prefix="/issues",
    tags=["Issues"],
    responses={
        401: {"description": "Not authenticated - missing or invalid JWT token"},
        403: {"description": "Not authorized to access this resource"},
        404: {"description": "Issue not found"},
        422: {"description": "Unprocessable entity"},
        500: {"description": "Internal server error"},
    },
)

logger = get_logger(__name__)

# Regex for human-readable issue identifiers like "PS-42" (1-10 uppercase chars, dash, int)
_IDENTIFIER_RE = re.compile(r"^([A-Z]{1,10})-(\d+)$")


async def _resolve_issue_id(
    issue_ref: str,
    workspace_id: UUID,
    issue_repo: IssueRepositoryDep,
) -> UUID:
    """Resolve an issue reference (UUID string or PS-42 identifier) to a UUID.

    Args:
        issue_ref: UUID string or human-readable identifier (e.g., "PS-42").
        workspace_id: Workspace UUID for scoping the identifier lookup.
        issue_repo: IssueRepository for database lookup.

    Returns:
        Resolved issue UUID.

    Raises:
        HTTPException 404: If identifier format is invalid or issue not found.
    """
    # Try parsing as UUID first
    try:
        return UUID(issue_ref)
    except ValueError:
        pass

    # Parse human-readable format e.g. "PS-42"
    match = _IDENTIFIER_RE.match(issue_ref)
    if not match:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Issue not found",
        )

    project_identifier = match.group(1)
    sequence_id = int(match.group(2))

    issue = await issue_repo.get_by_identifier(
        workspace_id=workspace_id,
        project_identifier=project_identifier,
        sequence_id=sequence_id,
    )
    if issue is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Issue not found",
        )
    return issue.id


@router.get(
    "/{issue_ref}/implement-context",
    response_model=ImplementContextResponse,
    summary="Get issue implement context for pilot CLI",
    description=(
        "Returns full context for implementing an issue via `pilot implement <id>`. "
        "Accepts UUID or human-readable identifier (e.g., PS-42). "
        "Caller must be the issue's assignee or a workspace admin/owner. "
        "Returns 422 if no GitHub integration is configured for the workspace."
    ),
)
async def get_implement_context(
    issue_ref: str,
    session: SessionDep,
    service: RichContextAssemblerDep,
    issue_repo: IssueRepositoryDep,
    requester_context: CLIRequesterContextDep,
) -> ImplementContextResponse:
    """Assemble and return the implement context for an issue.

    Accepts both Supabase JWT (web browser) and Pilot API key (CLI) auth.
    For API key auth, workspace_id is derived from the key record — no
    X-Workspace-Id header required.

    Args:
        issue_ref: UUID string or human-readable identifier (e.g., "PS-42").
        session: Database session (triggers RLS context).
        service: Injected GetImplementContextService.
        issue_repo: Injected IssueRepository for identifier resolution.
        requester_context: (user_id, workspace_id) resolved from JWT or API key.

    Returns:
        ImplementContextResponse with issue details, linked notes,
        repository context, workspace and project metadata, and suggested branch.

    Raises:
        HTTPException 401: Missing or invalid credentials.
        HTTPException 403: Requester is not the assignee or an admin/owner.
        HTTPException 404: Issue does not exist or identifier is invalid.
        HTTPException 422: No active GitHub integration configured.
    """
    current_user_id, workspace_id = requester_context
    await set_rls_context(session, current_user_id, workspace_id)

    issue_id = await _resolve_issue_id(issue_ref, workspace_id, issue_repo)

    payload = RichContextPayload(
        issue_id=issue_id,
        workspace_id=workspace_id,
        requester_id=current_user_id,
    )

    result = await service.execute(payload)

    logger.info(
        "Implement context returned",
        extra={
            "issue_ref": issue_ref,
            "issue_id": str(issue_id),
            "workspace_id": str(workspace_id),
            "requester_id": str(current_user_id),
        },
    )

    return result.context


# ============================================================================
# State update endpoint (used by CLI `update_issue_status`)
# ============================================================================


@router.patch(
    "/{issue_ref}/state",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Update issue state via pilot CLI",
    description=(
        "Updates the state of an issue. "
        "Accepts UUID or human-readable identifier (e.g., PS-42). "
        "State value must match a known state name in the workspace."
    ),
)
async def update_issue_state(
    issue_ref: str,
    session: SessionDep,
    update_service: UpdateIssueServiceDep,
    issue_repo: IssueRepositoryDep,
    requester_context: CLIRequesterContextDep,
    body: StateUpdateRequest = Body(...),
) -> None:
    """Update the state of an issue.

    Accepts both Supabase JWT and Pilot API key authentication.

    Args:
        issue_ref: UUID string or human-readable identifier (e.g., "PS-42").
        session: Database session (triggers RLS context).
        update_service: Injected UpdateIssueService.
        issue_repo: Injected IssueRepository for identifier resolution.
        requester_context: (user_id, workspace_id) resolved from JWT or API key.
        body: Request body containing the target state name.

    Raises:
        HTTPException 400: State name not found in the workspace.
        HTTPException 401: Missing or invalid credentials.
        HTTPException 404: Issue does not exist or identifier is invalid.
    """
    from sqlalchemy import select

    from pilot_space.application.services.issue.update_issue_service import (
        UNCHANGED,
        UpdateIssuePayload,
    )
    from pilot_space.infrastructure.database.models.state import State

    current_user_id, workspace_id = requester_context
    await set_rls_context(session, current_user_id, workspace_id)

    issue_id = await _resolve_issue_id(issue_ref, workspace_id, issue_repo)

    # Normalize state name to match DB values
    state_name_map = {
        "backlog": "Backlog",
        "todo": "Todo",
        "in_progress": "In Progress",
        "in-progress": "In Progress",
        "in_review": "In Review",
        "in-review": "In Review",
        "done": "Done",
        "cancelled": "Cancelled",
        "canceled": "Cancelled",
    }
    normalized_state = state_name_map.get(body.state.lower(), body.state)

    state_result = await session.execute(
        select(State)
        .where(
            State.workspace_id == workspace_id,
            State.name == normalized_state,
            State.is_deleted.is_(False),
        )
        .limit(1)
    )
    new_state = state_result.scalar_one_or_none()
    if not new_state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"State '{body.state}' not found",
        )

    payload = UpdateIssuePayload(
        issue_id=issue_id,
        actor_id=current_user_id,
        name=UNCHANGED,
        description=UNCHANGED,
        description_html=UNCHANGED,
        priority=UNCHANGED,
        state_id=new_state.id,
        assignee_id=UNCHANGED,
        cycle_id=UNCHANGED,
        module_id=UNCHANGED,
        parent_id=UNCHANGED,
        estimate_points=UNCHANGED,
        start_date=UNCHANGED,
        target_date=UNCHANGED,
        sort_order=UNCHANGED,
        label_ids=UNCHANGED,
    )

    await update_service.execute(payload)

    logger.info(
        "Issue state updated via pilot CLI",
        extra={
            "issue_ref": issue_ref,
            "issue_id": str(issue_id),
            "new_state": normalized_state,
            "workspace_id": str(workspace_id),
        },
    )


__all__ = ["router"]
