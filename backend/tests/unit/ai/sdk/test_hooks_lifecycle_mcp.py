"""Tests for AuditLogHook remote MCP tool detection (Phase 34 — MCPOB-01).

Verifies that:
- Remote MCP tool calls (mcp__remote_*__*) write audit rows with action='ai.mcp_tool_call'
- Non-remote-MCP tools and plain tools do NOT write mcp_tool_call rows
- Audit write failures are non-fatal (callback returns {} without raising)
- server_key and bare_tool are parsed correctly, including tools with underscores in their name
- duration_ms is None when tool_use_id is absent
- input_hash is a full 64-character SHA-256 hex digest
- resource_id is the parsed server UUID from "remote_{uuid}"
"""

from __future__ import annotations

import hashlib
import json
import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from pilot_space.ai.sdk.hooks_lifecycle import AuditLogHook

# ========================================
# Constants
# ========================================

_WORKSPACE_ID = uuid4()
_ACTOR_ID = uuid4()
_SERVER_UUID = uuid4()
_SERVER_KEY = f"remote_{_SERVER_UUID}"

# Patch target: AuditLogRepository in the repository module.
# The callback imports it as:
#   from pilot_space.infrastructure.database.repositories.audit_log_repository import
#       AuditLogRepository as _Repo
# We patch it at the source module so the local alias picks up the mock.
_REPO_PATCH = (
    "pilot_space.infrastructure.database.repositories.audit_log_repository.AuditLogRepository"
)


# ========================================
# Helpers
# ========================================


def _make_input_data(
    tool_name: str | None = None,
    tool_input: dict[str, Any] | None = None,
    tool_output: str = "",
) -> dict[str, Any]:
    """Build a mock PostToolUse input_data dict."""
    if tool_name is None:
        tool_name = f"mcp__{_SERVER_KEY}__search_files"
    return {
        "tool_name": tool_name,
        "tool_input": tool_input or {"query": "test"},
        "tool_output": tool_output,
    }


def _make_hook() -> tuple[AuditLogHook, AsyncMock, MagicMock]:
    """Create an AuditLogHook with mock session_factory.

    Returns (hook, mock_repo, mock_session_factory).
    """
    mock_repo = MagicMock()
    mock_repo.create = AsyncMock(return_value=MagicMock())

    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)
    mock_session.commit = AsyncMock()

    mock_session_factory = MagicMock()
    mock_session_factory.return_value = mock_session

    hook = AuditLogHook(
        session_factory=mock_session_factory,
        workspace_id=_WORKSPACE_ID,
        actor_id=_ACTOR_ID,
    )
    return hook, mock_repo, mock_session_factory


async def _invoke_post_tool_use(
    hook: AuditLogHook,
    input_data: dict[str, Any],
    tool_use_id: str | None = "test-tuid-001",
) -> dict[str, Any]:
    """Extract and invoke the PostToolUse callback from the hook."""
    hooks_dict = hook.to_sdk_hooks()
    callback = hooks_dict["PostToolUse"][0]["hooks"][0]
    return await callback(input_data, tool_use_id, None)


# ========================================
# Task 1 Tests — MCPOB-01
# ========================================


class TestRemoteMcpAuditDetection:
    """Tests for remote MCP tool audit detection in AuditLogHook._create_audit_callback()."""

    @pytest.mark.asyncio
    async def test_remote_mcp_tool_writes_audit_row(self) -> None:
        """PostToolUse for mcp__remote_*__* writes audit row with action='ai.mcp_tool_call'.

        Verifies: action, resource_type, payload containing server_key, tool_name,
        input_hash (64-char hex), duration_ms.
        """
        hook, mock_repo, mock_sf = _make_hook()
        tool_input = {"query": "find all Python files"}
        input_data = _make_input_data(
            tool_name=f"mcp__{_SERVER_KEY}__search_files",
            tool_input=tool_input,
        )

        with patch(_REPO_PATCH, return_value=mock_repo):
            hook.record_tool_start("test-tuid-001")
            result = await _invoke_post_tool_use(hook, input_data, "test-tuid-001")

        assert result == {}
        mock_repo.create.assert_called_once()
        call_kwargs = mock_repo.create.call_args.kwargs

        assert call_kwargs["action"] == "ai.mcp_tool_call"
        assert call_kwargs["resource_type"] == "mcp_tool"
        assert call_kwargs["workspace_id"] == _WORKSPACE_ID
        assert call_kwargs["actor_id"] == _ACTOR_ID

        payload = call_kwargs["payload"]
        assert payload["server_key"] == _SERVER_KEY
        assert payload["tool_name"] == "search_files"
        assert isinstance(payload["input_hash"], str)
        assert len(payload["input_hash"]) == 64  # full SHA-256 hex
        assert payload["duration_ms"] is not None

    @pytest.mark.asyncio
    async def test_non_remote_mcp_no_mcp_audit(self) -> None:
        """mcp__pilot__ghost_text does NOT call repo.create() with action='ai.mcp_tool_call'."""
        hook, mock_repo, mock_sf = _make_hook()
        input_data = _make_input_data(tool_name="mcp__pilot__ghost_text")

        with patch(_REPO_PATCH, return_value=mock_repo):
            result = await _invoke_post_tool_use(hook, input_data)

        assert result == {}
        # repo.create may be called for the generic audit path, but NOT with ai.mcp_tool_call
        for c in mock_repo.create.call_args_list:
            assert c.kwargs.get("action") != "ai.mcp_tool_call", (
                "mcp__pilot__ tools should NOT produce ai.mcp_tool_call rows"
            )

    @pytest.mark.asyncio
    async def test_plain_tool_no_mcp_audit(self) -> None:
        """Plain tool name 'Read' does NOT call repo.create() with action='ai.mcp_tool_call'."""
        hook, mock_repo, mock_sf = _make_hook()
        input_data = _make_input_data(tool_name="Read")

        with patch(_REPO_PATCH, return_value=mock_repo):
            result = await _invoke_post_tool_use(hook, input_data)

        assert result == {}
        for c in mock_repo.create.call_args_list:
            assert c.kwargs.get("action") != "ai.mcp_tool_call", (
                "Plain tools should NOT produce ai.mcp_tool_call rows"
            )

    @pytest.mark.asyncio
    async def test_mcp_audit_nonfatal(self) -> None:
        """session_factory raises RuntimeError → callback returns {} without raising."""
        mock_session_factory = MagicMock()
        mock_session_factory.return_value.__aenter__ = AsyncMock(
            side_effect=RuntimeError("DB unavailable")
        )
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        hook = AuditLogHook(
            session_factory=mock_session_factory,
            workspace_id=_WORKSPACE_ID,
            actor_id=_ACTOR_ID,
        )
        input_data = _make_input_data(tool_name=f"mcp__{_SERVER_KEY}__search_files")

        # Should not raise — non-fatal
        result = await _invoke_post_tool_use(hook, input_data)
        assert result == {}

    @pytest.mark.asyncio
    async def test_mcp_tool_with_underscores(self) -> None:
        """mcp__remote_uuid__tool__with__underscores parses correctly.

        split("__", 2) yields ["mcp", "remote_uuid", "tool__with__underscores"].
        server_key = "remote_uuid", bare_tool = "tool__with__underscores".
        """
        hook, mock_repo, mock_sf = _make_hook()
        tool_name = f"mcp__{_SERVER_KEY}__tool__with__underscores"
        input_data = _make_input_data(tool_name=tool_name)

        with patch(_REPO_PATCH, return_value=mock_repo):
            result = await _invoke_post_tool_use(hook, input_data)

        assert result == {}
        mock_repo.create.assert_called_once()
        call_kwargs = mock_repo.create.call_args.kwargs
        assert call_kwargs["action"] == "ai.mcp_tool_call"
        payload = call_kwargs["payload"]
        assert payload["server_key"] == _SERVER_KEY
        assert payload["tool_name"] == "tool__with__underscores"

    @pytest.mark.asyncio
    async def test_duration_none_when_no_tool_use_id(self) -> None:
        """tool_use_id=None → payload['duration_ms'] is None, row still written."""
        hook, mock_repo, mock_sf = _make_hook()
        input_data = _make_input_data(tool_name=f"mcp__{_SERVER_KEY}__search_files")

        with patch(_REPO_PATCH, return_value=mock_repo):
            result = await _invoke_post_tool_use(hook, input_data, tool_use_id=None)

        assert result == {}
        mock_repo.create.assert_called_once()
        payload = mock_repo.create.call_args.kwargs["payload"]
        assert payload["duration_ms"] is None

    @pytest.mark.asyncio
    async def test_input_hash_is_full_sha256(self) -> None:
        """payload['input_hash'] is exactly 64 hex characters (full SHA-256 digest)."""
        hook, mock_repo, mock_sf = _make_hook()
        tool_input = {"file_path": "/src/main.py", "contents": "print('hello')"}
        input_data = _make_input_data(
            tool_name=f"mcp__{_SERVER_KEY}__read_file",
            tool_input=tool_input,
        )

        with patch(_REPO_PATCH, return_value=mock_repo):
            await _invoke_post_tool_use(hook, input_data)

        payload = mock_repo.create.call_args.kwargs["payload"]
        input_hash = payload["input_hash"]

        # Must be exactly 64 hex characters
        assert len(input_hash) == 64
        assert all(c in "0123456789abcdef" for c in input_hash)

        # Verify it matches expected SHA-256 of the input
        raw = json.dumps(tool_input, sort_keys=True, default=str)
        expected = hashlib.sha256(raw.encode()).hexdigest()
        assert input_hash == expected

    @pytest.mark.asyncio
    async def test_resource_id_is_server_uuid(self) -> None:
        """resource_id kwarg to repo.create() is UUID parsed from 'remote_{uuid}'."""
        hook, mock_repo, mock_sf = _make_hook()
        input_data = _make_input_data(tool_name=f"mcp__{_SERVER_KEY}__search_files")

        with patch(_REPO_PATCH, return_value=mock_repo):
            await _invoke_post_tool_use(hook, input_data)

        call_kwargs = mock_repo.create.call_args.kwargs
        resource_id = call_kwargs.get("resource_id")

        assert resource_id is not None
        assert isinstance(resource_id, uuid.UUID)
        assert resource_id == _SERVER_UUID
