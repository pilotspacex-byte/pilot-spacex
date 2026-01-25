"""Integrations API router.

T186: Create integrations router for GitHub OAuth and management.
T198: Add PR review trigger endpoint.
"""

from __future__ import annotations

import logging
import secrets
from typing import TYPE_CHECKING, Annotated
from uuid import UUID

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import APIRouter, HTTPException, Path, Query, Request, status

from pilot_space.api.v1.schemas.integration import (
    ConnectGitHubResponse,
    GitHubOAuthCallbackRequest,
    GitHubOAuthUrlResponse,
    GitHubRepositoriesResponse,
    GitHubRepositoryResponse,
    IntegrationLinkResponse,
    IntegrationLinksResponse,
    IntegrationListResponse,
    IntegrationResponse,
    LinkCommitRequest,
    LinkPullRequestRequest,
    WebhookSetupResponse,
)
from pilot_space.api.v1.schemas.pr_review import (
    TriggerReviewRequest,
    TriggerReviewResponse,
)
from pilot_space.config import get_settings
from pilot_space.dependencies import CurrentUser, CurrentUserId, DbSession
from pilot_space.infrastructure.database.models import IntegrationProvider
from pilot_space.infrastructure.database.repositories import (
    ActivityRepository,
    IntegrationLinkRepository,
    IntegrationRepository,
    IssueRepository,
    WorkspaceRepository,
)
from pilot_space.infrastructure.encryption import decrypt_api_key

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/integrations", tags=["integrations"])


# ============================================================================
# Workspace Resolution Helpers
# ============================================================================


def _is_valid_uuid(value: str) -> bool:
    """Check if a string is a valid UUID."""
    try:
        UUID(value)
        return True
    except ValueError:
        return False


async def _resolve_workspace_id(
    workspace_id_or_slug: str,
    session: AsyncSession,
) -> UUID:
    """Resolve a workspace identifier (UUID or slug) to a UUID.

    Args:
        workspace_id_or_slug: Either a UUID string or a workspace slug.
        session: Database session.

    Returns:
        The workspace UUID.

    Raises:
        HTTPException: If workspace not found.
    """
    workspace_repo = WorkspaceRepository(session)

    if _is_valid_uuid(workspace_id_or_slug):
        workspace = await workspace_repo.get_by_id(UUID(workspace_id_or_slug))
    else:
        workspace = await workspace_repo.get_by_slug(workspace_id_or_slug)

    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )

    return workspace.id


# ============================================================================
# List / Get Integrations
# ============================================================================


@router.get(
    "",
    response_model=IntegrationListResponse,
    summary="List integrations",
)
async def list_integrations(
    session: DbSession,
    current_user: CurrentUser,
    workspace_id: Annotated[str, Query(description="Workspace ID or slug")],
) -> IntegrationListResponse:
    """List all integrations for a workspace."""
    resolved_workspace_id = await _resolve_workspace_id(workspace_id, session)

    repo = IntegrationRepository(session)
    integrations = await repo.get_by_workspace(resolved_workspace_id)

    return IntegrationListResponse(
        items=[IntegrationResponse.from_integration(i) for i in integrations],
        total=len(integrations),
    )


@router.get(
    "/{integration_id}",
    response_model=IntegrationResponse,
    summary="Get integration",
)
async def get_integration(
    session: DbSession,
    current_user: CurrentUser,
    integration_id: Annotated[UUID, Path(description="Integration ID")],
) -> IntegrationResponse:
    """Get a specific integration."""
    repo = IntegrationRepository(session)
    integration = await repo.get_by_id(integration_id)

    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integration not found",
        )

    return IntegrationResponse.from_integration(integration)


@router.delete(
    "/{integration_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Disconnect integration",
)
async def disconnect_integration(
    session: DbSession,
    current_user: CurrentUser,
    integration_id: Annotated[UUID, Path(description="Integration ID")],
) -> None:
    """Disconnect (deactivate) an integration."""
    repo = IntegrationRepository(session)
    integration = await repo.get_by_id(integration_id)

    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integration not found",
        )

    await repo.deactivate(integration_id)
    await session.commit()

    logger.info(
        "Integration disconnected",
        extra={"integration_id": str(integration_id)},
    )


# ============================================================================
# GitHub OAuth
# ============================================================================


@router.get(
    "/github/authorize",
    response_model=GitHubOAuthUrlResponse,
    summary="Get GitHub OAuth URL",
)
async def get_github_authorize_url(
    session: DbSession,
    current_user: CurrentUser,
    workspace_id: Annotated[str, Query(description="Workspace ID or slug")],
) -> GitHubOAuthUrlResponse:
    """Generate GitHub OAuth authorization URL.

    The returned URL should be opened in a browser to start the OAuth flow.
    """
    settings = get_settings()

    if not settings.github_client_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GitHub integration not configured",
        )

    # Resolve workspace ID from slug if needed
    resolved_workspace_id = await _resolve_workspace_id(workspace_id, session)

    # Generate CSRF state
    state = f"{resolved_workspace_id}:{secrets.token_urlsafe(16)}"

    from pilot_space.integrations.github import GitHubClient

    authorize_url = GitHubClient.get_authorize_url(
        client_id=settings.github_client_id,
        redirect_uri=settings.github_callback_url,
        state=state,
    )

    return GitHubOAuthUrlResponse(
        authorize_url=authorize_url,
        state=state,
    )


@router.post(
    "/github/callback",
    response_model=ConnectGitHubResponse,
    summary="Complete GitHub OAuth",
)
async def github_oauth_callback(
    session: DbSession,
    current_user: CurrentUser,
    current_user_id: CurrentUserId,
    request: GitHubOAuthCallbackRequest,
) -> ConnectGitHubResponse:
    """Complete GitHub OAuth flow and create integration.

    This endpoint receives the OAuth code from GitHub callback
    and exchanges it for an access token.
    """
    settings = get_settings()

    if not settings.github_client_id or not settings.github_client_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GitHub integration not configured",
        )

    # Parse workspace_id from state
    if not request.state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing state parameter",
        )

    try:
        workspace_id = UUID(request.state.split(":")[0])
    except (ValueError, IndexError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid state parameter",
        ) from e

    from pilot_space.application.services.integration import (
        ConnectGitHubPayload,
        ConnectGitHubService,
    )

    service = ConnectGitHubService(
        session=session,
        integration_repo=IntegrationRepository(session),
    )

    try:
        result = await service.execute(
            ConnectGitHubPayload(
                workspace_id=workspace_id,
                code=request.code,
                user_id=current_user_id,
                client_id=settings.github_client_id,
                client_secret=settings.github_client_secret.get_secret_value(),
                redirect_uri=settings.github_callback_url,
            )
        )
    except Exception as e:
        logger.exception("GitHub OAuth failed")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    await session.commit()

    return ConnectGitHubResponse(
        integration=IntegrationResponse.from_integration(result.integration),
        github_login=result.github_login,
        github_name=result.github_name,
        github_avatar_url=result.github_avatar_url,
    )


# ============================================================================
# GitHub Repositories
# ============================================================================


@router.get(
    "/github/{integration_id}/repos",
    response_model=GitHubRepositoriesResponse,
    summary="List GitHub repositories",
)
async def list_github_repos(
    session: DbSession,
    current_user: CurrentUser,
    integration_id: Annotated[UUID, Path(description="Integration ID")],
) -> GitHubRepositoriesResponse:
    """List repositories accessible via the GitHub integration."""
    repo = IntegrationRepository(session)
    integration = await repo.get_by_id(integration_id)

    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integration not found",
        )

    if integration.provider != IntegrationProvider.GITHUB:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Not a GitHub integration",
        )

    if not integration.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Integration is not active",
        )

    from pilot_space.integrations.github import GitHubClient

    access_token = decrypt_api_key(integration.access_token)
    async with GitHubClient(access_token) as client:
        try:
            repos = await client.get_repos()
        except Exception as e:
            logger.exception("Failed to fetch repos")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to fetch repositories: {e}",
            ) from e

    return GitHubRepositoriesResponse(
        items=[
            GitHubRepositoryResponse(
                id=r.id,
                name=r.name,
                full_name=r.full_name,
                private=r.private,
                default_branch=r.default_branch,
                description=r.description,
                html_url=r.html_url,
            )
            for r in repos
        ],
        total=len(repos),
    )


@router.post(
    "/github/{integration_id}/repos/{owner}/{repo}/webhook",
    response_model=WebhookSetupResponse,
    summary="Setup webhook",
)
async def setup_github_webhook(
    session: DbSession,
    current_user: CurrentUser,
    integration_id: Annotated[UUID, Path(description="Integration ID")],
    owner: Annotated[str, Path(description="Repository owner")],
    repo: Annotated[str, Path(description="Repository name")],
) -> WebhookSetupResponse:
    """Setup a webhook on a GitHub repository."""
    settings = get_settings()
    integration_repo = IntegrationRepository(session)
    integration = await integration_repo.get_by_id(integration_id)

    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integration not found",
        )

    if not settings.github_webhook_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Webhook secret not configured",
        )

    # Determine webhook URL
    webhook_url = f"{settings.supabase_url.rstrip('/')}/api/v1/webhooks/github"

    from pilot_space.integrations.github import GitHubClient

    access_token = decrypt_api_key(integration.access_token)
    async with GitHubClient(access_token) as client:
        try:
            hook = await client.create_webhook(
                owner=owner,
                repo=repo,
                webhook_url=webhook_url,
                webhook_secret=settings.github_webhook_secret.get_secret_value(),
            )
        except Exception as e:
            logger.exception("Failed to create webhook")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to create webhook: {e}",
            ) from e

    return WebhookSetupResponse(
        hook_id=hook["id"],
        active=hook.get("active", True),
        events=hook.get("events", []),
    )


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
    # Get issue for workspace_id
    issue_repo = IssueRepository(session)
    issue = await issue_repo.get_by_id_with_relations(issue_id)
    if not issue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Issue not found",
        )

    from pilot_space.application.services.integration import (
        LinkCommitPayload,
        LinkCommitService,
    )

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
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

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
    # Get issue for workspace_id
    issue_repo = IssueRepository(session)
    issue = await issue_repo.get_by_id_with_relations(issue_id)
    if not issue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Issue not found",
        )

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
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

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
    # Get workspace from integration
    integration_repo = IntegrationRepository(session)
    integration = await integration_repo.get_by_id(integration_id)

    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integration not found",
        )

    workspace_id = integration.workspace_id

    # Get correlation ID from request headers
    correlation_id = request.headers.get("X-Correlation-ID", "")

    from pilot_space.application.services.ai import (
        TriggerPRReviewPayload,
        TriggerPRReviewService,
    )
    from pilot_space.container import get_container

    container = get_container()
    queue_client = container.queue_client()

    if not queue_client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Queue service not configured",
        )

    try:
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
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.exception("Failed to trigger PR review")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to trigger PR review",
        ) from e

    return TriggerReviewResponse(
        job_id=result.job_id,
        status=result.status.value,
        queued_at=result.queued_at,
        estimated_wait_minutes=result.estimated_wait_minutes,
        message=result.message,
    )


__all__ = ["router"]
