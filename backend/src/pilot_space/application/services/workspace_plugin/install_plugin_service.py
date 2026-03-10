"""Install plugin service — SKRG-02.

Handles plugin install, update, and uninstall operations.
Takes AsyncSession directly (no DI container) — follows SCIM/related-issues pattern.

Source: Phase 19, SKRG-02
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pilot_space.infrastructure.database.models.workspace_plugin import WorkspacePlugin
from pilot_space.infrastructure.database.repositories.workspace_plugin_repository import (
    WorkspacePluginRepository,
)
from pilot_space.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from pilot_space.integrations.github.plugin_service import SkillContent

logger = get_logger(__name__)


class InstallPluginService:
    """Service for installing, updating, and uninstalling workspace plugins.

    Plugins are created with is_active=True — SKILL.md content is auto-wired
    immediately on install (per CONTEXT.md decision). MCP tool bindings and
    action button definitions are stored but NOT wired until Phase 17.
    """

    def __init__(self, db_session: AsyncSession) -> None:
        """Initialize with a database session.

        Args:
            db_session: Active async database session.
        """
        self._session = db_session
        self._plugin_repo = WorkspacePluginRepository(db_session)

    async def install(
        self,
        workspace_id: UUID,
        repo_url: str,
        skill_name: str,
        skill_content: SkillContent,
        installed_sha: str,
        installed_by: UUID | None = None,
    ) -> WorkspacePlugin:
        """Install a plugin from a GitHub repository.

        Creates a WorkspacePlugin record with is_active=True. If a soft-deleted
        plugin with the same key exists, it is replaced with a new record.

        Args:
            workspace_id: Target workspace UUID.
            repo_url: Full GitHub repository URL.
            skill_name: Skill directory name in the repo.
            skill_content: Fetched SkillContent with markdown and references.
            installed_sha: Git commit SHA at install time.
            installed_by: User who triggered the install.

        Returns:
            Created WorkspacePlugin entity.
        """
        from pilot_space.integrations.github.plugin_service import parse_github_url

        owner, repo = parse_github_url(repo_url)

        # Check for existing (non-deleted) plugin
        existing = await self._plugin_repo.get_by_workspace_and_name(
            workspace_id=workspace_id,
            repo_owner=owner,
            repo_name=repo,
            skill_name=skill_name,
        )
        if existing is not None:
            logger.info(
                "Plugin %s/%s/%s already installed in workspace %s — updating",
                owner,
                repo,
                skill_name,
                workspace_id,
            )
            return await self.update(
                plugin=existing,
                skill_content=skill_content,
                new_sha=installed_sha,
            )

        plugin = WorkspacePlugin(
            workspace_id=workspace_id,
            repo_url=repo_url,
            repo_owner=owner,
            repo_name=repo,
            skill_name=skill_name,
            display_name=skill_content.display_name or skill_name,
            description=skill_content.description or None,
            skill_content=skill_content.skill_md,
            references=skill_content.references,
            installed_sha=installed_sha,
            is_active=True,
            installed_by=installed_by,
        )

        created = await self._plugin_repo.create(plugin)
        logger.info(
            "Installed plugin %s/%s/%s in workspace %s (SHA: %s)",
            owner,
            repo,
            skill_name,
            workspace_id,
            installed_sha[:8],
        )
        return created

    async def update(
        self,
        plugin: WorkspacePlugin,
        skill_content: SkillContent,
        new_sha: str,
    ) -> WorkspacePlugin:
        """Update a plugin with upstream content.

        Overwrites skill_content, references, and installed_sha.
        No diff or warning — always takes upstream version.

        Args:
            plugin: Existing WorkspacePlugin entity to update.
            skill_content: New SkillContent from upstream.
            new_sha: New Git commit SHA.

        Returns:
            Updated WorkspacePlugin entity.
        """
        plugin.skill_content = skill_content.skill_md
        plugin.references = skill_content.references
        plugin.installed_sha = new_sha
        plugin.display_name = skill_content.display_name or plugin.skill_name
        plugin.description = skill_content.description or None

        updated = await self._plugin_repo.update(plugin)
        logger.info(
            "Updated plugin %s (SHA: %s -> %s)",
            plugin.skill_name,
            plugin.installed_sha[:8] if plugin.installed_sha else "N/A",
            new_sha[:8],
        )
        return updated

    async def uninstall(self, plugin: WorkspacePlugin) -> None:
        """Uninstall (soft-delete) a plugin.

        Args:
            plugin: WorkspacePlugin entity to uninstall.
        """
        await self._plugin_repo.soft_delete(plugin)
        logger.info(
            "Uninstalled plugin %s from workspace %s",
            plugin.skill_name,
            plugin.workspace_id,
        )


__all__ = ["InstallPluginService"]
