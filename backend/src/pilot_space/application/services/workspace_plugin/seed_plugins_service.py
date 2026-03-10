"""Seed plugins service — SKRG-05.

Seeds new workspaces with default official plugins from a pre-configured list.
Uses system GITHUB_TOKEN; skips silently when not configured.

Source: Phase 19, SKRG-05
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from pilot_space.application.services.workspace_plugin.install_plugin_service import (
    InstallPluginService,
)
from pilot_space.infrastructure.logging import get_logger
from pilot_space.integrations.github.plugin_service import GitHubPluginService

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)

# Default plugins to seed into new workspaces.
# Format: (owner, repo, [skill_names])
DEFAULT_PLUGINS: list[tuple[str, str, list[str]]] = [
    ("anthropics", "skills", ["mcp-builder", "claude-api"]),
]


class SeedPluginsService:
    """Seed new workspaces with default official plugins.

    Non-fatal: all exceptions are caught and logged. Workspace creation
    succeeds regardless of seeding outcome.
    """

    def __init__(self, db_session: AsyncSession) -> None:
        """Initialize with a database session.

        Args:
            db_session: Active async database session.
        """
        self._session = db_session

    async def seed_workspace(self, workspace_id: UUID) -> None:
        """Install default plugins into a newly created workspace.

        Uses GITHUB_TOKEN env var for authentication. If missing, seeding
        is skipped silently. All errors are logged but never propagated.

        Args:
            workspace_id: UUID of the newly created workspace.
        """
        token = os.getenv("GITHUB_TOKEN")
        if not token:
            logger.info(
                "GITHUB_TOKEN not set — skipping plugin seeding for workspace %s",
                workspace_id,
            )
            return

        install_svc = InstallPluginService(db_session=self._session)

        for owner, repo, skill_names in DEFAULT_PLUGINS:
            gh = GitHubPluginService(token=token)
            try:
                repo_url = f"https://github.com/{owner}/{repo}"
                head_sha = await gh.get_head_sha(owner, repo)

                for skill_name in skill_names:
                    try:
                        skill_content = await gh.fetch_skill_content(owner, repo, skill_name)
                        await install_svc.install(
                            workspace_id=workspace_id,
                            repo_url=repo_url,
                            skill_name=skill_name,
                            skill_content=skill_content,
                            installed_sha=head_sha,
                        )
                        logger.info(
                            "Seeded plugin %s/%s/%s into workspace %s",
                            owner,
                            repo,
                            skill_name,
                            workspace_id,
                        )
                    except Exception:
                        logger.exception(
                            "Failed to seed plugin %s/%s/%s into workspace %s",
                            owner,
                            repo,
                            skill_name,
                            workspace_id,
                        )
            except Exception:
                logger.exception(
                    "Failed to fetch HEAD SHA for %s/%s during workspace seeding",
                    owner,
                    repo,
                )
            finally:
                await gh.aclose()


__all__ = ["SeedPluginsService"]
