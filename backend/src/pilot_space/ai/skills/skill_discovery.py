"""Skill discovery service.

Scans the skills template directory, parses YAML frontmatter from each
SKILL.md, merges with UI metadata, and returns a list of user-invocable skills.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from pilot_space.ai.skills.skill_metadata import get_skill_ui_metadata
from pilot_space.infrastructure.logging import get_logger

logger = get_logger(__name__)

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
    feature_module: list[str] | None = field(default=None)


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

    # Parse feature_module — normalize single string to list.
    # Invalid types (int, dict, bool, etc.) produce [] so the skill is gated
    # out rather than bypassing feature checks via the None="always keep" path.
    raw_module = frontmatter.get("feature_module")
    feature_module: list[str] | None = None
    if isinstance(raw_module, str):
        feature_module = [raw_module]
    elif isinstance(raw_module, list):
        feature_module = [str(m) for m in raw_module]
    elif raw_module is not None:
        # Malformed value — restrict rather than bypass gating.
        feature_module = []

    ui = get_skill_ui_metadata(name)

    return SkillInfo(
        name=name,
        description=description,
        category=ui.category,
        icon=ui.icon,
        examples=list(ui.examples),
        feature_module=feature_module,
    )


def filter_skills_by_features(
    skills: list[SkillInfo],
    feature_toggles: dict[str, bool],
) -> list[SkillInfo]:
    """Filter skills based on workspace feature toggles.

    A skill is removed only when ALL of its feature_module values are
    disabled.  Skills with ``feature_module=None`` (no gate declared) are
    always kept.  Skills with ``feature_module=[]`` (malformed/unknown gate)
    are always removed — ``any()`` over an empty iterable is False.

    Callers are expected to pass a fully-populated toggle dict (schema
    defaults merged with stored overrides) so that missing keys are not
    silently treated as enabled or disabled.  The fallback default here
    is ``False`` (disabled) to be conservative — the normalisation in
    pilotspace_agent._build_stream_config is the canonical source of truth.

    Args:
        skills: List of discovered skills.
        feature_toggles: Fully-populated mapping of feature key to
            enabled/disabled state (defaults already merged by caller).

    Returns:
        Filtered list of skills that are available in this workspace.
    """
    result: list[SkillInfo] = []
    for skill in skills:
        if skill.feature_module is None:
            result.append(skill)
            continue
        # Keep if ANY listed module is enabled.
        # Default to False: a missing key means the caller didn't normalise
        # properly; being conservative avoids exposing disabled-feature tools.
        if any(feature_toggles.get(m, False) for m in skill.feature_module):
            result.append(skill)
    return result
