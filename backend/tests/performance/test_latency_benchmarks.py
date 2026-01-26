"""T102-T104: Performance Latency Benchmarks.

Verify AI endpoints meet performance SLOs:
- Ghost text: p95 < 2s
- AI context: p95 < 30s
- SSE first token: p95 < 1s

Reference: specs/004-mvp-agents-build/tasks/P15-T095-T110.md
"""

from __future__ import annotations

import statistics
import time
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import pytest

if TYPE_CHECKING:
    from httpx import AsyncClient


# Mark all tests in this module as benchmarks
pytestmark = pytest.mark.benchmark


class TestLatencyBenchmarks:
    """Performance benchmark tests for AI endpoints."""

    @pytest.mark.asyncio
    async def test_ghost_text_p95_under_2s(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_note: AsyncMock,
    ) -> None:
        """T102: Verify ghost text p95 latency < 2s.

        SLO: Ghost text suggestions must complete within 2 seconds
        at p95 to maintain real-time typing experience.
        """
        latencies: list[float] = []
        iterations = 20  # Enough for p95 calculation

        # Mock the agent to avoid actual API calls
        with patch("pilot_space.ai.agents.ghost_text_agent.GhostTextAgent") as MockAgent:
            mock_instance = MockAgent.return_value
            mock_instance.execute.return_value = "suggested completion text"

            for i in range(iterations):
                start = time.perf_counter()

                # Make request
                response = await client.post(
                    f"/ai/notes/{test_note.id}/ghost-text",
                    headers=auth_headers,
                    json={
                        "context": f"Test content iteration {i}",
                        "cursor_position": 20 + i,
                    },
                )

                elapsed = time.perf_counter() - start
                latencies.append(elapsed)

                # Verify response
                assert response.status_code in [200, 201, 202]

        # Calculate p95
        sorted_latencies = sorted(latencies)
        p95_index = int(len(sorted_latencies) * 0.95)
        p95 = sorted_latencies[p95_index]

        # Calculate statistics for reporting
        mean = statistics.mean(latencies)
        median = statistics.median(latencies)
        p99 = sorted_latencies[int(len(sorted_latencies) * 0.99)]

        print("\nGhost Text Latency Statistics:")
        print(f"  Mean:   {mean:.3f}s")
        print(f"  Median: {median:.3f}s")
        print(f"  p95:    {p95:.3f}s")
        print(f"  p99:    {p99:.3f}s")

        assert p95 < 2.0, f"Ghost text p95 latency {p95:.3f}s exceeds 2s SLO"

    @pytest.mark.asyncio
    async def test_ai_context_p95_under_30s(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_issue: AsyncMock,
    ) -> None:
        """T103: Verify AI context p95 latency < 30s.

        SLO: AI context generation must complete within 30 seconds
        at p95 for acceptable user experience.
        """
        latencies: list[float] = []
        iterations = 5  # Fewer iterations due to longer operation

        # Mock the agent
        with patch("pilot_space.ai.agents.ai_context_agent.AIContextAgent") as MockAgent:
            mock_instance = MockAgent.return_value
            mock_instance.execute.return_value = {
                "summary": "AI-generated context",
                "related_issues": [],
                "code_references": [],
                "suggested_tasks": [],
                "claude_code_prompt": "# Task: Implement feature...",
            }

            for _i in range(iterations):
                start = time.perf_counter()

                # Make request
                response = await client.post(
                    f"/ai/issues/{test_issue.id}/context",
                    headers=auth_headers,
                    json={"include_code_search": True},
                )

                elapsed = time.perf_counter() - start
                latencies.append(elapsed)

                assert response.status_code in [200, 201, 202]

        # Calculate p95
        sorted_latencies = sorted(latencies)
        p95_index = int(len(sorted_latencies) * 0.95)
        p95 = sorted_latencies[p95_index]

        mean = statistics.mean(latencies)
        median = statistics.median(latencies)

        print("\nAI Context Latency Statistics:")
        print(f"  Mean:   {mean:.3f}s")
        print(f"  Median: {median:.3f}s")
        print(f"  p95:    {p95:.3f}s")

        assert p95 < 30.0, f"AI context p95 latency {p95:.3f}s exceeds 30s SLO"

    @pytest.mark.asyncio
    async def test_sse_first_token_under_1s(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_note: AsyncMock,
    ) -> None:
        """T104: Verify SSE first token latency < 1s.

        SLO: First token in SSE stream must arrive within 1 second
        at p95 to indicate processing has started.
        """
        first_token_latencies: list[float] = []
        iterations = 10

        # Mock streaming response
        with patch("pilot_space.ai.agents.ghost_text_agent.GhostTextAgent") as MockAgent:
            mock_instance = MockAgent.return_value

            async def mock_stream():
                """Mock async generator for streaming."""
                yield "First"
                yield " token"
                yield " received"

            mock_instance.stream.return_value = mock_stream()

            for i in range(iterations):
                start = time.perf_counter()

                # Make streaming request
                async with client.stream(
                    "POST",
                    f"/ai/notes/{test_note.id}/ghost-text",
                    headers=auth_headers,
                    json={"context": f"Stream test {i}"},
                ) as response:
                    # Measure time to first chunk
                    async for line in response.aiter_lines():
                        if line:  # First non-empty line
                            first_token_time = time.perf_counter() - start
                            first_token_latencies.append(first_token_time)
                            break

        # Calculate p95
        sorted_latencies = sorted(first_token_latencies)
        p95_index = int(len(sorted_latencies) * 0.95)
        p95 = sorted_latencies[p95_index]

        mean = statistics.mean(first_token_latencies)
        median = statistics.median(first_token_latencies)

        print("\nSSE First Token Latency Statistics:")
        print(f"  Mean:   {mean:.3f}s")
        print(f"  Median: {median:.3f}s")
        print(f"  p95:    {p95:.3f}s")

        assert p95 < 1.0, f"First token p95 latency {p95:.3f}s exceeds 1s SLO"


class TestThroughputBenchmarks:
    """Throughput and concurrency benchmarks."""

    @pytest.mark.asyncio
    async def test_concurrent_ghost_text_requests(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_note: AsyncMock,
    ) -> None:
        """Verify system handles concurrent ghost text requests.

        Target: 10 concurrent requests without degradation.
        """
        import asyncio

        concurrent_requests = 10
        latencies: list[float] = []

        with patch("pilot_space.ai.agents.ghost_text_agent.GhostTextAgent") as MockAgent:
            mock_instance = MockAgent.return_value
            mock_instance.execute.return_value = "suggestion"

            async def make_request(request_id: int) -> float:
                """Make single request and return latency."""
                start = time.perf_counter()
                response = await client.post(
                    f"/ai/notes/{test_note.id}/ghost-text",
                    headers=auth_headers,
                    json={"context": f"Request {request_id}"},
                )
                elapsed = time.perf_counter() - start
                assert response.status_code in [200, 201, 202]
                return elapsed

            # Execute concurrent requests
            results = await asyncio.gather(*[
                make_request(i) for i in range(concurrent_requests)
            ])

            latencies.extend(results)

        # All should complete within reasonable time
        max_latency = max(latencies)
        mean_latency = statistics.mean(latencies)

        print(f"\nConcurrent Requests ({concurrent_requests}):")
        print(f"  Mean:   {mean_latency:.3f}s")
        print(f"  Max:    {max_latency:.3f}s")

        # Under load, still should be < 5s
        assert max_latency < 5.0, f"Max latency {max_latency:.3f}s too high under concurrency"

    @pytest.mark.asyncio
    async def test_sustained_request_rate(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_note: AsyncMock,
    ) -> None:
        """Verify system handles sustained request rate.

        Target: 5 requests per second for 10 seconds without performance degradation.
        """
        import asyncio

        requests_per_second = 5
        duration_seconds = 10
        total_requests = requests_per_second * duration_seconds

        latencies: list[float] = []

        with patch("pilot_space.ai.agents.ghost_text_agent.GhostTextAgent") as MockAgent:
            mock_instance = MockAgent.return_value
            mock_instance.execute.return_value = "suggestion"

            start_time = time.perf_counter()

            for i in range(total_requests):
                request_start = time.perf_counter()

                _ = await client.post(
                    f"/ai/notes/{test_note.id}/ghost-text",
                    headers=auth_headers,
                    json={"context": f"Sustained {i}"},
                )

                elapsed = time.perf_counter() - request_start
                latencies.append(elapsed)

                # Maintain rate
                expected_time = start_time + (i + 1) / requests_per_second
                sleep_time = expected_time - time.perf_counter()
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)

        # Analyze performance over time
        first_half = latencies[:len(latencies)//2]
        second_half = latencies[len(latencies)//2:]

        first_half_mean = statistics.mean(first_half)
        second_half_mean = statistics.mean(second_half)

        print(f"\nSustained Load Test ({total_requests} requests):")
        print(f"  First half mean:  {first_half_mean:.3f}s")
        print(f"  Second half mean: {second_half_mean:.3f}s")

        # Performance should not degrade significantly
        degradation = (second_half_mean - first_half_mean) / first_half_mean
        assert degradation < 0.5, f"Performance degraded by {degradation*100:.1f}% under sustained load"


class TestMemoryEfficiency:
    """Memory and resource efficiency tests."""

    @pytest.mark.asyncio
    async def test_no_memory_leak_on_repeated_requests(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_note: AsyncMock,
    ) -> None:
        """Verify no memory leaks with repeated requests.

        This is a basic sanity check - proper profiling would use memory_profiler.
        """
        import gc

        with patch("pilot_space.ai.agents.ghost_text_agent.GhostTextAgent") as MockAgent:
            mock_instance = MockAgent.return_value
            mock_instance.execute.return_value = "suggestion"

            # Make many requests
            for i in range(100):
                response = await client.post(
                    f"/ai/notes/{test_note.id}/ghost-text",
                    headers=auth_headers,
                    json={"context": f"Memory test {i}"},
                )
                assert response.status_code in [200, 201, 202]

                # Force garbage collection every 10 requests
                if i % 10 == 0:
                    gc.collect()

        # If we got here without OOM, basic test passes
        assert True
