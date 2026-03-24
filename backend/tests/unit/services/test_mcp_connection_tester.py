"""Unit tests for TestMcpConnectionService._test_process argv tokenisation."""

from __future__ import annotations

import pytest

from pilot_space.application.services.mcp.mcp_connection_tester import (
    McpTestResult,
    TestMcpConnectionService,
)
from pilot_space.infrastructure.database.models.workspace_mcp_server import (
    McpCommandRunner,
    McpStatus,
    WorkspaceMcpServer,
)


def _make_server(
    url_or_command: str,
    command_args: str | None = None,
    command_runner: McpCommandRunner | None = None,
) -> WorkspaceMcpServer:
    from unittest.mock import MagicMock

    server = MagicMock(spec=WorkspaceMcpServer)
    server.url_or_command = url_or_command
    server.command_args = command_args
    server.env_vars_encrypted = None
    server.id = "test-server-id"
    server.command_runner = command_runner
    return server


class TestCommandRunnerPrepend:
    """Verify that _test_process prepends the command_runner binary.

    url_or_command stores only the package/args string (e.g. "@context7/mcp").
    The runner binary (npx/uvx) must be prepended before subprocess.exec so
    that the package name is never treated as the executable itself.
    """

    @pytest.mark.asyncio
    async def test_npx_runner_prepended_to_package_name(self) -> None:
        """NPX runner must be prepended as parts[0] before the package name."""
        from unittest.mock import AsyncMock, patch

        server = _make_server("@context7/mcp", command_runner=McpCommandRunner.NPX)
        captured_parts: list[list[str]] = []

        async def _fake_probe(parts, env, start, checked_at):  # type: ignore[override]
            captured_parts.append(parts)
            return McpTestResult(status=McpStatus.ENABLED, latency_ms=10, checked_at=checked_at)

        with patch.object(
            TestMcpConnectionService,
            "_probe_subprocess",
            new=AsyncMock(side_effect=_fake_probe),
        ):
            await TestMcpConnectionService._test_process(server)

        assert len(captured_parts) == 1
        parts = captured_parts[0]
        assert parts[0] == "npx", f"Expected 'npx' as parts[0], got {parts[0]!r}"
        assert parts[1] == "@context7/mcp", f"Expected package as parts[1], got {parts[1]!r}"

    @pytest.mark.asyncio
    async def test_uvx_runner_prepended_to_package_name(self) -> None:
        """UVX runner must be prepended as parts[0] before the package name."""
        from unittest.mock import AsyncMock, patch

        server = _make_server("mcp-server-fetch", command_runner=McpCommandRunner.UVX)
        captured_parts: list[list[str]] = []

        async def _fake_probe(parts, env, start, checked_at):  # type: ignore[override]
            captured_parts.append(parts)
            return McpTestResult(status=McpStatus.ENABLED, latency_ms=5, checked_at=checked_at)

        with patch.object(
            TestMcpConnectionService,
            "_probe_subprocess",
            new=AsyncMock(side_effect=_fake_probe),
        ):
            await TestMcpConnectionService._test_process(server)

        assert len(captured_parts) == 1
        parts = captured_parts[0]
        assert parts[0] == "uvx"
        assert parts[1] == "mcp-server-fetch"

    @pytest.mark.asyncio
    async def test_runner_prepended_with_extra_args(self) -> None:
        """Runner is prepended before package; command_args appended at the end."""
        from unittest.mock import AsyncMock, patch

        server = _make_server(
            "@context7/mcp",
            command_args="--verbose --port 8080",
            command_runner=McpCommandRunner.NPX,
        )
        captured_parts: list[list[str]] = []

        async def _fake_probe(parts, env, start, checked_at):  # type: ignore[override]
            captured_parts.append(parts)
            return McpTestResult(status=McpStatus.ENABLED, latency_ms=10, checked_at=checked_at)

        with patch.object(
            TestMcpConnectionService,
            "_probe_subprocess",
            new=AsyncMock(side_effect=_fake_probe),
        ):
            await TestMcpConnectionService._test_process(server)

        parts = captured_parts[0]
        assert parts[0] == "npx"
        assert parts[1] == "@context7/mcp"
        assert "--verbose" in parts
        assert "--port" in parts
        assert "8080" in parts

    @pytest.mark.asyncio
    async def test_no_command_runner_returns_config_error(self) -> None:
        """When command_runner is None, process test should not crash.

        With command_runner=None the package string is used directly as parts[0].
        The actual _probe_subprocess handles FileNotFoundError internally and
        returns CONFIG_ERROR.  Here we simulate that internal handling by having
        the fake return CONFIG_ERROR directly, confirming _test_process passes
        the result through correctly.
        """
        from unittest.mock import AsyncMock, patch

        server = _make_server("@context7/mcp", command_runner=None)

        # Simulate _probe_subprocess returning CONFIG_ERROR (as it does internally
        # when subprocess raises FileNotFoundError for an unknown executable)
        async def _fake_probe_config_error(parts, env, start, checked_at):  # type: ignore
            return McpTestResult(
                status=McpStatus.CONFIG_ERROR,
                latency_ms=None,
                checked_at=checked_at,
                error_detail=f"Executable not found: {parts[0]!r}",
            )

        with patch.object(
            TestMcpConnectionService,
            "_probe_subprocess",
            new=AsyncMock(side_effect=_fake_probe_config_error),
        ):
            result = await TestMcpConnectionService._test_process(server)

        assert result.status == McpStatus.CONFIG_ERROR


class TestTestProcessArgvTokenisation:
    """Verify that _test_process uses shlex.split for command tokenisation.

    str.split() breaks quoted arguments such as --name "foo bar".
    shlex.split(posix=True) produces the correct POSIX token list and is what
    _probe_subprocess receives.

    Note: These tests now pass command_runner=McpCommandRunner.NPX since the
    runner binary is prepended by _test_process before the package string.
    The full "npx ..." command is NO LONGER valid in url_or_command — only the
    package/args portion belongs there.
    """

    @pytest.mark.asyncio
    async def test_quoted_arg_becomes_single_argv_token(self) -> None:
        """Quoted argument in url_or_command must arrive as one argv element."""
        from unittest.mock import AsyncMock, patch

        # url_or_command contains only the package + its own args (not the runner)
        server = _make_server(
            '--name "foo bar" --flag',
            command_runner=McpCommandRunner.NPX,
        )
        captured_parts: list[list[str]] = []

        async def _fake_probe(parts, env, start, checked_at):  # type: ignore[override]
            captured_parts.append(parts)
            return McpTestResult(status=McpStatus.ENABLED, latency_ms=10, checked_at=checked_at)

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

        server = _make_server(
            "my-pkg",
            command_args='--title "my title"',
            command_runner=McpCommandRunner.NPX,
        )
        captured_parts: list[list[str]] = []

        async def _fake_probe(parts, env, start, checked_at):  # type: ignore[override]
            captured_parts.append(parts)
            return McpTestResult(status=McpStatus.ENABLED, latency_ms=5, checked_at=checked_at)

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
        server = _make_server(
            '--name "unterminated',
            command_runner=McpCommandRunner.NPX,
        )
        result = await TestMcpConnectionService._test_process(server)
        assert result.status == McpStatus.CONFIG_ERROR
        assert result.error_detail is not None
        assert "syntax" in result.error_detail.lower() or "invalid" in result.error_detail.lower()

    @pytest.mark.asyncio
    async def test_malformed_command_args_returns_config_error(self) -> None:
        """Unterminated quote in command_args must return CONFIG_ERROR, not raise."""
        server = _make_server(
            "my-pkg",
            command_args="--flag 'unterminated",
            command_runner=McpCommandRunner.NPX,
        )
        result = await TestMcpConnectionService._test_process(server)
        assert result.status == McpStatus.CONFIG_ERROR
        assert result.error_detail is not None

    @pytest.mark.asyncio
    async def test_simple_command_no_quotes(self) -> None:
        """Plain whitespace-separated command still works correctly after shlex change."""
        from unittest.mock import AsyncMock, patch

        server = _make_server(
            "my-pkg --verbose",
            command_runner=McpCommandRunner.NPX,
        )
        captured_parts: list[list[str]] = []

        async def _fake_probe(parts, env, start, checked_at):  # type: ignore[override]
            captured_parts.append(parts)
            return McpTestResult(status=McpStatus.ENABLED, latency_ms=8, checked_at=checked_at)

        with patch.object(
            TestMcpConnectionService,
            "_probe_subprocess",
            new=AsyncMock(side_effect=_fake_probe),
        ):
            await TestMcpConnectionService._test_process(server)

        assert captured_parts[0] == ["npx", "my-pkg", "--verbose"]
