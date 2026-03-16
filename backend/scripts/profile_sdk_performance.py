"""Profiling script for Claude Agent SDK performance analysis.

Measures CPU, memory, and timing for SDK operations including:
- Subprocess spawn time
- Note sync performance
- MCP tool execution
- Context size tracking
- Resource cleanup

Usage:
    uv run python -m scripts.profile_sdk_performance
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
import tracemalloc
from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid4

import anyio
import psutil

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Performance metrics for SDK operations."""

    operation: str
    duration_ms: float
    memory_delta_mb: float
    cpu_percent: float
    subprocess_count: int
    subprocess_memory_mb: float
    subprocess_cpu_percent: float
    context_size_chars: int | None = None
    metadata: dict[str, Any] | None = None


class SDKProfiler:
    """Profiler for Claude Agent SDK operations."""

    def __init__(self) -> None:
        """Initialize profiler."""
        self.process = psutil.Process()
        self.metrics: list[PerformanceMetrics] = []

    def _get_subprocess_stats(self) -> tuple[int, float, float]:
        """Get subprocess count, memory, and CPU usage.

        Returns:
            Tuple of (count, total_memory_mb, total_cpu_percent)
        """
        try:
            children = self.process.children(recursive=True)
            count = len(children)
            total_memory = sum(c.memory_info().rss for c in children)
            total_cpu = sum(c.cpu_percent() for c in children)
            return count, total_memory / 1024 / 1024, total_cpu
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return 0, 0.0, 0.0

    async def profile_operation(
        self,
        operation_name: str,
        operation_func: Any,
        context_size: int | None = None,
    ) -> PerformanceMetrics:
        """Profile a single async operation.

        Args:
            operation_name: Name of the operation for logging
            operation_func: Async function to profile
            context_size: Optional context size in characters

        Returns:
            PerformanceMetrics with timing and resource usage
        """
        logger.info(f"[Profile] Starting: {operation_name}")

        # Start profiling
        tracemalloc.start()
        mem_before = self.process.memory_info().rss
        cpu_before = self.process.cpu_percent()
        subprocess_before = self._get_subprocess_stats()

        start = time.perf_counter()

        # Execute operation
        try:
            result = await operation_func()
        except Exception as e:
            logger.error(f"[Profile] {operation_name} failed: {e}", exc_info=True)
            raise
        finally:
            # Stop profiling
            duration_ms = (time.perf_counter() - start) * 1000
            mem_after = self.process.memory_info().rss
            cpu_after = self.process.cpu_percent()
            subprocess_after = self._get_subprocess_stats()

            current_mem, peak_mem = tracemalloc.get_traced_memory()
            tracemalloc.stop()

            memory_delta_mb = (mem_after - mem_before) / 1024 / 1024

            metrics = PerformanceMetrics(
                operation=operation_name,
                duration_ms=duration_ms,
                memory_delta_mb=memory_delta_mb,
                cpu_percent=(cpu_after + cpu_before) / 2,
                subprocess_count=subprocess_after[0] - subprocess_before[0],
                subprocess_memory_mb=subprocess_after[1] - subprocess_before[1],
                subprocess_cpu_percent=subprocess_after[2] - subprocess_before[2],
                context_size_chars=context_size,
                metadata={"peak_memory_mb": peak_mem / 1024 / 1024},
            )

            self.metrics.append(metrics)

            logger.info(
                f"[Profile] {operation_name} completed:\n"
                f"  Duration: {duration_ms:.2f}ms\n"
                f"  Memory delta: {memory_delta_mb:+.2f}MB\n"
                f"  CPU: {metrics.cpu_percent:.1f}%\n"
                f"  Subprocess count: {metrics.subprocess_count:+d}\n"
                f"  Subprocess memory: {metrics.subprocess_memory_mb:+.2f}MB\n"
                f"  Subprocess CPU: {metrics.subprocess_cpu_percent:+.1f}%"
            )

        return metrics

    def print_summary(self) -> None:
        """Print summary of all profiled operations."""
        if not self.metrics:
            logger.warning("No metrics collected")
            return

        print("\n" + "=" * 80)
        print("PERFORMANCE PROFILE SUMMARY")
        print("=" * 80)

        total_duration = sum(m.duration_ms for m in self.metrics)
        total_memory = sum(m.memory_delta_mb for m in self.metrics)

        print(f"\nTotal operations: {len(self.metrics)}")
        print(f"Total duration: {total_duration:.2f}ms")
        print(f"Total memory delta: {total_memory:+.2f}MB")

        print("\nPer-operation breakdown:")
        print(f"{'Operation':<30} {'Duration':<12} {'Memory':<12} {'Subprocess':<15}")
        print("-" * 80)

        for m in self.metrics:
            print(
                f"{m.operation:<30} "
                f"{m.duration_ms:>10.2f}ms "
                f"{m.memory_delta_mb:>+10.2f}MB "
                f"{m.subprocess_count:>+5d} procs"
            )

        # Identify bottlenecks
        print("\nBottlenecks (>100ms or >10MB):")
        bottlenecks = [
            m for m in self.metrics if m.duration_ms > 100 or abs(m.memory_delta_mb) > 10
        ]

        if bottlenecks:
            for m in bottlenecks:
                print(f"  ⚠️  {m.operation}: {m.duration_ms:.2f}ms, {m.memory_delta_mb:+.2f}MB")
        else:
            print("  ✅ No bottlenecks detected")

        print("\n" + "=" * 80)


async def profile_sdk_client_lifecycle() -> None:
    """Profile SDK client creation, connection, query, and cleanup."""
    profiler = SDKProfiler()

    # Import after setup to avoid import-time dependencies
    from pilot_space.ai.agents.agent_base import AgentContext
    from pilot_space.ai.agents.pilotspace_agent import ChatInput, PilotSpaceAgent
    from pilot_space.container import AppContainer

    # Initialize container
    container = AppContainer()
    container.config.from_dict(
        {
            "database_url": os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./test.db"),
            "redis_url": os.getenv("REDIS_URL"),
        }
    )
    await container.init_resources()

    try:
        # Get PilotSpaceAgent from container
        agent: PilotSpaceAgent = container.pilot_space_agent()

        workspace_id = UUID("00000000-0000-0000-0000-000000000001")
        user_id = UUID("00000000-0000-0000-0000-000000000001")

        # Profile 1: Client creation
        async def create_client_op():
            chat_input = ChatInput(
                message="Test message",
                session_id=uuid4(),
                user_id=user_id,
                workspace_id=workspace_id,
            )
            context = AgentContext(workspace_id=workspace_id, user_id=user_id)
            return await agent.create_client(chat_input, context)

        client_metrics = await profiler.profile_operation("SDK Client Creation", create_client_op)

        if client_metrics.subprocess_count > 0:
            logger.warning(
                f"⚠️  Client creation spawned {client_metrics.subprocess_count} subprocess(es)"
            )

        # Profile 2: Note sync (simulate large note)
        from pilot_space.ai.agents.note_space_sync import NoteSpaceSync

        sync_service = NoteSpaceSync()

        async def note_sync_op():
            # Simulate syncing a note (mock implementation)
            test_space = anyio.Path("/tmp/pilot-space-profile-test")
            await test_space.mkdir(exist_ok=True)

            # Create large mock note content
            large_note_markdown = "# Large Note\n\n" + ("- Item\n" * 10000)

            sync_service.write_note_markdown(
                test_space, UUID("00000000-0000-0000-0000-000000000001"), large_note_markdown
            )

            return len(large_note_markdown)

        note_sync_metrics = await profiler.profile_operation(
            "Note Sync (10k blocks)", note_sync_op, context_size=None
        )

        # Profile 3: MCP tool registration overhead
        from pilot_space.ai.mcp.event_publisher import EventPublisher
        from pilot_space.ai.mcp.note_server import create_note_tools_server

        async def mcp_tool_setup_op():
            tool_queue: asyncio.Queue[str] = asyncio.Queue()
            server = create_note_tools_server(EventPublisher(tool_queue), context_note_id=None)
            return server

        await profiler.profile_operation("MCP Tool Server Setup", mcp_tool_setup_op)

        # Profile 4: Cleanup
        async def cleanup_op():
            test_space = anyio.Path("/tmp/pilot-space-profile-test")
            if await test_space.exists():
                import shutil

                shutil.rmtree(test_space)

        await profiler.profile_operation("Cleanup", cleanup_op)

    finally:
        await container.shutdown_resources()
        profiler.print_summary()


async def profile_concurrent_sessions() -> None:
    """Profile multiple concurrent SDK sessions to detect resource leaks."""
    profiler = SDKProfiler()

    logger.info("Starting concurrent session profiling (10 sessions)...")

    from pilot_space.ai.agents.agent_base import AgentContext
    from pilot_space.ai.agents.pilotspace_agent import ChatInput, PilotSpaceAgent
    from pilot_space.container import AppContainer

    container = AppContainer()
    container.config.from_dict(
        {
            "database_url": os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./test.db"),
            "redis_url": os.getenv("REDIS_URL"),
        }
    )
    await container.init_resources()

    try:
        agent: PilotSpaceAgent = container.pilot_space_agent()

        async def create_session(session_num: int):
            workspace_id = UUID(f"00000000-0000-0000-0000-00000000000{session_num % 10}")
            user_id = UUID(f"00000000-0000-0000-0000-00000000000{session_num % 10}")

            chat_input = ChatInput(
                message=f"Test session {session_num}",
                session_id=uuid4(),
                user_id=user_id,
                workspace_id=workspace_id,
            )
            context = AgentContext(workspace_id=workspace_id, user_id=user_id)

            client, _ = await agent.create_client(chat_input, context)
            await asyncio.sleep(0.1)  # Simulate some work
            return client

        await profiler.profile_operation(
            "10 Concurrent Sessions",
            lambda: asyncio.gather(*[create_session(i) for i in range(10)]),
        )

    finally:
        await container.shutdown_resources()
        profiler.print_summary()


async def main() -> None:
    """Run all profiling scenarios."""
    print("\n" + "=" * 80)
    print("CLAUDE AGENT SDK PERFORMANCE PROFILER")
    print("=" * 80)
    print("\nThis script profiles:")
    print("  1. SDK client lifecycle (creation, connection, cleanup)")
    print("  2. Note sync performance")
    print("  3. MCP tool overhead")
    print("  4. Concurrent session handling")
    print("\n" + "=" * 80 + "\n")

    # Scenario 1: Basic SDK lifecycle
    print("\n[Scenario 1] SDK Client Lifecycle")
    print("-" * 80)
    try:
        await profile_sdk_client_lifecycle()
    except Exception as e:
        logger.error(f"SDK lifecycle profiling failed: {e}", exc_info=True)

    await asyncio.sleep(2)

    # Scenario 2: Concurrent sessions
    print("\n[Scenario 2] Concurrent Sessions")
    print("-" * 80)
    try:
        await profile_concurrent_sessions()
    except Exception as e:
        logger.error(f"Concurrent session profiling failed: {e}", exc_info=True)

    print("\n" + "=" * 80)
    print("PROFILING COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
