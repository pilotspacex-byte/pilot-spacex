"""Tests for InstallPluginService — SKRG-02.

Tests use mock AsyncSession and mock repository to verify install,
update, and uninstall operations.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

pytestmark = pytest.mark.asyncio


def _make_skill_content() -> MagicMock:
    """Create a mock SkillContent."""
    from pilot_space.integrations.github.plugin_service import SkillContent

    return SkillContent(
        skill_md="---\nname: test-skill\ndescription: A test skill\n---\n# Test",
        references=[{"filename": "guide.md", "content": "# Guide"}],
        display_name="test-skill",
        description="A test skill",
    )


async def test_install_creates_workspace_plugin_record() -> None:
    """SKRG-02: install creates a WorkspacePlugin row with correct metadata."""
    from pilot_space.application.services.workspace_plugin.install_plugin_service import (
        InstallPluginService,
    )

    mock_session = AsyncMock()
    workspace_id = uuid4()
    user_id = uuid4()

    with patch(
        "pilot_space.application.services.workspace_plugin.install_plugin_service.WorkspacePluginRepository"
    ) as MockRepo:
        mock_repo = MockRepo.return_value
        mock_repo.get_by_workspace_and_name = AsyncMock(return_value=None)
        mock_repo.create = AsyncMock(side_effect=lambda entity: entity)

        svc = InstallPluginService(db_session=mock_session)
        skill_content = _make_skill_content()

        result = await svc.install(
            workspace_id=workspace_id,
            repo_url="https://github.com/anthropics/skills",
            skill_name="test-skill",
            skill_content=skill_content,
            installed_sha="a" * 40,
            installed_by=user_id,
        )

        assert result.workspace_id == workspace_id
        assert result.skill_name == "test-skill"
        assert result.is_active is True
        mock_repo.create.assert_awaited_once()


async def test_install_auto_wires_skill_content_immediately() -> None:
    """SKRG-02: installed plugin has is_active=True (auto-wired)."""
    from pilot_space.application.services.workspace_plugin.install_plugin_service import (
        InstallPluginService,
    )

    mock_session = AsyncMock()

    with patch(
        "pilot_space.application.services.workspace_plugin.install_plugin_service.WorkspacePluginRepository"
    ) as MockRepo:
        mock_repo = MockRepo.return_value
        mock_repo.get_by_workspace_and_name = AsyncMock(return_value=None)
        mock_repo.create = AsyncMock(side_effect=lambda entity: entity)

        svc = InstallPluginService(db_session=mock_session)
        skill_content = _make_skill_content()

        result = await svc.install(
            workspace_id=uuid4(),
            repo_url="https://github.com/anthropics/skills",
            skill_name="test-skill",
            skill_content=skill_content,
            installed_sha="b" * 40,
        )

        # is_active=True means SKILL.md is auto-wired (per CONTEXT.md decision)
        assert result.is_active is True


async def test_update_plugin_overwrites_content_with_upstream() -> None:
    """SKRG-02: update replaces local content with upstream version."""
    from pilot_space.application.services.workspace_plugin.install_plugin_service import (
        InstallPluginService,
    )

    mock_session = AsyncMock()

    with patch(
        "pilot_space.application.services.workspace_plugin.install_plugin_service.WorkspacePluginRepository"
    ) as MockRepo:
        mock_repo = MockRepo.return_value
        mock_repo.update = AsyncMock(side_effect=lambda entity: entity)

        # Simulate existing plugin
        existing = MagicMock()
        existing.skill_content = "old content"
        existing.installed_sha = "a" * 40
        existing.references = []

        svc = InstallPluginService(db_session=mock_session)

        new_content = _make_skill_content()
        new_content.skill_md = "# New content"
        new_sha = "c" * 40

        result = await svc.update(
            plugin=existing,
            skill_content=new_content,
            new_sha=new_sha,
        )

        assert existing.skill_content == "# New content"
        assert existing.installed_sha == new_sha
        mock_repo.update.assert_awaited_once()
