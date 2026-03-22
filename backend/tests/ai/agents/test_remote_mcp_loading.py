"""Tests for workspace MCP server loading into PilotSpaceAgent (FR-08).

``load_workspace_mcp_servers()`` (formerly ``_load_remote_mcp_servers``) lives in
``pilotspace_stream_utils.py`` and is called on every chat request in
``pilotspace_agent.py`` (lines ~550-552).  These are the definitive contract
tests for FR-08: load & verify agent MCP config.

Contract guarantees:
  - Active remote server with bearer token  →  McpSSEServerConfig keyed as ``WORKSPACE_{NORMALIZED_NAME}``
  - Corrupt auth_token_encrypted            →  server silently skipped, no exception
  - workspace_id=None / db_session=None     →  empty dict returned immediately
  - remote+streamable_http                  →  McpHttpServerConfig  keyed as ``WORKSPACE_{NORMALIZED_NAME}``
  - npx/uvx+stdio                           →  McpStdioServerConfig keyed as ``WORKSPACE_{NORMALIZED_NAME}``
  - headers_json takes priority over headers_encrypted
  - Disabled server (is_enabled=False)      →  excluded from result

Key pattern: ``WORKSPACE_{NORMALIZED_NAME}`` where
``NORMALIZED_NAME = re.sub(r"[^A-Z0-9]", "_", display_name.upper())``
e.g. display_name="Test Remote MCP" → key "WORKSPACE_TEST_REMOTE_MCP"
"""

from __future__ import annotations

import re

import pytest

# ---------------------------------------------------------------------------
# T089: Existing integration tests (xfail removed; updated to public API)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_load_workspace_mcp_servers_builds_sse_config(
    db_session,
    workspace_factory,
) -> None:
    """FR-08: Active registered server with bearer token -> McpSSEServerConfig in result.

    Given:
      - A WorkspaceMcpServer row with auth_type=bearer, non-null auth_token_encrypted
      - workspace_id matching the server row

    When:
      - load_workspace_mcp_servers(workspace_id, db_session) is called

    Then:
      - Returns a dict with key "WORKSPACE_TEST_REMOTE_MCP" (display_name="Test Remote MCP")
      - Value is McpSSEServerConfig: {"type": "sse", "url": ..., "headers": {"Authorization": "Bearer ..."}}
      - Exactly one entry per active server
    """

    from pilot_space.ai.agents.pilotspace_stream_utils import load_workspace_mcp_servers
    from pilot_space.infrastructure.database.models.workspace_mcp_server import (
        McpAuthType,
        McpServerType,
        McpTransport,
        WorkspaceMcpServer,
    )
    from pilot_space.infrastructure.encryption import encrypt_api_key

    workspace = workspace_factory()
    plain_token = "sk-bearer-token-123"
    encrypted_token = encrypt_api_key(plain_token)

    server = WorkspaceMcpServer(
        workspace_id=workspace.id,
        display_name="Test Remote MCP",
        url="https://mcp.example.com/sse",
        url_or_command="https://mcp.example.com/sse",
        auth_type=McpAuthType.BEARER,
        auth_token_encrypted=encrypted_token,
        server_type=McpServerType.REMOTE,
        transport=McpTransport.SSE,
        is_enabled=True,
    )
    db_session.add(server)
    await db_session.flush()

    result = await load_workspace_mcp_servers(workspace.id, db_session)

    # display_name="Test Remote MCP" → WORKSPACE_TEST_REMOTE_MCP_{SHORT_ID}
    normalized = re.sub(r"[^A-Z0-9]", "_", server.display_name.upper())
    short_id = server.id.hex[:8].upper()
    key = f"WORKSPACE_{normalized}_{short_id}"
    assert key in result
    config = result[key]
    assert config["type"] == "sse"
    assert config["url"] == "https://mcp.example.com/sse"
    assert "headers" in config
    assert config["headers"]["Authorization"] == f"Bearer {plain_token}"


@pytest.mark.asyncio
async def test_load_workspace_mcp_servers_skips_on_decrypt_failure(
    db_session,
    workspace_factory,
) -> None:
    """FR-08: Corrupt auth_token_encrypted -> server skipped silently, no exception.

    Given:
      - A WorkspaceMcpServer row with auth_token_encrypted = "corrupted-garbage"
        (not valid Fernet ciphertext)

    When:
      - load_workspace_mcp_servers(workspace_id, db_session) is called

    Then:
      - No exception raised (decrypt failure is swallowed with warning log)
      - The result dict does NOT contain the corrupt server's key
      - Other valid servers in the same workspace ARE included
    """

    from pilot_space.ai.agents.pilotspace_stream_utils import load_workspace_mcp_servers
    from pilot_space.infrastructure.database.models.workspace_mcp_server import (
        McpAuthType,
        McpServerType,
        McpTransport,
        WorkspaceMcpServer,
    )
    from pilot_space.infrastructure.encryption import encrypt_api_key

    workspace = workspace_factory()

    # Corrupt server - decrypt will raise InvalidToken
    corrupt_server = WorkspaceMcpServer(
        workspace_id=workspace.id,
        display_name="Corrupt Token Server",
        url="https://mcp.corrupt.example.com/sse",
        url_or_command="https://mcp.corrupt.example.com/sse",
        auth_type=McpAuthType.BEARER,
        auth_token_encrypted="this-is-not-valid-fernet-ciphertext",
        server_type=McpServerType.REMOTE,
        transport=McpTransport.SSE,
        is_enabled=True,
    )

    # Valid server - should still be loaded
    valid_token = encrypt_api_key("sk-good-token")
    valid_server = WorkspaceMcpServer(
        workspace_id=workspace.id,
        display_name="Valid Token Server",
        url="https://mcp.valid.example.com/sse",
        url_or_command="https://mcp.valid.example.com/sse",
        auth_type=McpAuthType.BEARER,
        auth_token_encrypted=valid_token,
        server_type=McpServerType.REMOTE,
        transport=McpTransport.SSE,
        is_enabled=True,
    )

    db_session.add(corrupt_server)
    db_session.add(valid_server)
    await db_session.flush()

    # Must not raise
    result = await load_workspace_mcp_servers(workspace.id, db_session)

    def _key(s):  # type: ignore[no-untyped-def]
        normalized = re.sub(r"[^A-Z0-9]", "_", s.display_name.upper())
        short_id = s.id.hex[:8].upper()
        return f"WORKSPACE_{normalized}_{short_id}"

    # Corrupt server excluded
    assert _key(corrupt_server) not in result
    # Valid server included
    assert _key(valid_server) in result


@pytest.mark.asyncio
async def test_load_workspace_mcp_servers_empty_no_workspace() -> None:
    """FR-08: workspace_id=None -> returns empty dict immediately, no DB query.

    This is the guard clause at the top of load_workspace_mcp_servers() that
    short-circuits for non-workspace (CLI/anonymous) chat requests.
    db_session=None is also tested to confirm both None guards work.
    """
    from pilot_space.ai.agents.pilotspace_stream_utils import load_workspace_mcp_servers

    # workspace_id=None
    result_no_workspace = await load_workspace_mcp_servers(None, None)
    assert result_no_workspace == {}

    # db_session=None with a real workspace_id
    from uuid import uuid4

    result_no_session = await load_workspace_mcp_servers(uuid4(), None)
    assert result_no_session == {}


# ---------------------------------------------------------------------------
# T090: _build_server_config — all four config branches
# ---------------------------------------------------------------------------


def _make_remote_server(workspace_id, *, transport, url_or_command, auth_type=None, **kwargs):  # type: ignore[no-untyped-def]
    """Helper: build a WorkspaceMcpServer instance (not persisted)."""
    from pilot_space.infrastructure.database.models.workspace_mcp_server import (
        McpAuthType,
        McpServerType,
        WorkspaceMcpServer,
    )

    return WorkspaceMcpServer(
        workspace_id=workspace_id,
        display_name="test-server",
        url=url_or_command,
        url_or_command=url_or_command,
        auth_type=auth_type or McpAuthType.NONE,
        server_type=McpServerType.REMOTE,
        transport=transport,
        is_enabled=True,
        **kwargs,
    )


def _make_command_server(workspace_id, *, command_runner, url_or_command, **kwargs):  # type: ignore[no-untyped-def]
    """Helper: build a stdio WorkspaceMcpServer instance (not persisted)."""
    from pilot_space.infrastructure.database.models.workspace_mcp_server import (
        McpAuthType,
        McpCommandRunner,
        McpServerType,
        McpTransport,
        WorkspaceMcpServer,
    )

    runner = McpCommandRunner(command_runner) if isinstance(command_runner, str) else command_runner

    return WorkspaceMcpServer(
        workspace_id=workspace_id,
        display_name="test-cmd-server",
        url=url_or_command,
        url_or_command=url_or_command,
        auth_type=McpAuthType.NONE,
        server_type=McpServerType.COMMAND,
        command_runner=runner,
        transport=McpTransport.STDIO,
        is_enabled=True,
        **kwargs,
    )


def test_build_server_config_remote_sse(workspace_factory) -> None:  # type: ignore[no-untyped-def]
    """T090a: remote+sse -> McpSSEServerConfig with auth header."""
    from pilot_space.ai.agents.pilotspace_stream_utils import _build_server_config
    from pilot_space.infrastructure.database.models.workspace_mcp_server import McpTransport
    from pilot_space.infrastructure.encryption import decrypt_api_key, encrypt_api_key

    workspace = workspace_factory()
    token = encrypt_api_key("sk-test")
    server = _make_remote_server(
        workspace.id,
        transport=McpTransport.SSE,
        url_or_command="https://mcp.example.com/sse",
        auth_token_encrypted=token,
    )

    config = _build_server_config(server, decrypt_fn=decrypt_api_key)
    assert config is not None
    assert config["type"] == "sse"
    assert config["url"] == "https://mcp.example.com/sse"
    assert config["headers"]["Authorization"] == "Bearer sk-test"


def test_build_server_config_remote_streamable_http(workspace_factory) -> None:  # type: ignore[no-untyped-def]
    """T090b: remote+streamable_http -> McpHttpServerConfig."""
    from pilot_space.ai.agents.pilotspace_stream_utils import _build_server_config
    from pilot_space.infrastructure.database.models.workspace_mcp_server import McpTransport
    from pilot_space.infrastructure.encryption import decrypt_api_key

    workspace = workspace_factory()
    server = _make_remote_server(
        workspace.id,
        transport=McpTransport.STREAMABLE_HTTP,
        url_or_command="https://mcp.example.com/http",
    )

    config = _build_server_config(server, decrypt_fn=decrypt_api_key)
    assert config is not None
    assert config["type"] == "http"
    assert config["url"] == "https://mcp.example.com/http"
    assert "headers" not in config  # no auth configured


def test_build_server_config_npx_stdio(workspace_factory) -> None:  # type: ignore[no-untyped-def]
    """T090c: command+npx+stdio -> McpStdioServerConfig with command/args/env."""
    from pilot_space.ai.agents.pilotspace_stream_utils import _build_server_config
    from pilot_space.infrastructure.encryption import decrypt_api_key
    from pilot_space.infrastructure.encryption_kv import encrypt_kv

    workspace = workspace_factory()
    env_blob = encrypt_kv({"API_KEY": "secret123"})
    server = _make_command_server(
        workspace.id,
        command_runner="npx",
        url_or_command="@modelcontextprotocol/server-filesystem",
        command_args="--allow-write",
        env_vars_encrypted=env_blob,
    )

    config = _build_server_config(server, decrypt_fn=decrypt_api_key)
    assert config is not None
    assert config["type"] == "stdio"
    assert config["command"] == "npx"
    assert "@modelcontextprotocol/server-filesystem" in config["args"]
    assert "--allow-write" in config["args"]
    assert config["env"] == {"API_KEY": "secret123"}


def test_build_server_config_uvx_stdio(workspace_factory) -> None:  # type: ignore[no-untyped-def]
    """T090d: command+uvx+stdio -> McpStdioServerConfig with command only (no env)."""
    from pilot_space.ai.agents.pilotspace_stream_utils import _build_server_config
    from pilot_space.infrastructure.encryption import decrypt_api_key

    workspace = workspace_factory()
    server = _make_command_server(
        workspace.id,
        command_runner="uvx",
        url_or_command="mcp-server-git",
    )

    config = _build_server_config(server, decrypt_fn=decrypt_api_key)
    assert config is not None
    assert config["type"] == "stdio"
    assert config["command"] == "uvx"
    assert "mcp-server-git" in config["args"]
    assert "env" not in config


def test_build_server_config_headers_json_priority(workspace_factory) -> None:  # type: ignore[no-untyped-def]
    """T090e: headers_json takes priority over headers_encrypted for remote servers."""
    from pilot_space.ai.agents.pilotspace_stream_utils import _build_server_config
    from pilot_space.infrastructure.database.models.workspace_mcp_server import McpTransport
    from pilot_space.infrastructure.encryption import decrypt_api_key
    from pilot_space.infrastructure.encryption_kv import encrypt_kv

    workspace = workspace_factory()
    # headers_json has plaintext headers; headers_encrypted has different values
    encrypted_headers = encrypt_kv({"X-Source": "encrypted"})
    server = _make_remote_server(
        workspace.id,
        transport=McpTransport.SSE,
        url_or_command="https://mcp.example.com/sse",
        headers_json='{"X-Source": "plaintext"}',
        headers_encrypted=encrypted_headers,
    )

    config = _build_server_config(server, decrypt_fn=decrypt_api_key)
    assert config is not None
    # headers_json wins — plaintext value used
    assert config["headers"]["X-Source"] == "plaintext"


# ---------------------------------------------------------------------------
# T091: _build_server_config — decryption failure paths
# ---------------------------------------------------------------------------


def test_build_server_config_returns_none_on_auth_token_decrypt_failure(workspace_factory) -> None:  # type: ignore[no-untyped-def]
    """T091a: Corrupt auth_token_encrypted -> _build_server_config returns None."""
    from pilot_space.ai.agents.pilotspace_stream_utils import _build_server_config
    from pilot_space.infrastructure.database.models.workspace_mcp_server import (
        McpAuthType,
        McpTransport,
    )
    from pilot_space.infrastructure.encryption import decrypt_api_key

    workspace = workspace_factory()
    server = _make_remote_server(
        workspace.id,
        transport=McpTransport.SSE,
        url_or_command="https://mcp.example.com/sse",
        auth_type=McpAuthType.BEARER,
        auth_token_encrypted="not-valid-fernet",
    )

    result = _build_server_config(server, decrypt_fn=decrypt_api_key)
    assert result is None


def test_build_server_config_skips_env_on_decrypt_failure(workspace_factory) -> None:  # type: ignore[no-untyped-def]
    """T091b: command server with corrupt env_vars_encrypted -> config returned without env."""
    from pilot_space.ai.agents.pilotspace_stream_utils import _build_server_config
    from pilot_space.infrastructure.encryption import decrypt_api_key

    workspace = workspace_factory()
    server = _make_command_server(
        workspace.id,
        command_runner="npx",
        url_or_command="some-mcp-server",
        env_vars_encrypted="not-valid-fernet-blob",
    )

    # Must not raise; server config returned without env
    config = _build_server_config(server, decrypt_fn=decrypt_api_key)
    assert config is not None
    assert config["type"] == "stdio"
    assert "env" not in config


# ---------------------------------------------------------------------------
# T092: Repository — enabled_only filter
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_active_by_workspace_excludes_disabled(
    db_session,
    workspace_factory,
) -> None:
    """T092: get_active_by_workspace(enabled_only=True) excludes is_enabled=False servers."""
    from pilot_space.infrastructure.database.models.workspace_mcp_server import (
        McpAuthType,
        McpServerType,
        McpTransport,
        WorkspaceMcpServer,
    )
    from pilot_space.infrastructure.database.repositories.workspace_mcp_server_repository import (
        WorkspaceMcpServerRepository,
    )

    workspace = workspace_factory()

    enabled_server = WorkspaceMcpServer(
        workspace_id=workspace.id,
        display_name="Enabled Server",
        url="https://mcp.enabled.example.com/sse",
        url_or_command="https://mcp.enabled.example.com/sse",
        auth_type=McpAuthType.NONE,
        server_type=McpServerType.REMOTE,
        transport=McpTransport.SSE,
        is_enabled=True,
    )
    disabled_server = WorkspaceMcpServer(
        workspace_id=workspace.id,
        display_name="Disabled Server",
        url="https://mcp.disabled.example.com/sse",
        url_or_command="https://mcp.disabled.example.com/sse",
        auth_type=McpAuthType.NONE,
        server_type=McpServerType.REMOTE,
        transport=McpTransport.SSE,
        is_enabled=False,
    )
    db_session.add(enabled_server)
    db_session.add(disabled_server)
    await db_session.flush()

    repo = WorkspaceMcpServerRepository(session=db_session)
    results = await repo.get_active_by_workspace(workspace.id, enabled_only=True)
    ids = {s.id for s in results}

    assert enabled_server.id in ids
    assert disabled_server.id not in ids


@pytest.mark.asyncio
async def test_get_active_by_workspace_includes_reenabled(
    db_session,
    workspace_factory,
) -> None:
    """T092b: Re-enabled server appears in next get_active_by_workspace(enabled_only=True) call."""
    from pilot_space.infrastructure.database.models.workspace_mcp_server import (
        McpAuthType,
        McpServerType,
        McpTransport,
        WorkspaceMcpServer,
    )
    from pilot_space.infrastructure.database.repositories.workspace_mcp_server_repository import (
        WorkspaceMcpServerRepository,
    )

    workspace = workspace_factory()
    server = WorkspaceMcpServer(
        workspace_id=workspace.id,
        display_name="Toggle Server",
        url="https://mcp.toggle.example.com/sse",
        url_or_command="https://mcp.toggle.example.com/sse",
        auth_type=McpAuthType.NONE,
        server_type=McpServerType.REMOTE,
        transport=McpTransport.SSE,
        is_enabled=False,
    )
    db_session.add(server)
    await db_session.flush()

    repo = WorkspaceMcpServerRepository(session=db_session)

    # Initially disabled — should not appear
    results = await repo.get_active_by_workspace(workspace.id, enabled_only=True)
    assert server.id not in {s.id for s in results}

    # Re-enable
    server.is_enabled = True
    await db_session.flush()

    # Now should appear
    results = await repo.get_active_by_workspace(workspace.id, enabled_only=True)
    assert server.id in {s.id for s in results}


# ---------------------------------------------------------------------------
# T093: Integration smoke-test — NPX server config is SDK-ready
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_load_workspace_mcp_servers_npx_sdk_ready(
    db_session,
    workspace_factory,
) -> None:
    """T093: NPX server row -> load_workspace_mcp_servers produces JSON-serialisable SDK config.

    Given:
      - A WorkspaceMcpServer row with server_type=npx, url_or_command="npx -y some-pkg"
      - is_enabled=True

    When:
      - load_workspace_mcp_servers(workspace_id, db_session) is called

    Then:
      - Result contains key "WORKSPACE_NPX_SMOKE_TEST" (display_name="NPX Smoke Test")
      - Config has type=="stdio", command=="npx", args include "-y" and "some-pkg"
      - Config is fully JSON-serialisable (no non-serialisable types) — SDK-ready
    """
    import json

    from pilot_space.ai.agents.pilotspace_stream_utils import load_workspace_mcp_servers
    from pilot_space.infrastructure.database.models.workspace_mcp_server import (
        McpAuthType,
        McpCommandRunner,
        McpServerType,
        McpTransport,
        WorkspaceMcpServer,
    )

    workspace = workspace_factory()
    server = WorkspaceMcpServer(
        workspace_id=workspace.id,
        display_name="NPX Smoke Test",
        url="-y some-pkg",
        url_or_command="-y some-pkg",
        auth_type=McpAuthType.NONE,
        server_type=McpServerType.COMMAND,
        command_runner=McpCommandRunner.NPX,
        transport=McpTransport.STDIO,
        is_enabled=True,
    )
    db_session.add(server)
    await db_session.flush()

    result = await load_workspace_mcp_servers(workspace.id, db_session)

    # display_name="NPX Smoke Test" → WORKSPACE_NPX_SMOKE_TEST_{SHORT_ID}
    normalized = re.sub(r"[^A-Z0-9]", "_", server.display_name.upper())
    short_id = server.id.hex[:8].upper()
    key = f"WORKSPACE_{normalized}_{short_id}"
    assert key in result, f"Expected key '{key}' in result, got: {list(result.keys())}"

    config = result[key]
    assert config["type"] == "stdio"
    assert config["command"] == "npx"
    assert "-y" in config["args"]
    assert "some-pkg" in config["args"]

    # Verify fully JSON-serialisable — no unserializable SDK internals
    serialised = json.dumps(config)
    assert serialised  # non-empty string confirms success


def test_build_server_config_returns_none_when_command_runner_missing(workspace_factory) -> None:  # type: ignore[no-untyped-def]
    """T025 extra: command server without command_runner -> _build_server_config returns None."""

    from pilot_space.ai.agents.pilotspace_stream_utils import _build_server_config
    from pilot_space.infrastructure.database.models.workspace_mcp_server import (
        McpAuthType,
        McpServerType,
        McpTransport,
        WorkspaceMcpServer,
    )
    from pilot_space.infrastructure.encryption import decrypt_api_key

    workspace = workspace_factory()
    # Build a COMMAND server with no command_runner
    server = WorkspaceMcpServer(
        workspace_id=workspace.id,
        display_name="No Runner Server",
        url_or_command="some-pkg",
        auth_type=McpAuthType.NONE,
        server_type=McpServerType.COMMAND,
        command_runner=None,
        transport=McpTransport.STDIO,
        is_enabled=True,
    )

    config = _build_server_config(server, decrypt_fn=decrypt_api_key)
    assert config is None, "COMMAND server without command_runner should return None"
