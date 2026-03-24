"""Git proxy router.

Backend proxy for GitHub/GitLab git operations. All git operations go through
the backend to avoid CORS issues, token exposure, and centralize rate limiting.
Frontend calls /api/v1/git/... which proxies to the correct provider.
"""

from __future__ import annotations

from typing import Annotated, NoReturn
from uuid import UUID

from fastapi import APIRouter, HTTPException, Path, Query, Response, status

from pilot_space.api.v1.schemas.git_proxy import (
    BranchListResponse,
    BranchSchema,
    ChangedFileSchema,
    CommitRequest,
    CommitResponse,
    CreateBranchRequest,
    CreatePRRequest,
    CreatePRResponse,
    FileContentResponse,
    GitStatusResponse,
)
from pilot_space.application.services.git_provider import (
    FileChange,
    GitProvider,
    resolve_provider,
)
from pilot_space.dependencies import CurrentUser, DbSession
from pilot_space.infrastructure.database.repositories import IntegrationRepository
from pilot_space.infrastructure.encryption import decrypt_api_key
from pilot_space.infrastructure.logging import get_logger
from pilot_space.integrations.github.exceptions import (
    GitHubAPIError,
    GitHubAuthError,
    GitHubRateLimitError,
)
from pilot_space.integrations.gitlab.exceptions import (
    GitLabAPIError,
    GitLabAuthError,
    GitLabRateLimitError,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/git", tags=["git-proxy"])

# 1 MB size guard for file content
_MAX_FILE_SIZE = 1_048_576

# GitHub returns at most 300 files in a compare response
_GITHUB_MAX_FILES = 300

# Provider types supported for git proxy
_SUPPORTED_PROVIDERS = {"github", "gitlab"}


# ============================================================================
# Helpers
# ============================================================================


async def _get_provider(
    session: DbSession,
    current_user: CurrentUser,
    integration_id: UUID,
) -> GitProvider:
    """Load integration from DB, decrypt token, return a GitProvider.

    Args:
        session: Database session.
        current_user: Authenticated user.
        integration_id: Integration UUID.

    Returns:
        GitProvider instance for the integration's provider type.

    Raises:
        HTTPException: If integration not found or inactive.
    """
    repo = IntegrationRepository(session)
    integration = await repo.get_by_id(integration_id)

    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integration not found",
        )

    if not integration.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Integration is not active",
        )

    access_token = decrypt_api_key(integration.access_token)

    # IntegrationProvider is a StrEnum; .value gives "github", "slack", etc.
    provider_type = str(integration.provider.value)
    if provider_type not in _SUPPORTED_PROVIDERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported provider: {integration.provider}",
        )

    return resolve_provider(provider_type, access_token)


def _handle_provider_error(exc: Exception) -> NoReturn:
    """Map provider exceptions to HTTP responses.

    Always raises -- NoReturn tells pyright variables after try/except are bound.

    Raises:
        HTTPException: Mapped from the provider exception.
    """
    if isinstance(exc, (GitHubRateLimitError, GitLabRateLimitError)):
        headers: dict[str, str] = {}
        if isinstance(exc, GitHubRateLimitError):
            headers["Retry-After"] = str(int(exc.reset_at.timestamp()))
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(exc),
            headers=headers or None,
        )

    if isinstance(exc, (GitHubAuthError, GitLabAuthError)):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        )

    if isinstance(exc, (GitHubAPIError, GitLabAPIError)):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        )

    raise exc


# ============================================================================
# Endpoints
# ============================================================================


@router.get(
    "/repos/{owner}/{repo}/status",
    response_model=GitStatusResponse,
    summary="Get changed files between refs",
)
async def get_status(
    session: DbSession,
    current_user: CurrentUser,
    owner: Annotated[str, Path(description="Repository owner")],
    repo: Annotated[str, Path(description="Repository name")],
    branch: Annotated[str, Query(description="Head ref (branch or SHA)")],
    base_ref: Annotated[str, Query(description="Base ref to compare against")],
    integration_id: Annotated[UUID, Query(description="Integration ID")],
) -> GitStatusResponse:
    """Get files changed between two refs."""
    provider = await _get_provider(session, current_user, integration_id)

    try:
        files = await provider.get_changed_files(owner, repo, branch, base_ref)
    except Exception as exc:
        _handle_provider_error(exc)

    truncated = len(files) >= _GITHUB_MAX_FILES
    return GitStatusResponse(
        files=[
            ChangedFileSchema(
                path=f.path,
                status=f.status,
                additions=f.additions,
                deletions=f.deletions,
                patch=f.patch,
            )
            for f in files
        ],
        branch=branch,
        total_files=len(files),
        truncated=truncated,
    )


@router.get(
    "/repos/{owner}/{repo}/files/{path:path}",
    response_model=FileContentResponse,
    summary="Get file content at a ref",
)
async def get_file_content(
    session: DbSession,
    current_user: CurrentUser,
    owner: Annotated[str, Path(description="Repository owner")],
    repo: Annotated[str, Path(description="Repository name")],
    path: Annotated[str, Path(description="File path")],
    ref: Annotated[str, Query(description="Branch name or commit SHA")],
    integration_id: Annotated[UUID, Query(description="Integration ID")],
) -> FileContentResponse:
    """Get file content at a specific ref."""
    provider = await _get_provider(session, current_user, integration_id)

    try:
        content = await provider.get_file_content(owner, repo, path, ref)
    except Exception as exc:
        _handle_provider_error(exc)

    # 1MB size guard (Pitfall 7)
    content_bytes = len(content.encode("utf-8"))
    if content_bytes > _MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File too large",
        )

    return FileContentResponse(
        content=content,
        encoding="utf-8",
        size=content_bytes,
    )


@router.get(
    "/repos/{owner}/{repo}/branches",
    response_model=BranchListResponse,
    summary="List branches",
)
async def list_branches(
    session: DbSession,
    current_user: CurrentUser,
    owner: Annotated[str, Path(description="Repository owner")],
    repo: Annotated[str, Path(description="Repository name")],
    integration_id: Annotated[UUID, Query(description="Integration ID")],
    search: Annotated[str | None, Query(description="Search filter")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=100)] = 30,
) -> BranchListResponse:
    """List branches in a repository."""
    provider = await _get_provider(session, current_user, integration_id)

    try:
        branches = await provider.list_branches(
            owner, repo, search=search, page=page, per_page=per_page
        )
    except Exception as exc:
        _handle_provider_error(exc)

    return BranchListResponse(
        branches=[
            BranchSchema(
                name=b.name,
                sha=b.sha,
                is_default=b.is_default,
                is_protected=b.is_protected,
            )
            for b in branches
        ],
        page=page,
        per_page=per_page,
    )


@router.post(
    "/repos/{owner}/{repo}/branches",
    response_model=BranchSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create a branch",
)
async def create_branch(
    session: DbSession,
    current_user: CurrentUser,
    owner: Annotated[str, Path(description="Repository owner")],
    repo: Annotated[str, Path(description="Repository name")],
    integration_id: Annotated[UUID, Query(description="Integration ID")],
    body: CreateBranchRequest,
) -> BranchSchema:
    """Create a new branch from a ref."""
    provider = await _get_provider(session, current_user, integration_id)

    try:
        branch_info = await provider.create_branch(owner, repo, body.name, body.from_ref)
    except Exception as exc:
        _handle_provider_error(exc)

    return BranchSchema(
        name=branch_info.name,
        sha=branch_info.sha,
        is_default=branch_info.is_default,
        is_protected=branch_info.is_protected,
    )


@router.delete(
    "/repos/{owner}/{repo}/branches/{branch_name}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a branch",
)
async def delete_branch(
    session: DbSession,
    current_user: CurrentUser,
    owner: Annotated[str, Path(description="Repository owner")],
    repo: Annotated[str, Path(description="Repository name")],
    branch_name: Annotated[str, Path(description="Branch name")],
    integration_id: Annotated[UUID, Query(description="Integration ID")],
) -> Response:
    """Delete a branch."""
    provider = await _get_provider(session, current_user, integration_id)

    try:
        await provider.delete_branch(owner, repo, branch_name)
    except Exception as exc:
        _handle_provider_error(exc)

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/repos/{owner}/{repo}/default-branch",
    summary="Get default branch",
)
async def get_default_branch(
    session: DbSession,
    current_user: CurrentUser,
    owner: Annotated[str, Path(description="Repository owner")],
    repo: Annotated[str, Path(description="Repository name")],
    integration_id: Annotated[UUID, Query(description="Integration ID")],
) -> dict[str, str]:
    """Get the default branch name for a repository."""
    provider = await _get_provider(session, current_user, integration_id)

    try:
        default_branch = await provider.get_default_branch(owner, repo)
    except Exception as exc:
        _handle_provider_error(exc)

    return {"default_branch": default_branch}


@router.post(
    "/repos/{owner}/{repo}/commits",
    response_model=CommitResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a commit",
)
async def create_commit(
    session: DbSession,
    current_user: CurrentUser,
    owner: Annotated[str, Path(description="Repository owner")],
    repo: Annotated[str, Path(description="Repository name")],
    integration_id: Annotated[UUID, Query(description="Integration ID")],
    body: CommitRequest,
) -> CommitResponse:
    """Create a commit with file changes."""
    provider = await _get_provider(session, current_user, integration_id)

    file_changes = [
        FileChange(
            path=f.path,
            content=f.content,
            encoding=f.encoding,
            action=f.action,
        )
        for f in body.files
    ]

    try:
        result = await provider.create_commit(owner, repo, body.branch, body.message, file_changes)
    except Exception as exc:
        _handle_provider_error(exc)

    return CommitResponse(
        sha=result.sha,
        html_url=result.html_url,
        message=result.message,
    )


@router.post(
    "/repos/{owner}/{repo}/pulls",
    response_model=CreatePRResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a pull request",
)
async def create_pull_request(
    session: DbSession,
    current_user: CurrentUser,
    owner: Annotated[str, Path(description="Repository owner")],
    repo: Annotated[str, Path(description="Repository name")],
    integration_id: Annotated[UUID, Query(description="Integration ID")],
    body: CreatePRRequest,
) -> CreatePRResponse:
    """Create a pull/merge request."""
    provider = await _get_provider(session, current_user, integration_id)

    try:
        result = await provider.create_pull_request(
            owner, repo, body.title, body.body, body.head, body.base, draft=body.draft
        )
    except Exception as exc:
        _handle_provider_error(exc)

    return CreatePRResponse(
        number=result.number,
        html_url=result.html_url,
        title=result.title,
        draft=result.draft,
    )


__all__ = ["router"]
