"""AI agent templates for workspace hydration.

This module provides system templates that are copied into user workspaces
during space preparation. Templates include:
- CLAUDE.md: Agent instructions and tool documentation
- skills/: Pre-built AI workflows
- rules/: Code quality and pattern rules
"""

from __future__ import annotations

from pathlib import Path

# Path to the CLAUDE.md template file
CLAUDE_MD_PATH = Path(__file__).parent / "CLAUDE.md"

__all__ = ["CLAUDE_MD_PATH"]
