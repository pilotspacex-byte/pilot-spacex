"""Test circuit breaker behavior with SDK client failures.

T320: Tests circuit breaker state transitions and failure recovery.
"""

from __future__ import annotations

import asyncio

import pytest

from pilot_space.ai.circuit_breaker import CircuitBreaker, CircuitBreakerConfig
from pilot_space.ai.exceptions import ProviderUnavailableError


class TestCircuitBreaker:
    """Test circuit breaker state machine and resilience behavior."""

    @pytest.mark.asyncio
    async def test_opens_after_threshold(self) -> None:
        """Verify circuit opens after consecutive failures exceed threshold."""
        breaker = CircuitBreaker(
            name="test_provider",
            config=CircuitBreakerConfig(failure_threshold=3, timeout_seconds=10),
        )

        # Simulate 3 consecutive failures
        async def failing_operation() -> None:
            raise ConnectionError("Provider unavailable")

        for i in range(3):
            with pytest.raises(ConnectionError):
                await breaker.execute(failing_operation)

            # Circuit should remain closed until threshold
            if i < 2:
                assert not breaker.is_open
            else:
                assert breaker.is_open

        # Next call should fail fast without executing operation
        call_count = 0

        async def counting_operation() -> str:
            nonlocal call_count
            call_count += 1
            return "success"

        with pytest.raises(ProviderUnavailableError) as exc:
            await breaker.execute(counting_operation)

        assert "circuit" in str(exc.value).lower()
        assert call_count == 0  # Operation not executed

    @pytest.mark.asyncio
    async def test_half_open_after_timeout(self) -> None:
        """Verify circuit transitions to half-open after timeout period."""
        breaker = CircuitBreaker(
            name="test_provider_timeout",
            config=CircuitBreakerConfig(failure_threshold=3, timeout_seconds=1),
        )

        # Open the circuit
        async def failing_operation() -> None:
            raise ConnectionError("Provider unavailable")

        for _ in range(3):
            with pytest.raises(ConnectionError):
                await breaker.execute(failing_operation)

        assert breaker.is_open

        # Wait for timeout period
        await asyncio.sleep(1.1)

        # Next call should be allowed (half-open state)
        call_executed = False

        async def test_operation() -> str:
            nonlocal call_executed
            call_executed = True
            return "success"

        result = await breaker.execute(test_operation)
        assert result == "success"
        assert call_executed

    @pytest.mark.asyncio
    async def test_closes_on_success(self) -> None:
        """Verify circuit closes after successful request in half-open state."""
        breaker = CircuitBreaker(
            name="test_provider_recovery",
            config=CircuitBreakerConfig(
                failure_threshold=3,
                timeout_seconds=1,
                success_threshold=1,
            ),
        )

        # Open the circuit
        async def failing_operation() -> None:
            raise ConnectionError("Provider unavailable")

        for _ in range(3):
            with pytest.raises(ConnectionError):
                await breaker.execute(failing_operation)

        assert breaker.is_open

        # Wait for timeout
        await asyncio.sleep(1.1)

        # Successful call should close circuit
        async def successful_operation() -> str:
            return "recovered"

        result = await breaker.execute(successful_operation)
        assert result == "recovered"
        assert breaker.is_closed

        # Subsequent calls should work normally
        result2 = await breaker.execute(successful_operation)
        assert result2 == "recovered"

    @pytest.mark.asyncio
    async def test_reopens_on_half_open_failure(self) -> None:
        """Verify circuit reopens if call fails during half-open state."""
        breaker = CircuitBreaker(
            name="test_provider_reopen",
            config=CircuitBreakerConfig(failure_threshold=3, timeout_seconds=1),
        )

        # Open the circuit
        async def failing_operation() -> None:
            raise ConnectionError("Provider unavailable")

        for _ in range(3):
            with pytest.raises(ConnectionError):
                await breaker.execute(failing_operation)

        # Wait for timeout
        await asyncio.sleep(1.1)

        # Fail during half-open - should reopen immediately
        with pytest.raises(ConnectionError):
            await breaker.execute(failing_operation)

        assert breaker.is_open

        # Should fail fast now
        with pytest.raises(ProviderUnavailableError):
            await breaker.execute(failing_operation)

    @pytest.mark.asyncio
    async def test_resets_failure_count_on_closed_success(self) -> None:
        """Verify failure count resets after success in closed state."""
        breaker = CircuitBreaker(
            name="test_provider_reset",
            config=CircuitBreakerConfig(failure_threshold=3, timeout_seconds=10),
        )

        # Two failures (below threshold)
        async def failing_operation() -> None:
            raise ConnectionError("Provider unavailable")

        for _ in range(2):
            with pytest.raises(ConnectionError):
                await breaker.execute(failing_operation)

        assert breaker.is_closed
        assert breaker._state.failure_count == 2

        # Success should reset counter
        async def successful_operation() -> str:
            return "success"

        await breaker.execute(successful_operation)
        assert breaker._state.failure_count == 0

        # Can handle 3 more failures before opening
        for _ in range(2):
            with pytest.raises(ConnectionError):
                await breaker.execute(failing_operation)

        assert breaker.is_closed

    @pytest.mark.asyncio
    async def test_get_metrics(self) -> None:
        """Verify circuit breaker metrics are tracked correctly."""
        breaker = CircuitBreaker(
            name="test_provider_metrics",
            config=CircuitBreakerConfig(failure_threshold=2, timeout_seconds=5),
        )

        # Initial metrics
        metrics = breaker.get_metrics()
        assert metrics["name"] == "test_provider_metrics"
        assert metrics["state"] == "closed"
        assert metrics["failure_count"] == 0

        # After failures
        async def failing_operation() -> None:
            raise ConnectionError("Provider unavailable")

        for _ in range(2):
            with pytest.raises(ConnectionError):
                await breaker.execute(failing_operation)

        metrics = breaker.get_metrics()
        assert metrics["state"] == "open"
        assert metrics["failure_count"] == 2
        assert metrics["last_failure_time"] is not None
        assert metrics["config"]["failure_threshold"] == 2
        assert metrics["config"]["timeout_seconds"] == 5

    @pytest.mark.asyncio
    async def test_multiple_concurrent_half_open_calls(self) -> None:
        """Verify only limited concurrent calls allowed in half-open state."""
        breaker = CircuitBreaker(
            name="test_provider_concurrent",
            config=CircuitBreakerConfig(
                failure_threshold=2,
                timeout_seconds=1,
                half_open_max_calls=1,
            ),
        )

        # Open circuit
        async def failing_operation() -> None:
            raise ConnectionError("Provider unavailable")

        for _ in range(2):
            with pytest.raises(ConnectionError):
                await breaker.execute(failing_operation)

        # Wait for timeout
        await asyncio.sleep(1.1)

        # First call should be allowed
        call_count = 0

        async def slow_operation() -> str:
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.1)
            return "success"

        # Start first call (won't await it yet)
        task = asyncio.create_task(breaker.execute(slow_operation))

        # Give it time to enter half-open
        await asyncio.sleep(0.01)

        # Second call should be rejected
        with pytest.raises(ProviderUnavailableError):
            await breaker.execute(slow_operation)

        # Complete first call
        result = await task
        assert result == "success"
        assert call_count == 1


@pytest.fixture(autouse=True)
def reset_circuit_breakers() -> None:
    """Reset all circuit breakers before each test."""
    CircuitBreaker.reset_all()
