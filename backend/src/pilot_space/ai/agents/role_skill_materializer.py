"""Role skill materializer for PilotSpaceAgent.

Writes user's role skills as SKILL.md files to the sandbox's `.claude/skills/`
directory so the Claude Agent SDK auto-discovers them.

Source: 011-role-based-skills, FR-006, FR-007, FR-008, FR-014
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING

from pilot_space.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)

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

    # Build set of expected role-skill directory names
    expected_dirs: set[str] = set()

    for skill in skills:
        dir_name = f"{_ROLE_SKILL_PREFIX}{skill.role_type}"
        expected_dirs.add(dir_name)
        skill_dir = skills_dir / dir_name

        frontmatter = _build_frontmatter(skill.role_name, skill.role_type, skill.is_primary)
        content = f"{frontmatter}\n{skill.skill_content}"

        await asyncio.to_thread(_write_skill_file, skill_dir, content)

    # WRSKL-03: Load active workspace skills as fallback (only for roles not covered by personal skills)
    # user_role_types is empty set when skills=[] — workspace skills are always considered for new members
    from sqlalchemy.exc import OperationalError

    from pilot_space.infrastructure.database.repositories.workspace_role_skill_repository import (
        WorkspaceRoleSkillRepository,
    )

    user_role_types = {s.role_type for s in skills}
    ws_repo = WorkspaceRoleSkillRepository(db_session)
    try:
        workspace_skills = await ws_repo.get_active_by_workspace(workspace_id)
    except OperationalError:
        # Table may not exist yet (pre-migration 073 environment or SQLite test DB).
        # Treat as empty — personal skills still materialized correctly.
        logger.debug(
            "workspace_role_skills table not accessible for workspace %s, skipping workspace skill injection",
            workspace_id,
        )
        workspace_skills = []
    for ws_skill in workspace_skills:
        if ws_skill.role_type in user_role_types:
            continue  # WRSKL-04: personal skill takes precedence
        dir_name = f"{_ROLE_SKILL_PREFIX}{ws_skill.role_type}"
        expected_dirs.add(dir_name)
        skill_dir = skills_dir / dir_name
        frontmatter = _build_workspace_frontmatter(ws_skill.role_name, ws_skill.role_type)
        content = f"{frontmatter}\n{ws_skill.skill_content}"
        await asyncio.to_thread(_write_skill_file, skill_dir, content)

    # FR-014: Clean up stale skill files from deleted/changed roles
    await asyncio.to_thread(_cleanup_stale_role_skills, skills_dir, expected_dirs)

    total_materialized = len(skills) + sum(
        1 for ws_skill in workspace_skills if ws_skill.role_type not in user_role_types
    )

    if total_materialized == 0:
        logger.debug(
            "No role skills to materialize for user %s in workspace %s",
            user_id,
            workspace_id,
        )
    else:
        logger.info(
            "Materialized %d role skills (%d personal, %d workspace-inherited) for user %s in workspace %s",
            total_materialized,
            len(skills),
            total_materialized - len(skills),
            user_id,
            workspace_id,
        )

    # SKRG-03: materialize plugin skills (workspace-scoped, all members)
    plugin_count = await materialize_plugin_skills(
        db_session=db_session,
        workspace_id=workspace_id,
        skills_dir=skills_dir,
    )
    total_materialized += plugin_count

    return total_materialized


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


def _build_workspace_frontmatter(role_name: str, role_type: str) -> str:
    """Build YAML frontmatter for workspace-inherited skill files.

    Args:
        role_name: Display name (e.g., "Senior Developer").
        role_type: Role type key (e.g., "developer").

    Returns:
        YAML frontmatter string including delimiters and origin: workspace marker.
    """
    lines = [
        "---",
        f"name: role-{role_type}",
        f'description: "{role_name}" workspace role skill (inherited)',
        "origin: workspace",
        "---",
    ]
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


# ---------------------------------------------------------------------------
# Plugin skill materialization (SKRG-03)
# ---------------------------------------------------------------------------

_PLUGIN_SKILL_PREFIX = "plugin-"


async def materialize_plugin_skills(
    db_session: AsyncSession,
    workspace_id: UUID,
    skills_dir: Path,
) -> int:
    """Write installed plugin skills to .claude/skills/ as plugin-{name}/SKILL.md.

    Also writes reference/ files alongside SKILL.md. Workspace-scoped:
    all members in a workspace get all active plugins.

    Handles OperationalError gracefully (pre-migration-074 or SQLite test DB).

    Args:
        db_session: Active database session.
        workspace_id: Current workspace UUID.
        skills_dir: Path to ``.claude/skills/`` in the sandbox.

    Returns:
        Number of plugin skills materialized.
    """
    from sqlalchemy.exc import OperationalError

    from pilot_space.infrastructure.database.repositories.workspace_plugin_repository import (
        WorkspacePluginRepository,
    )

    repo = WorkspacePluginRepository(db_session)
    try:
        plugins = await repo.get_active_by_workspace(workspace_id)
    except OperationalError:
        logger.debug(
            "workspace_plugins table not accessible for workspace %s, skipping plugin skill injection",
            workspace_id,
        )
        return 0

    expected_dirs: set[str] = set()
    for plugin in plugins:
        dir_name = f"{_PLUGIN_SKILL_PREFIX}{plugin.skill_name}"
        expected_dirs.add(dir_name)
        plugin_dir = skills_dir / dir_name
        await asyncio.to_thread(_write_plugin_files, plugin_dir, plugin)

    await asyncio.to_thread(_cleanup_stale_plugin_skills, skills_dir, expected_dirs)

    if plugins:
        logger.info(
            "Materialized %d plugin skills for workspace %s",
            len(plugins),
            workspace_id,
        )

    return len(plugins)


def _write_plugin_files(plugin_dir: Path, plugin: object) -> None:
    """Write SKILL.md and reference files for a plugin (runs in thread pool).

    Args:
        plugin_dir: Directory for this plugin (e.g., plugin-mcp-builder/).
        plugin: WorkspacePlugin entity with skill_content and references.
    """
    plugin_dir.mkdir(parents=True, exist_ok=True)
    skill_file = plugin_dir / "SKILL.md"
    skill_file.write_text(getattr(plugin, "skill_content", ""), encoding="utf-8")

    # Write reference files
    references = getattr(plugin, "references", []) or []
    if references:
        ref_dir = plugin_dir / "reference"
        ref_dir.mkdir(parents=True, exist_ok=True)
        for ref in references:
            filename = ref.get("filename", "")
            content = ref.get("content", "")
            if filename:
                (ref_dir / filename).write_text(content, encoding="utf-8")


def _cleanup_stale_plugin_skills(skills_dir: Path, expected_dirs: set[str]) -> None:
    """Remove plugin-skill directories that are no longer active.

    Only removes directories prefixed with ``plugin-``. Role skills and
    system skills are never touched.

    Args:
        skills_dir: Path to ``.claude/skills/``.
        expected_dirs: Set of directory names that should be kept.
    """
    if not skills_dir.exists():
        return

    import shutil

    for entry in skills_dir.iterdir():
        if entry.is_dir() and entry.name.startswith(_PLUGIN_SKILL_PREFIX):
            if entry.name not in expected_dirs:
                shutil.rmtree(entry, ignore_errors=True)
                logger.debug("Cleaned up stale plugin skill: %s", entry.name)


__all__ = [
    "_build_workspace_frontmatter",
    "materialize_plugin_skills",
    "materialize_role_skills",
]
