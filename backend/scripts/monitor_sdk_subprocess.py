"""Real-time monitoring of Claude SDK subprocess resources.

Monitors CPU, memory, and thread count of claude subprocess during operations.
Helps identify resource leaks, zombie processes, and performance bottlenecks.

Usage:
    # Terminal 1: Start monitoring
    uv run python -m scripts.monitor_sdk_subprocess

    # Terminal 2: Perform extract-issues operation
    # (monitoring will capture resource usage in real-time)
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from datetime import datetime

import psutil

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@dataclass
class ProcessSnapshot:
    """Snapshot of process resource usage."""

    timestamp: datetime
    pid: int
    name: str
    cpu_percent: float
    memory_mb: float
    num_threads: int
    status: str
    cmdline: str


class SDKSubprocessMonitor:
    """Monitors Claude SDK subprocess resource usage."""

    def __init__(self, poll_interval: float = 1.0) -> None:
        """Initialize monitor.

        Args:
            poll_interval: Seconds between polls (default: 1.0)
        """
        self.poll_interval = poll_interval
        self.snapshots: list[ProcessSnapshot] = []
        self._running = False

    def find_claude_processes(self) -> list[psutil.Process]:
        """Find all running Claude SDK processes.

        Returns:
            List of Process objects for claude binaries
        """
        claude_procs = []
        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                # Check if process is claude binary
                name = proc.info["name"]
                cmdline = proc.info["cmdline"]

                if (name and "claude" in name.lower()) or (
                    cmdline and any("claude" in arg.lower() for arg in cmdline)
                ):
                    claude_procs.append(proc)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        return claude_procs

    def capture_snapshot(self, proc: psutil.Process) -> ProcessSnapshot:
        """Capture resource snapshot for a process.

        Args:
            proc: Process to snapshot

        Returns:
            ProcessSnapshot with current resource usage
        """
        try:
            return ProcessSnapshot(
                timestamp=datetime.now(),
                pid=proc.pid,
                name=proc.name(),
                cpu_percent=proc.cpu_percent(),
                memory_mb=proc.memory_info().rss / 1024 / 1024,
                num_threads=proc.num_threads(),
                status=proc.status(),
                cmdline=" ".join(proc.cmdline()),
            )
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return ProcessSnapshot(
                timestamp=datetime.now(),
                pid=proc.pid,
                name="<terminated>",
                cpu_percent=0.0,
                memory_mb=0.0,
                num_threads=0,
                status="terminated",
                cmdline="",
            )

    async def monitor(self, duration_seconds: int | None = None) -> None:
        """Monitor Claude processes until stopped or duration expires.

        Args:
            duration_seconds: Optional monitoring duration (None = forever)
        """
        self._running = True
        start_time = time.time()

        logger.info(f"[Monitor] Starting (interval={self.poll_interval}s)")

        if duration_seconds:
            logger.info(f"[Monitor] Will run for {duration_seconds}s")

        while self._running:
            # Check duration
            if duration_seconds and (time.time() - start_time) > duration_seconds:
                logger.info("[Monitor] Duration limit reached, stopping")
                break

            # Find and snapshot all Claude processes
            procs = self.find_claude_processes()

            if not procs:
                logger.debug("[Monitor] No Claude processes found")
            else:
                for proc in procs:
                    snapshot = self.capture_snapshot(proc)
                    self.snapshots.append(snapshot)

                    logger.info(
                        f"[Monitor] PID={snapshot.pid} "
                        f"CPU={snapshot.cpu_percent:.1f}% "
                        f"MEM={snapshot.memory_mb:.1f}MB "
                        f"THREADS={snapshot.num_threads} "
                        f"STATUS={snapshot.status}"
                    )

            await asyncio.sleep(self.poll_interval)

        logger.info(f"[Monitor] Stopped. Captured {len(self.snapshots)} snapshots")

    def stop(self) -> None:
        """Stop monitoring."""
        self._running = False

    def print_summary(self) -> None:
        """Print summary statistics."""
        if not self.snapshots:
            logger.warning("[Summary] No snapshots captured")
            return

        print("\n" + "=" * 80)
        print("SDK SUBPROCESS MONITORING SUMMARY")
        print("=" * 80)

        # Group by PID
        by_pid: dict[int, list[ProcessSnapshot]] = {}
        for snap in self.snapshots:
            if snap.pid not in by_pid:
                by_pid[snap.pid] = []
            by_pid[snap.pid].append(snap)

        print(f"\nTotal processes monitored: {len(by_pid)}")
        print(f"Total snapshots: {len(self.snapshots)}")

        for pid, snapshots in by_pid.items():
            if not snapshots:
                continue

            print(f"\n--- PID {pid} ({snapshots[0].name}) ---")
            print(f"Snapshots: {len(snapshots)}")
            print(
                f"Duration: {(snapshots[-1].timestamp - snapshots[0].timestamp).total_seconds():.1f}s"
            )

            cpu_values = [s.cpu_percent for s in snapshots]
            mem_values = [s.memory_mb for s in snapshots]

            print(f"CPU: avg={sum(cpu_values) / len(cpu_values):.1f}% max={max(cpu_values):.1f}%")
            print(
                f"Memory: avg={sum(mem_values) / len(mem_values):.1f}MB max={max(mem_values):.1f}MB"
            )
            print(f"Threads: {snapshots[-1].num_threads}")
            print(f"Final status: {snapshots[-1].status}")

            # Check for issues
            if max(cpu_values) > 80:
                print("  ⚠️  HIGH CPU USAGE DETECTED")

            if max(mem_values) > 500:
                print("  ⚠️  HIGH MEMORY USAGE DETECTED (>500MB)")

            if snapshots[-1].status in ["zombie", "sleeping"]:
                print(f"  ⚠️  PROCESS IN {snapshots[-1].status.upper()} STATE")

        print("\n" + "=" * 80)

    def export_csv(self, filename: str = "sdk_monitoring.csv") -> None:
        """Export snapshots to CSV file.

        Args:
            filename: Output CSV filename
        """
        import csv

        with open(filename, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "timestamp",
                    "pid",
                    "name",
                    "cpu_percent",
                    "memory_mb",
                    "num_threads",
                    "status",
                ]
            )

            for snap in self.snapshots:
                writer.writerow(
                    [
                        snap.timestamp.isoformat(),
                        snap.pid,
                        snap.name,
                        snap.cpu_percent,
                        snap.memory_mb,
                        snap.num_threads,
                        snap.status,
                    ]
                )

        logger.info(f"[Export] Wrote {len(self.snapshots)} snapshots to {filename}")


async def main() -> None:
    """Run monitoring."""
    import argparse

    parser = argparse.ArgumentParser(description="Monitor Claude SDK subprocess resources")
    parser.add_argument(
        "--duration",
        type=int,
        default=None,
        help="Monitoring duration in seconds (default: run until Ctrl+C)",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=1.0,
        help="Polling interval in seconds (default: 1.0)",
    )
    parser.add_argument(
        "--export",
        type=str,
        default=None,
        help="Export results to CSV file",
    )

    args = parser.parse_args()

    monitor = SDKSubprocessMonitor(poll_interval=args.interval)

    try:
        await monitor.monitor(duration_seconds=args.duration)
    except KeyboardInterrupt:
        logger.info("[Main] Interrupted by user")
        monitor.stop()

    monitor.print_summary()

    if args.export:
        monitor.export_csv(args.export)


if __name__ == "__main__":
    asyncio.run(main())
