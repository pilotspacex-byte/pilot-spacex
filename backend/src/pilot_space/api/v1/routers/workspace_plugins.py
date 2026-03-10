"""Workspace plugins REST API endpoints (SKRG-01..05).

Admin-only endpoints for plugin lifecycle:
- GET  /{workspace_id}/plugins              -> list installed
- GET  /{workspace_id}/plugins/browse       -> browse GitHub repo
- POST /{workspace_id}/plugins              -> install plugin
- DELETE /{workspace_id}/plugins/{plugin_id} -> uninstall
- GET  /{workspace_id}/plugins/check-updates -> version check
- POST /{workspace_id}/plugins/github-credential -> save PAT
- GET  /{workspace_id}/plugins/github-credential -> check PAT status

Uses direct instantiation pattern (not @inject DI) — follows SCIM/related-issues
pattern to avoid wiring_config.modules updates.

Source: Phase 19, SKRG-01..05
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from pilot_space.api.middleware.request_context import WorkspaceId
from pilot_space.api.v1.schemas.workspace_plugin import (
    SkillListItem,
    WorkspaceGithubCredentialRequest,
    WorkspaceGithubCredentialResponse,
    WorkspacePluginInstallRequest,
    WorkspacePluginResponse,
    WorkspacePluginUpdateCheckResponse,
)
from pilot_space.dependencies import CurrentUserId, DbSession, RedisDep
from pilot_space.infrastructure.database.models.workspace_member import (
    WorkspaceMember,
    WorkspaceRole,
)
from pilot_space.infrastructure.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(
    prefix="/{workspace_id}/plugins",
    tags=["Workspace Plugins"],
)

# Redis TTL for HEAD SHA cache (5 minutes)
_PLUGIN_SHA_CACHE_TTL = 300


async def _require_admin(
    user_id: UUID,
    workspace_id: UUID,
    session: DbSession,
) -> None:
    """Verify the requesting user is an ADMIN or OWNER in the workspace.

    Args:
        user_id: Authenticated user UUID.
        workspace_id: Workspace UUID to check.
        session: Database session.

    Raises:
        HTTPException: 403 if user is not a member or lacks ADMIN/OWNER role.
    """
    stmt = select(WorkspaceMember.role).where(
        WorkspaceMember.workspace_id == workspace_id,
        WorkspaceMember.user_id == user_id,
    )
    result = await session.execute(stmt)
    row = result.scalar()

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this workspace",
        )

    role = row.value if hasattr(row, "value") else str(row)
    if role not in (WorkspaceRole.ADMIN.value, WorkspaceRole.OWNER.value):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin or owner role required",
        )


@router.get(
    "",
    response_model=list[WorkspacePluginResponse],
    status_code=status.HTTP_200_OK,
    summary="List installed plugins",
    description="Return all installed (non-deleted) plugins for this workspace.",
)
async def list_installed_plugins(
    workspace_id: WorkspaceId,
    session: DbSession,
    current_user_id: CurrentUserId,
) -> list[WorkspacePluginResponse]:
    """List installed plugins for a workspace.

    Args:
        workspace_id: Workspace UUID from path.
        session: Database session.
        current_user_id: Authenticated user UUID.

    Returns:
        List of installed plugins.
    """
    await _require_admin(current_user_id, workspace_id, session)

    from pilot_space.infrastructure.database.repositories.workspace_plugin_repository import (
        WorkspacePluginRepository,
    )

    repo = WorkspacePluginRepository(session)
    plugins = await repo.get_installed_by_workspace(workspace_id)

    return [WorkspacePluginResponse.model_validate(p) for p in plugins]


@router.get(
    "/browse",
    response_model=list[SkillListItem],
    status_code=status.HTTP_200_OK,
    summary="Browse skills in a GitHub repo",
    description="Fetch available skills from a GitHub repository URL.",
)
async def browse_repo(
    workspace_id: WorkspaceId,
    session: DbSession,
    current_user_id: CurrentUserId,
    repo_url: str = Query(description="GitHub repository URL to browse"),
) -> list[SkillListItem]:
    """Browse available skills in a GitHub repository.

    Uses workspace PAT if configured, otherwise falls back to system GITHUB_TOKEN.

    Args:
        workspace_id: Workspace UUID from path.
        session: Database session.
        current_user_id: Authenticated user UUID.
        repo_url: GitHub repository URL.

    Returns:
        List of available skills.
    """
    await _require_admin(current_user_id, workspace_id, session)

    from pilot_space.integrations.github.plugin_service import (
        GitHubPluginService,
        PluginRateLimitError,
        PluginRepoError,
        parse_github_url,
    )

    try:
        owner, repo = parse_github_url(repo_url)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    token = await _get_workspace_token(workspace_id, session)
    gh = GitHubPluginService(token=token)

    try:
        skill_names = await gh.list_skills(owner, repo)
        items: list[SkillListItem] = []
        for name in skill_names:
            try:
                content = await gh.fetch_skill_content(owner, repo, name)
                items.append(
                    SkillListItem(
                        skill_name=name,
                        display_name=content.display_name or name,
                        description=content.description or None,
                    )
                )
            except Exception:
                # Individual skill fetch failure — include with minimal info
                items.append(SkillListItem(skill_name=name, display_name=name))
        return items
    except PluginRepoError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except PluginRateLimitError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"GitHub API error: {exc}",
        ) from exc
    finally:
        await gh.aclose()


@router.post(
    "",
    response_model=WorkspacePluginResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Install a plugin",
    description="Install a skill from a GitHub repository into this workspace.",
)
async def install_plugin(
    workspace_id: WorkspaceId,
    request: WorkspacePluginInstallRequest,
    session: DbSession,
    current_user_id: CurrentUserId,
) -> WorkspacePluginResponse:
    """Install a plugin from a GitHub repository.

    Fetches SKILL.md + references from GitHub, creates a WorkspacePlugin record
    with is_active=True (SKILL.md auto-wired immediately). MCP tools and action
    button definitions from frontmatter are stored but NOT wired (Phase 17).

    Args:
        workspace_id: Workspace UUID from path.
        request: Install request with repo_url and skill_name.
        session: Database session.
        current_user_id: Authenticated user UUID.

    Returns:
        Created plugin record.
    """
    await _require_admin(current_user_id, workspace_id, session)

    from pilot_space.application.services.workspace_plugin.install_plugin_service import (
        InstallPluginService,
    )
    from pilot_space.integrations.github.plugin_service import (
        GitHubPluginService,
        parse_github_url,
    )

    try:
        owner, repo = parse_github_url(request.repo_url)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    token = await _get_workspace_token(workspace_id, session)
    gh = GitHubPluginService(token=token)

    try:
        skill_content = await gh.fetch_skill_content(owner, repo, request.skill_name)
        head_sha = await gh.get_head_sha(owner, repo)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"GitHub API error: {exc}",
        ) from exc
    finally:
        await gh.aclose()

    install_svc = InstallPluginService(db_session=session)
    plugin = await install_svc.install(
        workspace_id=workspace_id,
        repo_url=request.repo_url,
        skill_name=request.skill_name,
        skill_content=skill_content,
        installed_sha=head_sha,
        installed_by=current_user_id,
    )

    logger.info(
        "[WorkspacePlugins] Installed %s in workspace %s by user %s",
        request.skill_name,
        workspace_id,
        current_user_id,
    )

    return WorkspacePluginResponse.model_validate(plugin)


@router.delete(
    "/{plugin_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Uninstall a plugin",
    description="Soft-delete an installed plugin.",
)
async def uninstall_plugin(
    workspace_id: WorkspaceId,
    plugin_id: UUID,
    session: DbSession,
    current_user_id: CurrentUserId,
) -> None:
    """Uninstall (soft-delete) a plugin.

    Args:
        workspace_id: Workspace UUID from path.
        plugin_id: UUID of the plugin to uninstall.
        session: Database session.
        current_user_id: Authenticated user UUID.

    Raises:
        HTTPException: 404 if plugin not found.
    """
    await _require_admin(current_user_id, workspace_id, session)

    from pilot_space.application.services.workspace_plugin.install_plugin_service import (
        InstallPluginService,
    )
    from pilot_space.infrastructure.database.repositories.workspace_plugin_repository import (
        WorkspacePluginRepository,
    )

    repo = WorkspacePluginRepository(session)
    plugin = await repo.get_by_id(plugin_id)
    if plugin is None or plugin.workspace_id != workspace_id or plugin.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plugin not found",
        )

    install_svc = InstallPluginService(db_session=session)
    await install_svc.uninstall(plugin)

    logger.info(
        "[WorkspacePlugins] Uninstalled plugin %s from workspace %s by user %s",
        plugin_id,
        workspace_id,
        current_user_id,
    )


@router.get(
    "/check-updates",
    response_model=WorkspacePluginUpdateCheckResponse,
    status_code=status.HTTP_200_OK,
    summary="Check for plugin updates",
    description="Check if installed plugins have newer versions available.",
)
async def check_updates(
    workspace_id: WorkspaceId,
    session: DbSession,
    current_user_id: CurrentUserId,
    redis: RedisDep,
) -> WorkspacePluginUpdateCheckResponse:
    """Check installed plugins for available updates.

    Compares installed SHA against HEAD SHA of source repos. Results are
    cached in Redis for 5 minutes per (workspace, repo) to avoid rate limits.

    Args:
        workspace_id: Workspace UUID from path.
        session: Database session.
        current_user_id: Authenticated user UUID.
        redis: Redis client for SHA caching.

    Returns:
        List of plugins with has_update status.
    """
    await _require_admin(current_user_id, workspace_id, session)

    from pilot_space.infrastructure.database.repositories.workspace_plugin_repository import (
        WorkspacePluginRepository,
    )

    repo = WorkspacePluginRepository(session)
    plugins = await repo.get_installed_by_workspace(workspace_id)

    token = await _get_workspace_token(workspace_id, session)

    # Group plugins by (repo_owner, repo_name) to avoid duplicate SHA lookups
    repo_shas: dict[tuple[str, str], str | None] = {}

    from pilot_space.integrations.github.plugin_service import GitHubPluginService

    gh = GitHubPluginService(token=token)
    try:
        for plugin in plugins:
            key = (plugin.repo_owner, plugin.repo_name)
            if key not in repo_shas:
                head_sha = await _get_cached_head_sha(
                    redis=redis,
                    workspace_id=str(workspace_id),
                    owner=plugin.repo_owner,
                    repo=plugin.repo_name,
                    gh=gh,
                )
                repo_shas[key] = head_sha
    finally:
        await gh.aclose()

    results: list[WorkspacePluginResponse] = []
    for plugin in plugins:
        key = (plugin.repo_owner, plugin.repo_name)
        head_sha = repo_shas.get(key)
        has_update = head_sha is not None and head_sha != plugin.installed_sha
        resp = WorkspacePluginResponse.model_validate(plugin)
        resp.has_update = has_update
        results.append(resp)

    return WorkspacePluginUpdateCheckResponse(plugins=results)


@router.post(
    "/github-credential",
    response_model=WorkspaceGithubCredentialResponse,
    status_code=status.HTTP_200_OK,
    summary="Save workspace GitHub PAT",
    description="Encrypt and store a GitHub PAT for this workspace.",
)
async def save_github_credential(
    workspace_id: WorkspaceId,
    request: WorkspaceGithubCredentialRequest,
    session: DbSession,
    current_user_id: CurrentUserId,
) -> WorkspaceGithubCredentialResponse:
    """Save a workspace GitHub PAT (encrypted).

    Args:
        workspace_id: Workspace UUID from path.
        request: Raw PAT to encrypt and store.
        session: Database session.
        current_user_id: Authenticated user UUID.

    Returns:
        Credential status (has_pat=True).
    """
    await _require_admin(current_user_id, workspace_id, session)

    from pilot_space.infrastructure.database.repositories.workspace_github_credential_repository import (
        WorkspaceGithubCredentialRepository,
    )
    from pilot_space.infrastructure.encryption import encrypt_api_key

    pat_encrypted = encrypt_api_key(request.pat)
    cred_repo = WorkspaceGithubCredentialRepository(session)
    await cred_repo.upsert(
        workspace_id=workspace_id,
        pat_encrypted=pat_encrypted,
        created_by=current_user_id,
    )

    logger.info(
        "[WorkspacePlugins] GitHub PAT saved for workspace %s by user %s",
        workspace_id,
        current_user_id,
    )

    return WorkspaceGithubCredentialResponse(has_pat=True)


@router.get(
    "/github-credential",
    response_model=WorkspaceGithubCredentialResponse,
    status_code=status.HTTP_200_OK,
    summary="Check GitHub PAT status",
    description="Check if a GitHub PAT is configured for this workspace.",
)
async def get_github_credential(
    workspace_id: WorkspaceId,
    session: DbSession,
    current_user_id: CurrentUserId,
) -> WorkspaceGithubCredentialResponse:
    """Check if a GitHub PAT is configured.

    Args:
        workspace_id: Workspace UUID from path.
        session: Database session.
        current_user_id: Authenticated user UUID.

    Returns:
        Credential status (has_pat=True/False).
    """
    await _require_admin(current_user_id, workspace_id, session)

    from pilot_space.infrastructure.database.repositories.workspace_github_credential_repository import (
        WorkspaceGithubCredentialRepository,
    )

    cred_repo = WorkspaceGithubCredentialRepository(session)
    credential = await cred_repo.get_by_workspace(workspace_id)

    return WorkspaceGithubCredentialResponse(has_pat=credential is not None)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _get_workspace_token(
    workspace_id: UUID,
    session: DbSession,
) -> str | None:
    """Get decrypted workspace GitHub PAT, or None for system token fallback.

    Args:
        workspace_id: Workspace UUID.
        session: Database session.

    Returns:
        Decrypted PAT string or None.
    """
    from pilot_space.infrastructure.database.repositories.workspace_github_credential_repository import (
        WorkspaceGithubCredentialRepository,
    )
    from pilot_space.infrastructure.encryption import decrypt_api_key

    cred_repo = WorkspaceGithubCredentialRepository(session)
    credential = await cred_repo.get_by_workspace(workspace_id)
    if credential is None:
        return None

    try:
        return decrypt_api_key(credential.pat_encrypted)
    except Exception:
        logger.warning(
            "Failed to decrypt GitHub PAT for workspace %s",
            workspace_id,
        )
        return None


async def _get_cached_head_sha(
    redis: RedisDep,
    workspace_id: str,
    owner: str,
    repo: str,
    gh: object,
) -> str | None:
    """Get HEAD SHA with 5-minute Redis cache.

    Args:
        redis: Redis client.
        workspace_id: Workspace UUID string.
        owner: GitHub owner.
        repo: Repository name.
        gh: GitHubPluginService instance.

    Returns:
        SHA string or None on error.
    """
    cache_key = f"plugin:head_sha:{workspace_id}:{owner}:{repo}"

    # Check cache first
    cached = await redis.get(cache_key)
    if cached is not None and isinstance(cached, str):
        return cached

    # Fetch from GitHub
    try:
        from pilot_space.integrations.github.plugin_service import GitHubPluginService

        if isinstance(gh, GitHubPluginService):
            sha = await gh.get_head_sha(owner, repo)
            await redis.set(cache_key, sha, ttl=_PLUGIN_SHA_CACHE_TTL)
            return sha
    except Exception:
        logger.warning(
            "Failed to fetch HEAD SHA for %s/%s",
            owner,
            repo,
        )

    return None


__all__ = ["router"]
