"""Git proxy router.

Backend proxy for GitHub/GitLab git operations. All git operations go through
the backend to avoid CORS issues, token exposure, and to centralize rate limiting.

Frontend calls /api/v1/workspaces/{workspace_id}/git/... which proxies to the
correct provider. The workspace_id path parameter is used to verify that the
requested integration belongs to the calling user's workspace (tenant isolation).

No DI factory is required — GitHubGitProvider is constructed inline per-request
from the decrypted OAuth token in the integration record.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Path, Query, Response, status

from pilot_space.api.v1.schemas.git_proxy import (
    BranchInfo,
    BranchListResponse,
    ChangedFileSchema,
    CommitRequest,
    CommitResponse,
    CreateBranchRequest,
    CreatePRRequest,
    FileContentResponse,
    PRResponse,
    RepoStatusResponse,
)
from pilot_space.application.services.git_provider import (
    FileChange,
    GitHubGitProvider,
    GitProvider,
)
from pilot_space.dependencies import CurrentUser, DbSession
from pilot_space.domain.exceptions import AppError, NotFoundError, ValidationError
from pilot_space.infrastructure.database.models import IntegrationProvider
from pilot_space.infrastructure.database.repositories import IntegrationRepository
from pilot_space.infrastructure.encryption import decrypt_api_key
from pilot_space.infrastructure.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()

# 1 MB size guard for file content responses
_MAX_FILE_SIZE = 1_048_576

# GitHub returns at most 300 files in a compare response
_MAX_COMPARE_FILES = 300


# ============================================================================
# Helpers
# ============================================================================


async def _get_provider(
    session: DbSession,
    workspace_id: UUID,
    owner: str,
    repo: str,
) -> GitProvider:
    """Load the GitHub integration for the workspace and return a GitProvider.

    Verifies that the integration belongs to the requested workspace to
    prevent cross-tenant token access.

    Args:
        session: Database session (request-scoped).
        workspace_id: Workspace UUID from URL path.
        owner: GitHub repository owner.
        repo: GitHub repository name.

    Returns:
        GitHubGitProvider instance ready to use.

    Raises:
        NotFoundError: If no active GitHub integration is found for the workspace.
        AppError: If the integration is inactive.
    """
    repo_instance = IntegrationRepository(session)
    integration = await repo_instance.get_by_provider(workspace_id, IntegrationProvider.GITHUB)

    if not integration:
        raise NotFoundError("GitHub integration not found for this workspace")

    if not integration.is_active:
        raise AppError("GitHub integration is not active")

    # Extra tenant isolation guard — belt-and-suspenders
    if integration.workspace_id != workspace_id:
        raise NotFoundError("GitHub integration not found for this workspace")

    access_token = decrypt_api_key(integration.access_token)
    return GitHubGitProvider(token=access_token, owner=owner, repo=repo)


# ============================================================================
# Endpoints
# ============================================================================


@router.get(
    "/repos/{owner}/{repo}/branches",
    response_model=BranchListResponse,
    summary="List branches",
)
async def list_branches(
    session: DbSession,
    current_user: CurrentUser,
    workspace_id: Annotated[UUID, Path(description="Workspace ID")],
    owner: Annotated[str, Path(description="Repository owner")],
    repo: Annotated[str, Path(description="Repository name")],
) -> BranchListResponse:
    """List branches in a GitHub repository."""
    provider = await _get_provider(session, workspace_id, owner, repo)
    try:
        branches = await provider.get_branches()
        return BranchListResponse(
            branches=[
                BranchInfo(
                    name=b.name,
                    sha=b.sha,
                    is_default=b.is_default,
                    is_protected=b.is_protected,
                )
                for b in branches
            ],
            total=len(branches),
        )
    finally:
        await provider.aclose()


@router.post(
    "/repos/{owner}/{repo}/branches",
    response_model=BranchInfo,
    status_code=status.HTTP_201_CREATED,
    summary="Create a branch",
)
async def create_branch(
    session: DbSession,
    current_user: CurrentUser,
    workspace_id: Annotated[UUID, Path(description="Workspace ID")],
    owner: Annotated[str, Path(description="Repository owner")],
    repo: Annotated[str, Path(description="Repository name")],
    body: CreateBranchRequest,
) -> BranchInfo:
    """Create a new branch from a source branch."""
    provider = await _get_provider(session, workspace_id, owner, repo)
    try:
        branch_info = await provider.create_branch(body.name, body.source_branch)
        return BranchInfo(
            name=branch_info.name,
            sha=branch_info.sha,
            is_default=branch_info.is_default,
            is_protected=branch_info.is_protected,
        )
    finally:
        await provider.aclose()


@router.delete(
    "/repos/{owner}/{repo}/branches/{branch_name:path}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a branch",
)
async def delete_branch(
    session: DbSession,
    current_user: CurrentUser,
    workspace_id: Annotated[UUID, Path(description="Workspace ID")],
    owner: Annotated[str, Path(description="Repository owner")],
    repo: Annotated[str, Path(description="Repository name")],
    branch_name: Annotated[str, Path(description="Branch name to delete")],
) -> Response:
    """Delete a branch from a GitHub repository."""
    provider = await _get_provider(session, workspace_id, owner, repo)
    try:
        await provider.delete_branch(branch_name)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    finally:
        await provider.aclose()


@router.get(
    "/repos/{owner}/{repo}/default-branch",
    summary="Get default branch",
)
async def get_default_branch(
    session: DbSession,
    current_user: CurrentUser,
    workspace_id: Annotated[UUID, Path(description="Workspace ID")],
    owner: Annotated[str, Path(description="Repository owner")],
    repo: Annotated[str, Path(description="Repository name")],
) -> dict[str, str]:
    """Get the default branch name for a repository."""
    provider = await _get_provider(session, workspace_id, owner, repo)
    try:
        default_branch = await provider.get_default_branch()
        return {"default_branch": default_branch}
    finally:
        await provider.aclose()


@router.get(
    "/repos/{owner}/{repo}/files/{path:path}",
    response_model=FileContentResponse,
    summary="Get file content at a ref",
)
async def get_file_content(
    session: DbSession,
    current_user: CurrentUser,
    workspace_id: Annotated[UUID, Path(description="Workspace ID")],
    owner: Annotated[str, Path(description="Repository owner")],
    repo: Annotated[str, Path(description="Repository name")],
    path: Annotated[str, Path(description="File path within the repository")],
    ref: str | None = Query(None, description="Branch or SHA (defaults to repo default branch)"),
) -> FileContentResponse:
    """Get file content at a specific ref (branch or SHA)."""
    provider = await _get_provider(session, workspace_id, owner, repo)
    try:
        if not ref:
            ref = await provider.get_default_branch()
        file_content = await provider.get_file_content(path, ref)

        # HTTP-level size guard (1 MB)
        content_bytes = len(file_content.content.encode("utf-8"))
        if content_bytes > _MAX_FILE_SIZE:
            raise ValidationError("File exceeds 1 MB size limit for web editor")

        return FileContentResponse(
            content=file_content.content,
            encoding="utf-8",
            sha=file_content.sha,
            size=file_content.size,
        )
    finally:
        await provider.aclose()


@router.get(
    "/repos/{owner}/{repo}/status",
    response_model=RepoStatusResponse,
    summary="Get changed files between branches",
)
async def get_repo_status(
    session: DbSession,
    current_user: CurrentUser,
    workspace_id: Annotated[UUID, Path(description="Workspace ID")],
    owner: Annotated[str, Path(description="Repository owner")],
    repo: Annotated[str, Path(description="Repository name")],
    base_branch: Annotated[str, Query(description="Base branch")] = "main",
    head_branch: Annotated[str, Query(description="Head branch")] = "HEAD",
) -> RepoStatusResponse:
    """Get files changed between two branches."""
    provider = await _get_provider(session, workspace_id, owner, repo)
    try:
        files = await provider.get_repo_status(base_branch, head_branch)
        truncated = len(files) >= _MAX_COMPARE_FILES
        return RepoStatusResponse(
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
            base_branch=base_branch,
            head_branch=head_branch,
            total_files=len(files),
            truncated=truncated,
        )
    finally:
        await provider.aclose()


@router.post(
    "/repos/{owner}/{repo}/commits",
    response_model=CommitResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a commit",
)
async def create_commit(
    session: DbSession,
    current_user: CurrentUser,
    workspace_id: Annotated[UUID, Path(description="Workspace ID")],
    owner: Annotated[str, Path(description="Repository owner")],
    repo: Annotated[str, Path(description="Repository name")],
    body: CommitRequest,
) -> CommitResponse:
    """Create a commit with one or more file changes via GitHub Git Data API."""
    provider = await _get_provider(session, workspace_id, owner, repo)
    try:
        file_changes = [
            FileChange(
                path=f.path,
                content=f.content,
                encoding=f.encoding,
                action=f.action,
            )
            for f in body.files
        ]
        result = await provider.create_commit(body.branch, body.message, file_changes)
        return CommitResponse(
            sha=result.sha,
            html_url=result.html_url,
            message=result.message,
        )
    finally:
        await provider.aclose()


@router.post(
    "/repos/{owner}/{repo}/pulls",
    response_model=PRResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a pull request",
)
async def create_pull_request(
    session: DbSession,
    current_user: CurrentUser,
    workspace_id: Annotated[UUID, Path(description="Workspace ID")],
    owner: Annotated[str, Path(description="Repository owner")],
    repo: Annotated[str, Path(description="Repository name")],
    body: CreatePRRequest,
) -> PRResponse:
    """Create a pull request on GitHub."""
    provider = await _get_provider(session, workspace_id, owner, repo)
    try:
        result = await provider.create_pull_request(
            body.title, body.body, body.head, body.base, draft=body.draft
        )
        return PRResponse(
            number=result.number,
            html_url=result.html_url,
            title=result.title,
            draft=result.draft,
        )
    finally:
        await provider.aclose()


__all__ = ["router"]
