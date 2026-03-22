"""Unit tests for TestMcpConnectionService._test_process argv tokenisation."""

from __future__ import annotations

import pytest

from pilot_space.application.services.mcp.mcp_connection_tester import (
    McpTestResult,
    TestMcpConnectionService,
)
from pilot_space.infrastructure.database.models.workspace_mcp_server import (
    McpStatus,
    WorkspaceMcpServer,
)


class TestTestProcessArgvTokenisation:
    """Verify that _test_process uses shlex.split for command tokenisation.

    str.split() breaks quoted arguments such as --name "foo bar".
    shlex.split(posix=True) produces the correct POSIX token list and is what
    _probe_subprocess receives.
    """

    def _make_server(
        self,
        url_or_command: str,
        command_args: str | None = None,
    ) -> WorkspaceMcpServer:
        from unittest.mock import MagicMock

        server = MagicMock(spec=WorkspaceMcpServer)
        server.url_or_command = url_or_command
        server.command_args = command_args
        server.env_vars_encrypted = None
        server.id = "test-server-id"
        return server

    @pytest.mark.asyncio
    async def test_quoted_arg_becomes_single_argv_token(self) -> None:
        """Quoted argument in url_or_command must arrive as one argv element."""
        from unittest.mock import AsyncMock, patch

        server = self._make_server('npx --name "foo bar" --flag')
        captured_parts: list[list[str]] = []

        async def _fake_probe(parts, env, start, checked_at):  # type: ignore[override]
            captured_parts.append(parts)
            return McpTestResult(
                status=McpStatus.ENABLED,
                latency_ms=10,
                checked_at=checked_at,
            )

        with patch.object(
            TestMcpConnectionService,
            "_probe_subprocess",
            new=AsyncMock(side_effect=_fake_probe),
        ):
            await TestMcpConnectionService._test_process(server)

        assert len(captured_parts) == 1
        parts = captured_parts[0]
        assert parts[0] == "npx"
        assert "--name" in parts
        assert "foo bar" in parts  # single token
        assert '"foo' not in parts  # NOT split on whitespace inside quotes
        assert 'bar"' not in parts

    @pytest.mark.asyncio
    async def test_command_args_quoted_token_is_single_element(self) -> None:
        """Quoted token in command_args must be a single argv element."""
        from unittest.mock import AsyncMock, patch

        server = self._make_server("npx my-pkg", command_args='--title "my title"')
        captured_parts: list[list[str]] = []

        async def _fake_probe(parts, env, start, checked_at):  # type: ignore[override]
            captured_parts.append(parts)
            return McpTestResult(
                status=McpStatus.ENABLED,
                latency_ms=5,
                checked_at=checked_at,
            )

        with patch.object(
            TestMcpConnectionService,
            "_probe_subprocess",
            new=AsyncMock(side_effect=_fake_probe),
        ):
            await TestMcpConnectionService._test_process(server)

        assert len(captured_parts) == 1
        parts = captured_parts[0]
        assert "my-pkg" in parts
        assert "--title" in parts
        assert "my title" in parts  # single token, quotes stripped
        assert '"my title"' not in parts  # NOT with surrounding quotes

    @pytest.mark.asyncio
    async def test_malformed_quotes_returns_config_error(self) -> None:
        """Unterminated quote in url_or_command must return CONFIG_ERROR, not raise."""
        server = self._make_server('npx --name "unterminated')
        result = await TestMcpConnectionService._test_process(server)
        assert result.status == McpStatus.CONFIG_ERROR
        assert result.error_detail is not None
        assert "syntax" in result.error_detail.lower() or "invalid" in result.error_detail.lower()

    @pytest.mark.asyncio
    async def test_malformed_command_args_returns_config_error(self) -> None:
        """Unterminated quote in command_args must return CONFIG_ERROR, not raise."""
        server = self._make_server("npx my-pkg", command_args="--flag 'unterminated")
        result = await TestMcpConnectionService._test_process(server)
        assert result.status == McpStatus.CONFIG_ERROR
        assert result.error_detail is not None

    @pytest.mark.asyncio
    async def test_simple_command_no_quotes(self) -> None:
        """Plain whitespace-separated command still works correctly after shlex change."""
        from unittest.mock import AsyncMock, patch

        server = self._make_server("npx my-pkg --verbose")
        captured_parts: list[list[str]] = []

        async def _fake_probe(parts, env, start, checked_at):  # type: ignore[override]
            captured_parts.append(parts)
            return McpTestResult(
                status=McpStatus.ENABLED,
                latency_ms=8,
                checked_at=checked_at,
            )

        with patch.object(
            TestMcpConnectionService,
            "_probe_subprocess",
            new=AsyncMock(side_effect=_fake_probe),
        ):
            await TestMcpConnectionService._test_process(server)

        assert captured_parts[0] == ["npx", "my-pkg", "--verbose"]
