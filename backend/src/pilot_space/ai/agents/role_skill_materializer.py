"""Role skill materializer for PilotSpaceAgent.

Writes user's role skills as SKILL.md files to the sandbox's `.claude/skills/`
directory so the Claude Agent SDK auto-discovers them.

Source: 011-role-based-skills, FR-006, FR-007, FR-008, FR-014
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Prefix used for role skill directories to distinguish from system skills
_ROLE_SKILL_PREFIX = "role-"


async def materialize_role_skills(
    db_session: AsyncSession,
    user_id: UUID,
    workspace_id: UUID,
    skills_dir: Path,
) -> int:
    """Write user's role skills to the skills directory as SKILL.md files.

    Each role skill is written as ``role-{role_type}/SKILL.md`` with YAML
    frontmatter.  Primary role gets ``priority: primary`` in frontmatter.
    Stale role-skill directories (from deleted/changed roles) are cleaned up.

    File I/O is offloaded to a thread pool via ``asyncio.to_thread`` to avoid
    blocking the event loop (H-28-1 fix).

    Args:
        db_session: Active database session.
        user_id: Current user UUID.
        workspace_id: Current workspace UUID.
        skills_dir: Path to ``.claude/skills/`` in the sandbox.

    Returns:
        Number of role skills materialized (0 if user has none - FR-008).
    """
    from pilot_space.infrastructure.database.repositories.role_skill_repository import (
        RoleSkillRepository,
    )

    repo = RoleSkillRepository(db_session)
    skills = await repo.get_by_user_workspace(user_id, workspace_id)

    # FR-008: If no skills exist, skip materialization (agent uses generic behavior)
    if not skills:
        await asyncio.to_thread(_cleanup_stale_role_skills, skills_dir, set())
        return 0

    # Build set of expected role-skill directory names
    expected_dirs: set[str] = set()

    for skill in skills:
        dir_name = f"{_ROLE_SKILL_PREFIX}{skill.role_type}"
        expected_dirs.add(dir_name)
        skill_dir = skills_dir / dir_name

        frontmatter = _build_frontmatter(skill.role_name, skill.role_type, skill.is_primary)
        content = f"{frontmatter}\n{skill.skill_content}"

        await asyncio.to_thread(_write_skill_file, skill_dir, content)

    # FR-014: Clean up stale skill files from deleted/changed roles
    await asyncio.to_thread(_cleanup_stale_role_skills, skills_dir, expected_dirs)

    logger.info(
        "Materialized %d role skills for user %s in workspace %s",
        len(skills),
        user_id,
        workspace_id,
    )
    return len(skills)


def _write_skill_file(skill_dir: Path, content: str) -> None:
    """Write a single SKILL.md file (runs in thread pool)."""
    skill_dir.mkdir(parents=True, exist_ok=True)
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text(content, encoding="utf-8")


def _build_frontmatter(role_name: str, role_type: str, is_primary: bool) -> str:
    """Build YAML frontmatter for a role skill SKILL.md file.

    Args:
        role_name: Display name (e.g., "Senior Developer").
        role_type: Role type key (e.g., "developer").
        is_primary: Whether this is the user's primary role.

    Returns:
        YAML frontmatter string including delimiters.
    """
    lines = [
        "---",
        f"name: role-{role_type}",
        f'description: "{role_name}" role skill for AI context personalization',
    ]
    if is_primary:
        lines.append("priority: primary")
    lines.append("---")
    return "\n".join(lines)


def _cleanup_stale_role_skills(skills_dir: Path, expected_dirs: set[str]) -> None:
    """Remove role-skill directories that are no longer active.

    Only removes directories prefixed with ``role-``.  System skills
    (e.g., ``extract-issues``) are never touched.

    Args:
        skills_dir: Path to ``.claude/skills/``.
        expected_dirs: Set of directory names that should be kept.
    """
    if not skills_dir.exists():
        return

    import shutil

    for entry in skills_dir.iterdir():
        if entry.is_dir() and entry.name.startswith(_ROLE_SKILL_PREFIX):
            if entry.name not in expected_dirs:
                shutil.rmtree(entry, ignore_errors=True)
                logger.debug("Cleaned up stale role skill: %s", entry.name)


__all__ = ["materialize_role_skills"]
