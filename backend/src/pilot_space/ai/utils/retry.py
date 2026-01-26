"""Retry utilities with exponential backoff for AI operations.

Provides decorators and utilities for handling transient failures
with intelligent retry strategies.

T091c: Retry decorator for AI operations.
"""

from __future__ import annotations

import asyncio
import logging
import random
from dataclasses import dataclass
from functools import wraps
from typing import TYPE_CHECKING, Any, Self, TypeVar

from pilot_space.ai.exceptions import (
    AITimeoutError,
    ProviderUnavailableError,
    RateLimitError,
)

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

logger = logging.getLogger(__name__)

T = TypeVar("T")

# Transient errors that should trigger retries
TRANSIENT_ERRORS = (
    RateLimitError,
    ProviderUnavailableError,
    AITimeoutError,
    asyncio.TimeoutError,
    ConnectionError,
    TimeoutError,
)


@dataclass
class RetryConfig:
    """Configuration for retry behavior.

    Attributes:
        max_retries: Maximum number of retry attempts.
        initial_delay_seconds: Initial delay before first retry.
        max_delay_seconds: Maximum delay between retries.
        exponential_base: Base for exponential backoff calculation.
        jitter: Whether to add random jitter to delays.
        jitter_factor: Maximum jitter as fraction of delay (0.0-1.0).
    """

    max_retries: int = 3
    initial_delay_seconds: float = 1.0
    max_delay_seconds: float = 30.0
    exponential_base: float = 2.0
    jitter: bool = True
    jitter_factor: float = 0.1


def calculate_delay(
    attempt: int,
    config: RetryConfig,
) -> float:
    """Calculate delay for retry attempt with exponential backoff.

    Args:
        attempt: Current attempt number (0-indexed).
        config: Retry configuration.

    Returns:
        Delay in seconds before next retry.
    """
    # Exponential backoff: initial * base^attempt
    delay = config.initial_delay_seconds * (config.exponential_base**attempt)

    # Cap at maximum delay
    delay = min(delay, config.max_delay_seconds)

    # Add jitter if enabled
    if config.jitter:
        jitter_range = delay * config.jitter_factor
        delay += random.uniform(-jitter_range, jitter_range)
        delay = max(0.1, delay)  # Ensure positive delay

    return delay


def is_transient_error(error: Exception) -> bool:
    """Check if an error is transient and should trigger retry.

    Args:
        error: The exception to check.

    Returns:
        True if error is transient and retriable.
    """
    # Check against known transient error types
    if isinstance(error, TRANSIENT_ERRORS):
        return True

    # Check for specific HTTP errors from providers
    error_str = str(error).lower()
    transient_indicators = [
        "rate limit",
        "too many requests",
        "service unavailable",
        "temporarily unavailable",
        "timeout",
        "connection reset",
        "connection refused",
        "504",
        "503",
        "502",
        "429",
    ]

    return any(indicator in error_str for indicator in transient_indicators)


async def retry_async(  # noqa: UP047 - keeping TypeVar for Python 3.11 compat
    func: Callable[..., Awaitable[T]],
    *args: Any,
    config: RetryConfig | None = None,
    on_retry: Callable[[int, Exception, float], None] | None = None,
    **kwargs: Any,
) -> T:
    """Execute async function with retries.

    Args:
        func: Async function to execute.
        *args: Positional arguments for func.
        config: Retry configuration.
        on_retry: Callback invoked on each retry (attempt, error, delay).
        **kwargs: Keyword arguments for func.

    Returns:
        Result from successful function execution.

    Raises:
        Exception: The last exception if all retries fail.
    """
    config = config or RetryConfig()
    last_error: Exception | None = None

    for attempt in range(config.max_retries + 1):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            last_error = e

            # Check if this is the last attempt
            if attempt >= config.max_retries:
                logger.exception(
                    "All retry attempts exhausted",
                    extra={
                        "function": func.__name__,
                        "attempts": attempt + 1,
                        "error": str(e),
                    },
                )
                raise

            # Check if error is transient
            if not is_transient_error(e):
                logger.warning(
                    "Non-transient error, not retrying",
                    extra={
                        "function": func.__name__,
                        "error_type": type(e).__name__,
                        "error": str(e),
                    },
                )
                raise

            # Calculate delay for this attempt
            delay = calculate_delay(attempt, config)

            # Special handling for rate limit errors with explicit retry-after
            if isinstance(e, RateLimitError) and e.retry_after_seconds > 0:
                delay = max(delay, float(e.retry_after_seconds))

            logger.warning(
                "Transient error, retrying",
                extra={
                    "function": func.__name__,
                    "attempt": attempt + 1,
                    "max_retries": config.max_retries,
                    "delay_seconds": delay,
                    "error_type": type(e).__name__,
                    "error": str(e),
                },
            )

            # Invoke callback if provided
            if on_retry:
                on_retry(attempt, e, delay)

            # Wait before retry
            await asyncio.sleep(delay)

    # Should not reach here, but satisfy type checker
    if last_error:
        raise last_error
    raise RuntimeError("Retry loop exited without result or error")


def with_retry(
    config: RetryConfig | None = None,
    on_retry: Callable[[int, Exception, float], None] | None = None,
) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    """Decorator to add retry logic to async functions.

    Args:
        config: Retry configuration.
        on_retry: Callback invoked on each retry.

    Returns:
        Decorator function.

    Usage:
        @with_retry(RetryConfig(max_retries=3))
        async def call_ai_provider(prompt: str) -> str:
            ...
    """
    config = config or RetryConfig()

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            return await retry_async(
                func,
                *args,
                config=config,
                on_retry=on_retry,
                **kwargs,
            )

        return wrapper

    return decorator


class RetryContext:
    """Context manager for tracking retry state.

    Useful for more complex retry scenarios where state
    needs to be shared across retries.

    Usage:
        async with RetryContext(config) as ctx:
            while ctx.should_retry:
                try:
                    result = await operation()
                    break
                except TransientError as e:
                    await ctx.handle_error(e)
    """

    def __init__(self, config: RetryConfig | None = None) -> None:
        """Initialize retry context.

        Args:
            config: Retry configuration.
        """
        self.config = config or RetryConfig()
        self.attempt = 0
        self.last_error: Exception | None = None
        self._exhausted = False

    @property
    def should_retry(self) -> bool:
        """Check if more retries are available."""
        return not self._exhausted and self.attempt <= self.config.max_retries

    @property
    def is_first_attempt(self) -> bool:
        """Check if this is the first attempt."""
        return self.attempt == 0

    async def handle_error(self, error: Exception) -> None:
        """Handle an error and prepare for retry if applicable.

        Args:
            error: The exception that occurred.

        Raises:
            Exception: If error is not transient or retries exhausted.
        """
        self.last_error = error

        # Check if we should retry
        if self.attempt >= self.config.max_retries:
            self._exhausted = True
            raise error

        if not is_transient_error(error):
            self._exhausted = True
            raise error

        # Calculate and apply delay
        delay = calculate_delay(self.attempt, self.config)

        if isinstance(error, RateLimitError) and error.retry_after_seconds > 0:
            delay = max(delay, float(error.retry_after_seconds))

        logger.warning(
            "Retry context handling transient error",
            extra={
                "attempt": self.attempt + 1,
                "max_retries": self.config.max_retries,
                "delay_seconds": delay,
                "error": str(error),
            },
        )

        await asyncio.sleep(delay)
        self.attempt += 1

    async def __aenter__(self) -> Self:
        """Enter retry context."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> bool:
        """Exit retry context."""
        # Don't suppress exceptions
        return False


__all__ = [
    "RetryConfig",
    "RetryContext",
    "calculate_delay",
    "is_transient_error",
    "retry_async",
    "with_retry",
]
