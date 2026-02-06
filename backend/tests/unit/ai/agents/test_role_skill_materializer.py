"""Unit tests for role_skill_materializer.

Tests filesystem materialization, YAML frontmatter generation,
and stale skill cleanup.

Source: 011-role-based-skills, FR-006, FR-007, FR-008, FR-014
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest

from pilot_space.ai.agents.role_skill_materializer import (
    _build_frontmatter,
    _cleanup_stale_role_skills,
    materialize_role_skills,
)
from pilot_space.infrastructure.database.models.user_role_skill import UserRoleSkill

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class TestBuildFrontmatter:
    """Tests for _build_frontmatter helper."""

    def test_standard_role(self) -> None:
        """Non-primary role produces standard frontmatter."""
        result = _build_frontmatter("Senior Developer", "developer", is_primary=False)
        assert result.startswith("---\n")
        assert result.endswith("\n---")
        assert "name: role-developer" in result
        assert 'description: "Senior Developer"' in result
        assert "priority" not in result

    def test_primary_role(self) -> None:
        """Primary role includes priority: primary."""
        result = _build_frontmatter("Lead Architect", "architect", is_primary=True)
        assert "priority: primary" in result
        assert "name: role-architect" in result


class TestCleanupStaleRoleSkills:
    """Tests for _cleanup_stale_role_skills helper."""

    def test_removes_stale_role_dirs(self, tmp_path: Path) -> None:
        """Removes role-* dirs not in expected set."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()

        # Create some role dirs
        (skills_dir / "role-developer").mkdir()
        (skills_dir / "role-developer" / "SKILL.md").write_text("content")
        (skills_dir / "role-tester").mkdir()
        (skills_dir / "role-tester" / "SKILL.md").write_text("content")

        # Only keep developer
        _cleanup_stale_role_skills(skills_dir, {"role-developer"})

        assert (skills_dir / "role-developer").exists()
        assert not (skills_dir / "role-tester").exists()

    def test_preserves_system_skills(self, tmp_path: Path) -> None:
        """System skills (without role- prefix) are never removed."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()

        (skills_dir / "extract-issues").mkdir()
        (skills_dir / "extract-issues" / "SKILL.md").write_text("content")

        _cleanup_stale_role_skills(skills_dir, set())

        assert (skills_dir / "extract-issues").exists()

    def test_handles_nonexistent_dir(self, tmp_path: Path) -> None:
        """Does not raise when skills_dir does not exist."""
        _cleanup_stale_role_skills(tmp_path / "nonexistent", set())


@pytest.mark.asyncio
class TestMaterializeRoleSkills:
    """Tests for materialize_role_skills using real DB session."""

    async def test_writes_skill_files(
        self,
        db_session: AsyncSession,
        tmp_path: Path,
    ) -> None:
        """Materializes role skills as SKILL.md files."""
        user_id = uuid4()
        workspace_id = uuid4()
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()

        # Seed user and workspace via raw model insert
        from pilot_space.infrastructure.database.models import User, Workspace

        user = User(id=user_id, email="mat-test@example.com")
        ws = Workspace(id=workspace_id, name="Mat WS", slug="mat-ws", owner_id=user_id)
        db_session.add(user)
        db_session.add(ws)
        await db_session.flush()

        skill = UserRoleSkill(
            id=uuid4(),
            user_id=user_id,
            workspace_id=workspace_id,
            role_type="developer",
            role_name="Senior Dev",
            skill_content="# Developer\n\nWrite clean code.",
            is_primary=True,
        )
        db_session.add(skill)
        await db_session.flush()

        count = await materialize_role_skills(
            db_session=db_session,
            user_id=user_id,
            workspace_id=workspace_id,
            skills_dir=skills_dir,
        )

        assert count == 1
        skill_file = skills_dir / "role-developer" / "SKILL.md"
        assert skill_file.exists()

        content = skill_file.read_text()
        assert "name: role-developer" in content
        assert "priority: primary" in content
        assert "# Developer" in content
        assert "Write clean code." in content

    async def test_no_skills_returns_zero(
        self,
        db_session: AsyncSession,
        tmp_path: Path,
    ) -> None:
        """FR-008: Returns 0 when user has no skills."""
        user_id = uuid4()
        workspace_id = uuid4()
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()

        from pilot_space.infrastructure.database.models import User, Workspace

        user = User(id=user_id, email="empty-mat@example.com")
        ws = Workspace(id=workspace_id, name="Empty WS", slug="empty-ws", owner_id=user_id)
        db_session.add(user)
        db_session.add(ws)
        await db_session.flush()

        count = await materialize_role_skills(
            db_session=db_session,
            user_id=user_id,
            workspace_id=workspace_id,
            skills_dir=skills_dir,
        )

        assert count == 0

    async def test_cleans_up_stale_on_materialize(
        self,
        db_session: AsyncSession,
        tmp_path: Path,
    ) -> None:
        """FR-014: Stale role skill directories are removed."""
        user_id = uuid4()
        workspace_id = uuid4()
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()

        # Pre-create a stale role skill dir
        stale_dir = skills_dir / "role-tester"
        stale_dir.mkdir()
        (stale_dir / "SKILL.md").write_text("old content")

        from pilot_space.infrastructure.database.models import User, Workspace

        user = User(id=user_id, email="stale-mat@example.com")
        ws = Workspace(id=workspace_id, name="Stale WS", slug="stale-ws", owner_id=user_id)
        db_session.add(user)
        db_session.add(ws)
        await db_session.flush()

        # User has a developer skill but NOT tester
        skill = UserRoleSkill(
            id=uuid4(),
            user_id=user_id,
            workspace_id=workspace_id,
            role_type="developer",
            role_name="Dev",
            skill_content="# Developer",
            is_primary=False,
        )
        db_session.add(skill)
        await db_session.flush()

        await materialize_role_skills(
            db_session=db_session,
            user_id=user_id,
            workspace_id=workspace_id,
            skills_dir=skills_dir,
        )

        # Stale tester dir should be removed
        assert not stale_dir.exists()
        # Developer dir should exist
        assert (skills_dir / "role-developer" / "SKILL.md").exists()

    async def test_multiple_skills_materialized(
        self,
        db_session: AsyncSession,
        tmp_path: Path,
    ) -> None:
        """Multiple role skills are all written."""
        user_id = uuid4()
        workspace_id = uuid4()
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()

        from pilot_space.infrastructure.database.models import User, Workspace

        user = User(id=user_id, email="multi-mat@example.com")
        ws = Workspace(id=workspace_id, name="Multi WS", slug="multi-ws", owner_id=user_id)
        db_session.add(user)
        db_session.add(ws)
        await db_session.flush()

        for role_type, is_primary in [("developer", True), ("tester", False)]:
            db_session.add(
                UserRoleSkill(
                    id=uuid4(),
                    user_id=user_id,
                    workspace_id=workspace_id,
                    role_type=role_type,
                    role_name=f"{role_type.title()} Role",
                    skill_content=f"# {role_type.title()}",
                    is_primary=is_primary,
                )
            )
        await db_session.flush()

        count = await materialize_role_skills(
            db_session=db_session,
            user_id=user_id,
            workspace_id=workspace_id,
            skills_dir=skills_dir,
        )

        assert count == 2
        assert (skills_dir / "role-developer" / "SKILL.md").exists()
        assert (skills_dir / "role-tester" / "SKILL.md").exists()

        # Check primary frontmatter
        dev_content = (skills_dir / "role-developer" / "SKILL.md").read_text()
        assert "priority: primary" in dev_content

        tester_content = (skills_dir / "role-tester" / "SKILL.md").read_text()
        assert "priority" not in tester_content
