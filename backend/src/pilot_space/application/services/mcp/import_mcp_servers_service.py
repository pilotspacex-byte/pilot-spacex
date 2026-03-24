"""ImportMcpServersService — bulk MCP server import from JSON config.

Supports Claude Desktop, Cursor, and VS Code MCP config formats:
  { "mcpServers": { "<name>": { "url": "...", "command": "...", ... } } }

Each parsed server is validated for SSRF / command injection before import.
Duplicate display_names within the workspace are skipped (not overwritten).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import TYPE_CHECKING
from uuid import UUID

from pilot_space.application.services.mcp.exceptions import (
    McpConfigParseError,
    McpEnvVarsEncryptionError,
)
from pilot_space.infrastructure.database.models.workspace_mcp_server import (
    McpAuthType,
    McpCommandRunner,
    McpServerType,
    McpStatus,
    McpTransport,
    WorkspaceMcpServer,
)
from pilot_space.infrastructure.logging import get_logger
from pilot_space.security.mcp_validation import (
    SHELL_METACHAR_RE as _SHELL_METACHAR_RE,
    validate_mcp_url as _validate_mcp_url,
)

if TYPE_CHECKING:
    from pilot_space.infrastructure.database.repositories.workspace_mcp_server_repository import (
        WorkspaceMcpServerRepository,
    )

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Parsed intermediate type
# ---------------------------------------------------------------------------


@dataclass
class ParsedMcpServer:
    """Intermediate representation of a parsed MCP server config entry."""

    name: str
    server_type: McpServerType
    transport: McpTransport
    url_or_command: str
    command_runner: McpCommandRunner | None = None
    command_args: str | None = None
    env_vars: dict[str, str] | None = None
    headers: dict[str, str] | None = None


# ---------------------------------------------------------------------------
# Import result
# ---------------------------------------------------------------------------


@dataclass
class ImportedEntry:
    """A successfully imported server."""

    name: str
    id: UUID


@dataclass
class SkippedEntry:
    """A server entry skipped during import."""

    name: str
    reason: str


@dataclass
class ErrorEntry:
    """A server entry that failed validation during import."""

    name: str
    reason: str


@dataclass
class ImportResult:
    """Aggregated result of an import_servers call."""

    imported: list[ImportedEntry] = field(default_factory=list)
    skipped: list[SkippedEntry] = field(default_factory=list)
    errors: list[ErrorEntry] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class ImportMcpServersService:
    """Parse a JSON MCP config and bulk-import servers into a workspace."""

    @staticmethod
    def parse_config_json(raw: str) -> tuple[list[ParsedMcpServer], list[ErrorEntry]]:
        """Parse a Claude / Cursor / VS Code MCP config JSON string.

        Expected shape:
            { "mcpServers": { "<name>": { ... } } }

        Each server entry may contain:
            - ``url`` or ``httpUrl``: remote HTTPS endpoint → McpServerType.REMOTE
            - ``command``: executable string → inferred as NPX or UVX
            - ``args``: list of CLI arguments (joined to command_args)
            - ``env``: environment variable dict
            - ``transport``: "sse" | "stdio" | "streamable_http" (optional, inferred)

        Args:
            raw: Raw JSON string.

        Returns:
            Tuple of (parsed servers, parse-time errors). Entries that cannot be
            identified at all (e.g. non-dict config values) are silently skipped;
            entries that are recognisable but unsupported produce an ErrorEntry.

        Raises:
            ValueError: If the JSON is malformed.
            TypeError: If the top-level shape is wrong.
        """
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise McpConfigParseError(f"Invalid JSON: {exc}") from exc

        if not isinstance(data, dict):
            raise McpConfigParseError("Config JSON must be a JSON object")

        mcp_servers = data.get("mcpServers") or data.get("mcp_servers") or {}
        if not isinstance(mcp_servers, dict):
            raise McpConfigParseError(
                "'mcpServers' must be a JSON object mapping names to server configs"
            )

        parsed: list[ParsedMcpServer] = []
        errors: list[ErrorEntry] = []
        for name, config in mcp_servers.items():
            if not isinstance(config, dict):
                continue

            entry = ImportMcpServersService._parse_server_entry(name, config)
            if isinstance(entry, ErrorEntry):
                errors.append(entry)
            elif entry is not None:
                parsed.append(entry)

        return parsed, errors

    @staticmethod
    def _parse_server_entry(
        name: str, config: dict[str, object]
    ) -> ParsedMcpServer | ErrorEntry | None:
        """Parse a single server config entry.

        Returns:
            ParsedMcpServer on success, ErrorEntry when the entry is recognisable
            but cannot be imported (e.g. unsupported runner, no url/command), or
            None when the entry is entirely unidentifiable and should be skipped
            silently.
        """
        # Determine server type and url_or_command
        url_value = config.get("url")
        http_url_value = config.get("httpUrl")
        url = (
            url_value
            if url_value and isinstance(url_value, str)
            else (http_url_value if http_url_value and isinstance(http_url_value, str) else None)
        )
        from_http_url = not (url_value and isinstance(url_value, str)) and bool(url)
        command = config.get("command")

        if url:
            server_type = McpServerType.REMOTE
            url_or_command = url

            # Infer transport; httpUrl implies streamable_http unless overridden
            default_transport = "streamable_http" if from_http_url else "sse"
            transport_str = str(config.get("transport", default_transport)).lower()
            if transport_str == "stdio":
                transport = McpTransport.STDIO
            elif transport_str in ("streamable_http", "streamablehttp"):
                transport = McpTransport.STREAMABLE_HTTP
            else:
                transport = McpTransport.SSE

            return ParsedMcpServer(
                name=name,
                server_type=server_type,
                transport=transport,
                url_or_command=url_or_command,
                env_vars=_extract_env_vars(config),
                headers=_extract_headers(config),
            )

        if command and isinstance(command, str):
            # Parse runner from first token
            parts = command.split()
            runner_str = parts[0].lower() if parts else ""

            if runner_str == "npx":
                command_runner = McpCommandRunner.NPX
            elif runner_str == "uvx":
                command_runner = McpCommandRunner.UVX
            else:
                # Unsupported runner — surface as an error entry
                return ErrorEntry(
                    name=name,
                    reason=f"unsupported_command_runner: '{runner_str}' is not supported (use npx or uvx)",
                )

            # Strip runner from url_or_command; remaining tokens are the package/args
            package_args = " ".join(parts[1:]).strip() if len(parts) > 1 else ""

            # Append JSON args list
            args_list = config.get("args")
            if isinstance(args_list, list):
                str_args = " ".join(str(a) for a in args_list if a)
                if str_args:
                    package_args = f"{package_args} {str_args}".strip()

            return ParsedMcpServer(
                name=name,
                server_type=McpServerType.COMMAND,
                command_runner=command_runner,
                transport=McpTransport.STDIO,
                url_or_command=package_args,
                env_vars=_extract_env_vars(config),
            )

        return ErrorEntry(
            name=name,
            reason="unsupported_entry: no 'url', 'httpUrl', or 'command' key found",
        )

    @staticmethod
    async def import_servers(
        workspace_id: UUID,
        parsed: list[ParsedMcpServer],
        repo: WorkspaceMcpServerRepository,
        parse_errors: list[ErrorEntry] | None = None,
    ) -> ImportResult:
        """Bulk-import parsed servers into a workspace.

        For each parsed server:
        - Validates SSRF / command injection rules.
        - Checks for existing display_name in workspace (application-level dedup).
        - Creates the server row if no conflicts.

        Args:
            workspace_id: Target workspace UUID.
            parsed: List of ParsedMcpServer instances from parse_config_json.
            repo: WorkspaceMcpServerRepository instance.
            parse_errors: Optional list of ErrorEntry items produced during parsing
                (e.g. unsupported command runners). Pre-seeded into the result.

        Returns:
            ImportResult with imported, skipped, and errors lists.
        """
        result = ImportResult()
        if parse_errors:
            result.errors.extend(parse_errors)

        # Load existing server names for this workspace
        existing = await repo.get_active_by_workspace(workspace_id)
        existing_names = {s.display_name.lower() for s in existing}

        for entry in parsed:
            # Validate url_or_command
            validation_error = _validate_entry(entry)
            if validation_error:
                result.errors.append(ErrorEntry(name=entry.name, reason=validation_error))
                logger.info(
                    "mcp_import_validation_error",
                    name=entry.name,
                    reason=validation_error,
                )
                continue

            # Check for duplicate name
            if entry.name.lower() in existing_names:
                result.skipped.append(SkippedEntry(name=entry.name, reason="name_conflict"))
                logger.info("mcp_import_skipped_duplicate", name=entry.name)
                continue

            # Encrypt env_vars and headers if provided
            from pilot_space.infrastructure.encryption_kv import encrypt_kv

            headers_encrypted: str | None = None
            headers_json: str | None = None
            if entry.headers:
                import json as _json

                headers_json = _json.dumps(entry.headers)

            env_vars_encrypted: str | None = None
            if entry.env_vars:
                try:
                    env_vars_encrypted = encrypt_kv(entry.env_vars)
                except Exception as exc:
                    logger.exception(
                        "mcp_import_env_vars_encryption_failed",
                        name=entry.name,
                    )
                    raise McpEnvVarsEncryptionError(
                        f"Failed to encrypt env_vars for server '{entry.name}': {exc}"
                    ) from exc

            server = WorkspaceMcpServer(
                workspace_id=workspace_id,
                display_name=entry.name,
                url=entry.url_or_command,
                url_or_command=entry.url_or_command,
                server_type=entry.server_type,
                command_runner=entry.command_runner,
                transport=entry.transport,
                command_args=entry.command_args,
                auth_type=McpAuthType.NONE,
                headers_json=headers_json,
                headers_encrypted=headers_encrypted,
                env_vars_encrypted=env_vars_encrypted,
                is_enabled=True,
                last_status=McpStatus.ENABLED,
            )
            server = await repo.create(server)
            existing_names.add(entry.name.lower())
            result.imported.append(ImportedEntry(name=entry.name, id=server.id))
            logger.info(
                "mcp_import_server_created",
                workspace_id=str(workspace_id),
                name=entry.name,
                server_id=str(server.id),
            )

        return result


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_env_vars(config: dict[str, object]) -> dict[str, str] | None:
    """Extract environment variables from a server config entry."""
    env = config.get("env")
    if isinstance(env, dict):
        return {str(k): str(v) for k, v in env.items() if k and v is not None}
    return None


def _extract_headers(config: dict[str, object]) -> dict[str, str] | None:
    """Extract headers from a server config entry."""
    headers = config.get("headers")
    if isinstance(headers, dict):
        return {str(k): str(v) for k, v in headers.items() if k and v is not None}
    return None


def _validate_entry(entry: ParsedMcpServer) -> str | None:
    """Validate a parsed server entry for SSRF and command injection.

    For REMOTE servers, applies the full SSRF blocklist (HTTPS scheme +
    private/metadata IP range check) via ``validate_mcp_url`` — identical to
    the rules enforced by the POST and PATCH endpoints.

    Returns:
        An error message string if invalid, or None if valid.
    """
    if entry.server_type == McpServerType.REMOTE:
        try:
            _validate_mcp_url(entry.url_or_command)
        except ValueError as exc:
            return f"invalid_url: {exc}"
    elif entry.server_type == McpServerType.COMMAND:
        if not entry.url_or_command.strip():
            return "invalid_command: command must not be empty"
        if _SHELL_METACHAR_RE.search(entry.url_or_command):
            return "invalid_command: contains disallowed shell metacharacters"

    return None


__all__ = [
    "ErrorEntry",
    "ImportMcpServersService",
    "ImportResult",
    "ImportedEntry",
    "ParsedMcpServer",
    "SkippedEntry",
]
