"""Domain-layer enumerations shared across application and infrastructure layers.

Defining enums here avoids coupling schemas or services to infrastructure models.
Infrastructure models import from this module rather than defining their own.
"""

from __future__ import annotations

import enum


class BindingType(enum.StrEnum):
    """Type of action button binding."""

    SKILL = "skill"
    MCP_TOOL = "mcp_tool"


__all__ = ["BindingType"]
