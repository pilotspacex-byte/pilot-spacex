"""AI-specific exception types.

Provides structured exceptions for AI operations following RFC 7807 style.
These exceptions are caught by the error handler and converted to Problem Details.

T091a: AI error types for the AI layer.
"""

from __future__ import annotations

import uuid
from typing import Any


class AIError(Exception):
    """Base exception for all AI-related errors.

    Attributes:
        message: Human-readable error description.
        code: Machine-readable error code.
        details: Additional error context.
    """

    error_code: str = "ai_error"
    http_status: int = 500

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize AI error.

        Args:
            message: Error description.
            code: Optional error code override.
            details: Additional context for debugging.
        """
        super().__init__(message)
        self.message = message
        self.code = code or self.error_code
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API response.

        Returns:
            Dictionary with error information.
        """
        result: dict[str, Any] = {
            "error_code": self.code,
            "message": self.message,
        }
        if self.details:
            result["details"] = self.details
        return result


class RateLimitError(AIError):
    """Raised when AI provider rate limit is exceeded.

    Indicates temporary throttling from the AI provider.
    Clients should retry after the specified delay.
    """

    error_code = "rate_limit_exceeded"
    http_status = 429

    def __init__(
        self,
        message: str = "AI provider rate limit exceeded",
        *,
        retry_after_seconds: int = 60,
        provider: str | None = None,
    ) -> None:
        """Initialize rate limit error.

        Args:
            message: Error description.
            retry_after_seconds: Recommended retry delay.
            provider: AI provider that triggered the limit.
        """
        super().__init__(
            message,
            details={
                "retry_after_seconds": retry_after_seconds,
                "provider": provider,
            },
        )
        self.retry_after_seconds = retry_after_seconds
        self.provider = provider


class ProviderUnavailableError(AIError):
    """Raised when an AI provider is temporarily unavailable.

    Indicates service disruption. Circuit breaker may be open.
    """

    error_code = "provider_unavailable"
    http_status = 503

    def __init__(
        self,
        provider: str,
        message: str | None = None,
        *,
        circuit_open: bool = False,
    ) -> None:
        """Initialize provider unavailable error.

        Args:
            provider: Name of the unavailable provider.
            message: Optional custom message.
            circuit_open: Whether circuit breaker is open.
        """
        msg = message or f"AI provider '{provider}' is temporarily unavailable"
        super().__init__(
            msg,
            details={
                "provider": provider,
                "circuit_open": circuit_open,
            },
        )
        self.provider = provider
        self.circuit_open = circuit_open


class TokenLimitExceededError(AIError):
    """Raised when input exceeds provider's token limit.

    Indicates the request content is too large for the model.
    """

    error_code = "token_limit_exceeded"
    http_status = 400

    def __init__(
        self,
        message: str = "Input exceeds token limit",
        *,
        input_tokens: int | None = None,
        max_tokens: int | None = None,
        provider: str | None = None,
    ) -> None:
        """Initialize token limit error.

        Args:
            message: Error description.
            input_tokens: Number of tokens in the input.
            max_tokens: Maximum allowed tokens.
            provider: AI provider with the limit.
        """
        details: dict[str, Any] = {}
        if input_tokens is not None:
            details["input_tokens"] = input_tokens
        if max_tokens is not None:
            details["max_tokens"] = max_tokens
        if provider:
            details["provider"] = provider

        super().__init__(message, details=details)
        self.input_tokens = input_tokens
        self.max_tokens = max_tokens
        self.provider = provider


class InvalidResponseError(AIError):
    """Raised when AI provider returns an invalid response.

    Indicates parsing failure or unexpected response format.
    """

    error_code = "invalid_response"
    http_status = 502

    def __init__(
        self,
        message: str = "AI provider returned invalid response",
        *,
        raw_response: str | None = None,
        provider: str | None = None,
    ) -> None:
        """Initialize invalid response error.

        Args:
            message: Error description.
            raw_response: The problematic response (truncated for safety).
            provider: AI provider that returned the invalid response.
        """
        details: dict[str, Any] = {}
        if raw_response:
            # Truncate to prevent log bloat
            details["raw_response"] = (
                raw_response[:500] + "..." if len(raw_response) > 500 else raw_response
            )
        if provider:
            details["provider"] = provider

        super().__init__(message, details=details)
        self.raw_response = raw_response
        self.provider = provider


class AITimeoutError(AIError):
    """Raised when AI operation exceeds timeout.

    Indicates the operation took too long to complete.
    """

    error_code = "ai_timeout"
    http_status = 504

    def __init__(
        self,
        message: str = "AI operation timed out",
        *,
        timeout_seconds: float | None = None,
        operation: str | None = None,
        provider: str | None = None,
    ) -> None:
        """Initialize timeout error.

        Args:
            message: Error description.
            timeout_seconds: The timeout that was exceeded.
            operation: The operation that timed out.
            provider: AI provider involved.
        """
        details: dict[str, Any] = {}
        if timeout_seconds is not None:
            details["timeout_seconds"] = timeout_seconds
        if operation:
            details["operation"] = operation
        if provider:
            details["provider"] = provider

        super().__init__(message, details=details)
        self.timeout_seconds = timeout_seconds
        self.operation = operation
        self.provider = provider


class AINotConfiguredError(AIError):
    """Raised when a workspace AI call is made without a valid BYOK API key.

    Per AIGOV-05: every workspace-scoped AI call requires a WorkspaceAPIKey row.
    The platform env key (ANTHROPIC_API_KEY) must not be used as fallback for
    workspace calls — that would violate the BYOK billing model.

    System-only operations (workspace_id=None) may still use the env key.
    """

    error_code = "ai_byok_required"
    http_status = 503

    def __init__(self, workspace_id: uuid.UUID | None = None) -> None:
        """Initialize BYOK configuration error.

        Args:
            workspace_id: Workspace that is missing a BYOK key, or None for
                          system-level operations with no env key configured.
        """
        self.workspace_id = workspace_id
        if workspace_id is not None:
            msg = (
                f"No BYOK API key configured for workspace {workspace_id}. "
                "Configure a key in Settings > API Keys."
            )
        else:
            msg = "No AI provider API key configured. Set ANTHROPIC_API_KEY for system operations."
        super().__init__(
            msg,
            details={"workspace_id": str(workspace_id) if workspace_id else None},
        )


class AIConfigurationError(AIError):
    """Raised when AI configuration is invalid or missing.

    Indicates missing API keys or invalid provider configuration.
    """

    error_code = "ai_configuration_error"
    http_status = 400

    def __init__(
        self,
        message: str = "AI configuration is invalid or missing",
        *,
        provider: str | None = None,
        missing_fields: list[str] | None = None,
    ) -> None:
        """Initialize configuration error.

        Args:
            message: Error description.
            provider: Provider with configuration issue.
            missing_fields: List of missing required fields.
        """
        details: dict[str, Any] = {}
        if provider:
            details["provider"] = provider
        if missing_fields:
            details["missing_fields"] = missing_fields

        super().__init__(message, details=details)
        self.provider = provider
        self.missing_fields = missing_fields


class ContextTooLargeError(AIError):
    """Raised when the context window is exceeded.

    Indicates the combined context is too large for the model.
    """

    error_code = "context_too_large"
    http_status = 400

    def __init__(
        self,
        message: str = "Context exceeds maximum size",
        *,
        context_size: int | None = None,
        max_context: int | None = None,
    ) -> None:
        """Initialize context size error.

        Args:
            message: Error description.
            context_size: Current context size.
            max_context: Maximum allowed context.
        """
        details: dict[str, Any] = {}
        if context_size is not None:
            details["context_size"] = context_size
        if max_context is not None:
            details["max_context"] = max_context

        super().__init__(message, details=details)
        self.context_size = context_size
        self.max_context = max_context


class AgentExecutionError(AIError):
    """Raised when an AI agent fails during execution.

    Wraps underlying errors with agent context.
    """

    error_code = "agent_execution_error"
    http_status = 500

    def __init__(
        self,
        agent_name: str,
        message: str | None = None,
        *,
        cause: Exception | None = None,
    ) -> None:
        """Initialize agent execution error.

        Args:
            agent_name: Name of the agent that failed.
            message: Optional custom message.
            cause: The underlying exception.
        """
        msg = message or f"Agent '{agent_name}' execution failed"
        if cause:
            msg = f"{msg}: {cause!s}"

        super().__init__(
            msg,
            details={
                "agent_name": agent_name,
                "cause_type": type(cause).__name__ if cause else None,
            },
        )
        self.agent_name = agent_name
        self.__cause__ = cause


__all__ = [
    "AIConfigurationError",
    "AIError",
    "AINotConfiguredError",
    "AITimeoutError",
    "AgentExecutionError",
    "ContextTooLargeError",
    "InvalidResponseError",
    "ProviderUnavailableError",
    "RateLimitError",
    "TokenLimitExceededError",
]
