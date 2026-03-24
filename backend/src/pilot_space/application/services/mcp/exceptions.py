"""MCP service exception types.

Follows the project TranscriptionError pattern (error_code + http_status + message)
so the middleware error handler can convert these to RFC 7807 Problem Details
responses without try/except in every router.
"""

from __future__ import annotations


class McpServerError(Exception):
    """Base exception for all MCP server service errors.

    Attributes:
        message: Human-readable error description.
        error_code: Machine-readable error code.
        http_status: HTTP status code for the Problem Details response.
    """

    error_code: str = "mcp_server_error"
    http_status: int = 500

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        if code is not None:
            self.error_code = code


class McpConfigParseError(McpServerError):
    """Raised when the bulk-import config JSON cannot be parsed.

    Corresponds to malformed JSON or an unexpected top-level shape.
    """

    error_code = "mcp_config_parse_error"
    http_status = 422


class McpEnvVarsEncryptionError(McpServerError):
    """Raised when env_vars encryption fails during bulk import.

    Indicates an internal server-side key management failure.
    """

    error_code = "mcp_env_vars_encryption_error"
    http_status = 500


__all__ = [
    "McpConfigParseError",
    "McpEnvVarsEncryptionError",
    "McpServerError",
]
