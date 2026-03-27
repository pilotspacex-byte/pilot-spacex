"""Plugin lifecycle service for workspace plugin management.

Handles GitHub token flow, bulk toggle/uninstall, update checking with caching.
Extracted from workspace_plugins.py router to enforce thin-router pattern.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import UUID

from pilot_space.domain.exceptions import NotFoundError, ServiceUnavailableError
from pilot_space.infrastructure.database.repositories.skill_action_button_repository import (
    SkillActionButtonRepository,
)
from pilot_space.infrastructure.database.repositories.workspace_github_credential_repository import (
    WorkspaceGithubCredentialRepository,
)
from pilot_space.infrastructure.database.repositories.workspace_plugin_repository import (
    WorkspacePluginRepository,
)
from pilot_space.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from redis.asyncio import Redis
    from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)

_PLUGIN_SHA_CACHE_TTL = 300


@dataclass
class BrowseRepoResult:
    """Result of browsing a GitHub repo for skills."""

    skill_name: str
    display_name: str
    description: str | None = None


@dataclass
class ToggleResult:
    """Result of toggling plugin(s)."""

    toggled_count: int


class PluginLifecycleService:
    """Manages plugin lifecycle: browse, toggle, uninstall, update checks.

    Args:
        session: Request-scoped async database session.
        redis: Redis client for caching HEAD SHAs.
        workspace_github_credential_repository: Repository for GitHub credentials.
        workspace_plugin_repository: Repository for workspace plugins.
        skill_action_button_repository: Repository for skill action buttons.
    """

    def __init__(
        self,
        session: AsyncSession,
        redis: Redis,
        workspace_github_credential_repository: WorkspaceGithubCredentialRepository,
        workspace_plugin_repository: WorkspacePluginRepository,
        skill_action_button_repository: SkillActionButtonRepository,
    ) -> None:
        self._session = session
        self._redis = redis
        self._cred_repo = workspace_github_credential_repository
        self._plugin_repo = workspace_plugin_repository
        self._button_repo = skill_action_button_repository

    # ------------------------------------------------------------------
    # GitHub token helpers
    # ------------------------------------------------------------------

    async def get_workspace_token(self, workspace_id: UUID) -> str | None:
        """Get decrypted workspace GitHub PAT, or None for system token fallback."""
        from pilot_space.infrastructure.encryption import decrypt_api_key

        credential = await self._cred_repo.get_by_workspace(workspace_id)
        if credential is None:
            return None
        try:
            return decrypt_api_key(credential.pat_encrypted)
        except Exception:
            logger.warning("Failed to decrypt GitHub PAT for workspace %s", workspace_id)
            return None

    async def save_github_credential(self, workspace_id: UUID, pat: str, created_by: UUID) -> None:
        """Encrypt and store a GitHub PAT for a workspace."""
        from pilot_space.infrastructure.encryption import encrypt_api_key

        pat_encrypted = encrypt_api_key(pat)
        await self._cred_repo.upsert(
            workspace_id=workspace_id, pat_encrypted=pat_encrypted, created_by=created_by
        )
        logger.info("[Plugins] GitHub PAT saved for workspace %s", workspace_id)

    async def has_github_credential(self, workspace_id: UUID) -> bool:
        """Check if a GitHub PAT is configured for a workspace."""
        credential = await self._cred_repo.get_by_workspace(workspace_id)
        return credential is not None

    # ------------------------------------------------------------------
    # Browse
    # ------------------------------------------------------------------

    async def browse_repo(self, workspace_id: UUID, repo_url: str) -> list[BrowseRepoResult]:
        """Fetch available skills from a GitHub repository URL."""
        from pilot_space.integrations.github.plugin_service import (
            GitHubPluginService,
            parse_github_url,
        )

        owner, repo = parse_github_url(repo_url)
        token = await self.get_workspace_token(workspace_id)
        gh = GitHubPluginService(token=token)
        try:
            skill_names = await gh.list_skills(owner, repo)
            items: list[BrowseRepoResult] = []
            for name in skill_names:
                try:
                    content = await gh.fetch_skill_content(owner, repo, name)
                    items.append(
                        BrowseRepoResult(
                            skill_name=name,
                            display_name=content.display_name or name,
                            description=content.description or None,
                        )
                    )
                except Exception:
                    items.append(BrowseRepoResult(skill_name=name, display_name=name))
            return items
        finally:
            await gh.aclose()

    # ------------------------------------------------------------------
    # Toggle
    # ------------------------------------------------------------------

    async def toggle_plugin(self, workspace_id: UUID, plugin_id: UUID, is_active: bool) -> object:
        """Toggle a single plugin active/inactive. Returns the updated plugin model."""
        plugin = await self._plugin_repo.get_by_id(plugin_id)
        if plugin is None or plugin.workspace_id != workspace_id or plugin.is_deleted:
            raise NotFoundError("Plugin not found")

        plugin.is_active = is_active
        updated = await self._plugin_repo.update(plugin)
        logger.info("[Plugins] Toggled %s to %s", plugin_id, "active" if is_active else "inactive")
        return updated

    async def toggle_repo_plugins(
        self, workspace_id: UUID, repo_url: str, is_active: bool
    ) -> list[object]:
        """Toggle all plugins from a repo. Returns updated plugin models."""
        from pilot_space.integrations.github.plugin_service import parse_github_url

        owner, repo = parse_github_url(repo_url)

        plugins = await self._plugin_repo.get_by_workspace_and_repo(workspace_id, owner, repo)
        if not plugins:
            raise NotFoundError("No plugins from this repo.")

        plugin_ids = [p.id for p in plugins]
        await self._plugin_repo.bulk_set_active(plugin_ids, is_active)

        for plugin in plugins:
            await self._session.refresh(plugin)

        logger.info("[Plugins] Toggled %d from %s/%s to %s", len(plugins), owner, repo, is_active)
        return list(plugins)

    # ------------------------------------------------------------------
    # Uninstall
    # ------------------------------------------------------------------

    async def uninstall_repo_plugins(self, workspace_id: UUID, repo_url: str) -> int:
        """Soft-delete all plugins from a repo. Returns count of uninstalled plugins."""
        from pilot_space.integrations.github.plugin_service import parse_github_url

        owner, repo = parse_github_url(repo_url)

        plugins = await self._plugin_repo.get_by_workspace_and_repo(workspace_id, owner, repo)
        if not plugins:
            raise NotFoundError("No plugins from this repo.")

        plugin_ids = [p.id for p in plugins]

        # Bulk deactivate associated action buttons (non-fatal)
        for plugin_id in plugin_ids:
            try:
                await self._button_repo.deactivate_by_plugin_id(
                    workspace_id=workspace_id,
                    plugin_id=str(plugin_id),
                )
            except Exception:
                logger.warning(
                    "Failed to bulk-deactivate action buttons for plugin %s in workspace %s",
                    plugin_id,
                    workspace_id,
                    exc_info=True,
                )

        # Bulk soft-delete all plugins
        await self._plugin_repo.bulk_soft_delete(plugin_ids)

        logger.info(
            "[Plugins] Uninstalled %d from %s/%s in workspace %s",
            len(plugins),
            owner,
            repo,
            workspace_id,
        )
        return len(plugins)

    # ------------------------------------------------------------------
    # Install all from repo
    # ------------------------------------------------------------------

    async def install_all_from_repo(
        self,
        workspace_id: UUID,
        repo_url: str,
        installed_by: UUID,
    ) -> list[object]:
        """Browse and install all skills from a GitHub repo. Returns plugin models."""
        from pilot_space.application.services.workspace_plugin.install_plugin_service import (
            InstallPluginService,
        )
        from pilot_space.integrations.github.plugin_service import (
            GitHubPluginService,
            parse_github_url,
        )

        owner, repo = parse_github_url(repo_url)
        token = await self.get_workspace_token(workspace_id)
        gh = GitHubPluginService(token=token)

        skill_names = await gh.list_skills(owner, repo)
        head_sha = await gh.get_head_sha(owner, repo) if skill_names else ""

        if not skill_names:
            await gh.aclose()
            raise NotFoundError("No skills found.")

        install_svc = InstallPluginService(db_session=self._session)
        results: list[object] = []
        try:

            async def _fetch(name: str) -> tuple[str, object] | None:
                try:
                    content = await gh.fetch_skill_content(owner, repo, name)
                    return (name, content)
                except Exception:
                    logger.warning(
                        "[Plugins] Failed to fetch skill %s from %s/%s",
                        name,
                        owner,
                        repo,
                        exc_info=True,
                    )
                    return None

            fetched_results = await asyncio.gather(*[_fetch(name) for name in skill_names])
            fetched_skills = [r for r in fetched_results if r is not None]

            for name, content in fetched_skills:
                try:
                    plugin = await install_svc.install(
                        workspace_id=workspace_id,
                        repo_url=repo_url,
                        skill_name=name,
                        skill_content=content,  # type: ignore[arg-type]
                        installed_sha=head_sha,
                        installed_by=installed_by,
                    )
                    results.append(plugin)
                except Exception:
                    logger.warning(
                        "[Plugins] Failed to install skill %s from %s/%s",
                        name,
                        owner,
                        repo,
                        exc_info=True,
                    )
        finally:
            await gh.aclose()

        if not results:
            raise ServiceUnavailableError("Failed to install any skills.")

        logger.info(
            "[Plugins] Installed %d skills from %s/%s in workspace %s",
            len(results),
            owner,
            repo,
            workspace_id,
        )
        return results

    # ------------------------------------------------------------------
    # Update checks
    # ------------------------------------------------------------------

    async def _get_cached_head_sha(
        self, workspace_id: str, owner: str, repo: str, gh: object
    ) -> str | None:
        """Get HEAD SHA with 5-minute Redis cache."""
        cache_key = f"plugin:head_sha:{workspace_id}:{owner}:{repo}"
        cached = await self._redis.get(cache_key)
        if cached is not None and isinstance(cached, str):
            return cached
        try:
            from pilot_space.integrations.github.plugin_service import GitHubPluginService

            if isinstance(gh, GitHubPluginService):
                sha = await gh.get_head_sha(owner, repo)
                await self._redis.set(cache_key, sha, ex=_PLUGIN_SHA_CACHE_TTL)
                return sha
        except Exception:
            logger.warning("Failed to fetch HEAD SHA for %s/%s", owner, repo)
        return None

    async def check_updates(self, workspace_id: UUID) -> list[tuple[object, bool]]:
        """Check installed plugins for updates. Returns list of (plugin, has_update) tuples."""
        from pilot_space.integrations.github.plugin_service import GitHubPluginService

        plugins = await self._plugin_repo.get_installed_by_workspace(workspace_id)
        token = await self.get_workspace_token(workspace_id)

        repo_shas: dict[tuple[str, str], str | None] = {}
        gh = GitHubPluginService(token=token)
        try:
            for plugin in plugins:
                key = (plugin.repo_owner, plugin.repo_name)
                if key not in repo_shas:
                    repo_shas[key] = await self._get_cached_head_sha(
                        workspace_id=str(workspace_id),
                        owner=plugin.repo_owner,
                        repo=plugin.repo_name,
                        gh=gh,
                    )
        finally:
            await gh.aclose()

        results: list[tuple[object, bool]] = []
        for plugin in plugins:
            key = (plugin.repo_owner, plugin.repo_name)
            head_sha = repo_shas.get(key)
            has_update = head_sha is not None and head_sha != plugin.installed_sha
            results.append((plugin, has_update))

        return results
