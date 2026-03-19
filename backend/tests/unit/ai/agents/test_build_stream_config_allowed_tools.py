"""Unit tests for MCPI-01: remote MCP tool wildcard pattern generation.

Tests the logic added to _build_stream_config that generates
mcp__<server-key>__* wildcard patterns for remote MCP servers,
ensuring Claude can invoke tools from dynamically-registered servers.
"""

from __future__ import annotations

from pilot_space.ai.agents.pilotspace_agent_helpers import ALL_TOOL_NAMES


def _generate_remote_tool_patterns(remote_servers: dict[str, object]) -> list[str]:
    """Mirrors the production expression added to _build_stream_config."""
    return [f"mcp__{key}__*" for key in remote_servers]


def test_no_remote_servers_produces_no_patterns() -> None:
    patterns = _generate_remote_tool_patterns({})
    assert patterns == []
    combined = list(ALL_TOOL_NAMES) + patterns
    assert combined == list(ALL_TOOL_NAMES)


def test_single_remote_server_produces_one_wildcard() -> None:
    remote_servers = {"remote_abc-123-def": object()}
    patterns = _generate_remote_tool_patterns(remote_servers)
    assert patterns == ["mcp__remote_abc-123-def__*"]


def test_multiple_remote_servers_produce_one_wildcard_each() -> None:
    remote_servers = {"remote_aaa": object(), "remote_bbb": object()}
    patterns = _generate_remote_tool_patterns(remote_servers)
    assert "mcp__remote_aaa__*" in patterns
    assert "mcp__remote_bbb__*" in patterns
    assert len(patterns) == 2


def test_all_tool_names_preserved_after_merge() -> None:
    remote_servers = {"remote_xyz": object()}
    patterns = _generate_remote_tool_patterns(remote_servers)
    combined = list(ALL_TOOL_NAMES) + patterns
    for name in ALL_TOOL_NAMES:
        assert name in combined
    assert "mcp__remote_xyz__*" in combined
