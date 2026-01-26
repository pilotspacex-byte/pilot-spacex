"""Resilient execution with retry logic and circuit breaker integration.

Provides retry mechanisms with exponential backoff and jitter for AI provider calls.
Integrates with CircuitBreaker for comprehensive resilience patterns.

T016: ResilientExecutor with retry and circuit breaker.
"""

from __future__ import annotations

import asyncio
import logging
import random
from dataclasses import dataclass
from functools import wraps
from typing import TYPE_CHECKING, Any, TypeVar

from pilot_space.ai.circuit_breaker import CircuitBreaker, CircuitBreakerConfig
from pilot_space.ai.exceptions import AITimeoutError, RateLimitError

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Awaitable, Callable

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass(frozen=True, slots=True, kw_only=True)
class RetryConfig:
    """Configuration for retry behavior with exponential backoff.

    Attributes:
        max_retries: Maximum number of retry attempts (0 = no retries).
        base_delay_seconds: Initial delay between retries.
        max_delay_seconds: Maximum delay between retries (caps exponential growth).
        jitter: Whether to add randomization to delays (0.0-1.0 multiplier).
        retry_on_timeout: Whether to retry on timeout errors.
        retry_on_rate_limit: Whether to retry on rate limit errors.
    """

    max_retries: int = 3
    base_delay_seconds: float = 1.0
    max_delay_seconds: float = 60.0
    jitter: float = 0.3
    retry_on_timeout: bool = True
    retry_on_rate_limit: bool = True

    def __post_init__(self) -> None:
        """Validate retry configuration."""
        if self.max_retries < 0:
            raise ValueError("max_retries must be >= 0")
        if self.base_delay_seconds < 0:
            raise ValueError("base_delay_seconds must be >= 0")
        if self.max_delay_seconds < self.base_delay_seconds:
            raise ValueError("max_delay_seconds must be >= base_delay_seconds")
        if not 0 <= self.jitter <= 1:
            raise ValueError("jitter must be between 0.0 and 1.0")


class ResilientExecutor:
    """Executes operations with retry logic and circuit breaker protection.

    Combines retry patterns (exponential backoff with jitter) and circuit breakers
    to provide comprehensive resilience for AI provider calls.

    Usage:
        executor = ResilientExecutor()
        result = await executor.execute(
            provider="anthropic",
            operation=lambda: call_api(),
            timeout_sec=30.0,
            retry_config=RetryConfig(max_retries=3),
        )
    """

    def __init__(
        self,
        circuit_config: CircuitBreakerConfig | None = None,
    ) -> None:
        """Initialize resilient executor.

        Args:
            circuit_config: Default circuit breaker configuration for all providers.
        """
        self._circuit_config = circuit_config or CircuitBreakerConfig()
        self._circuit_breakers: dict[str, CircuitBreaker] = {}

    def _get_circuit_breaker(self, provider: str) -> CircuitBreaker:
        """Get or create circuit breaker for provider.

        Args:
            provider: Provider name for circuit breaker isolation.

        Returns:
            CircuitBreaker instance.
        """
        if provider not in self._circuit_breakers:
            self._circuit_breakers[provider] = CircuitBreaker.get_or_create(
                name=provider,
                config=self._circuit_config,
            )
        return self._circuit_breakers[provider]

    def _calculate_delay(
        self,
        attempt: int,
        config: RetryConfig,
    ) -> float:
        """Calculate retry delay with exponential backoff and jitter.

        Args:
            attempt: Current attempt number (1-based).
            config: Retry configuration.

        Returns:
            Delay in seconds.
        """
        # Exponential backoff: base * 2^(attempt-1)
        delay = config.base_delay_seconds * (2 ** (attempt - 1))
        delay = min(delay, config.max_delay_seconds)

        # Add jitter to prevent thundering herd
        if config.jitter > 0:
            jitter_range = delay * config.jitter
            jitter_value = random.uniform(-jitter_range, jitter_range)
            delay = max(0, delay + jitter_value)

        return delay

    def _should_retry(
        self,
        error: Exception,
        attempt: int,
        config: RetryConfig,
    ) -> bool:
        """Determine if operation should be retried.

        Args:
            error: The exception that occurred.
            attempt: Current attempt number (1-based).
            config: Retry configuration.

        Returns:
            True if should retry, False otherwise.
        """
        if attempt > config.max_retries:
            return False

        # Retry on timeout if configured
        if isinstance(error, (AITimeoutError, asyncio.TimeoutError)):
            return config.retry_on_timeout

        # Retry on rate limit if configured
        if isinstance(error, RateLimitError):
            return config.retry_on_rate_limit

        # Retry on transient errors (connection, temporary failures)
        return isinstance(error, (ConnectionError, OSError))

    async def execute_once(
        self,
        provider: str,
        operation: Callable[[], Awaitable[T]],
        timeout_sec: float | None = None,
    ) -> T:
        """Execute operation once with timeout and circuit breaker.

        Args:
            provider: Provider name for circuit breaker isolation.
            operation: Async callable to execute.
            timeout_sec: Optional timeout in seconds.

        Returns:
            Result from the operation.

        Raises:
            AITimeoutError: If operation exceeds timeout.
            ProviderUnavailableError: If circuit breaker is open.
            Any exception from the operation.
        """
        breaker = self._get_circuit_breaker(provider)

        async def _execute_with_timeout() -> T:
            if timeout_sec is None:
                return await operation()

            try:
                async with asyncio.timeout(timeout_sec):
                    return await operation()
            except TimeoutError as e:
                raise AITimeoutError(
                    timeout_seconds=timeout_sec,
                    provider=provider,
                ) from e

        return await breaker.execute(_execute_with_timeout)

    async def execute(
        self,
        provider: str,
        operation: Callable[[], Awaitable[T]],
        timeout_sec: float | None = None,
        retry_config: RetryConfig | None = None,
    ) -> T:
        """Execute operation with retry logic, timeout, and circuit breaker.

        Args:
            provider: Provider name for circuit breaker isolation.
            operation: Async callable to execute.
            timeout_sec: Optional timeout in seconds for each attempt.
            retry_config: Retry configuration (defaults to RetryConfig()).

        Returns:
            Result from the operation.

        Raises:
            AITimeoutError: If operation exceeds timeout.
            ProviderUnavailableError: If circuit breaker is open.
            Any exception from the operation after all retries exhausted.
        """
        config = retry_config or RetryConfig()
        attempt = 0
        last_error: Exception | None = None

        while attempt <= config.max_retries:
            attempt += 1

            try:
                logger.debug(
                    "Executing operation",
                    extra={
                        "provider": provider,
                        "attempt": attempt,
                        "max_retries": config.max_retries,
                        "timeout_sec": timeout_sec,
                    },
                )

                result = await self.execute_once(
                    provider=provider,
                    operation=operation,
                    timeout_sec=timeout_sec,
                )

                if attempt > 1:
                    logger.info(
                        "Operation succeeded after retry",
                        extra={
                            "provider": provider,
                            "attempt": attempt,
                            "previous_errors": attempt - 1,
                        },
                    )

                return result

            except Exception as e:
                last_error = e

                if not self._should_retry(e, attempt, config):
                    logger.debug(
                        "Not retrying operation",
                        extra={
                            "provider": provider,
                            "attempt": attempt,
                            "error_type": type(e).__name__,
                            "error": str(e),
                        },
                    )
                    raise

                if attempt > config.max_retries:
                    logger.warning(
                        "Operation failed after all retries",
                        extra={
                            "provider": provider,
                            "total_attempts": attempt,
                            "max_retries": config.max_retries,
                            "error_type": type(e).__name__,
                            "error": str(e),
                        },
                    )
                    raise

                delay = self._calculate_delay(attempt, config)
                logger.info(
                    "Retrying operation after delay",
                    extra={
                        "provider": provider,
                        "attempt": attempt,
                        "max_retries": config.max_retries,
                        "delay_seconds": delay,
                        "error_type": type(e).__name__,
                    },
                )

                await asyncio.sleep(delay)

        # Should never reach here, but for type safety
        if last_error:
            raise last_error
        raise RuntimeError("Unexpected state: no result and no error")

    async def execute_streaming(
        self,
        provider: str,
        operation: Callable[[], AsyncGenerator[T, None]],
        timeout_sec: float | None = None,
        retry_config: RetryConfig | None = None,
    ) -> AsyncGenerator[T, None]:
        """Execute streaming operation with retry logic and circuit breaker.

        For streaming operations, retries apply to the initial connection.
        Once streaming starts, errors during streaming are propagated immediately.

        Args:
            provider: Provider name for circuit breaker isolation.
            operation: Async generator to execute.
            timeout_sec: Optional timeout in seconds for initial connection.
            retry_config: Retry configuration for initial connection.

        Yields:
            Items from the operation stream.

        Raises:
            AITimeoutError: If initial connection exceeds timeout.
            ProviderUnavailableError: If circuit breaker is open.
            Any exception from the operation.
        """
        config = retry_config or RetryConfig()
        attempt = 0
        last_error: Exception | None = None
        breaker = self._get_circuit_breaker(provider)

        while attempt <= config.max_retries:
            attempt += 1

            try:
                logger.debug(
                    "Starting streaming operation",
                    extra={
                        "provider": provider,
                        "attempt": attempt,
                        "max_retries": config.max_retries,
                        "timeout_sec": timeout_sec,
                    },
                )

                # Create stream starter that can be wrapped by circuit breaker
                stream_iterator: AsyncGenerator[T, None] | None = None

                async def _create_stream() -> bool:
                    """Create the stream and return success flag.

                    This is a workaround since circuit breaker.execute()
                    doesn't support async generators directly.
                    """
                    nonlocal stream_iterator
                    if timeout_sec is None:
                        stream_iterator = operation()
                    else:

                        async def _timed_operation() -> AsyncGenerator[T, None]:
                            try:
                                async with asyncio.timeout(timeout_sec):
                                    async for item in operation():
                                        yield item
                            except TimeoutError as e:
                                raise AITimeoutError(
                                    timeout_seconds=timeout_sec,
                                    provider=provider,
                                ) from e

                        stream_iterator = _timed_operation()
                    return True

                # Use circuit breaker to check state and create stream
                await breaker.execute(_create_stream)

                # Stream is created, now yield items
                if stream_iterator is None:
                    raise RuntimeError("Stream iterator not created")  # noqa: TRY301

                stream_started = False
                try:
                    async for item in stream_iterator:
                        if not stream_started:
                            stream_started = True
                            if attempt > 1:
                                logger.info(
                                    "Streaming operation started after retry",
                                    extra={
                                        "provider": provider,
                                        "attempt": attempt,
                                    },
                                )
                        yield item
                finally:
                    # Close the generator if needed
                    if stream_iterator is not None:
                        await stream_iterator.aclose()

                return

            except Exception as e:
                last_error = e

                if not self._should_retry(e, attempt, config):
                    logger.debug(
                        "Not retrying streaming operation",
                        extra={
                            "provider": provider,
                            "attempt": attempt,
                            "error_type": type(e).__name__,
                        },
                    )
                    raise

                if attempt > config.max_retries:
                    logger.warning(
                        "Streaming operation failed after all retries",
                        extra={
                            "provider": provider,
                            "total_attempts": attempt,
                            "error_type": type(e).__name__,
                        },
                    )
                    raise

                delay = self._calculate_delay(attempt, config)
                logger.info(
                    "Retrying streaming operation after delay",
                    extra={
                        "provider": provider,
                        "attempt": attempt,
                        "delay_seconds": delay,
                        "error_type": type(e).__name__,
                    },
                )

                await asyncio.sleep(delay)

        # Should never reach here, but for type safety
        if last_error:
            raise last_error
        raise RuntimeError("Unexpected state: no result and no error")

    def get_metrics(self) -> dict[str, Any]:
        """Get metrics for all circuit breakers.

        Returns:
            Dictionary mapping provider names to circuit breaker metrics.
        """
        return {
            provider: breaker.get_metrics() for provider, breaker in self._circuit_breakers.items()
        }


def with_resilience(
    provider: str,
    timeout_sec: float | None = None,
    retry_config: RetryConfig | None = None,
    circuit_config: CircuitBreakerConfig | None = None,
) -> Callable[[Callable[[], Awaitable[T]]], Callable[[], Awaitable[T]]]:
    """Decorator to wrap async function with resilient execution.

    Args:
        provider: Provider name for circuit breaker isolation.
        timeout_sec: Optional timeout in seconds for each attempt.
        retry_config: Retry configuration.
        circuit_config: Circuit breaker configuration.

    Returns:
        Decorator function.

    Usage:
        @with_resilience(
            provider="anthropic",
            timeout_sec=30.0,
            retry_config=RetryConfig(max_retries=3),
        )
        async def call_claude(prompt: str) -> str:
            ...
    """
    executor = ResilientExecutor(circuit_config=circuit_config)

    def decorator(
        func: Callable[[], Awaitable[T]],
    ) -> Callable[[], Awaitable[T]]:
        @wraps(func)
        async def wrapper() -> T:
            return await executor.execute(
                provider=provider,
                operation=func,
                timeout_sec=timeout_sec,
                retry_config=retry_config,
            )

        return wrapper

    return decorator


__all__ = [
    "ResilientExecutor",
    "RetryConfig",
    "with_resilience",
]
