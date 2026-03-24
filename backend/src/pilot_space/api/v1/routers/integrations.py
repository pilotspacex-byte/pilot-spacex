"""Integrations API router.

T186: Create integrations router for GitHub OAuth and management.
T198: Add PR review trigger endpoint.
"""

from __future__ import annotations

import secrets
from typing import TYPE_CHECKING, Annotated
from uuid import UUID

from pilot_space.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import APIRouter, Path, Query, status

from pilot_space.api.v1.schemas.integration import (
    ConnectGitHubResponse,
    GitHubOAuthCallbackRequest,
    GitHubOAuthUrlResponse,
    GitHubRepositoriesResponse,
    GitHubRepositoryResponse,
    IntegrationListResponse,
    IntegrationResponse,
    WebhookSetupResponse,
)
from pilot_space.config import get_settings
from pilot_space.dependencies import CurrentUser, CurrentUserId, DbSession
from pilot_space.domain.exceptions import (
    NotFoundError,
    ServiceUnavailableError,
    ValidationError as DomainValidationError,
)
from pilot_space.infrastructure.database.models import IntegrationProvider
from pilot_space.infrastructure.database.repositories import (
    IntegrationRepository,
    WorkspaceRepository,
)
from pilot_space.infrastructure.encryption import decrypt_api_key

logger = get_logger(__name__)

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
        NotFoundError: If workspace not found.
    """
    workspace_repo = WorkspaceRepository(session)

    if _is_valid_uuid(workspace_id_or_slug):
        workspace = await workspace_repo.get_by_id(UUID(workspace_id_or_slug))
    else:
        workspace = await workspace_repo.get_by_slug(workspace_id_or_slug)

    if not workspace:
        raise NotFoundError("Workspace not found")

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
        raise NotFoundError("Integration not found")

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
        raise NotFoundError("Integration not found")

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
        raise ServiceUnavailableError("GitHub integration not configured")

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
        raise ServiceUnavailableError("GitHub integration not configured")

    # Parse workspace_id from state
    if not request.state:
        raise DomainValidationError("Missing state parameter")

    try:
        workspace_id = UUID(request.state.split(":")[0])
    except (ValueError, IndexError) as e:
        raise DomainValidationError("Invalid state parameter") from e

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
        raise ServiceUnavailableError(str(e)) from e

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
        raise NotFoundError("Integration not found")

    if integration.provider != IntegrationProvider.GITHUB:
        raise DomainValidationError("Not a GitHub integration")

    if not integration.is_active:
        raise DomainValidationError("Integration is not active")

    from pilot_space.integrations.github import GitHubClient

    access_token = decrypt_api_key(integration.access_token)
    async with GitHubClient(access_token) as client:
        try:
            repos = await client.get_repos()
        except Exception as e:
            logger.exception("Failed to fetch repos")
            raise ServiceUnavailableError(f"Failed to fetch repositories: {e}") from e

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
        raise NotFoundError("Integration not found")

    if not settings.github_webhook_secret:
        raise ServiceUnavailableError("Webhook secret not configured")

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
            raise ServiceUnavailableError(f"Failed to create webhook: {e}") from e

    return WebhookSetupResponse(
        hook_id=hook["id"],
        active=hook.get("active", True),
        events=hook.get("events", []),
    )


# ============================================================================
# Workspace-Scoped GitHub Shortcuts (C-6, C-7)
# Frontend calls workspace-scoped URLs; these resolve the active integration first.
# ============================================================================


@router.get(
    "/workspaces/{workspace_id}/github/repositories",
    response_model=GitHubRepositoriesResponse,
    summary="List GitHub repositories for workspace",
    tags=["integrations"],
)
async def list_workspace_github_repos(
    session: DbSession,
    current_user: CurrentUser,
    workspace_id: Annotated[str, Path(description="Workspace ID or slug")],
) -> GitHubRepositoriesResponse:
    """List GitHub repos for the active integration of a workspace."""
    resolved_id = await _resolve_workspace_id(workspace_id, session)
    repo = IntegrationRepository(session)
    integration = await repo.get_active_github(resolved_id)

    if not integration:
        raise NotFoundError("No active GitHub integration found for this workspace")

    from pilot_space.integrations.github import GitHubClient

    access_token = decrypt_api_key(integration.access_token)
    async with GitHubClient(access_token) as client:
        try:
            repos = await client.get_repos()
        except Exception as e:
            logger.exception("Failed to fetch repos for workspace %s", workspace_id)
            raise ServiceUnavailableError(f"Failed to fetch repositories: {e}") from e

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


@router.delete(
    "/workspaces/{workspace_id}/github",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Disconnect GitHub integration for workspace",
    tags=["integrations"],
)
async def disconnect_workspace_github(
    session: DbSession,
    current_user: CurrentUser,
    workspace_id: Annotated[str, Path(description="Workspace ID or slug")],
) -> None:
    """Deactivate the active GitHub integration for a workspace."""
    resolved_id = await _resolve_workspace_id(workspace_id, session)
    repo = IntegrationRepository(session)
    integration = await repo.get_active_github(resolved_id)

    if not integration:
        raise NotFoundError("No active GitHub integration found for this workspace")

    await repo.deactivate(integration.id)
    await session.commit()

    logger.info(
        "GitHub integration disconnected via workspace route",
        extra={"workspace_id": str(resolved_id), "integration_id": str(integration.id)},
    )


__all__ = ["router"]
