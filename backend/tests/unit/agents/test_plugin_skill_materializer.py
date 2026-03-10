"""Tests for materialize_plugin_skills — SKRG-03.

Tests verify that plugin skills are written to the sandbox skills directory
and stale plugin directories are cleaned up.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

pytestmark = pytest.mark.asyncio


def _make_plugin(
    skill_name: str = "test-skill",
    skill_content: str = "# Test Skill",
    references: list | None = None,
    is_active: bool = True,
) -> MagicMock:
    """Create a mock WorkspacePlugin."""
    plugin = MagicMock()
    plugin.skill_name = skill_name
    plugin.skill_content = skill_content
    plugin.references = references or []
    plugin.is_active = is_active
    return plugin


async def test_materialize_plugin_skills_writes_skill_md_files(tmp_path: Path) -> None:
    """SKRG-03: materialize_plugin_skills writes SKILL.md for each active plugin."""
    from pilot_space.ai.agents.role_skill_materializer import materialize_plugin_skills

    mock_session = AsyncMock()
    workspace_id = uuid4()
    skills_dir = tmp_path / ".claude" / "skills"
    skills_dir.mkdir(parents=True)

    plugin = _make_plugin(skill_name="mcp-builder", skill_content="# MCP Builder Skill")

    with patch(
        "pilot_space.infrastructure.database.repositories.workspace_plugin_repository.WorkspacePluginRepository"
    ) as MockRepo:
        mock_repo = MockRepo.return_value
        mock_repo.get_active_by_workspace = AsyncMock(return_value=[plugin])

        count = await materialize_plugin_skills(
            db_session=mock_session,
            workspace_id=workspace_id,
            skills_dir=skills_dir,
        )

    assert count == 1
    skill_file = skills_dir / "plugin-mcp-builder" / "SKILL.md"
    assert skill_file.exists()
    assert skill_file.read_text() == "# MCP Builder Skill"


async def test_materialize_plugin_skills_writes_reference_files_alongside_skill_md(
    tmp_path: Path,
) -> None:
    """SKRG-03: materialize_plugin_skills writes reference/ files alongside SKILL.md."""
    from pilot_space.ai.agents.role_skill_materializer import materialize_plugin_skills

    mock_session = AsyncMock()
    workspace_id = uuid4()
    skills_dir = tmp_path / ".claude" / "skills"
    skills_dir.mkdir(parents=True)

    plugin = _make_plugin(
        skill_name="claude-api",
        skill_content="# Claude API",
        references=[
            {"filename": "guide.md", "content": "# Usage Guide"},
            {"filename": "examples.md", "content": "# Examples"},
        ],
    )

    with patch(
        "pilot_space.infrastructure.database.repositories.workspace_plugin_repository.WorkspacePluginRepository"
    ) as MockRepo:
        mock_repo = MockRepo.return_value
        mock_repo.get_active_by_workspace = AsyncMock(return_value=[plugin])

        count = await materialize_plugin_skills(
            db_session=mock_session,
            workspace_id=workspace_id,
            skills_dir=skills_dir,
        )

    assert count == 1
    ref_dir = skills_dir / "plugin-claude-api" / "reference"
    assert ref_dir.exists()
    assert (ref_dir / "guide.md").read_text() == "# Usage Guide"
    assert (ref_dir / "examples.md").read_text() == "# Examples"


async def test_materialize_plugin_skills_cleans_up_stale_plugin_dirs(
    tmp_path: Path,
) -> None:
    """SKRG-03: materialize_plugin_skills removes directories for uninstalled plugins."""
    from pilot_space.ai.agents.role_skill_materializer import materialize_plugin_skills

    mock_session = AsyncMock()
    workspace_id = uuid4()
    skills_dir = tmp_path / ".claude" / "skills"
    skills_dir.mkdir(parents=True)

    # Create a stale plugin-old-skill directory
    stale_dir = skills_dir / "plugin-old-skill"
    stale_dir.mkdir()
    (stale_dir / "SKILL.md").write_text("old content")

    # Only plugin-active is active
    plugin = _make_plugin(skill_name="active")

    with patch(
        "pilot_space.infrastructure.database.repositories.workspace_plugin_repository.WorkspacePluginRepository"
    ) as MockRepo:
        mock_repo = MockRepo.return_value
        mock_repo.get_active_by_workspace = AsyncMock(return_value=[plugin])

        await materialize_plugin_skills(
            db_session=mock_session,
            workspace_id=workspace_id,
            skills_dir=skills_dir,
        )

    # Stale dir should be cleaned up
    assert not stale_dir.exists()
    # Active plugin should exist
    assert (skills_dir / "plugin-active" / "SKILL.md").exists()


async def test_materialize_plugin_skills_handles_operational_error_gracefully(
    tmp_path: Path,
) -> None:
    """SKRG-03: materialize_plugin_skills handles OperationalError without crashing."""
    from sqlalchemy.exc import OperationalError

    from pilot_space.ai.agents.role_skill_materializer import materialize_plugin_skills

    mock_session = AsyncMock()
    workspace_id = uuid4()
    skills_dir = tmp_path / ".claude" / "skills"
    skills_dir.mkdir(parents=True)

    with patch(
        "pilot_space.infrastructure.database.repositories.workspace_plugin_repository.WorkspacePluginRepository"
    ) as MockRepo:
        mock_repo = MockRepo.return_value
        mock_repo.get_active_by_workspace = AsyncMock(
            side_effect=OperationalError("no such table", {}, None)
        )

        # Should not raise — returns 0
        count = await materialize_plugin_skills(
            db_session=mock_session,
            workspace_id=workspace_id,
            skills_dir=skills_dir,
        )

    assert count == 0
