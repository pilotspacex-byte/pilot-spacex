"""Top-level exception re-exports for Pilot Space.

Provides a single import path for common exceptions used across the application.
Domain-specific exceptions are defined in their respective modules (e.g.,
pilot_space.ai.exceptions, pilot_space.integrations.github.exceptions).
"""

from __future__ import annotations

# Re-export AI-specific exceptions for convenience
from pilot_space.ai.exceptions import (
    AgentExecutionError,
    AIConfigurationError,
    AIError,
    AINotConfiguredError,
    AITimeoutError,
    ContextTooLargeError,
    InvalidResponseError,
    ProviderUnavailableError,
    RateLimitError,
    TokenLimitExceededError,
)

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
