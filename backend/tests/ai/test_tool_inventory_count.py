"""Phase 69 Wave 0 — Tool inventory snapshot test.

Locks the actual MCP tool count and per-server breakdown used by the
Phase 69 AI Permissions settings UI and permission service. This is
executable documentation: if a new MCP tool is added without updating
the settings UI seed, this test fails and forces a conscious update.

See ``.planning/phases/69-ai-memory-and-granular-tool-permissions/``
"""

from __future__ import annotations

import pytest

from pilot_space.ai.agents.pilotspace_agent_helpers import ALL_TOOL_NAMES
from pilot_space.ai.mcp.comment_server import TOOL_NAMES as COMMENT_TOOL_NAMES
from pilot_space.ai.mcp.interaction_server import TOOL_NAMES as INTERACTION_TOOL_NAMES
from pilot_space.ai.mcp.issue_relation_server import TOOL_NAMES as ISSUE_REL_TOOL_NAMES
from pilot_space.ai.mcp.issue_server import TOOL_NAMES as ISSUE_TOOL_NAMES
from pilot_space.ai.mcp.note_content_server import TOOL_NAMES as NOTE_CONTENT_TOOL_NAMES
from pilot_space.ai.mcp.note_query_server import TOOL_NAMES as NOTE_QUERY_TOOL_NAMES
from pilot_space.ai.mcp.note_server import TOOL_NAMES as NOTE_TOOL_NAMES
from pilot_space.ai.mcp.project_server import TOOL_NAMES as PROJECT_TOOL_NAMES

# Phase 69 Wave 0 locked value. If this changes, update the settings UI
# seed in frontend/src/features/settings/ai-permissions/ and bump here.
PHASE69_TOOL_COUNT = 39


@pytest.fixture
def grouped_tool_names() -> dict[str, list[str]]:
    """Per-MCP-server tool name groups for Wave 4 settings UI tests."""
    return {
        "note": list(NOTE_TOOL_NAMES),
        "note_query": list(NOTE_QUERY_TOOL_NAMES),
        "note_content": list(NOTE_CONTENT_TOOL_NAMES),
        "issue": list(ISSUE_TOOL_NAMES),
        "issue_relation": list(ISSUE_REL_TOOL_NAMES),
        "project": list(PROJECT_TOOL_NAMES),
        "comment": list(COMMENT_TOOL_NAMES),
        "interaction": list(INTERACTION_TOOL_NAMES),
    }


def test_all_tool_names_has_no_duplicates() -> None:
    """ALL_TOOL_NAMES must not contain duplicates — used as dict keys in settings UI."""
    assert len(ALL_TOOL_NAMES) == len(set(ALL_TOOL_NAMES)), (
        f"Duplicate tool names detected: "
        f"{[name for name in ALL_TOOL_NAMES if ALL_TOOL_NAMES.count(name) > 1]}"
    )


def test_all_tool_names_matches_per_server_sum(
    grouped_tool_names: dict[str, list[str]],
) -> None:
    """Sum of per-server tool counts must equal len(ALL_TOOL_NAMES)."""
    per_server_total = sum(len(names) for names in grouped_tool_names.values())
    assert per_server_total == len(ALL_TOOL_NAMES), (
        f"Per-server sum {per_server_total} != ALL_TOOL_NAMES len {len(ALL_TOOL_NAMES)}. "
        f"Breakdown: {[(k, len(v)) for k, v in grouped_tool_names.items()]}"
    )


def test_phase69_tool_count_snapshot() -> None:
    """Locked snapshot. Update PHASE69_TOOL_COUNT + settings UI seed if this fails."""
    # Printed so `pytest -s` captures the value for 69-VALIDATION.md updates.
    print(f"PHASE69_TOOL_COUNT={len(ALL_TOOL_NAMES)}")
    assert len(ALL_TOOL_NAMES) == PHASE69_TOOL_COUNT, (
        f"Tool count changed: expected {PHASE69_TOOL_COUNT}, got {len(ALL_TOOL_NAMES)}. "
        "Update PHASE69_TOOL_COUNT + 69-VALIDATION.md + settings UI seed."
    )
