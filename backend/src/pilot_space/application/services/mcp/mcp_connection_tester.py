"""TestMcpConnectionService — on-demand MCP server connectivity probe.

Supports:
  - Remote servers: HTTP GET with 10s timeout via httpx.AsyncClient.
  - Command/NPX/UVX servers: subprocess health check with 10s timeout.

Returns McpTestResult with status, latency_ms, and optional error_detail.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from datetime import UTC, datetime

from pilot_space.infrastructure.database.models.workspace_mcp_server import (
    McpServerType,
    McpStatus,
    WorkspaceMcpServer,
)
from pilot_space.infrastructure.logging import get_logger

logger = get_logger(__name__)

# Connection test timeout in seconds (per spec FR-05-1)
_TEST_TIMEOUT_S = 10.0


@dataclass
class McpTestResult:
    """Result of an on-demand MCP server connection test."""

    status: McpStatus
    latency_ms: int | None
    checked_at: datetime
    error_detail: str | None = None


class TestMcpConnectionService:
    """Perform an on-demand connectivity probe for an MCP server."""

    @staticmethod
    async def test(server: WorkspaceMcpServer) -> McpTestResult:
        """Test connectivity for a given MCP server.

        Dispatches to _test_remote or _test_process based on server_type.
        Always returns within ~10 seconds.

        Args:
            server: WorkspaceMcpServer ORM instance (already loaded from DB).

        Returns:
            McpTestResult with status and optional latency/error.
        """
        if server.server_type == McpServerType.REMOTE:
            return await TestMcpConnectionService._test_remote(server)
        return await TestMcpConnectionService._test_process(server)

    @staticmethod
    async def _test_remote(server: WorkspaceMcpServer) -> McpTestResult:
        """Probe a remote HTTP MCP server.

        Sends an HTTP GET to url_or_command (or url fallback).
        - HTTP < 500: status=ENABLED
        - HTTP >= 500: status=UNHEALTHY
        - Connection error / timeout: status=UNREACHABLE
        """
        import httpx

        url = server.url_or_command or server.url
        if not url:
            return McpTestResult(
                status=McpStatus.CONFIG_ERROR,
                latency_ms=None,
                checked_at=datetime.now(UTC),
                error_detail="No URL configured for remote server",
            )

        # Build headers with auth
        headers: dict[str, str] = {}
        if server.auth_token_encrypted:
            try:
                from pilot_space.infrastructure.encryption import decrypt_api_key

                token = decrypt_api_key(server.auth_token_encrypted)
                headers["Authorization"] = f"Bearer {token}"
            except Exception:
                logger.warning("mcp_test_token_decrypt_failed", server_id=str(server.id))

        # Inject custom headers — prefer plaintext headers_json, fallback to encrypted
        if server.headers_json:
            import json as _json

            try:
                custom_headers = _json.loads(server.headers_json)
                headers.update(custom_headers)
            except (ValueError, TypeError):
                logger.warning("mcp_test_headers_json_parse_failed", server_id=str(server.id))
        elif server.headers_encrypted:
            try:
                from pilot_space.infrastructure.encryption_kv import decrypt_kv

                custom_headers = decrypt_kv(server.headers_encrypted)
                headers.update(custom_headers)
            except Exception:
                logger.warning("mcp_test_headers_decrypt_failed", server_id=str(server.id))

        start = time.monotonic()
        checked_at = datetime.now(UTC)

        try:
            async with httpx.AsyncClient(
                timeout=_TEST_TIMEOUT_S,
                follow_redirects=False,
            ) as client:
                response = await client.get(url, headers=headers)
                elapsed_ms = int((time.monotonic() - start) * 1000)

                if response.status_code < 500:
                    return McpTestResult(
                        status=McpStatus.ENABLED,
                        latency_ms=elapsed_ms,
                        checked_at=checked_at,
                    )
                return McpTestResult(
                    status=McpStatus.UNHEALTHY,
                    latency_ms=elapsed_ms,
                    checked_at=checked_at,
                    error_detail=f"HTTP {response.status_code}",
                )
        except httpx.TimeoutException:
            return McpTestResult(
                status=McpStatus.UNREACHABLE,
                latency_ms=int(_TEST_TIMEOUT_S * 1000),
                checked_at=checked_at,
                error_detail="Connection timed out after 10s",
            )
        except (httpx.ConnectError, httpx.RequestError) as exc:
            return McpTestResult(
                status=McpStatus.UNREACHABLE,
                latency_ms=None,
                checked_at=checked_at,
                error_detail=str(exc),
            )
        except Exception as exc:
            logger.warning("mcp_test_remote_unexpected", error=str(exc))
            return McpTestResult(
                status=McpStatus.UNREACHABLE,
                latency_ms=None,
                checked_at=checked_at,
                error_detail=f"Unexpected error: {exc}",
            )

    @staticmethod
    async def _test_process(server: WorkspaceMcpServer) -> McpTestResult:
        """Check if an NPX/UVX process starts without immediate failure.

        Spawns the command with a 10s timeout. If the process starts without
        immediately exiting with a non-zero code, it is considered healthy.
        The subprocess is terminated after the timeout or on success.

        Note: This is a best-effort check — it does not validate MCP protocol
        compliance, only that the command is launchable.
        """
        command_str = server.url_or_command
        if not command_str:
            return McpTestResult(
                status=McpStatus.CONFIG_ERROR,
                latency_ms=None,
                checked_at=datetime.now(UTC),
                error_detail="No command configured",
            )

        import shlex

        try:
            parts = shlex.split(command_str, posix=True)
        except ValueError as exc:
            return McpTestResult(
                status=McpStatus.CONFIG_ERROR,
                latency_ms=None,
                checked_at=datetime.now(UTC),
                error_detail=f"Invalid command syntax: {exc}",
            )

        if not parts:
            return McpTestResult(
                status=McpStatus.CONFIG_ERROR,
                latency_ms=None,
                checked_at=datetime.now(UTC),
                error_detail="Empty command",
            )

        # Prepend the command runner (npx/uvx) so the package name is not
        # treated as the executable. url_or_command stores only the package/args
        # string (e.g. "@context7/mcp"), not the full binary path.
        if server.command_runner is not None:
            parts = [server.command_runner.value, *parts]

        # Extend with command_args if present, also tokenised with shlex
        if server.command_args:
            try:
                parts.extend(shlex.split(server.command_args, posix=True))
            except ValueError as exc:
                return McpTestResult(
                    status=McpStatus.CONFIG_ERROR,
                    latency_ms=None,
                    checked_at=datetime.now(UTC),
                    error_detail=f"Invalid command_args syntax: {exc}",
                )

        import os

        env = dict(os.environ)
        if server.env_vars_encrypted:
            try:
                from pilot_space.infrastructure.encryption_kv import decrypt_kv

                env_vars = decrypt_kv(server.env_vars_encrypted)
                env.update(env_vars)
            except Exception:
                logger.warning("mcp_test_env_decrypt_failed", server_id=str(server.id))

        start = time.monotonic()
        checked_at = datetime.now(UTC)
        return await TestMcpConnectionService._probe_subprocess(parts, env, start, checked_at)

    @staticmethod
    async def _probe_subprocess(
        parts: list[str],
        env: dict[str, str],
        start: float,
        checked_at: datetime,
    ) -> McpTestResult:
        """Run a subprocess probe and return the McpTestResult."""
        try:
            proc = await asyncio.create_subprocess_exec(
                *parts,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )

            # Wait briefly to detect immediate exit
            try:
                await asyncio.wait_for(proc.wait(), timeout=2.0)
                elapsed_ms = int((time.monotonic() - start) * 1000)
                if proc.returncode and proc.returncode != 0:
                    return McpTestResult(
                        status=McpStatus.UNREACHABLE,
                        latency_ms=elapsed_ms,
                        checked_at=checked_at,
                        error_detail=f"Process exited immediately with code {proc.returncode}",
                    )
                # Process exited with 0 — acceptable for some tools
                return McpTestResult(
                    status=McpStatus.ENABLED,
                    latency_ms=elapsed_ms,
                    checked_at=checked_at,
                )
            except TimeoutError:
                # Process is still running after 2s — good, it started
                elapsed_ms = int((time.monotonic() - start) * 1000)
                from contextlib import suppress

                try:
                    proc.terminate()
                    await asyncio.wait_for(proc.wait(), timeout=3.0)
                except (TimeoutError, ProcessLookupError):
                    with suppress(ProcessLookupError):
                        proc.kill()
                return McpTestResult(
                    status=McpStatus.ENABLED,
                    latency_ms=elapsed_ms,
                    checked_at=checked_at,
                )

        except FileNotFoundError:
            return McpTestResult(
                status=McpStatus.CONFIG_ERROR,
                latency_ms=None,
                checked_at=checked_at,
                error_detail=f"Executable not found: {parts[0]!r}",
            )
        except Exception as exc:
            logger.warning("mcp_test_process_unexpected", error=str(exc))
            return McpTestResult(
                status=McpStatus.UNREACHABLE,
                latency_ms=None,
                checked_at=checked_at,
                error_detail=f"Launch error: {exc}",
            )


__all__ = ["McpTestResult", "TestMcpConnectionService"]
