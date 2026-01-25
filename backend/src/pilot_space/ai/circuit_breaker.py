"""Circuit breaker pattern for AI provider resilience.

Implements the Circuit Breaker pattern to prevent cascading failures:
- CLOSED: Normal operation, requests pass through
- OPEN: Failures exceeded threshold, requests fail fast
- HALF_OPEN: Testing if service has recovered

T091b: Circuit breaker pattern for AI providers.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, ClassVar, TypeVar

from pilot_space.ai.exceptions import ProviderUnavailableError

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CircuitState(Enum):
    """Circuit breaker state."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing fast
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior.

    Attributes:
        failure_threshold: Number of consecutive failures to open circuit.
        success_threshold: Number of successes in half-open to close circuit.
        timeout_seconds: Time to wait before transitioning from open to half-open.
        half_open_max_calls: Maximum concurrent calls in half-open state.
    """

    failure_threshold: int = 3
    success_threshold: int = 1
    timeout_seconds: float = 30.0
    half_open_max_calls: int = 1


@dataclass
class CircuitBreakerState:
    """Internal state tracking for circuit breaker.

    Attributes:
        state: Current circuit state.
        failure_count: Consecutive failure counter.
        success_count: Success counter in half-open state.
        last_failure_time: Timestamp of last failure.
        half_open_calls: Current calls in half-open state.
    """

    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: float | None = None
    half_open_calls: int = 0
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


class CircuitBreaker:
    """Circuit breaker for protecting AI provider calls.

    Prevents cascading failures by failing fast when a provider
    is experiencing issues.

    Usage:
        breaker = CircuitBreaker("anthropic")
        result = await breaker.execute(provider.generate, prompt)
    """

    # Class-level registry of circuit breakers per provider
    _instances: ClassVar[dict[str, CircuitBreaker]] = {}

    def __init__(
        self,
        name: str,
        config: CircuitBreakerConfig | None = None,
    ) -> None:
        """Initialize circuit breaker.

        Args:
            name: Identifier for this circuit breaker (usually provider name).
            config: Circuit breaker configuration.
        """
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self._state = CircuitBreakerState()

    @classmethod
    def get_or_create(
        cls,
        name: str,
        config: CircuitBreakerConfig | None = None,
    ) -> CircuitBreaker:
        """Get existing circuit breaker or create new one.

        Args:
            name: Circuit breaker identifier.
            config: Configuration for new breaker.

        Returns:
            CircuitBreaker instance.
        """
        if name not in cls._instances:
            cls._instances[name] = cls(name, config)
        return cls._instances[name]

    @classmethod
    def reset_all(cls) -> None:
        """Reset all circuit breakers. Used for testing."""
        for breaker in cls._instances.values():
            breaker.reset()

    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        return self._state.state

    @property
    def is_open(self) -> bool:
        """Check if circuit is open (failing fast)."""
        return self._state.state == CircuitState.OPEN

    @property
    def is_closed(self) -> bool:
        """Check if circuit is closed (normal operation)."""
        return self._state.state == CircuitState.CLOSED

    def reset(self) -> None:
        """Reset circuit breaker to closed state."""
        self._state = CircuitBreakerState()
        logger.info(
            "Circuit breaker reset",
            extra={"breaker": self.name},
        )

    async def execute(
        self,
        func: Callable[..., Awaitable[T]],
        *args: Any,
        **kwargs: Any,
    ) -> T:
        """Execute a function with circuit breaker protection.

        Args:
            func: Async function to execute.
            *args: Positional arguments for func.
            **kwargs: Keyword arguments for func.

        Returns:
            Result from the function.

        Raises:
            ProviderUnavailableError: If circuit is open.
            Any exception from func if it fails.
        """
        async with self._state.lock:
            await self._check_state_transition()

            if self._state.state == CircuitState.OPEN:
                logger.warning(
                    "Circuit breaker is open, failing fast",
                    extra={
                        "breaker": self.name,
                        "failure_count": self._state.failure_count,
                    },
                )
                raise ProviderUnavailableError(
                    provider=self.name,
                    circuit_open=True,
                )

            if self._state.state == CircuitState.HALF_OPEN:
                if self._state.half_open_calls >= self.config.half_open_max_calls:
                    raise ProviderUnavailableError(
                        provider=self.name,
                        message=f"Circuit breaker '{self.name}' in half-open state, max calls reached",
                        circuit_open=True,
                    )
                self._state.half_open_calls += 1

        try:
            result = await func(*args, **kwargs)
            await self._on_success()
            return result
        except Exception as e:
            await self._on_failure(e)
            raise

    async def _check_state_transition(self) -> None:
        """Check and perform state transitions based on time."""
        if self._state.state != CircuitState.OPEN:
            return

        if self._state.last_failure_time is None:
            return

        elapsed = time.monotonic() - self._state.last_failure_time
        if elapsed >= self.config.timeout_seconds:
            self._state.state = CircuitState.HALF_OPEN
            self._state.half_open_calls = 0
            self._state.success_count = 0
            logger.info(
                "Circuit breaker transitioning to half-open",
                extra={
                    "breaker": self.name,
                    "elapsed_seconds": elapsed,
                },
            )

    async def _on_success(self) -> None:
        """Handle successful call."""
        async with self._state.lock:
            if self._state.state == CircuitState.HALF_OPEN:
                self._state.success_count += 1
                self._state.half_open_calls = max(0, self._state.half_open_calls - 1)

                if self._state.success_count >= self.config.success_threshold:
                    self._state.state = CircuitState.CLOSED
                    self._state.failure_count = 0
                    self._state.success_count = 0
                    logger.info(
                        "Circuit breaker closed after recovery",
                        extra={"breaker": self.name},
                    )
            elif self._state.state == CircuitState.CLOSED:
                # Reset failure count on success
                self._state.failure_count = 0

    async def _on_failure(self, error: Exception) -> None:
        """Handle failed call.

        Args:
            error: The exception that occurred.
        """
        async with self._state.lock:
            self._state.failure_count += 1
            self._state.last_failure_time = time.monotonic()

            if self._state.state == CircuitState.HALF_OPEN:
                # Any failure in half-open immediately opens circuit
                self._state.state = CircuitState.OPEN
                self._state.half_open_calls = 0
                logger.warning(
                    "Circuit breaker re-opened after half-open failure",
                    extra={
                        "breaker": self.name,
                        "error": str(error),
                    },
                )
            elif self._state.state == CircuitState.CLOSED:
                if self._state.failure_count >= self.config.failure_threshold:
                    self._state.state = CircuitState.OPEN
                    logger.warning(
                        "Circuit breaker opened after consecutive failures",
                        extra={
                            "breaker": self.name,
                            "failure_count": self._state.failure_count,
                            "error": str(error),
                        },
                    )

    def get_metrics(self) -> dict[str, Any]:
        """Get current circuit breaker metrics.

        Returns:
            Dictionary with state and counters.
        """
        return {
            "name": self.name,
            "state": self._state.state.value,
            "failure_count": self._state.failure_count,
            "success_count": self._state.success_count,
            "last_failure_time": self._state.last_failure_time,
            "config": {
                "failure_threshold": self.config.failure_threshold,
                "timeout_seconds": self.config.timeout_seconds,
            },
        }


def with_circuit_breaker(
    name: str,
    config: CircuitBreakerConfig | None = None,
) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    """Decorator to wrap async function with circuit breaker.

    Args:
        name: Circuit breaker identifier.
        config: Circuit breaker configuration.

    Returns:
        Decorator function.

    Usage:
        @with_circuit_breaker("anthropic")
        async def call_claude(prompt: str) -> str:
            ...
    """
    breaker = CircuitBreaker.get_or_create(name, config)

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            return await breaker.execute(func, *args, **kwargs)

        return wrapper

    return decorator


__all__ = [
    "CircuitBreaker",
    "CircuitBreakerConfig",
    "CircuitState",
    "with_circuit_breaker",
]
