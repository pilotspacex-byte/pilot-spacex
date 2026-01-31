"""
Request-scoped context management for AI operations.

Provides thread-safe, request-scoped storage for workspace context
using contextvars for observability and debugging.

API keys are now passed via SDK's `env` parameter instead of os.environ mutation.
"""

from contextvars import ContextVar
from uuid import UUID

# Additional context for debugging and observability
_workspace_id_var: ContextVar[UUID | None] = ContextVar("workspace_id", default=None)
_user_id_var: ContextVar[UUID | None] = ContextVar("user_id", default=None)


def set_workspace_context(workspace_id: UUID, user_id: UUID) -> None:
    """Set workspace context for current request (for logging/debugging).

    Args:
        workspace_id: Current workspace UUID
        user_id: Current user UUID
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
    """Clear all context variables for current request.

    Should be called in finally block to ensure full cleanup.
    """
    _workspace_id_var.set(None)
    _user_id_var.set(None)
