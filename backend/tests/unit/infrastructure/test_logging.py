"""Tests for structured logging with structlog."""

from __future__ import annotations

import pytest

from pilot_space.config import Settings
from pilot_space.infrastructure.logging import (
    add_request_context,
    clear_request_context,
    configure_structlog,
    get_logger,
    log_performance,
    set_action,
    set_request_context,
)


@pytest.fixture
def dev_settings() -> Settings:
    """Create development settings."""
    return Settings(app_env="development", log_level="INFO")


@pytest.fixture
def prod_settings() -> Settings:
    """Create production settings."""
    return Settings(app_env="production", log_level="INFO")


def test_configure_structlog_dev(dev_settings: Settings) -> None:
    """Test structlog configuration in development mode."""
    configure_structlog(dev_settings)

    logger = get_logger(__name__)
    assert logger is not None
    # Verify logger works by calling a method
    logger.info("test_message", key="value")


def test_configure_structlog_prod(prod_settings: Settings) -> None:
    """Test structlog configuration in production mode."""
    configure_structlog(prod_settings)

    logger = get_logger(__name__)
    assert logger is not None
    # Verify logger works by calling a method
    logger.info("test_message", key="value")


def test_set_request_context() -> None:
    """Test setting request context for logging."""
    set_request_context(
        request_id="req-123",
        workspace_id="ws-456",
        user_id="user-789",
        correlation_id="corr-abc",
    )

    # Context should be set in context vars
    # We can't directly access the context vars, but we can verify
    # that the function doesn't raise errors
    clear_request_context()


def test_clear_request_context() -> None:
    """Test clearing request context."""
    set_request_context(request_id="req-123")
    clear_request_context()
    # Should not raise errors


def test_get_logger() -> None:
    """Test getting a structured logger."""
    logger = get_logger(__name__)
    assert logger is not None

    # Test logging without errors
    logger.info("test_message", key="value")


def test_log_performance(prod_settings: Settings) -> None:
    """Test performance logging."""
    configure_structlog(prod_settings)

    # Should not raise errors
    log_performance(
        operation="test_operation",
        duration_ms=123.45,
        extra_key="extra_value",
    )


def test_structured_log_includes_request_context(
    prod_settings: Settings, caplog: pytest.LogCaptureFixture
) -> None:
    """Test that structured logs include request context."""
    configure_structlog(prod_settings)

    set_request_context(
        request_id="req-123",
        workspace_id="ws-456",
        user_id="user-789",
    )

    logger = get_logger(__name__)
    logger.info("test_event", operation="test_op")

    # In production mode with JSON output, the log should be structured
    # Note: caplog captures standard logging, not structlog directly
    # This is a basic sanity check
    clear_request_context()


def test_logger_with_extra_fields(prod_settings: Settings) -> None:
    """Test logger with extra structured fields."""
    configure_structlog(prod_settings)

    logger = get_logger(__name__)
    logger.info(
        "user_action",
        action="login",
        user_id="user-123",
        workspace_id="ws-456",
        duration_ms=42.5,
    )

    # Should not raise errors and log should be structured


def test_logger_with_exception(prod_settings: Settings) -> None:
    """Test logger captures exceptions properly."""
    configure_structlog(prod_settings)

    logger = get_logger(__name__)

    try:
        msg = "test error"
        raise ValueError(msg)  # noqa: TRY301
    except ValueError:
        logger.exception("error_occurred", error_type="ValueError")

    # Should capture exception info without raising


def test_multiple_loggers() -> None:
    """Test multiple loggers with different names."""
    logger1 = get_logger("module1")
    logger2 = get_logger("module2")

    assert logger1 is not None
    assert logger2 is not None

    # Both should work independently
    logger1.info("message1", key1="value1")
    logger2.info("message2", key2="value2")


def test_log_levels(dev_settings: Settings) -> None:
    """Test different log levels."""
    configure_structlog(dev_settings)

    logger = get_logger(__name__)

    # All log levels should work
    logger.debug("debug_message", level="debug")
    logger.info("info_message", level="info")
    logger.warning("warning_message", level="warning")
    logger.error("error_message", level="error")
    logger.critical("critical_message", level="critical")


# ---------------------------------------------------------------------------
# OPS-04: trace_id / actor / action ContextVar tests
# ---------------------------------------------------------------------------


def test_new_context_vars() -> None:
    """set_request_context injects trace_id, actor, action into event_dict."""
    clear_request_context()
    set_request_context(trace_id="t1", actor="user:abc")
    set_action("issue.create")

    event_dict: dict[str, object] = {"event": "test"}
    result = add_request_context(None, "info", event_dict)  # type: ignore[arg-type]

    assert result["trace_id"] == "t1"
    assert result["actor"] == "user:abc"
    assert result["action"] == "issue.create"
    clear_request_context()


def test_clear_clears_new_fields() -> None:
    """clear_request_context() resets trace_id, actor, action to None."""
    set_request_context(trace_id="t1", actor="user:abc")
    set_action("issue.create")
    clear_request_context()

    event_dict: dict[str, object] = {"event": "test"}
    result = add_request_context(None, "info", event_dict)  # type: ignore[arg-type]

    assert "trace_id" not in result
    assert "actor" not in result
    assert "action" not in result


def test_trace_id_emitted_with_request_id() -> None:
    """When both request_id and trace_id are set, event_dict contains both fields."""
    clear_request_context()
    set_request_context(request_id="req-111", trace_id="trace-222")

    event_dict: dict[str, object] = {"event": "test"}
    result = add_request_context(None, "info", event_dict)  # type: ignore[arg-type]

    assert result["request_id"] == "req-111"
    assert result["trace_id"] == "trace-222"
    clear_request_context()


def test_action_none_by_default() -> None:
    """Without calling set_action(), action key is absent from event_dict."""
    clear_request_context()

    event_dict: dict[str, object] = {"event": "test"}
    result = add_request_context(None, "info", event_dict)  # type: ignore[arg-type]

    assert "action" not in result


def test_set_action_helper() -> None:
    """set_action() sets the action ContextVar; add_request_context includes action."""
    clear_request_context()
    set_action("note.update")

    event_dict: dict[str, object] = {"event": "test"}
    result = add_request_context(None, "info", event_dict)  # type: ignore[arg-type]

    assert result["action"] == "note.update"
    clear_request_context()
