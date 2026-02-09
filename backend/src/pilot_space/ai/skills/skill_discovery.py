"""Skill discovery service.

Scans the skills template directory, parses YAML frontmatter from each
SKILL.md, merges with UI metadata, and returns a list of user-invocable skills.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from pilot_space.ai.skills.skill_metadata import get_skill_ui_metadata

logger = logging.getLogger(__name__)

# Triggers that indicate the skill is NOT user-invocable via slash command
_NON_INVOCABLE_TRIGGERS = frozenset({"scheduled", "intent_detection"})

# Compiled once, reused for every parse
_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)


@dataclass(frozen=True, slots=True)
class SkillInfo:
    """Parsed skill definition ready for API response."""

    name: str
    description: str
    category: str
    icon: str
    examples: list[str] = field(default_factory=list)


def discover_skills(skills_dir: Path) -> list[SkillInfo]:
    """Discover all user-invocable skills from the templates directory.

    Args:
        skills_dir: Path to the ``templates/skills/`` directory.

    Returns:
        Sorted list of :class:`SkillInfo` for skills that are user-invocable.
    """
    if not skills_dir.is_dir():
        logger.warning("Skills directory not found: %s", skills_dir)
        return []

    skills: list[SkillInfo] = []

    for skill_dir in sorted(skills_dir.iterdir()):
        if not skill_dir.is_dir():
            continue

        skill_file = skill_dir / "SKILL.md"
        if not skill_file.exists():
            continue

        try:
            info = _parse_skill_file(skill_file)
            if info is not None:
                skills.append(info)
        except Exception:
            logger.warning("Failed to parse skill %s", skill_file, exc_info=True)

    return skills


def _parse_skill_file(skill_file: Path) -> SkillInfo | None:
    """Parse a single SKILL.md and return a SkillInfo, or None if not invocable."""
    content = skill_file.read_text(encoding="utf-8")

    match = _FRONTMATTER_RE.match(content)
    if not match:
        logger.warning("Missing YAML frontmatter in %s", skill_file)
        return None

    frontmatter: dict[str, object] = yaml.safe_load(match.group(1)) or {}

    # Filter out non-invocable skills (scheduled cron jobs, intent-only)
    trigger = str(frontmatter.get("trigger", ""))
    if trigger in _NON_INVOCABLE_TRIGGERS:
        logger.debug(
            "Skipping non-invocable skill %s (trigger=%s)", skill_file.parent.name, trigger
        )
        return None

    name = str(frontmatter.get("name", "")) or skill_file.parent.name
    description = str(frontmatter.get("description", ""))

    ui = get_skill_ui_metadata(name)

    return SkillInfo(
        name=name,
        description=description,
        category=ui.category,
        icon=ui.icon,
        examples=list(ui.examples),
    )
