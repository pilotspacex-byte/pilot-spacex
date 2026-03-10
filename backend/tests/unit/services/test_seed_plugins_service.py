"""Tests for SeedPluginsService — SKRG-05.

Tests verify default plugin seeding behavior on workspace creation.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

pytestmark = pytest.mark.asyncio


async def test_seed_workspace_installs_default_plugins() -> None:
    """SKRG-05: seed_workspace installs the default plugin set."""
    from pilot_space.application.services.workspace_plugin.seed_plugins_service import (
        SeedPluginsService,
    )

    mock_session = AsyncMock()
    workspace_id = uuid4()

    with (
        patch.dict("os.environ", {"GITHUB_TOKEN": "test-token"}),
        patch(
            "pilot_space.application.services.workspace_plugin.seed_plugins_service.GitHubPluginService"
        ) as MockGH,
        patch(
            "pilot_space.application.services.workspace_plugin.seed_plugins_service.InstallPluginService"
        ) as MockInstall,
    ):
        from pilot_space.integrations.github.plugin_service import SkillContent

        mock_gh = MockGH.return_value
        mock_gh.fetch_skill_content = AsyncMock(
            return_value=SkillContent(
                skill_md="---\nname: test\n---\n# Test",
                references=[],
                display_name="test",
                description="test desc",
            )
        )
        mock_gh.get_head_sha = AsyncMock(return_value="a" * 40)
        mock_gh.aclose = AsyncMock()

        mock_install = MockInstall.return_value
        mock_install.install = AsyncMock()

        svc = SeedPluginsService(db_session=mock_session)
        await svc.seed_workspace(workspace_id=workspace_id)

        # Should install at least 2 default plugins (mcp-builder, claude-api)
        assert mock_install.install.await_count >= 2


async def test_seed_workspace_skips_when_github_token_missing() -> None:
    """SKRG-05: seed_workspace gracefully skips when GITHUB_TOKEN is absent."""
    from pilot_space.application.services.workspace_plugin.seed_plugins_service import (
        SeedPluginsService,
    )

    mock_session = AsyncMock()

    with patch.dict("os.environ", {}, clear=False):
        # Ensure GITHUB_TOKEN is not set
        import os

        os.environ.pop("GITHUB_TOKEN", None)

        svc = SeedPluginsService(db_session=mock_session)
        # Should not raise — just return silently
        await svc.seed_workspace(workspace_id=uuid4())


async def test_seed_failure_is_nonfatal() -> None:
    """SKRG-05: seed failure does not propagate — workspace creation succeeds."""
    from pilot_space.application.services.workspace_plugin.seed_plugins_service import (
        SeedPluginsService,
    )

    mock_session = AsyncMock()

    with (
        patch.dict("os.environ", {"GITHUB_TOKEN": "test-token"}),
        patch(
            "pilot_space.application.services.workspace_plugin.seed_plugins_service.GitHubPluginService"
        ) as MockGH,
    ):
        mock_gh = MockGH.return_value
        mock_gh.fetch_skill_content = AsyncMock(side_effect=Exception("GitHub down"))
        mock_gh.get_head_sha = AsyncMock(side_effect=Exception("GitHub down"))
        mock_gh.aclose = AsyncMock()

        svc = SeedPluginsService(db_session=mock_session)
        # Should not raise — seed failures are non-fatal
        await svc.seed_workspace(workspace_id=uuid4())
