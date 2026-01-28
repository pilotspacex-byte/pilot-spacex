"""
Request-scoped context management for AI operations.

Provides thread-safe, request-scoped storage for API keys and other
sensitive context data using contextvars.

This replaces the unsafe pattern of setting os.environ["ANTHROPIC_API_KEY"]
per request, which causes race conditions in concurrent request scenarios.

Since the Claude Agent SDK reads API keys from os.environ, we use an asyncio.Lock
to serialize access to the environment variable, ensuring only one request
manipulates it at a time.
"""

import asyncio
from contextvars import ContextVar
from uuid import UUID

# Lock storage per event loop to serialize os.environ["ANTHROPIC_API_KEY"] access
# Required because Claude Agent SDK reads from environment, not from constructor
# Stored per event loop to avoid RuntimeError when event loop changes
_api_key_locks: dict[asyncio.AbstractEventLoop, asyncio.Lock] = {}

# Request-scoped API key storage
# Each async task gets its own copy, preventing cross-request contamination
_api_key_var: ContextVar[str | None] = ContextVar("anthropic_api_key", default=None)

# Additional context for debugging and observability
_workspace_id_var: ContextVar[UUID | None] = ContextVar("workspace_id", default=None)
_user_id_var: ContextVar[UUID | None] = ContextVar("user_id", default=None)


def set_api_key(key: str) -> None:
    """
    Set Anthropic API key for current request context.

    Args:
        key: Anthropic API key (sk-ant-...)

    Example:
        >>> set_api_key("sk-ant-api03-...")
        >>> # Key is now available for current async context only
    """
    _api_key_var.set(key)


def get_api_key() -> str | None:
    """
    Retrieve Anthropic API key from current request context.

    Returns:
        API key if set, None otherwise

    Example:
        >>> key = get_api_key()
        >>> if key:
        ...     # Use key for SDK calls
    """
    return _api_key_var.get()


def clear_api_key() -> None:
    """
    Clear API key from current request context.

    Should be called in finally block to ensure cleanup.

    Example:
        >>> set_api_key("sk-ant-...")
        >>> try:
        ...     # Do work
        ...     pass
        ... finally:
        ...     clear_api_key()
    """
    _api_key_var.set(None)


def set_workspace_context(workspace_id: UUID, user_id: UUID) -> None:
    """
    Set workspace context for current request (for logging/debugging).

    Args:
        workspace_id: Current workspace UUID
        user_id: Current user UUID

    Example:
        >>> set_workspace_context(workspace_id, user_id)
        >>> # Context available for logging throughout request
    """
    _workspace_id_var.set(workspace_id)
    _user_id_var.set(user_id)


def get_workspace_id() -> UUID | None:
    """Get workspace ID from current context."""
    return _workspace_id_var.get()


def get_user_id() -> UUID | None:
    """Get user ID from current context."""
    return _user_id_var.get()


def clear_context() -> None:
    """
    Clear all context variables for current request.

    Should be called in finally block to ensure full cleanup.

    Example:
        >>> set_api_key("sk-ant-...")
        >>> set_workspace_context(workspace_id, user_id)
        >>> try:
        ...     # Do work
        ...     pass
        ... finally:
        ...     clear_context()
    """
    clear_api_key()
    _workspace_id_var.set(None)
    _user_id_var.set(None)


def get_api_key_lock() -> asyncio.Lock:
    """
    Get the asyncio.Lock used to serialize os.environ["ANTHROPIC_API_KEY"] access.

    This lock MUST be acquired before setting os.environ["ANTHROPIC_API_KEY"]
    to prevent race conditions when multiple concurrent requests use different API keys.

    The lock is stored per event loop to avoid RuntimeError when the event loop
    changes (e.g., between test runs).

    Returns:
        asyncio.Lock for serializing environment variable access

    Example:
        >>> async with get_api_key_lock():
        ...     original_key = os.getenv("ANTHROPIC_API_KEY")
        ...     os.environ["ANTHROPIC_API_KEY"] = workspace_key
        ...     try:
        ...         # Call SDK (reads from os.environ)
        ...         await query(...)
        ...     finally:
        ...         # Restore original key
        ...         if original_key:
        ...             os.environ["ANTHROPIC_API_KEY"] = original_key
        ...         else:
        ...             del os.environ["ANTHROPIC_API_KEY"]
    """
    # Get current event loop
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # No event loop running, create one (shouldn't happen in async context)
        raise RuntimeError(
            "get_api_key_lock() must be called from within an async context"
        ) from None

    # Get or create lock for this event loop
    if loop not in _api_key_locks:
        _api_key_locks[loop] = asyncio.Lock()

    return _api_key_locks[loop]
