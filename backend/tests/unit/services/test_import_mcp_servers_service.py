"""Unit tests for ImportMcpServersService (T035).

Tests:
- Parse Claude Desktop format
- Parse VS Code / Cursor format
- Skip duplicate names
- Reject invalid SSRF URL
- Reject shell metacharacter in command
- Return correct imported/skipped/errors split
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from pilot_space.application.services.mcp.exceptions import McpConfigParseError
from pilot_space.application.services.mcp.import_mcp_servers_service import (
    ImportMcpServersService,
    ParsedMcpServer,
)
from pilot_space.infrastructure.database.models.workspace_mcp_server import (
    McpCommandRunner,
    McpServerType,
    McpTransport,
)


class TestParseConfigJson:
    """Tests for ImportMcpServersService.parse_config_json."""

    def test_parse_claude_format(self) -> None:
        """Parses Claude Desktop JSON config format correctly."""
        config = """{
            "mcpServers": {
                "my-remote": {
                    "url": "https://mcp.example.com/sse",
                    "transport": "sse"
                },
                "my-npx": {
                    "command": "npx",
                    "args": ["-y", "@my-pkg/mcp-server"]
                }
            }
        }"""
        result, errors = ImportMcpServersService.parse_config_json(config)
        assert len(errors) == 0
        assert len(result) == 2

        remote = next(r for r in result if r.name == "my-remote")
        assert remote.server_type == McpServerType.REMOTE
        assert remote.url_or_command == "https://mcp.example.com/sse"
        assert remote.transport == McpTransport.SSE

        npx = next(r for r in result if r.name == "my-npx")
        assert npx.server_type == McpServerType.COMMAND
        assert npx.command_runner == McpCommandRunner.NPX
        assert "@my-pkg/mcp-server" in npx.url_or_command
        assert not npx.url_or_command.startswith("npx")
        assert npx.transport == McpTransport.STDIO

    def test_parse_vscode_format(self) -> None:
        """Parses VS Code / Cursor MCP config format."""
        config = """{
            "mcpServers": {
                "uvx-server": {
                    "command": "uvx",
                    "args": ["my-mcp-tool"],
                    "env": {"API_KEY": "secret-value"}
                }
            }
        }"""
        result, errors = ImportMcpServersService.parse_config_json(config)
        assert len(errors) == 0
        assert len(result) == 1
        entry = result[0]
        assert entry.name == "uvx-server"
        assert entry.server_type == McpServerType.COMMAND
        assert "my-mcp-tool" in entry.url_or_command
        assert entry.env_vars == {"API_KEY": "secret-value"}

    def test_parse_streamable_http_transport(self) -> None:
        """Recognises streamable_http transport."""
        config = """{
            "mcpServers": {
                "http-server": {
                    "url": "https://mcp.example.com/http",
                    "transport": "streamable_http"
                }
            }
        }"""
        result, errors = ImportMcpServersService.parse_config_json(config)
        assert len(errors) == 0
        assert len(result) == 1
        assert result[0].transport == McpTransport.STREAMABLE_HTTP

    def test_invalid_json_raises(self) -> None:
        """Malformed JSON raises McpConfigParseError."""
        with pytest.raises(McpConfigParseError, match="Invalid JSON"):
            ImportMcpServersService.parse_config_json("{ invalid json }")

    def test_missing_mcp_servers_key_returns_empty(self) -> None:
        """Missing 'mcpServers' key returns empty list (no error)."""
        result, errors = ImportMcpServersService.parse_config_json('{"other": "data"}')
        assert result == []
        assert errors == []

    def test_empty_mcp_servers(self) -> None:
        """Empty mcpServers object returns empty list."""
        result, errors = ImportMcpServersService.parse_config_json('{"mcpServers": {}}')
        assert result == []
        assert errors == []


class TestImportServers:
    """Tests for ImportMcpServersService.import_servers."""

    def _make_repo(self, existing_names: list[str]) -> AsyncMock:
        """Create a mock repository with pre-existing server names."""
        repo = AsyncMock()

        existing_servers = []
        for name in existing_names:
            mock_server = MagicMock()
            mock_server.display_name = name
            existing_servers.append(mock_server)

        repo.get_active_by_workspace = AsyncMock(return_value=existing_servers)

        created_ids = []

        async def fake_create(server: Any) -> Any:
            server.id = uuid4()
            created_ids.append(server.id)
            return server

        repo.create = AsyncMock(side_effect=fake_create)
        return repo

    @pytest.mark.asyncio
    async def test_import_new_servers(self) -> None:
        """Successfully imports servers that don't already exist."""
        parsed = [
            ParsedMcpServer(
                name="new-server",
                server_type=McpServerType.REMOTE,
                transport=McpTransport.SSE,
                url_or_command="https://mcp.example.com/sse",
            )
        ]
        repo = self._make_repo([])
        workspace_id = uuid4()

        result = await ImportMcpServersService.import_servers(
            workspace_id=workspace_id,
            parsed=parsed,
            repo=repo,
        )

        assert len(result.imported) == 1
        assert result.imported[0].name == "new-server"
        assert len(result.skipped) == 0
        assert len(result.errors) == 0

    @pytest.mark.asyncio
    async def test_skip_duplicate_name(self) -> None:
        """Skips servers whose display_name already exists in workspace."""
        parsed = [
            ParsedMcpServer(
                name="Existing Server",
                server_type=McpServerType.REMOTE,
                transport=McpTransport.SSE,
                url_or_command="https://new-url.example.com/sse",
            )
        ]
        repo = self._make_repo(["existing server"])  # same after .lower()
        workspace_id = uuid4()

        result = await ImportMcpServersService.import_servers(
            workspace_id=workspace_id,
            parsed=parsed,
            repo=repo,
        )

        assert len(result.imported) == 0
        assert len(result.skipped) == 1
        assert result.skipped[0].name == "Existing Server"
        assert result.skipped[0].reason == "name_conflict"

    @pytest.mark.asyncio
    async def test_reject_http_url(self) -> None:
        """Rejects remote server with HTTP (not HTTPS) URL."""
        parsed = [
            ParsedMcpServer(
                name="insecure-server",
                server_type=McpServerType.REMOTE,
                transport=McpTransport.SSE,
                url_or_command="http://mcp.example.com/sse",  # HTTP not HTTPS
            )
        ]
        repo = self._make_repo([])
        workspace_id = uuid4()

        result = await ImportMcpServersService.import_servers(
            workspace_id=workspace_id,
            parsed=parsed,
            repo=repo,
        )

        assert len(result.imported) == 0
        assert len(result.errors) == 1
        assert "invalid_url" in result.errors[0].reason

    @pytest.mark.asyncio
    async def test_reject_shell_metachar_in_command(self) -> None:
        """Rejects NPX command with shell metacharacters."""
        parsed = [
            ParsedMcpServer(
                name="bad-server",
                server_type=McpServerType.COMMAND,
                transport=McpTransport.STDIO,
                url_or_command="npx my-pkg; rm -rf /",
            )
        ]
        repo = self._make_repo([])
        workspace_id = uuid4()

        result = await ImportMcpServersService.import_servers(
            workspace_id=workspace_id,
            parsed=parsed,
            repo=repo,
        )

        assert len(result.imported) == 0
        assert len(result.errors) == 1
        assert "metacharacter" in result.errors[0].reason

    @pytest.mark.asyncio
    async def test_mixed_import_result(self) -> None:
        """Returns correct split for mixed imported / skipped / errored."""
        parsed = [
            ParsedMcpServer(
                name="good-server",
                server_type=McpServerType.REMOTE,
                transport=McpTransport.SSE,
                url_or_command="https://good.example.com/sse",
            ),
            ParsedMcpServer(
                name="duplicate",
                server_type=McpServerType.REMOTE,
                transport=McpTransport.SSE,
                url_or_command="https://other.example.com/sse",
            ),
            ParsedMcpServer(
                name="bad",
                server_type=McpServerType.REMOTE,
                transport=McpTransport.SSE,
                url_or_command="http://insecure.example.com",
            ),
        ]
        repo = self._make_repo(["duplicate"])
        workspace_id = uuid4()

        result = await ImportMcpServersService.import_servers(
            workspace_id=workspace_id,
            parsed=parsed,
            repo=repo,
        )

        assert len(result.imported) == 1
        assert result.imported[0].name == "good-server"
        assert len(result.skipped) == 1
        assert result.skipped[0].name == "duplicate"
        assert len(result.errors) == 1
        assert result.errors[0].name == "bad"


# ---------------------------------------------------------------------------
# _validate_entry — SSRF blocklist parity tests
# ---------------------------------------------------------------------------


class TestValidateEntry:
    """Tests for the _validate_entry helper — SSRF and command-injection checks."""

    def _make_remote(self, url: str) -> ParsedMcpServer:
        return ParsedMcpServer(
            name="test",
            server_type=McpServerType.REMOTE,
            transport=McpTransport.SSE,
            url_or_command=url,
        )

    def test_rejects_http_url(self) -> None:
        """HTTP (non-HTTPS) URL is still rejected."""
        from pilot_space.application.services.mcp.import_mcp_servers_service import (
            _validate_entry,
        )

        err = _validate_entry(self._make_remote("http://example.com/mcp"))
        assert err is not None
        assert "HTTPS" in err

    def test_rejects_private_ip_url(self) -> None:
        """URL resolving to a private RFC-1918 IP is rejected by the SSRF blocklist."""
        from unittest.mock import patch

        from pilot_space.application.services.mcp.import_mcp_servers_service import (
            _validate_entry,
        )

        # Simulate getaddrinfo returning a private address (10.0.0.1)
        fake_addr = [(None, None, None, None, ("10.0.0.1", 0))]
        with patch("socket.getaddrinfo", return_value=fake_addr):
            err = _validate_entry(self._make_remote("https://internal.corp/mcp"))

        assert err is not None
        assert "private" in err.lower() or "restricted" in err.lower()

    def test_rejects_metadata_ip_url(self) -> None:
        """URL resolving to the AWS metadata IP (169.254.169.254) is rejected."""
        from unittest.mock import patch

        from pilot_space.application.services.mcp.import_mcp_servers_service import (
            _validate_entry,
        )

        fake_addr = [(None, None, None, None, ("169.254.169.254", 0))]
        with patch("socket.getaddrinfo", return_value=fake_addr):
            err = _validate_entry(self._make_remote("https://metadata.internal/latest"))

        assert err is not None
        assert "private" in err.lower() or "restricted" in err.lower()

    def test_accepts_unresolvable_hostname(self) -> None:
        """Hostname that cannot be resolved at validation time is accepted (probe handles it)."""
        import socket
        from unittest.mock import patch

        from pilot_space.application.services.mcp.import_mcp_servers_service import (
            _validate_entry,
        )

        with patch("socket.getaddrinfo", side_effect=socket.gaierror("no such host")):
            err = _validate_entry(self._make_remote("https://nonexistent.example.com/mcp"))

        assert err is None

    def test_accepts_valid_https_url(self) -> None:
        """Valid HTTPS URL with a public IP passes validation."""
        from unittest.mock import patch

        from pilot_space.application.services.mcp.import_mcp_servers_service import (
            _validate_entry,
        )

        # Simulate getaddrinfo returning a public IP
        fake_addr = [(None, None, None, None, ("93.184.216.34", 0))]
        with patch("socket.getaddrinfo", return_value=fake_addr):
            err = _validate_entry(self._make_remote("https://example.com/mcp"))

        assert err is None
