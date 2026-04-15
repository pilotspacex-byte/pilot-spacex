"""Workspace-scoped Issues API router.

Provides nested routes for issues under workspaces.
GET /workspaces/{workspace_id}/issues
GET /workspaces/{workspace_id}/issues/{issue_id}
POST /workspaces/{workspace_id}/issues
etc.

Supports both UUID and slug for workspace identification.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Path, Query, Response, status
from sqlalchemy import select

from pilot_space.api.v1.dependencies import (
    BatchCreateIssuesServiceDep,
    CreateIssueServiceDep,
    DeleteIssueServiceDep,
    GetIssueServiceDep,
    IssueRepositoryDep,
    ListIssuesServiceDep,
    NoteIssueLinkRepositoryDep,
    ProjectRbacServiceDep,
    UpdateIssueServiceDep,
    WorkspaceRepositoryDep,
)
from pilot_space.api.v1.repository_deps import IssueLinkRepositoryDep
from pilot_space.api.v1.routers.workspace_quota import (
    _check_storage_quota,  # pyright: ignore[reportPrivateUsage]
    _update_storage_usage,  # pyright: ignore[reportPrivateUsage]
)
from pilot_space.api.v1.schemas.base import DeleteResponse, PaginatedResponse
from pilot_space.api.v1.schemas.issue import (
    BatchCreateIssueRequest,
    BatchCreateIssueResponse,
    BatchCreateIssueResult,
    IssueBriefResponse,
    IssueLinkSchema,
    IssueResponse,
    NoteIssueLinkBriefSchema,
    StateBriefSchema,
    StateUpdateRequest,
    UserBriefSchema,
    WorkspaceIssueCreateRequest,
    WorkspaceIssueResponse,
    WorkspaceIssueUpdateRequest,
)
from pilot_space.dependencies import DbSession, SyncedUserId
from pilot_space.dependencies.auth import SessionDep
from pilot_space.domain.exceptions import (
    ForbiddenError,
    NotFoundError,
    ValidationError as DomainValidationError,
)
from pilot_space.domain.mappers.issue_priority import map_priority_string
from pilot_space.domain.mappers.state_name import normalize_state_name
from pilot_space.infrastructure.database.models.issue import Issue
from pilot_space.infrastructure.database.models.state import State
from pilot_space.infrastructure.database.models.workspace import Workspace
from pilot_space.infrastructure.database.rls import set_rls_context
from pilot_space.infrastructure.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()

# Accept string to support both UUID and slug
WorkspaceIdOrSlug = Annotated[str, Path(description="Workspace ID (UUID) or slug")]
IssueIdPath = Annotated[UUID, Path(description="Issue ID")]


def _is_valid_uuid(value: str) -> bool:
    """Check if a string is a valid UUID."""
    try:
        UUID(value)
        return True
    except ValueError:
        return False


async def _resolve_workspace(
    workspace_id_or_slug: str,
    workspace_repo: WorkspaceRepositoryDep,
) -> Workspace:
    """Resolve workspace by UUID or slug (scalar-only, no relationships).

    Uses lazyload to prevent the Workspace model's 7 default selectin
    relationships from firing. Only scalar columns (id, slug, name, etc.)
    are loaded. Use this for validation/ownership checks.
    """
    if _is_valid_uuid(workspace_id_or_slug):
        workspace = await workspace_repo.get_by_id_scalar(UUID(workspace_id_or_slug))
    else:
        workspace = await workspace_repo.get_by_slug_scalar(workspace_id_or_slug)

    if not workspace:
        raise NotFoundError("Workspace not found")
    return workspace


def _issue_to_response(issue: Issue) -> WorkspaceIssueResponse:
    """Convert Issue model to WorkspaceIssueResponse schema."""
    return WorkspaceIssueResponse(
        id=issue.id,
        workspace_id=issue.workspace_id,
        identifier=issue.identifier or f"ISSUE-{issue.sequence_id}",
        sequence_id=issue.sequence_id or 0,
        name=issue.name,
        description=issue.description,
        description_html=issue.description_html,
        state=StateBriefSchema.model_validate(issue.state),
        priority=issue.priority.value if issue.priority else "none",
        type="task",
        project_id=issue.project_id,
        assignee_id=issue.assignee_id,
        reporter_id=issue.reporter_id,
        cycle_id=issue.cycle_id,
        parent_id=issue.parent_id,
        labels=[],
        target_date=issue.target_date.isoformat() if issue.target_date else None,
        start_date=issue.start_date.isoformat() if issue.start_date else None,
        estimate_hours=float(issue.estimate_hours) if issue.estimate_hours is not None else None,
        estimate_points=issue.estimate_points,
        sort_order=issue.sort_order or 0,
        has_ai_enhancements=issue.has_ai_enhancements,
        sub_issue_count=0,
        created_at=issue.created_at,
        updated_at=issue.updated_at,
    )


@router.get(
    "/{workspace_id}/issues",
    response_model=PaginatedResponse[WorkspaceIssueResponse],
    tags=["workspace-issues"],
    summary="List issues in workspace",
)
async def list_workspace_issues(
    workspace_id: WorkspaceIdOrSlug,
    current_user_id: SyncedUserId,
    list_service: ListIssuesServiceDep,
    workspace_repo: WorkspaceRepositoryDep,
    rbac_svc: ProjectRbacServiceDep,
    session: SessionDep,
    project_id: Annotated[UUID | None, Query(description="Filter by project")] = None,
    state: Annotated[str | None, Query(description="Filter by state")] = None,
    priority: Annotated[str | None, Query(description="Filter by priority")] = None,
    assignee_id: Annotated[UUID | None, Query(description="Filter by assignee")] = None,
    search: Annotated[str | None, Query(description="Search query")] = None,
    cursor: Annotated[str | None, Query(description="Pagination cursor")] = None,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=100)] = 20,
) -> PaginatedResponse[WorkspaceIssueResponse]:
    """List all issues in a workspace."""
    from pilot_space.application.services.issue import ListIssuesPayload

    workspace = await _resolve_workspace(workspace_id, workspace_repo)
    await set_rls_context(session, current_user_id, workspace.id)

    if project_id is not None:
        await rbac_svc.check_project_access(project_id, workspace.id, current_user_id)

    project_ids: list[UUID] | None = None
    if project_id is None:
        project_ids = await rbac_svc.get_my_project_ids(workspace.id, current_user_id)

    payload = ListIssuesPayload(
        workspace_id=workspace.id,
        project_id=project_id,
        project_ids=project_ids,
        assignee_ids=[assignee_id] if assignee_id else None,
        search_term=search,
        cursor=cursor,
        page_size=page_size,
        sort_by="created_at",
        sort_order="desc",
    )

    result = await list_service.execute(payload)
    items = [_issue_to_response(issue) for issue in result.items]

    return PaginatedResponse(
        items=items,
        total=result.total,
        next_cursor=result.next_cursor,
        prev_cursor=result.prev_cursor,
        has_next=result.has_next,
        has_prev=result.has_prev,
        page_size=page_size,
    )


@router.get(
    "/{workspace_id}/issues/{issue_id}",
    response_model=IssueResponse,
    tags=["workspace-issues"],
    summary="Get issue by ID",
)
async def get_workspace_issue(
    session: SessionDep,
    workspace_id: WorkspaceIdOrSlug,
    issue_id: IssueIdPath,
    current_user_id: SyncedUserId,
    get_service: GetIssueServiceDep,
    workspace_repo: WorkspaceRepositoryDep,
    rbac_svc: ProjectRbacServiceDep,
) -> IssueResponse:
    """Get a specific issue by ID."""
    workspace = await _resolve_workspace(workspace_id, workspace_repo)
    await set_rls_context(session, current_user_id, workspace.id)

    result = await get_service.execute(issue_id)
    if not result.found or not result.issue:
        raise NotFoundError("Issue not found")

    if result.issue.workspace_id != workspace.id:
        raise NotFoundError("Issue not found")

    await rbac_svc.check_project_access(result.issue.project_id, workspace.id, current_user_id)

    return IssueResponse.from_issue(result.issue)


@router.get(
    "/{workspace_id}/issues/{issue_id}/notes",
    response_model=list[NoteIssueLinkBriefSchema],
    tags=["workspace-issues"],
    summary="List note links for an issue",
)
async def list_issue_note_links(
    session: SessionDep,
    workspace_id: WorkspaceIdOrSlug,
    issue_id: IssueIdPath,
    current_user_id: SyncedUserId,
    link_repo: NoteIssueLinkRepositoryDep,
    workspace_repo: WorkspaceRepositoryDep,
    issue_repo: IssueRepositoryDep,
) -> list[NoteIssueLinkBriefSchema]:
    """List all notes linked to a specific issue."""
    workspace = await _resolve_workspace(workspace_id, workspace_repo)
    await set_rls_context(session, current_user_id, workspace.id)

    issue = await issue_repo.get_by_id_with_relations(issue_id)
    if issue is None or issue.workspace_id != workspace.id:
        raise NotFoundError("Issue not found")

    links = await link_repo.get_by_issue(issue_id, workspace.id)
    return [
        NoteIssueLinkBriefSchema(
            id=link.id,
            note_id=link.note_id,
            issue_id=link.issue_id,
            link_type=link.link_type.value,
            note_title=link.note.title if link.note else "",
        )
        for link in links
    ]


@router.get(
    "/{workspace_id}/issues/{issue_id}/relations",
    response_model=list[IssueLinkSchema],
    tags=["workspace-issues"],
    summary="List issue-to-issue relations",
)
async def list_issue_relations(
    session: SessionDep,
    workspace_id: WorkspaceIdOrSlug,
    issue_id: IssueIdPath,
    current_user_id: SyncedUserId,
    workspace_repo: WorkspaceRepositoryDep,
    link_repo: IssueLinkRepositoryDep,
) -> list[IssueLinkSchema]:
    """List all issue-to-issue relations (blocks, blocked_by, duplicates, related)."""
    workspace = await _resolve_workspace(workspace_id, workspace_repo)
    await set_rls_context(session, current_user_id, workspace.id)

    # Scalar ownership check: avoid loading full issue relations just to verify workspace membership
    issue_ws_row = await session.execute(
        select(Issue.workspace_id).where(
            Issue.id == issue_id,
            Issue.is_deleted == False,  # noqa: E712
        )
    )
    issue_workspace_id = issue_ws_row.scalar_one_or_none()
    if issue_workspace_id is None or issue_workspace_id != workspace.id:
        raise NotFoundError("Issue not found")

    links = await link_repo.find_all_for_issue(issue_id, workspace.id)
    result: list[IssueLinkSchema] = []
    for link in links:
        rel = link.target_issue if link.source_issue_id == issue_id else link.source_issue
        if rel is None:  # pyright: ignore[reportUnnecessaryComparison]
            continue
        result.append(
            IssueLinkSchema(
                id=link.id,
                link_type=link.link_type.value,
                direction="outbound" if link.source_issue_id == issue_id else "inbound",
                related_issue=IssueBriefResponse(
                    id=rel.id,
                    identifier=rel.identifier,
                    name=rel.name,
                    priority=rel.priority,
                    state=StateBriefSchema.model_validate(rel.state),
                    assignee=UserBriefSchema.model_validate(rel.assignee) if rel.assignee else None,
                ),
            )
        )
    return result


@router.post(
    "/{workspace_id}/issues",
    response_model=IssueResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["workspace-issues"],
    summary="Create a new issue",
)
async def create_workspace_issue(
    workspace_id: WorkspaceIdOrSlug,
    issue_data: WorkspaceIssueCreateRequest,
    current_user_id: SyncedUserId,
    session: DbSession,
    create_service: CreateIssueServiceDep,
    workspace_repo: WorkspaceRepositoryDep,
    response: Response = Response(),
) -> IssueResponse:
    """Create a new issue in the workspace."""
    from pilot_space.application.services.issue import CreateIssuePayload

    workspace = await _resolve_workspace(workspace_id, workspace_repo)
    await set_rls_context(session, current_user_id, workspace.id)

    delta_bytes = len((issue_data.description or "").encode("utf-8"))
    _quota_ok, _warning_pct = await _check_storage_quota(session, workspace.id, delta_bytes)
    if not _quota_ok:
        raise HTTPException(
            status_code=status.HTTP_507_INSUFFICIENT_STORAGE,
            detail="Storage quota exceeded",
        )

    if not issue_data.project_id:
        raise DomainValidationError("project_id is required")

    priority = map_priority_string(issue_data.priority)

    label_uuids: list[UUID] = []
    if issue_data.label_ids:
        try:
            label_uuids = [UUID(label) for label in issue_data.label_ids]
        except ValueError as e:
            raise DomainValidationError(f"Invalid label UUID format: {e}") from e

    payload = CreateIssuePayload(
        workspace_id=workspace.id,
        project_id=issue_data.project_id,
        reporter_id=current_user_id,
        name=issue_data.name,
        description=issue_data.description,
        description_html=issue_data.description_html,
        priority=priority,
        state_id=issue_data.state_id,
        assignee_id=issue_data.assignee_id,
        cycle_id=issue_data.cycle_id,
        module_id=None,
        parent_id=issue_data.parent_id,
        estimate_points=issue_data.estimate_points,
        estimate_hours=issue_data.estimate_hours,
        start_date=issue_data.start_date,
        target_date=issue_data.target_date,
        label_ids=label_uuids,
        ai_enhanced=False,
    )

    result = await create_service.execute(payload)

    try:
        await _update_storage_usage(session, workspace.id, delta_bytes)
    except Exception:
        logger.warning("storage_usage_update_failed", workspace_id=str(workspace.id))
    if _warning_pct is not None:
        response.headers["X-Storage-Warning"] = str(round(_warning_pct, 4))

    logger.info(
        "Issue created",
        extra={"issue_id": str(result.issue.id), "workspace_id": str(workspace.id)},
    )

    return IssueResponse.from_issue(result.issue)


@router.patch(
    "/{workspace_id}/issues/{issue_id}",
    response_model=IssueResponse,
    tags=["workspace-issues"],
    summary="Update an issue",
)
async def update_workspace_issue(
    workspace_id: WorkspaceIdOrSlug,
    issue_id: IssueIdPath,
    issue_data: WorkspaceIssueUpdateRequest,
    current_user_id: SyncedUserId,
    update_service: UpdateIssueServiceDep,
    workspace_repo: WorkspaceRepositoryDep,
    rbac_svc: ProjectRbacServiceDep,
    session: SessionDep,
    response: Response = Response(),
) -> IssueResponse:
    """Update an existing issue."""
    from pilot_space.application.services.issue.update_issue_service import (
        UNCHANGED,
        UpdateIssuePayload,
    )

    workspace = await _resolve_workspace(workspace_id, workspace_repo)
    await set_rls_context(session, current_user_id, workspace.id)

    # Conservative delta: charge full new description size when description is being updated.
    # Avoids an extra round-trip to fetch the old description.
    delta_bytes = len((issue_data.description or "").encode("utf-8"))
    _quota_ok, _warning_pct = await _check_storage_quota(session, workspace.id, delta_bytes)
    if not _quota_ok:
        raise HTTPException(
            status_code=status.HTTP_507_INSUFFICIENT_STORAGE,
            detail="Storage quota exceeded",
        )

    issue_ws_row = await session.execute(select(Issue.workspace_id).where(Issue.id == issue_id))
    issue_workspace_id = issue_ws_row.scalar_one_or_none()
    if issue_workspace_id is None:
        raise NotFoundError("Issue not found")
    if issue_workspace_id != workspace.id:
        raise ForbiddenError("Access denied")

    await rbac_svc.check_resource_permission(current_user_id, workspace.id, "issues", "write")
    issue_project_row = await session.execute(
        select(Issue.project_id).where(Issue.id == issue_id, Issue.is_deleted == False)  # noqa: E712
    )
    issue_project_id = issue_project_row.scalar_one_or_none()
    if issue_project_id:
        await rbac_svc.check_project_access(issue_project_id, workspace.id, current_user_id)

    priority = UNCHANGED
    if issue_data.priority is not None:
        priority = map_priority_string(issue_data.priority)

    from datetime import date as date_type

    start_date_value = UNCHANGED
    if issue_data.clear_start_date:
        start_date_value = None
    elif issue_data.start_date is not None:
        try:
            start_date_value = date_type.fromisoformat(issue_data.start_date)
        except ValueError as e:
            raise DomainValidationError(f"Invalid start_date format: {e}") from e

    target_date_value = UNCHANGED
    if issue_data.clear_target_date:
        target_date_value = None
    elif issue_data.target_date is not None:
        try:
            target_date_value = date_type.fromisoformat(issue_data.target_date)
        except ValueError as e:
            raise DomainValidationError(f"Invalid target_date format: {e}") from e

    payload = UpdateIssuePayload(
        issue_id=issue_id,
        actor_id=current_user_id,
        name=issue_data.name if issue_data.name is not None else UNCHANGED,
        description=issue_data.description if issue_data.description is not None else UNCHANGED,
        description_html=issue_data.description_html
        if issue_data.description_html is not None
        else UNCHANGED,
        priority=priority,
        state_id=issue_data.state_id if issue_data.state_id is not None else UNCHANGED,
        assignee_id=None
        if issue_data.clear_assignee
        else (issue_data.assignee_id if issue_data.assignee_id is not None else UNCHANGED),
        cycle_id=None
        if issue_data.clear_cycle
        else (issue_data.cycle_id if issue_data.cycle_id is not None else UNCHANGED),
        module_id=None
        if issue_data.clear_module
        else (issue_data.module_id if issue_data.module_id is not None else UNCHANGED),
        parent_id=None
        if issue_data.clear_parent
        else (issue_data.parent_id if issue_data.parent_id is not None else UNCHANGED),
        estimate_points=None
        if issue_data.clear_estimate
        else (issue_data.estimate_points if issue_data.estimate_points is not None else UNCHANGED),
        estimate_hours=None
        if issue_data.clear_estimate
        else (issue_data.estimate_hours if issue_data.estimate_hours is not None else UNCHANGED),
        start_date=start_date_value,
        target_date=target_date_value,
        sort_order=issue_data.sort_order if issue_data.sort_order is not None else UNCHANGED,
        label_ids=issue_data.label_ids if issue_data.label_ids is not None else UNCHANGED,
        acceptance_criteria=issue_data.acceptance_criteria
        if issue_data.acceptance_criteria is not None
        else UNCHANGED,
    )

    result = await update_service.execute(payload)

    try:
        await _update_storage_usage(session, workspace.id, delta_bytes)
    except Exception:
        logger.warning("storage_usage_update_failed", workspace_id=str(workspace.id))
    if _warning_pct is not None:
        response.headers["X-Storage-Warning"] = str(round(_warning_pct, 4))

    logger.info(
        "Issue updated",
        extra={"issue_id": str(issue_id), "workspace_id": str(workspace.id)},
    )

    return IssueResponse.from_issue(result.issue)


@router.patch(
    "/{workspace_id}/issues/{issue_id}/state",
    response_model=IssueResponse,
    tags=["workspace-issues"],
    summary="Update issue state",
)
async def update_workspace_issue_state(
    workspace_id: WorkspaceIdOrSlug,
    issue_id: IssueIdPath,
    body: StateUpdateRequest,
    current_user_id: SyncedUserId,
    session: DbSession,
    update_service: UpdateIssueServiceDep,
    workspace_repo: WorkspaceRepositoryDep,
) -> IssueResponse:
    """Update issue state (for Kanban drag/drop)."""
    from pilot_space.application.services.issue.update_issue_service import (
        UNCHANGED,
        UpdateIssuePayload,
    )

    workspace = await _resolve_workspace(workspace_id, workspace_repo)
    await set_rls_context(session, current_user_id, workspace.id)

    issue_ws_row = await session.execute(select(Issue.workspace_id).where(Issue.id == issue_id))
    issue_workspace_id = issue_ws_row.scalar_one_or_none()
    if issue_workspace_id is None:
        raise NotFoundError("Issue not found")
    if issue_workspace_id != workspace.id:
        raise ForbiddenError("Access denied")

    state_name = body.state
    normalized_state = normalize_state_name(state_name)

    state_result = await session.execute(
        select(State)
        .where(
            State.workspace_id == workspace.id,
            State.name == normalized_state,
            State.is_deleted.is_(False),
        )
        .limit(1)
    )
    new_state = state_result.scalar_one_or_none()
    if not new_state:
        raise NotFoundError(f"State '{state_name}' not found")

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

    result = await update_service.execute(payload)

    return IssueResponse.from_issue(result.issue)


@router.delete(
    "/{workspace_id}/issues/{issue_id}",
    response_model=DeleteResponse,
    tags=["workspace-issues"],
    summary="Delete an issue",
)
async def delete_workspace_issue(
    workspace_id: WorkspaceIdOrSlug,
    issue_id: IssueIdPath,
    current_user_id: SyncedUserId,
    delete_service: DeleteIssueServiceDep,
    workspace_repo: WorkspaceRepositoryDep,
    session: SessionDep,
) -> DeleteResponse:
    """Soft delete an issue with activity tracking."""
    from pilot_space.application.services.issue import DeleteIssuePayload

    workspace = await _resolve_workspace(workspace_id, workspace_repo)
    await set_rls_context(session, current_user_id, workspace.id)

    result_row = await session.execute(select(Issue.workspace_id).where(Issue.id == issue_id))
    issue_workspace_id = result_row.scalar_one_or_none()
    if issue_workspace_id is None:
        raise NotFoundError("Issue not found")
    if issue_workspace_id != workspace.id:
        raise ForbiddenError("Access denied")

    result = await delete_service.execute(
        DeleteIssuePayload(
            issue_id=issue_id,
            actor_id=current_user_id,
        )
    )

    logger.info(
        "Issue deleted",
        extra={"issue_id": str(issue_id), "workspace_id": str(workspace.id)},
    )

    return DeleteResponse(id=result.issue_id, message="Issue deleted successfully")


# ============================================================================
# Batch Issue Creation (Phase 75 — CIP-01, CIP-02, CIP-05)
# ============================================================================


@router.post(
    "/{workspace_id}/issues/batch",
    response_model=BatchCreateIssueResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["workspace-issues"],
    summary="Batch create issues from AI proposals",
    description="""
Create multiple issues in a single request. Designed for the chat-to-issue pipeline
where a PM describes work in natural language and the AI generates structured proposals.

Each issue in the request may include:
- `acceptanceCriteria`: structured list of `{criterion, met}` objects (CIP-05)
- `sourceNoteId`: UUID of the note that originated this batch (CIP-02)

Partial failures are handled gracefully — if one issue fails, the others are still
created and the response includes per-issue success/failure details.
""",
    responses={
        201: {"description": "Batch created (may include partial failures)"},
        422: {"description": "Validation error (e.g., empty issues array)"},
    },
)
async def batch_create_issues(
    workspace_id: WorkspaceIdOrSlug,
    request: BatchCreateIssueRequest,
    session: SessionDep,
    current_user_id: SyncedUserId,
    workspace_repo: WorkspaceRepositoryDep,
    rbac_svc: ProjectRbacServiceDep,
    batch_service: BatchCreateIssuesServiceDep,
) -> BatchCreateIssueResponse:
    """Create multiple issues in batch from AI-generated proposals.

    Iterates over the issues array and creates each via CreateIssueService.
    Partial failures (per issue) are captured — the response includes
    per-issue success/failure and aggregate counts.

    Router signature includes `session: SessionDep` per DI ContextVar requirement.
    Service exceptions propagate to the global error handler (no try/except).
    """
    from pilot_space.application.services.issue.batch_create_issues_service import (
        BatchCreateIssuesPayload,
        BatchIssueItemPayload,
    )

    workspace = await _resolve_workspace(workspace_id, workspace_repo)
    await set_rls_context(session, current_user_id, workspace.id)

    # Verify the user has access to the project
    await rbac_svc.check_project_access(request.project_id, workspace.id, current_user_id)

    # Build service payload
    payload = BatchCreateIssuesPayload(
        workspace_id=workspace.id,
        project_id=request.project_id,
        reporter_id=current_user_id,
        issues=[
            BatchIssueItemPayload(
                title=item.title,
                description=item.description,
                acceptance_criteria=item.acceptance_criteria,
                priority=item.priority,
            )
            for item in request.issues
        ],
        source_note_id=request.source_note_id,
    )

    result = await batch_service.execute(payload)

    return BatchCreateIssueResponse(
        results=[
            BatchCreateIssueResult(
                index=r.index,
                success=r.success,
                issue_id=r.issue_id,
                error=r.error,
            )
            for r in result.results
        ],
        created_count=result.created_count,
        failed_count=result.failed_count,
    )


__all__ = ["router"]
