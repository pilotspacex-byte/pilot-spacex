"""SkillDefinition: parses YAML frontmatter from SKILL.md files.

T-044: SkillExecutionService — skill definition loading
Feature 015: AI Workforce Platform — Sprint 2
"""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

import yaml


class ApprovalMode(StrEnum):
    """Approval modes for skill executions (DD-003)."""

    AUTO = "auto"
    SUGGEST = "suggest"
    REQUIRE = "require"


class RequiredApprovalRole(StrEnum):
    """Minimum workspace role required to approve (C-7)."""

    ADMIN = "admin"
    MEMBER = "member"


_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)

# Base path for skill templates
_SKILLS_BASE_PATH = Path(__file__).parent.parent.parent.parent / "ai" / "templates" / "skills"


class SkillDefinitionError(ValueError):
    """Raised when a SKILL.md file is malformed or missing required fields."""


@dataclass(frozen=True, slots=True)
class SkillDefinition:
    """Parsed representation of a SKILL.md frontmatter block.

    Attributes:
        name: Unique skill identifier (e.g. 'generate-code').
        description: Human-readable skill description.
        model: LLM tier to use ('opus', 'sonnet', 'flash').
        tools: MCP tool names the skill is permitted to call.
        approval: Approval mode (auto / suggest / require).
        required_approval_role: Minimum role required to approve; None = no role gate.
    """

    name: str
    description: str
    model: str
    tools: list[str]
    approval: ApprovalMode
    required_approval_role: RequiredApprovalRole | None


class SkillDefinitionParser:
    """Parses SKILL.md files from the templates directory.

    Example:
        parser = SkillDefinitionParser()
        defn = parser.parse("generate-code")
    """

    def __init__(self, skills_base_path: Path | None = None) -> None:
        self._base = skills_base_path or _SKILLS_BASE_PATH

    async def parse(self, skill_name: str) -> SkillDefinition:
        """Parse SKILL.md frontmatter for the given skill name.

        Args:
            skill_name: Directory name under templates/skills/ (e.g. 'generate-code').

        Returns:
            Parsed SkillDefinition dataclass.

        Raises:
            SkillDefinitionError: If file not found, no frontmatter, or required fields missing.
        """
        skill_file = self._base / skill_name / "SKILL.md"
        if not skill_file.exists():
            msg = f"SKILL.md not found for skill: {skill_name!r}"
            raise SkillDefinitionError(msg)

        loop = asyncio.get_running_loop()
        raw = await loop.run_in_executor(None, lambda: skill_file.read_text(encoding="utf-8"))
        return self._parse_raw(raw, skill_name)

    def _parse_raw(self, raw: str, skill_name: str) -> SkillDefinition:
        match = _FRONTMATTER_RE.match(raw)
        if not match:
            msg = f"No YAML frontmatter found in SKILL.md for: {skill_name!r}"
            raise SkillDefinitionError(msg)

        try:
            data: dict[str, Any] = yaml.safe_load(match.group(1)) or {}
        except yaml.YAMLError as exc:
            msg = f"Invalid YAML frontmatter in SKILL.md for {skill_name!r}: {exc}"
            raise SkillDefinitionError(msg) from exc

        return self._build(data, skill_name)

    def _build(self, data: dict[str, Any], skill_name: str) -> SkillDefinition:
        missing = [f for f in ("name", "description", "model", "approval") if f not in data]
        if missing:
            msg = f"SKILL.md for {skill_name!r} is missing required fields: {missing}"
            raise SkillDefinitionError(msg)

        try:
            approval = ApprovalMode(data["approval"])
        except ValueError as exc:
            msg = f"Invalid approval mode {data['approval']!r} in SKILL.md for {skill_name!r}"
            raise SkillDefinitionError(msg) from exc

        raw_role = data.get("required_approval_role")
        required_approval_role: RequiredApprovalRole | None = None
        if raw_role is not None:
            try:
                required_approval_role = RequiredApprovalRole(raw_role)
            except ValueError as exc:
                msg = f"Invalid required_approval_role {raw_role!r} in SKILL.md for {skill_name!r}"
                raise SkillDefinitionError(msg) from exc

        raw_tools = data.get("tools", [])
        if isinstance(raw_tools, str):
            # Tolerate comma-separated string
            tools: list[str] = [t.strip() for t in raw_tools.split(",") if t.strip()]
        else:
            tools = list(raw_tools)

        return SkillDefinition(
            name=str(data["name"]),
            description=str(data["description"]),
            model=str(data["model"]),
            tools=tools,
            approval=approval,
            required_approval_role=required_approval_role,
        )


__all__ = [
    "ApprovalMode",
    "RequiredApprovalRole",
    "SkillDefinition",
    "SkillDefinitionError",
    "SkillDefinitionParser",
]
