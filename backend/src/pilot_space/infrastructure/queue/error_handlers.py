"""Queue error handling utilities with retry and dead letter support.

Provides:
- Exponential backoff retry decorator
- Dead letter queue routing
- Edge function timeout handling
- Circuit breaker pattern for queue operations
"""

from __future__ import annotations

import asyncio
import functools
import logging
import random
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any, ParamSpec, TypeVar

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

logger = logging.getLogger(__name__)

P = ParamSpec("P")
R = TypeVar("R")

# Default configuration
DEFAULT_MAX_RETRIES = 3
DEFAULT_BASE_DELAY = 1.0  # seconds
DEFAULT_MAX_DELAY = 30.0  # seconds
DEFAULT_EDGE_FUNCTION_TIMEOUT = 30  # seconds


class RetryStrategy(StrEnum):
    """Retry backoff strategies."""

    EXPONENTIAL = "exponential"  # 2^n * base_delay
    LINEAR = "linear"  # n * base_delay
    CONSTANT = "constant"  # base_delay (no increase)


@dataclass
class RetryConfig:
    """Configuration for retry behavior.

    Attributes:
        max_retries: Maximum number of retry attempts.
        base_delay: Initial delay in seconds.
        max_delay: Maximum delay cap in seconds.
        strategy: Backoff strategy (exponential, linear, constant).
        jitter: Add random jitter to prevent thundering herd.
        retryable_exceptions: Exception types that trigger retry.
        non_retryable_exceptions: Exception types that never retry.
    """

    max_retries: int = DEFAULT_MAX_RETRIES
    base_delay: float = DEFAULT_BASE_DELAY
    max_delay: float = DEFAULT_MAX_DELAY
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL
    jitter: bool = True
    retryable_exceptions: tuple[type[Exception], ...] = (Exception,)
    non_retryable_exceptions: tuple[type[Exception], ...] = ()


@dataclass
class RetryState:
    """Tracks retry state for a single operation.

    Attributes:
        attempt: Current attempt number (1-indexed).
        total_attempts: Total attempts including initial.
        last_exception: Most recent exception.
        start_time: When retries started.
        delays: List of actual delays used.
    """

    attempt: int = 0
    total_attempts: int = 0
    last_exception: Exception | None = None
    start_time: datetime = field(default_factory=lambda: datetime.now(tz=UTC))
    delays: list[float] = field(default_factory=lambda: [])  # noqa: PIE807

    @property
    def elapsed_seconds(self) -> float:
        """Total time elapsed since first attempt."""
        return (datetime.now(tz=UTC) - self.start_time).total_seconds()

    @property
    def total_delay_seconds(self) -> float:
        """Total time spent waiting between retries."""
        return sum(self.delays)


def calculate_delay(
    attempt: int,
    config: RetryConfig,
) -> float:
    """Calculate delay for a given attempt number.

    Args:
        attempt: Current attempt number (0-indexed for calculation).
        config: Retry configuration.

    Returns:
        Delay in seconds (with optional jitter).
    """
    if config.strategy == RetryStrategy.EXPONENTIAL:
        delay = config.base_delay * (2**attempt)
    elif config.strategy == RetryStrategy.LINEAR:
        delay = config.base_delay * (attempt + 1)
    else:  # CONSTANT
        delay = config.base_delay

    # Cap at max delay
    delay = min(delay, config.max_delay)

    # Add jitter (0-25% of delay)
    if config.jitter:
        jitter_amount = delay * 0.25 * random.random()
        delay += jitter_amount

    return delay


def is_retryable(
    exception: Exception,
    config: RetryConfig,
) -> bool:
    """Determine if an exception should trigger a retry.

    Args:
        exception: The exception to check.
        config: Retry configuration.

    Returns:
        True if exception is retryable.
    """
    # Never retry these
    if isinstance(exception, config.non_retryable_exceptions):
        return False

    # Check if it's in the retryable list
    return isinstance(exception, config.retryable_exceptions)


def with_retry(
    config: RetryConfig | None = None,
    *,
    max_retries: int = DEFAULT_MAX_RETRIES,
    base_delay: float = DEFAULT_BASE_DELAY,
    max_delay: float = DEFAULT_MAX_DELAY,
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL,
    on_retry: Callable[[int, Exception], None] | None = None,
    on_failure: Callable[[RetryState], None] | None = None,
) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
    """Decorator for async functions with exponential backoff retry.

    Retries the decorated function on exception with configurable backoff.
    Logs retry attempts and final failure.

    Args:
        config: Full retry configuration (overrides individual params).
        max_retries: Maximum retry attempts (default 3).
        base_delay: Initial delay in seconds (default 1s).
        max_delay: Maximum delay cap (default 30s).
        strategy: Backoff strategy (default exponential).
        on_retry: Callback called on each retry (attempt, exception).
        on_failure: Callback called on final failure (state).

    Returns:
        Decorated async function with retry behavior.

    Example:
        @with_retry(max_retries=3, base_delay=1.0)
        async def process_message(msg: QueueMessage) -> None:
            # This will retry up to 3 times with exponential backoff
            await do_work(msg)

        @with_retry(
            config=RetryConfig(
                max_retries=5,
                strategy=RetryStrategy.LINEAR,
                retryable_exceptions=(ConnectionError, TimeoutError),
            )
        )
        async def call_external_api() -> dict:
            return await http_client.get("/api")
    """
    if config is None:
        config = RetryConfig(
            max_retries=max_retries,
            base_delay=base_delay,
            max_delay=max_delay,
            strategy=strategy,
        )

    def decorator(func: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            state = RetryState()

            for attempt in range(config.max_retries + 1):
                state.attempt = attempt + 1
                state.total_attempts = attempt + 1

                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    state.last_exception = e

                    # Check if we should retry
                    if not is_retryable(e, config):
                        logger.warning(
                            "%s failed with non-retryable exception: %s",
                            func.__name__,
                            e,
                        )
                        raise

                    # Check if we have retries left
                    if attempt >= config.max_retries:
                        logger.exception(
                            "%s failed after %d attempts",
                            func.__name__,
                            state.total_attempts,
                        )
                        if on_failure:
                            on_failure(state)
                        raise

                    # Calculate and apply delay
                    delay = calculate_delay(attempt, config)
                    state.delays.append(delay)

                    logger.warning(
                        "%s attempt %d failed: %s. Retrying in %.2fs...",
                        func.__name__,
                        state.attempt,
                        e,
                        delay,
                    )

                    if on_retry:
                        on_retry(state.attempt, e)

                    await asyncio.sleep(delay)

            # Should not reach here, but satisfy type checker
            msg = f"{func.__name__} exhausted retries"
            raise RuntimeError(msg)

        return wrapper

    return decorator


# =============================================================================
# Dead Letter Queue Support
# =============================================================================


@dataclass
class DeadLetterRecord:
    """Record for dead letter queue entry.

    Attributes:
        original_queue: Source queue name.
        original_msg_id: Original message ID.
        payload: Original message payload.
        error: Final error that caused dead-lettering.
        attempts: Number of processing attempts.
        first_attempt: First processing attempt time.
        last_attempt: Last processing attempt time.
        errors: List of all errors encountered.
    """

    original_queue: str
    original_msg_id: str
    payload: dict[str, Any]
    error: str
    attempts: int = 0
    first_attempt: datetime | None = None
    last_attempt: datetime | None = None
    errors: list[str] = field(default_factory=lambda: [])  # noqa: PIE807

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for queue payload."""
        return {
            "original_queue": self.original_queue,
            "original_msg_id": self.original_msg_id,
            "payload": self.payload,
            "error": self.error,
            "attempts": self.attempts,
            "first_attempt": (self.first_attempt.isoformat() if self.first_attempt else None),
            "last_attempt": (self.last_attempt.isoformat() if self.last_attempt else None),
            "errors": self.errors,
        }


def should_dead_letter(
    attempts: int,
    max_attempts: int = DEFAULT_MAX_RETRIES,
) -> bool:
    """Determine if a message should be moved to dead letter queue.

    Args:
        attempts: Current number of attempts.
        max_attempts: Maximum allowed attempts.

    Returns:
        True if message should be dead-lettered.
    """
    return attempts >= max_attempts


# =============================================================================
# Edge Function Timeout Handling
# =============================================================================


class EdgeFunctionTimeoutError(Exception):
    """Edge function execution timed out."""

    def __init__(
        self,
        message: str = "Edge function timeout",
        timeout_seconds: int = DEFAULT_EDGE_FUNCTION_TIMEOUT,
    ) -> None:
        """Initialize timeout error.

        Args:
            message: Error message.
            timeout_seconds: Timeout duration that was exceeded.
        """
        super().__init__(message)
        self.timeout_seconds = timeout_seconds


def with_edge_function_timeout(
    timeout_seconds: int = DEFAULT_EDGE_FUNCTION_TIMEOUT,
    *,
    on_timeout: Callable[[], None] | None = None,
) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
    """Decorator for edge function timeout handling.

    Wraps async function with timeout and converts asyncio.TimeoutError
    to EdgeFunctionTimeoutError for consistent handling.

    Args:
        timeout_seconds: Timeout in seconds (default 30s for Supabase).
        on_timeout: Optional callback when timeout occurs.

    Returns:
        Decorated function with timeout handling.

    Example:
        @with_edge_function_timeout(30)
        async def call_edge_function(payload: dict) -> dict:
            return await supabase.functions.invoke("process", payload)
    """

    def decorator(func: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            try:
                return await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=timeout_seconds,
                )
            except TimeoutError as e:
                logger.exception(
                    "%s timed out after %ds",
                    func.__name__,
                    timeout_seconds,
                )
                if on_timeout:
                    on_timeout()
                raise EdgeFunctionTimeoutError(
                    f"{func.__name__} timed out after {timeout_seconds}s",
                    timeout_seconds,
                ) from e

        return wrapper

    return decorator


# =============================================================================
# Circuit Breaker Pattern
# =============================================================================


class CircuitState(StrEnum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing fast, not allowing calls
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreaker:
    """Simple circuit breaker for queue operations.

    Prevents cascading failures by stopping calls to failing services.

    Attributes:
        name: Circuit breaker identifier.
        failure_threshold: Failures before opening circuit.
        recovery_timeout: Seconds before attempting recovery.
        half_open_max_calls: Max calls in half-open state.
    """

    name: str
    failure_threshold: int = 5
    recovery_timeout: float = 30.0
    half_open_max_calls: int = 3

    _state: CircuitState = field(default=CircuitState.CLOSED, init=False)
    _failure_count: int = field(default=0, init=False)
    _last_failure_time: datetime | None = field(default=None, init=False)
    _half_open_calls: int = field(default=0, init=False)

    @property
    def state(self) -> CircuitState:
        """Get current circuit state (with automatic recovery check)."""
        if self._state == CircuitState.OPEN and self._should_attempt_recovery():
            self._state = CircuitState.HALF_OPEN
            self._half_open_calls = 0
            logger.info("Circuit %s transitioning to HALF_OPEN", self.name)
        return self._state

    def _should_attempt_recovery(self) -> bool:
        """Check if enough time has passed to attempt recovery."""
        if self._last_failure_time is None:
            return True
        elapsed = (datetime.now(tz=UTC) - self._last_failure_time).total_seconds()
        return elapsed >= self.recovery_timeout

    def record_success(self) -> None:
        """Record a successful call."""
        if self._state == CircuitState.HALF_OPEN:
            self._half_open_calls += 1
            if self._half_open_calls >= self.half_open_max_calls:
                self._state = CircuitState.CLOSED
                self._failure_count = 0
                logger.info("Circuit %s closed after recovery", self.name)
        elif self._state == CircuitState.CLOSED:
            self._failure_count = 0

    def record_failure(self, exception: Exception | None = None) -> None:
        """Record a failed call."""
        self._failure_count += 1
        self._last_failure_time = datetime.now(tz=UTC)

        if self._state == CircuitState.HALF_OPEN:
            self._state = CircuitState.OPEN
            logger.warning(
                "Circuit %s re-opened after failure in half-open: %s",
                self.name,
                exception,
            )
        elif self._state == CircuitState.CLOSED and self._failure_count >= self.failure_threshold:
            self._state = CircuitState.OPEN
            logger.warning(
                "Circuit %s opened after %d failures: %s",
                self.name,
                self._failure_count,
                exception,
            )

    def is_call_allowed(self) -> bool:
        """Check if a call is allowed through the circuit."""
        state = self.state  # Triggers recovery check
        if state == CircuitState.CLOSED:
            return True
        if state == CircuitState.HALF_OPEN:
            return self._half_open_calls < self.half_open_max_calls
        return False  # OPEN

    def reset(self) -> None:
        """Manually reset circuit to closed state."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time = None
        self._half_open_calls = 0
        logger.info("Circuit %s manually reset", self.name)


class CircuitOpenError(Exception):
    """Circuit breaker is open, call not allowed."""

    def __init__(self, circuit_name: str) -> None:
        """Initialize circuit open error.

        Args:
            circuit_name: Name of the open circuit.
        """
        super().__init__(f"Circuit breaker '{circuit_name}' is open")
        self.circuit_name = circuit_name


def with_circuit_breaker(
    circuit: CircuitBreaker,
) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
    """Decorator to wrap async function with circuit breaker protection.

    Args:
        circuit: CircuitBreaker instance to use.

    Returns:
        Decorated function with circuit breaker.

    Example:
        queue_circuit = CircuitBreaker("queue_operations", failure_threshold=5)

        @with_circuit_breaker(queue_circuit)
        async def enqueue_message(msg: dict) -> str:
            return await queue_client.enqueue("tasks", msg)
    """

    def decorator(func: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            if not circuit.is_call_allowed():
                raise CircuitOpenError(circuit.name)

            try:
                result = await func(*args, **kwargs)
            except Exception as e:
                circuit.record_failure(e)
                raise
            else:
                circuit.record_success()
                return result

        return wrapper

    return decorator
