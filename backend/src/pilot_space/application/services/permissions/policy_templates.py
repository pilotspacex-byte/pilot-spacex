"""Pre-baked policy templates for bulk permission application.

Phase 69 — PERM-05. Three templates map every known tool to a
``ToolPermissionMode``:

* **conservative** — every non-critical tool is ``ask``; read-only
  tools (``AUTO_EXECUTE`` classification) remain ``auto``; critical
  tools remain ``ask``.
* **standard** — mirror the DD-003 default from
  ``permission_handler.ACTION_CLASSIFICATIONS``. Applying this
  template is equivalent to removing all rows.
* **trusted** — every non-critical tool is ``auto``; critical tools
  stay ``ask`` (DD-003 invariant — they can never be ``auto``).

Templates are built at import time from ``ALL_TOOL_NAMES`` and
``ACTION_CLASSIFICATIONS`` so the inventory stays in lock-step with
the MCP server definitions.
"""

from __future__ import annotations

from pilot_space.ai.agents.pilotspace_agent_helpers import ALL_TOOL_NAMES
from pilot_space.ai.sdk.permission_handler import (
    ActionClassification,
    PermissionHandler,
)
from pilot_space.domain.permissions.tool_permission_mode import ToolPermissionMode

# Expose module-local alias for the DD-003 classification map.
ACTION_CLASSIFICATIONS: dict[str, ActionClassification] = (
    PermissionHandler.ACTION_CLASSIFICATIONS
)


def _classification_to_mode(c: ActionClassification) -> ToolPermissionMode:
    """Map DD-003 default classification to a ``ToolPermissionMode``."""
    if c is ActionClassification.AUTO_EXECUTE:
        return ToolPermissionMode.AUTO
    # DEFAULT_REQUIRE_APPROVAL and CRITICAL_REQUIRE_APPROVAL both map to ASK.
    return ToolPermissionMode.ASK


def _build_conservative() -> dict[str, ToolPermissionMode]:
    """All tools default to ``ask``; read-only tools stay ``auto``."""
    out: dict[str, ToolPermissionMode] = {}
    for tool in ALL_TOOL_NAMES:
        default = ACTION_CLASSIFICATIONS.get(
            tool, ActionClassification.DEFAULT_REQUIRE_APPROVAL
        )
        if default is ActionClassification.AUTO_EXECUTE:
            out[tool] = ToolPermissionMode.AUTO
        else:
            out[tool] = ToolPermissionMode.ASK
    return out


def _build_standard() -> dict[str, ToolPermissionMode]:
    """Mirror DD-003 default classifications verbatim."""
    return {
        tool: _classification_to_mode(
            ACTION_CLASSIFICATIONS.get(
                tool, ActionClassification.DEFAULT_REQUIRE_APPROVAL
            )
        )
        for tool in ALL_TOOL_NAMES
    }


def _build_trusted() -> dict[str, ToolPermissionMode]:
    """All non-critical tools ``auto``; critical tools remain ``ask``."""
    out: dict[str, ToolPermissionMode] = {}
    for tool in ALL_TOOL_NAMES:
        default = ACTION_CLASSIFICATIONS.get(
            tool, ActionClassification.DEFAULT_REQUIRE_APPROVAL
        )
        if default is ActionClassification.CRITICAL_REQUIRE_APPROVAL:
            out[tool] = ToolPermissionMode.ASK
        else:
            out[tool] = ToolPermissionMode.AUTO
    return out


def build_templates() -> dict[str, dict[str, ToolPermissionMode]]:
    """Build the full template map. Called once at import time."""
    return {
        "conservative": _build_conservative(),
        "standard": _build_standard(),
        "trusted": _build_trusted(),
    }


POLICY_TEMPLATES: dict[str, dict[str, ToolPermissionMode]] = build_templates()

TEMPLATE_NAMES: tuple[str, ...] = ("conservative", "standard", "trusted")


def is_critical(tool_name: str) -> bool:
    """Return ``True`` iff the tool's DD-003 classification is CRITICAL."""
    return (
        ACTION_CLASSIFICATIONS.get(tool_name)
        is ActionClassification.CRITICAL_REQUIRE_APPROVAL
    )


__all__ = [
    "ACTION_CLASSIFICATIONS",
    "POLICY_TEMPLATES",
    "TEMPLATE_NAMES",
    "build_templates",
    "is_critical",
]
