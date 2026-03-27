"""Workspace plugins REST API endpoints (SKRG-01..05).

Admin-only endpoints for plugin lifecycle. Thin HTTP shell delegating to
PluginLifecycleService for all business logic.

Source: Phase 19, SKRG-01..05
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from pilot_space.api.middleware.request_context import WorkspaceId
from pilot_space.api.v1.dependencies import PluginLifecycleServiceDep
from pilot_space.api.v1.schemas.workspace_plugin import (
    SkillListItem,
    WorkspaceGithubCredentialRequest,
    WorkspaceGithubCredentialResponse,
    WorkspacePluginInstallAllRequest,
    WorkspacePluginInstallRequest,
    WorkspacePluginResponse,
    WorkspacePluginToggleRepoRequest,
    WorkspacePluginToggleRequest,
    WorkspacePluginUpdateCheckResponse,
)
from pilot_space.dependencies import CurrentUserId, DbSession
from pilot_space.domain.exceptions import ForbiddenError
from pilot_space.infrastructure.database.models.workspace_member import (
    WorkspaceMember,
    WorkspaceRole,
)
from pilot_space.infrastructure.database.rls import set_rls_context
from pilot_space.infrastructure.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(
    prefix="/{workspace_id}/plugins",
    tags=["Workspace Plugins"],
)


async def _require_admin(user_id: UUID, workspace_id: UUID, session: DbSession) -> None:
    stmt = select(WorkspaceMember.role).where(
        WorkspaceMember.workspace_id == workspace_id,
        WorkspaceMember.user_id == user_id,
        WorkspaceMember.is_active.is_(True),
        WorkspaceMember.is_deleted.is_(False),
    )
    result = await session.execute(stmt)
    row = result.scalar()
    if row is None:
        raise ForbiddenError("Not a member of this workspace")
    role = row.value if hasattr(row, "value") else str(row)
    if role not in (WorkspaceRole.ADMIN.value, WorkspaceRole.OWNER.value):
        raise ForbiddenError("Admin or owner role required")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "",
    response_model=list[WorkspacePluginResponse],
    summary="List installed plugins",
)
async def list_installed_plugins(
    workspace_id: WorkspaceId,
    session: DbSession,
    current_user_id: CurrentUserId,
) -> list[WorkspacePluginResponse]:
    """Return all installed (non-deleted) plugins for this workspace."""
    await set_rls_context(session, current_user_id, workspace_id)
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
    summary="Browse skills in a GitHub repo",
)
async def browse_repo(
    workspace_id: WorkspaceId,
    session: DbSession,
    current_user_id: CurrentUserId,
    svc: PluginLifecycleServiceDep,
    repo_url: str = Query(description="GitHub repository URL to browse"),
) -> list[SkillListItem]:
    """Fetch available skills from a GitHub repository URL."""
    await set_rls_context(session, current_user_id, workspace_id)
    await _require_admin(current_user_id, workspace_id, session)

    results = await svc.browse_repo(workspace_id, repo_url)
    return [
        SkillListItem(
            skill_name=r.skill_name,
            display_name=r.display_name,
            description=r.description,
        )
        for r in results
    ]


@router.post(
    "",
    response_model=WorkspacePluginResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Install a single skill plugin",
)
async def install_plugin(
    workspace_id: WorkspaceId,
    request: WorkspacePluginInstallRequest,
    session: DbSession,
    current_user_id: CurrentUserId,
    svc: PluginLifecycleServiceDep,
) -> WorkspacePluginResponse:
    """Install one skill from a GitHub repository into this workspace."""
    await set_rls_context(session, current_user_id, workspace_id)
    await _require_admin(current_user_id, workspace_id, session)

    from pilot_space.application.services.workspace_plugin.install_plugin_service import (
        InstallPluginService,
    )
    from pilot_space.integrations.github.plugin_service import GitHubPluginService, parse_github_url

    token = await svc.get_workspace_token(workspace_id)

    owner, repo = parse_github_url(request.repo_url)
    gh = GitHubPluginService(token=token)
    try:
        skill_content = await gh.fetch_skill_content(owner, repo, request.skill_name)
        head_sha = await gh.get_head_sha(owner, repo)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=f"GitHub API error: {exc}"
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
    logger.info("[Plugins] Installed %s in workspace %s", request.skill_name, workspace_id)
    return WorkspacePluginResponse.model_validate(plugin)


@router.post(
    "/install-all",
    response_model=list[WorkspacePluginResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Install all skills from a GitHub repo",
)
async def install_all_from_repo(
    workspace_id: WorkspaceId,
    request: WorkspacePluginInstallAllRequest,
    session: DbSession,
    current_user_id: CurrentUserId,
    svc: PluginLifecycleServiceDep,
) -> list[WorkspacePluginResponse]:
    """Browse a GitHub repo and install all discovered skills at once."""
    await set_rls_context(session, current_user_id, workspace_id)
    await _require_admin(current_user_id, workspace_id, session)

    plugins = await svc.install_all_from_repo(workspace_id, request.repo_url, current_user_id)
    return [WorkspacePluginResponse.model_validate(p) for p in plugins]


@router.patch(
    "/{plugin_id}/toggle",
    response_model=WorkspacePluginResponse,
    summary="Toggle plugin active state",
)
async def toggle_plugin(
    workspace_id: WorkspaceId,
    plugin_id: UUID,
    request: WorkspacePluginToggleRequest,
    session: DbSession,
    current_user_id: CurrentUserId,
    svc: PluginLifecycleServiceDep,
) -> WorkspacePluginResponse:
    """Activate or deactivate a single plugin skill."""
    await set_rls_context(session, current_user_id, workspace_id)
    await _require_admin(current_user_id, workspace_id, session)

    updated = await svc.toggle_plugin(workspace_id, plugin_id, request.is_active)
    return WorkspacePluginResponse.model_validate(updated)


@router.patch(
    "/toggle-repo",
    response_model=list[WorkspacePluginResponse],
    summary="Toggle all plugins from a repo",
)
async def toggle_repo_plugins(
    workspace_id: WorkspaceId,
    request: WorkspacePluginToggleRepoRequest,
    session: DbSession,
    current_user_id: CurrentUserId,
    svc: PluginLifecycleServiceDep,
) -> list[WorkspacePluginResponse]:
    """Activate or deactivate all plugin skills from a specific repository."""
    await set_rls_context(session, current_user_id, workspace_id)
    await _require_admin(current_user_id, workspace_id, session)

    plugins = await svc.toggle_repo_plugins(workspace_id, request.repo_url, request.is_active)
    return [WorkspacePluginResponse.model_validate(p) for p in plugins]


@router.delete(
    "/uninstall-repo",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Uninstall all plugins from a repo",
)
async def uninstall_repo_plugins(
    workspace_id: WorkspaceId,
    session: DbSession,
    current_user_id: CurrentUserId,
    svc: PluginLifecycleServiceDep,
    repo_url: str = Query(description="GitHub repository URL to uninstall"),
) -> None:
    """Soft-delete all installed plugins from a specific repository."""
    await set_rls_context(session, current_user_id, workspace_id)
    await _require_admin(current_user_id, workspace_id, session)

    await svc.uninstall_repo_plugins(workspace_id, repo_url)


@router.delete(
    "/{plugin_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Uninstall a single plugin",
)
async def uninstall_plugin(
    workspace_id: WorkspaceId,
    plugin_id: UUID,
    session: DbSession,
    current_user_id: CurrentUserId,
) -> None:
    """Soft-delete an installed plugin."""
    await set_rls_context(session, current_user_id, workspace_id)
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
        from pilot_space.domain.exceptions import NotFoundError

        raise NotFoundError("Plugin not found")

    install_svc = InstallPluginService(db_session=session)
    await install_svc.uninstall(plugin)
    logger.info("[Plugins] Uninstalled %s from workspace %s", plugin_id, workspace_id)


@router.get(
    "/check-updates",
    response_model=WorkspacePluginUpdateCheckResponse,
    summary="Check for plugin updates",
)
async def check_updates(
    workspace_id: WorkspaceId,
    session: DbSession,
    current_user_id: CurrentUserId,
    svc: PluginLifecycleServiceDep,
) -> WorkspacePluginUpdateCheckResponse:
    """Check if installed plugins have newer versions available."""
    await set_rls_context(session, current_user_id, workspace_id)
    await _require_admin(current_user_id, workspace_id, session)

    results = await svc.check_updates(workspace_id)
    plugin_responses: list[WorkspacePluginResponse] = []
    for plugin, has_update in results:
        resp = WorkspacePluginResponse.model_validate(plugin)
        resp.has_update = has_update
        plugin_responses.append(resp)
    return WorkspacePluginUpdateCheckResponse(plugins=plugin_responses)


@router.post(
    "/github-credential",
    response_model=WorkspaceGithubCredentialResponse,
    summary="Save workspace GitHub PAT",
)
async def save_github_credential(
    workspace_id: WorkspaceId,
    request: WorkspaceGithubCredentialRequest,
    session: DbSession,
    current_user_id: CurrentUserId,
    svc: PluginLifecycleServiceDep,
) -> WorkspaceGithubCredentialResponse:
    """Encrypt and store a GitHub PAT for this workspace."""
    await set_rls_context(session, current_user_id, workspace_id)
    await _require_admin(current_user_id, workspace_id, session)

    await svc.save_github_credential(workspace_id, request.pat, current_user_id)
    return WorkspaceGithubCredentialResponse(has_pat=True)


@router.get(
    "/github-credential",
    response_model=WorkspaceGithubCredentialResponse,
    summary="Check GitHub PAT status",
)
async def get_github_credential(
    workspace_id: WorkspaceId,
    session: DbSession,
    current_user_id: CurrentUserId,
    svc: PluginLifecycleServiceDep,
) -> WorkspaceGithubCredentialResponse:
    """Check if a GitHub PAT is configured for this workspace."""
    await set_rls_context(session, current_user_id, workspace_id)
    await _require_admin(current_user_id, workspace_id, session)

    has_pat = await svc.has_github_credential(workspace_id)
    return WorkspaceGithubCredentialResponse(has_pat=has_pat)


__all__ = ["router"]
