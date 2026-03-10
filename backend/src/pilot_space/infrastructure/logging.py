"""Structured logging configuration with structlog.

Provides JSON-formatted logs with request context, telemetry, and observability.

Key features:
- JSON output for log aggregation (Datadog, CloudWatch, etc.)
- Request ID tracking across async boundaries
- Workspace and user context injection
- Performance metrics and latency tracking
- Integration with existing telemetry system
"""

from __future__ import annotations

import logging
import sys
from contextvars import ContextVar
from typing import Any

import structlog
from structlog.types import EventDict, Processor

from pilot_space.config import Settings

# Context variables for request tracking
_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)
_workspace_id: ContextVar[str | None] = ContextVar("workspace_id", default=None)
_user_id: ContextVar[str | None] = ContextVar("user_id", default=None)
_correlation_id: ContextVar[str | None] = ContextVar("correlation_id", default=None)

# OPS-04: Observability fields — trace_id, actor, action
_trace_id: ContextVar[str | None] = ContextVar("trace_id", default=None)
_actor: ContextVar[str | None] = ContextVar("actor", default=None)
_action: ContextVar[str | None] = ContextVar("action", default=None)


def add_request_context(
    logger: logging.Logger, method_name: str, event_dict: EventDict
) -> EventDict:
    """Add request context to log entries.

    Args:
        logger: Logger instance.
        method_name: Method name.
        event_dict: Event dictionary.

    Returns:
        Event dictionary with added context.
    """
    if request_id := _request_id.get():
        event_dict["request_id"] = request_id
    if workspace_id := _workspace_id.get():
        event_dict["workspace_id"] = workspace_id
    if user_id := _user_id.get():
        event_dict["user_id"] = user_id
    if correlation_id := _correlation_id.get():
        event_dict["correlation_id"] = correlation_id
    if trace_id := _trace_id.get():
        event_dict["trace_id"] = trace_id
    if actor := _actor.get():
        event_dict["actor"] = actor
    if action := _action.get():
        event_dict["action"] = action
    return event_dict


def drop_color_message_key(
    logger: logging.Logger, method_name: str, event_dict: EventDict
) -> EventDict:
    """Drop color_message key from event_dict (used by colorama).

    Args:
        logger: Logger instance.
        method_name: Method name.
        event_dict: Event dictionary.

    Returns:
        Event dictionary without color_message.
    """
    event_dict.pop("color_message", None)
    return event_dict


def configure_structlog(settings: Settings) -> None:
    """Configure structlog for structured logging.

    Args:
        settings: Application settings.
    """
    # Determine if we're in development mode
    is_dev = settings.is_development

    # Choose processors based on environment
    processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,  # Merge context vars
        structlog.stdlib.add_log_level,  # Add log level
        structlog.stdlib.add_logger_name,  # Add logger name
        structlog.processors.TimeStamper(fmt="iso", utc=True),  # ISO 8601 timestamps
        add_request_context,  # Add request/workspace/user context
        structlog.processors.StackInfoRenderer(),  # Render stack info
    ]

    # Add exception formatting
    if is_dev:
        # Development: Human-readable console output with colors
        processors.extend(
            [
                structlog.dev.set_exc_info,  # Better exception info
                structlog.processors.ExceptionPrettyPrinter(),  # Pretty exceptions
                drop_color_message_key,
                structlog.dev.ConsoleRenderer(colors=True),  # Colored console
            ]
        )
    else:
        # Production: JSON output for log aggregation
        processors.extend(
            [
                structlog.processors.format_exc_info,  # Format exception info
                structlog.processors.JSONRenderer(),  # JSON output
            ]
        )

    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",  # structlog handles formatting
        stream=sys.stdout,
        level=getattr(logging, settings.log_level.upper()),
    )

    # Set log levels for noisy third-party libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("fastapi").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)


def set_request_context(
    *,
    request_id: str | None = None,
    workspace_id: str | None = None,
    user_id: str | None = None,
    correlation_id: str | None = None,
    trace_id: str | None = None,
    actor: str | None = None,
) -> None:
    """Set request context for logging.

    Args:
        request_id: Request ID.
        workspace_id: Workspace ID.
        user_id: User ID.
        correlation_id: Correlation ID for distributed tracing.
        trace_id: Trace ID for cross-service correlation (OPS-04).
        actor: Actor identifier, e.g. "user:{user_id}" or "system:service" (OPS-04).
    """
    if request_id:
        _request_id.set(request_id)
    if workspace_id:
        _workspace_id.set(workspace_id)
    if user_id:
        _user_id.set(user_id)
    if correlation_id:
        _correlation_id.set(correlation_id)
    if trace_id:
        _trace_id.set(trace_id)
    if actor:
        _actor.set(actor)


def set_action(action: str) -> None:
    """Set the current action context for logging.

    Args:
        action: Action identifier, e.g. "issue.create" or "note.update" (OPS-04).
    """
    _action.set(action)


def clear_request_context() -> None:
    """Clear request context after request completion."""
    _request_id.set(None)
    _workspace_id.set(None)
    _user_id.set(None)
    _correlation_id.set(None)
    _trace_id.set(None)
    _actor.set(None)
    _action.set(None)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Get a structured logger instance.

    Args:
        name: Logger name (typically __name__).

    Returns:
        Structured logger with bound context.

    Usage:
        logger = get_logger(__name__)
        logger.info("user_login", user_id=str(user.id), workspace_id=str(ws.id))
        logger.error("database_error", error=str(e), query=query_str)
    """
    return structlog.get_logger(name)


def log_performance(
    operation: str,
    duration_ms: float,
    **extra: Any,
) -> None:
    """Log performance metrics for monitoring.

    Args:
        operation: Operation name.
        duration_ms: Duration in milliseconds.
        **extra: Additional context.
    """
    logger = get_logger("performance")
    logger.info(
        "performance_metric",
        operation=operation,
        duration_ms=duration_ms,
        **extra,
    )


__all__ = [
    "add_request_context",
    "clear_request_context",
    "configure_structlog",
    "get_logger",
    "log_performance",
    "set_action",
    "set_request_context",
]
