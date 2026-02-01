"""Project bootstrapper for hydrating user workspaces.

Copies system-provided skills, commands, and rules into user workspaces.
Uses dirs_exist_ok=True to update system files while preserving user content.

Reference: docs/architect/scalable-agent-architecture.md
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)


class ProjectBootstrapper:
    """Hydrates user spaces with system-provided .claude content.

    The bootstrapper copies templates from the backend's ai/templates/
    directory into user workspaces. This ensures:
    1. All users have access to system skills
    2. User-created skills/commands are preserved
    3. System updates propagate to existing workspaces

    Attributes:
        templates_dir: Path to backend/src/pilot_space/ai/templates/
    """

    def __init__(self, templates_dir: Path | str) -> None:
        """Initialize bootstrapper.

        Args:
            templates_dir: Path to templates directory containing
                skills/, rules/, and CLAUDE.md.
        """
        self._templates_dir = Path(templates_dir)
        if not self._templates_dir.exists():
            logger.warning(f"Templates directory not found: {self._templates_dir}")

    async def hydrate(self, target_path: Path) -> None:
        """Copy system skills/commands/rules to target space.

        This method is idempotent and safe to call multiple times.
        Uses dirs_exist_ok=True to update system files while preserving
        user-created content that doesn't conflict with system files.

        Args:
            target_path: Root path of user's workspace.

        Raises:
            OSError: If file operations fail.
        """
        claude_dir = target_path / ".claude"
        claude_dir.mkdir(parents=True, exist_ok=True)

        # Copy system skills (8 skills in templates/skills/)
        await self._copy_if_exists("skills", claude_dir)

        # Copy system rules
        await self._copy_if_exists("rules", claude_dir)

        # Copy CLAUDE.md (system instructions)
        src_claude = self._templates_dir / "CLAUDE.md"
        if src_claude.exists():
            dst_claude = claude_dir / "CLAUDE.md"
            # Only copy if destination doesn't exist or is older
            if not dst_claude.exists() or self._should_update(src_claude, dst_claude):
                shutil.copy2(src_claude, dst_claude)
                logger.debug(f"Copied CLAUDE.md to {dst_claude}")

        # Remove stale .mcp.json from previous file-based MCP approach
        # (note tools are now in-process SDK custom tools)
        stale_mcp = target_path / ".mcp.json"
        if stale_mcp.exists():
            stale_mcp.unlink()
            logger.debug(f"Removed stale .mcp.json from {target_path}")

        logger.info(f"Hydrated workspace at {target_path}")

    async def _copy_if_exists(self, subdir: str, claude_dir: Path) -> None:
        """Copy a subdirectory if it exists in templates.

        Args:
            subdir: Subdirectory name (skills, rules, etc.)
            claude_dir: Target .claude directory
        """
        src_dir = self._templates_dir / subdir
        if src_dir.exists():
            dst_dir = claude_dir / subdir
            shutil.copytree(src_dir, dst_dir, dirs_exist_ok=True)
            logger.debug(f"Copied {subdir}/ to {dst_dir}")

    def _should_update(self, src: Path, dst: Path) -> bool:
        """Check if destination file should be updated.

        Args:
            src: Source file path
            dst: Destination file path

        Returns:
            True if source is newer than destination.
        """
        if not dst.exists():
            return True
        return src.stat().st_mtime > dst.stat().st_mtime

    async def hydrate_skill(self, skill_name: str, target_path: Path) -> bool:
        """Hydrate a single skill to target workspace.

        Useful for on-demand skill loading without full hydration.

        Args:
            skill_name: Name of skill to hydrate (e.g., "extract-issues")
            target_path: Root path of user's workspace.

        Returns:
            True if skill was hydrated, False if not found.
        """
        src_skill = self._templates_dir / "skills" / skill_name
        if not src_skill.exists():
            return False

        dst_skill = target_path / ".claude" / "skills" / skill_name
        dst_skill.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(src_skill, dst_skill, dirs_exist_ok=True)
        logger.debug(f"Hydrated skill {skill_name} to {dst_skill}")
        return True
