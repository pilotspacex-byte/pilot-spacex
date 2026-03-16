"""Role skill materializer for PilotSpaceAgent.

Writes user's skills as SKILL.md files to the sandbox's `.claude/skills/`
directory so the Claude Agent SDK auto-discovers them.

Primary path: reads from user_skills + skill_templates tables (Phase 20).
Fallback path: reads from user_role_skills + workspace_role_skills (legacy).
OperationalError on new tables triggers fallback automatically.

Source: 011-role-based-skills, FR-006, FR-007, FR-008, FR-014, Phase 20
"""

from __future__ import annotations

import asyncio
import re
from pathlib import Path
from typing import TYPE_CHECKING

from pilot_space.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)

# Prefix used for skill directories to distinguish from system skills
_SKILL_PREFIX = "skill-"
# Legacy prefix for transition cleanup (Phase 20: role- -> skill-)
_LEGACY_ROLE_PREFIX = "role-"


def _sanitize_skill_dir_name(name: str, fallback_id: str) -> str:
    """Sanitize a skill name for use as a directory name.

    Lowercases, replaces non-alphanumeric runs with hyphens,
    strips leading/trailing hyphens. Falls back to truncated ID
    if result is empty.

    Args:
        name: Display name to sanitize.
        fallback_id: UUID string to use if name sanitizes to empty.

    Returns:
        Sanitized directory-safe name.
    """
    sanitized = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    if not sanitized:
        return fallback_id[:8]
    return sanitized


async def materialize_role_skills(
    db_session: AsyncSession,
    user_id: UUID,
    workspace_id: UUID,
    skills_dir: Path,
) -> int:
    """Write user's skills to the skills directory as SKILL.md files.

    Tries new tables (user_skills + skill_templates) first.
    Falls back to legacy tables on OperationalError.
    Always calls materialize_plugin_skills at the end.

    Args:
        db_session: Active database session.
        user_id: Current user UUID.
        workspace_id: Current workspace UUID.
        skills_dir: Path to ``.claude/skills/`` in the sandbox.

    Returns:
        Number of skills materialized (0 if user has none).
    """
    from sqlalchemy.exc import OperationalError

    try:
        count = await _materialize_from_new_tables(db_session, user_id, workspace_id, skills_dir)
    except OperationalError:
        logger.debug(
            "New skill tables not accessible for user %s workspace %s, falling back to legacy",
            user_id,
            workspace_id,
        )
        count = await _materialize_from_legacy_tables(db_session, user_id, workspace_id, skills_dir)

    # SKRG-03: materialize plugin skills (workspace-scoped, all members)
    plugin_count = await materialize_plugin_skills(
        db_session=db_session,
        workspace_id=workspace_id,
        skills_dir=skills_dir,
    )
    count += plugin_count

    return count


async def _materialize_from_new_tables(
    db_session: AsyncSession,
    user_id: UUID,
    workspace_id: UUID,
    skills_dir: Path,
) -> int:
    """Materialize skills from user_skills and skill_templates tables.

    1. Load user's active user_skills, write each as SKILL.md.
    2. Load active skill_templates for workspace.
    3. For templates not covered by user skills, write as workspace fallback.
    4. Clean up stale skill-* dirs.

    Args:
        db_session: Active database session.
        user_id: Current user UUID.
        workspace_id: Current workspace UUID.
        skills_dir: Path to ``.claude/skills/`` in the sandbox.

    Returns:
        Number of skills materialized.
    """
    from pilot_space.infrastructure.database.repositories.skill_template_repository import (
        SkillTemplateRepository,
    )
    from pilot_space.infrastructure.database.repositories.user_skill_repository import (
        UserSkillRepository,
    )

    user_repo = UserSkillRepository(db_session)
    template_repo = SkillTemplateRepository(db_session)

    # Load user's active skills (materializer needs only is_active=True)
    user_skills = await user_repo.get_active_by_user_workspace(user_id, workspace_id)

    expected_dirs: set[str] = set()
    covered_template_ids: set[UUID] = set()

    for skill in user_skills:
        # Determine name from template or fallback
        skill_id_str = str(skill.id)
        if skill.template is not None:
            name = _sanitize_skill_dir_name(skill.template.name, skill_id_str)
        else:
            name = _sanitize_skill_dir_name("", skill_id_str)

        dir_name = f"{_SKILL_PREFIX}{name}-{skill_id_str[:6]}"
        expected_dirs.add(dir_name)
        skill_dir = skills_dir / dir_name

        frontmatter = _build_frontmatter(
            name=skill.template.name if skill.template else skill_id_str[:8],
            skill_id=skill_id_str,
        )
        content = f"{frontmatter}\n{skill.skill_content}"
        await asyncio.to_thread(_write_skill_file, skill_dir, content)

        if skill.template_id is not None:
            covered_template_ids.add(skill.template_id)

    # Workspace template fallback: active templates without user skill
    templates = await template_repo.get_active_by_workspace(workspace_id)
    workspace_fallback_count = 0

    for template in templates:
        if template.id in covered_template_ids:
            continue
        template_id_str = str(template.id)
        name = _sanitize_skill_dir_name(template.name, template_id_str)
        dir_name = f"{_SKILL_PREFIX}{name}-{template_id_str[:6]}"
        expected_dirs.add(dir_name)
        skill_dir = skills_dir / dir_name

        frontmatter = _build_workspace_frontmatter(
            name=template.name,
            template_id=template_id_str,
        )
        content = f"{frontmatter}\n{template.skill_content}"
        await asyncio.to_thread(_write_skill_file, skill_dir, content)
        workspace_fallback_count += 1

    # Clean up stale skill dirs
    await asyncio.to_thread(_cleanup_stale_role_skills, skills_dir, expected_dirs)

    total = len(user_skills) + workspace_fallback_count

    if total == 0:
        logger.debug(
            "No skills to materialize for user %s in workspace %s",
            user_id,
            workspace_id,
        )
    else:
        logger.info(
            "Materialized %d skills (%d personal, %d workspace-fallback) for user %s in workspace %s",
            total,
            len(user_skills),
            workspace_fallback_count,
            user_id,
            workspace_id,
        )

    return total


async def _materialize_from_legacy_tables(
    db_session: AsyncSession,
    user_id: UUID,
    workspace_id: UUID,
    skills_dir: Path,
) -> int:
    """Materialize skills from legacy user_role_skills + workspace_role_skills.

    This is the pre-Phase-20 path, kept for backward compatibility until
    migration 077 is applied everywhere.

    Args:
        db_session: Active database session.
        user_id: Current user UUID.
        workspace_id: Current workspace UUID.
        skills_dir: Path to ``.claude/skills/`` in the sandbox.

    Returns:
        Number of role skills materialized.
    """
    from pilot_space.infrastructure.database.repositories.role_skill_repository import (
        RoleSkillRepository,
    )

    repo = RoleSkillRepository(db_session)
    skills = await repo.get_by_user_workspace(user_id, workspace_id)

    expected_dirs: set[str] = set()

    for skill in skills:
        dir_name = f"{_SKILL_PREFIX}{skill.role_type}"
        expected_dirs.add(dir_name)
        skill_dir = skills_dir / dir_name

        frontmatter = _build_legacy_frontmatter(skill.role_name, skill.role_type, skill.is_primary)
        content = f"{frontmatter}\n{skill.skill_content}"
        await asyncio.to_thread(_write_skill_file, skill_dir, content)

    # WRSKL-03: workspace skills fallback
    from sqlalchemy.exc import OperationalError

    from pilot_space.infrastructure.database.repositories.workspace_role_skill_repository import (
        WorkspaceRoleSkillRepository,
    )

    user_role_types = {s.role_type for s in skills}
    ws_repo = WorkspaceRoleSkillRepository(db_session)
    try:
        workspace_skills = await ws_repo.get_active_by_workspace(workspace_id)
    except OperationalError:
        logger.debug(
            "workspace_role_skills table not accessible for workspace %s, skipping",
            workspace_id,
        )
        workspace_skills = []

    for ws_skill in workspace_skills:
        if ws_skill.role_type in user_role_types:
            continue
        dir_name = f"{_SKILL_PREFIX}{ws_skill.role_type}"
        expected_dirs.add(dir_name)
        skill_dir = skills_dir / dir_name
        frontmatter = _build_legacy_workspace_frontmatter(ws_skill.role_name, ws_skill.role_type)
        content = f"{frontmatter}\n{ws_skill.skill_content}"
        await asyncio.to_thread(_write_skill_file, skill_dir, content)

    await asyncio.to_thread(_cleanup_stale_role_skills, skills_dir, expected_dirs)

    total = len(skills) + sum(
        1 for ws_skill in workspace_skills if ws_skill.role_type not in user_role_types
    )

    if total == 0:
        logger.debug(
            "No role skills to materialize for user %s in workspace %s",
            user_id,
            workspace_id,
        )
    else:
        logger.info(
            "Materialized %d legacy role skills for user %s in workspace %s",
            total,
            user_id,
            workspace_id,
        )

    return total


def _write_skill_file(skill_dir: Path, content: str) -> None:
    """Write a single SKILL.md file (runs in thread pool)."""
    skill_dir.mkdir(parents=True, exist_ok=True)
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text(content, encoding="utf-8")


def _build_frontmatter(name: str, skill_id: str) -> str:
    """Build YAML frontmatter for a personal skill SKILL.md file.

    Args:
        name: Display name for the skill.
        skill_id: Skill UUID string.

    Returns:
        YAML frontmatter string including delimiters.
    """
    sanitized = _sanitize_skill_dir_name(name, skill_id)
    lines = [
        "---",
        f"name: skill-{sanitized}",
        f'description: "{name}" skill for AI context personalization',
        "origin: personal",
        "---",
    ]
    return "\n".join(lines)


def _build_workspace_frontmatter(name: str, template_id: str) -> str:
    """Build YAML frontmatter for workspace template fallback skill files.

    Args:
        name: Template display name.
        template_id: Template UUID string.

    Returns:
        YAML frontmatter string including delimiters and origin: workspace.
    """
    sanitized = _sanitize_skill_dir_name(name, template_id)
    lines = [
        "---",
        f"name: skill-{sanitized}",
        f'description: "{name}" workspace skill (inherited)',
        "origin: workspace",
        "---",
    ]
    return "\n".join(lines)


def _build_legacy_frontmatter(role_name: str, role_type: str, is_primary: bool) -> str:
    """Build YAML frontmatter for legacy role skill SKILL.md file.

    Args:
        role_name: Display name (e.g., "Senior Developer").
        role_type: Role type key (e.g., "developer").
        is_primary: Whether this is the user's primary role.

    Returns:
        YAML frontmatter string including delimiters.
    """
    lines = [
        "---",
        f"name: skill-{role_type}",
        f'description: "{role_name}" skill for AI context personalization',
    ]
    if is_primary:
        lines.append("priority: primary")
    lines.append("---")
    return "\n".join(lines)


def _build_legacy_workspace_frontmatter(role_name: str, role_type: str) -> str:
    """Build YAML frontmatter for legacy workspace-inherited skill files.

    Args:
        role_name: Display name.
        role_type: Role type key.

    Returns:
        YAML frontmatter string including delimiters and origin: workspace.
    """
    lines = [
        "---",
        f"name: skill-{role_type}",
        f'description: "{role_name}" workspace skill (inherited)',
        "origin: workspace",
        "---",
    ]
    return "\n".join(lines)


def _cleanup_stale_role_skills(skills_dir: Path, expected_dirs: set[str]) -> None:
    """Remove skill directories that are no longer active.

    Removes directories prefixed with ``skill-`` that are not in the
    expected set.  Also removes legacy ``role-`` directories from before
    the Phase 20 rename.  System skills (e.g., ``extract-issues``) and
    plugin skills (``plugin-``) are never touched.

    Args:
        skills_dir: Path to ``.claude/skills/``.
        expected_dirs: Set of directory names that should be kept.
    """
    if not skills_dir.exists():
        return

    import shutil

    for entry in skills_dir.iterdir():
        if not entry.is_dir():
            continue
        # Clean legacy role- dirs unconditionally (Phase 20 transition)
        if entry.name.startswith(_LEGACY_ROLE_PREFIX):
            shutil.rmtree(entry, ignore_errors=True)
            logger.debug("Cleaned up legacy role skill: %s", entry.name)
        elif entry.name.startswith(_SKILL_PREFIX):
            if entry.name not in expected_dirs:
                shutil.rmtree(entry, ignore_errors=True)
                logger.debug("Cleaned up stale skill: %s", entry.name)


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
    "_LEGACY_ROLE_PREFIX",
    "_SKILL_PREFIX",
    "_build_frontmatter",
    "_build_workspace_frontmatter",
    "_cleanup_stale_role_skills",
    "_sanitize_skill_dir_name",
    "materialize_plugin_skills",
    "materialize_role_skills",
]
