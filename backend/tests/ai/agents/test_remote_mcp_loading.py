"""Tests for remote MCP server hot-loading into PilotSpaceAgent (MCP-04).

Phase 14 Plan 03 will implement _load_remote_mcp_servers() in
pilotspace_stream_utils.py. These stubs define the behavioral contract
for that implementation:

  - Active server with bearer token -> McpSSEServerConfig keyed as remote_{id}
  - Corrupt auth_token_encrypted -> server silently skipped, no exception
  - workspace_id=None -> empty dict returned immediately

All tests are xfail(strict=False) until plan 14-03 ships the implementation.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.asyncio


@pytest.mark.xfail(strict=False, reason="implementation pending - phase 14 plan 03")
async def test_load_remote_mcp_servers_builds_sse_config(
    db_session,
    workspace_factory,
) -> None:
    """MCP-04: Active registered server with bearer token -> McpSSEServerConfig in result.

    Given:
      - A WorkspaceMcpServer row with auth_type=bearer, non-null auth_token_encrypted
      - workspace_id matching the server row

    When:
      - _load_remote_mcp_servers(workspace_id, db_session) is called

    Then:
      - Returns a dict with key "remote_{server.id}"
      - Value is McpSSEServerConfig: {"type": "sse", "url": ..., "headers": {"Authorization": "Bearer ..."}}
      - Exactly one entry per active server
    """

    from pilot_space.ai.agents.pilotspace_stream_utils import _load_remote_mcp_servers
    from pilot_space.config import get_settings
    from pilot_space.infrastructure.database.models.workspace_mcp_server import (
        WorkspaceMcpServer,
    )
    from pilot_space.infrastructure.encryption import encrypt_api_key

    settings = get_settings()
    workspace = workspace_factory()
    plain_token = "sk-bearer-token-123"
    encrypted_token = encrypt_api_key(plain_token, settings.secret_key)

    server = WorkspaceMcpServer(
        workspace_id=workspace.id,
        display_name="Test Remote MCP",
        url="https://mcp.example.com/sse",
        auth_type="bearer",
        auth_token_encrypted=encrypted_token,
    )
    db_session.add(server)
    await db_session.flush()

    result = await _load_remote_mcp_servers(workspace.id, db_session)

    key = f"remote_{server.id}"
    assert key in result
    config = result[key]
    assert config["type"] == "sse"
    assert config["url"] == "https://mcp.example.com/sse"
    assert "headers" in config
    assert config["headers"]["Authorization"] == f"Bearer {plain_token}"


@pytest.mark.xfail(strict=False, reason="implementation pending - phase 14 plan 03")
async def test_load_remote_mcp_servers_skips_on_decrypt_failure(
    db_session,
    workspace_factory,
) -> None:
    """MCP-04: Corrupt auth_token_encrypted -> server skipped silently, no exception.

    Given:
      - A WorkspaceMcpServer row with auth_token_encrypted = "corrupted-garbage"
        (not valid Fernet ciphertext)

    When:
      - _load_remote_mcp_servers(workspace_id, db_session) is called

    Then:
      - No exception raised (decrypt failure is swallowed with warning log)
      - The result dict does NOT contain the corrupt server's key
      - Other valid servers in the same workspace ARE included
    """

    from pilot_space.ai.agents.pilotspace_stream_utils import _load_remote_mcp_servers
    from pilot_space.config import get_settings
    from pilot_space.infrastructure.database.models.workspace_mcp_server import (
        WorkspaceMcpServer,
    )
    from pilot_space.infrastructure.encryption import encrypt_api_key

    settings = get_settings()
    workspace = workspace_factory()

    # Corrupt server - decrypt will raise InvalidToken
    corrupt_server = WorkspaceMcpServer(
        workspace_id=workspace.id,
        display_name="Corrupt Token Server",
        url="https://mcp.corrupt.example.com/sse",
        auth_type="bearer",
        auth_token_encrypted="this-is-not-valid-fernet-ciphertext",
    )

    # Valid server - should still be loaded
    valid_token = encrypt_api_key("sk-good-token", settings.secret_key)
    valid_server = WorkspaceMcpServer(
        workspace_id=workspace.id,
        display_name="Valid Token Server",
        url="https://mcp.valid.example.com/sse",
        auth_type="bearer",
        auth_token_encrypted=valid_token,
    )

    db_session.add(corrupt_server)
    db_session.add(valid_server)
    await db_session.flush()

    # Must not raise
    result = await _load_remote_mcp_servers(workspace.id, db_session)

    # Corrupt server excluded
    assert f"remote_{corrupt_server.id}" not in result
    # Valid server included
    assert f"remote_{valid_server.id}" in result


@pytest.mark.xfail(strict=False, reason="implementation pending - phase 14 plan 03")
async def test_load_remote_mcp_servers_empty_no_workspace() -> None:
    """MCP-04: workspace_id=None -> returns empty dict immediately, no DB query.

    This is the guard clause at the top of _load_remote_mcp_servers() that
    short-circuits for non-workspace (CLI/anonymous) chat requests.
    db_session=None is also tested to confirm both None guards work.
    """
    from pilot_space.ai.agents.pilotspace_stream_utils import _load_remote_mcp_servers

    # workspace_id=None
    result_no_workspace = await _load_remote_mcp_servers(None, None)
    assert result_no_workspace == {}

    # db_session=None with a real workspace_id
    from uuid import uuid4

    result_no_session = await _load_remote_mcp_servers(uuid4(), None)
    assert result_no_session == {}
