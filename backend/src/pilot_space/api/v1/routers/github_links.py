"""GitHub integration links and PR review endpoints.

T186: Issue-commit and issue-PR linking.
T198: AI-powered PR review trigger.

Split from integrations.py to keep file size under the 700-line limit.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Path, Query, Request, status

from pilot_space.api.v1.schemas.integration import (
    CreateBranchRequest,
    IntegrationLinkResponse,
    IntegrationLinksResponse,
    LinkCommitRequest,
    LinkPullRequestRequest,
)
from pilot_space.api.v1.schemas.pr_review import (
    TriggerReviewRequest,
    TriggerReviewResponse,
)
from pilot_space.application.services.integration import (
    CreateBranchPayload,
    CreateBranchService,
)
from pilot_space.dependencies import CurrentUser, CurrentUserId, DbSession
from pilot_space.domain.exceptions import NotFoundError, ServiceUnavailableError
from pilot_space.infrastructure.database.repositories import (
    ActivityRepository,
    IntegrationLinkRepository,
    IntegrationRepository,
    IssueRepository,
)
from pilot_space.infrastructure.database.rls import set_rls_context
from pilot_space.infrastructure.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/integrations", tags=["integrations"])


# ============================================================================
# Integration Links
# ============================================================================


@router.get(
    "/issues/{issue_id}/links",
    response_model=IntegrationLinksResponse,
    summary="Get issue links",
)
async def get_issue_links(
    session: DbSession,
    current_user: CurrentUser,
    issue_id: Annotated[UUID, Path(description="Issue ID")],
) -> IntegrationLinksResponse:
    """Get all integration links (commits/PRs) for an issue."""
    link_repo = IntegrationLinkRepository(session)
    links = await link_repo.get_by_issue(issue_id)

    return IntegrationLinksResponse(
        items=[IntegrationLinkResponse.model_validate(link) for link in links],
        total=len(links),
    )


@router.post(
    "/issues/{issue_id}/links/commit",
    response_model=IntegrationLinkResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Link commit to issue",
)
async def link_commit_to_issue(
    session: DbSession,
    current_user: CurrentUser,
    current_user_id: CurrentUserId,
    issue_id: Annotated[UUID, Path(description="Issue ID")],
    integration_id: Annotated[UUID, Query(description="Integration ID")],
    request: LinkCommitRequest,
) -> IntegrationLinkResponse:
    """Manually link a commit to an issue."""
    issue_repo = IssueRepository(session)
    issue = await issue_repo.get_by_id_with_relations(issue_id)
    if not issue:
        raise NotFoundError("Issue not found")

    from pilot_space.application.services.integration import LinkCommitPayload, LinkCommitService

    service = LinkCommitService(
        session=session,
        integration_repo=IntegrationRepository(session),
        integration_link_repo=IntegrationLinkRepository(session),
        issue_repo=issue_repo,
        activity_repo=ActivityRepository(session),
    )

    try:
        result = await service.link_commit(
            LinkCommitPayload(
                workspace_id=issue.workspace_id,
                issue_id=issue_id,
                integration_id=integration_id,
                repository=request.repository,
                commit_sha=request.commit_sha,
                actor_id=current_user_id,
            )
        )
    except Exception as e:
        logger.exception("Failed to link commit")
        raise ServiceUnavailableError(str(e)) from e

    await session.commit()
    return IntegrationLinkResponse.model_validate(result.link)


@router.post(
    "/issues/{issue_id}/links/pull-request",
    response_model=IntegrationLinkResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Link PR to issue",
)
async def link_pr_to_issue(
    session: DbSession,
    current_user: CurrentUser,
    current_user_id: CurrentUserId,
    issue_id: Annotated[UUID, Path(description="Issue ID")],
    integration_id: Annotated[UUID, Query(description="Integration ID")],
    request: LinkPullRequestRequest,
) -> IntegrationLinkResponse:
    """Manually link a pull request to an issue."""
    issue_repo = IssueRepository(session)
    issue = await issue_repo.get_by_id_with_relations(issue_id)
    if not issue:
        raise NotFoundError("Issue not found")

    from pilot_space.application.services.integration import (
        LinkCommitService,
        LinkPullRequestPayload,
    )

    service = LinkCommitService(
        session=session,
        integration_repo=IntegrationRepository(session),
        integration_link_repo=IntegrationLinkRepository(session),
        issue_repo=issue_repo,
        activity_repo=ActivityRepository(session),
    )

    try:
        result = await service.link_pull_request(
            LinkPullRequestPayload(
                workspace_id=issue.workspace_id,
                issue_id=issue_id,
                integration_id=integration_id,
                repository=request.repository,
                pr_number=request.pr_number,
                actor_id=current_user_id,
            )
        )
    except Exception as e:
        logger.exception("Failed to link PR")
        raise ServiceUnavailableError(str(e)) from e

    await session.commit()
    return IntegrationLinkResponse.model_validate(result.link)


# ============================================================================
# PR Review (T198)
# ============================================================================


@router.post(
    "/github/{integration_id}/prs/{pr_number}/review",
    response_model=TriggerReviewResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger AI PR Review",
)
async def trigger_pr_review(
    request: Request,
    session: DbSession,
    current_user: CurrentUser,
    current_user_id: CurrentUserId,
    integration_id: Annotated[UUID, Path(description="Integration ID")],
    pr_number: Annotated[int, Path(description="PR number", ge=1)],
    review_request: TriggerReviewRequest,
) -> TriggerReviewResponse:
    """Trigger AI-powered PR review.

    Enqueues a PR review job for async processing. The review covers:
    - Architecture (SOLID principles, layer separation)
    - Security (OWASP Top 10, auth, input validation)
    - Code quality (readability, naming, error handling)
    - Performance (N+1 queries, blocking I/O)
    - Documentation (docstrings, comments)

    For large PRs (>5000 lines or >50 files), only priority files are reviewed.

    Returns:
        Job status with job_id for polling.
    """
    integration_repo = IntegrationRepository(session)
    integration = await integration_repo.get_by_id(integration_id)

    if not integration:
        raise NotFoundError("Integration not found")

    workspace_id = integration.workspace_id
    correlation_id = request.headers.get("X-Correlation-ID", "")

    from pilot_space.application.services.ai import TriggerPRReviewPayload, TriggerPRReviewService
    from pilot_space.container import get_container

    container = get_container()
    queue_client = container.queue_client()

    if not queue_client:
        raise ServiceUnavailableError("Queue service not configured")

    service = TriggerPRReviewService(
        session=session,
        queue_client=queue_client,
        integration_repo=integration_repo,
        cache_client=container.redis_client() if container.redis_client else None,
    )
    result = await service.execute(
        TriggerPRReviewPayload(
            workspace_id=workspace_id,
            integration_id=integration_id,
            repository=review_request.repository,
            pr_number=pr_number,
            user_id=current_user_id,
            correlation_id=correlation_id,
            post_comments=review_request.post_comments,
            post_summary=review_request.post_summary,
            project_context=review_request.project_context,
        )
    )

    return TriggerReviewResponse(
        job_id=result.job_id,
        status=result.status.value,
        queued_at=result.queued_at,
        estimated_wait_minutes=result.estimated_wait_minutes,
        message=result.message,
    )


# ============================================================================
# Branch Creation
# ============================================================================
# NOTE: GET /issues/{issue_id}/branch-name lives in workspace_issue_branches.py
# (registered under /workspaces prefix) to satisfy the frontend URL contract and
# to enforce workspace-scoped RLS. See C-1/C-2 in validator findings.


@router.post(
    "/issues/{issue_id}/links/branch",
    response_model=IntegrationLinkResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create GitHub branch and link to issue",
)
async def create_branch_for_issue(
    session: DbSession,
    current_user: CurrentUser,
    current_user_id: CurrentUserId,
    issue_id: Annotated[UUID, Path(description="Issue ID")],
    integration_id: Annotated[UUID, Query(description="Integration ID")],
    request: CreateBranchRequest,
) -> IntegrationLinkResponse:
    """Create a GitHub branch and link it to an issue.

    Derives workspace context from the integration to enforce RLS before
    querying the issue, preventing cross-workspace data access.
    """
    # Resolve integration first — its workspace_id is the RLS anchor.
    integration_repo = IntegrationRepository(session)
    integration = await integration_repo.get_by_id(integration_id)
    if not integration:
        raise NotFoundError("Integration not found")

    # Enforce RLS: user must belong to the integration's workspace.
    await set_rls_context(session, current_user_id, integration.workspace_id)

    issue_repo = IssueRepository(session)
    issue = await issue_repo.get_by_id_with_relations(issue_id)
    if not issue:
        raise NotFoundError("Issue not found")
    if issue.workspace_id != integration.workspace_id:
        raise NotFoundError("Issue not found")

    service = CreateBranchService(
        session=session,
        integration_repo=integration_repo,
        integration_link_repo=IntegrationLinkRepository(session),
        issue_repo=issue_repo,
        activity_repo=ActivityRepository(session),
    )

    result = await service.execute(
        CreateBranchPayload(
            workspace_id=issue.workspace_id,
            issue_id=issue_id,
            integration_id=integration_id,
            repository=request.repository,
            branch_name=request.branch_name,
            base_branch=request.base_branch,
            actor_id=current_user_id,
        )
    )

    await session.commit()
    return IntegrationLinkResponse.model_validate(result.link)


__all__ = ["router"]
