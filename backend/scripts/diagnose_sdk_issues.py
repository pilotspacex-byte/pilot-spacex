"""Diagnostic script for Claude SDK resource issues.

Checks for:
- Zombie/orphaned SDK processes
- Memory leaks
- Client pool issues
- Configuration problems

Provides actionable recommendations for fixing issues.

Usage:
    uv run python -m scripts.diagnose_sdk_issues
"""

from __future__ import annotations

import asyncio
import logging
import os
import shutil
from dataclasses import dataclass
from pathlib import Path

import psutil

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@dataclass
class DiagnosticIssue:
    """Represents a detected issue."""

    severity: str  # "critical", "warning", "info"
    category: str
    description: str
    recommendation: str


class SDKDiagnostics:
    """Diagnostic tool for SDK issues."""

    def __init__(self) -> None:
        """Initialize diagnostics."""
        self.issues: list[DiagnosticIssue] = []

    def add_issue(
        self,
        severity: str,
        category: str,
        description: str,
        recommendation: str,
    ) -> None:
        """Add a diagnostic issue.

        Args:
            severity: "critical", "warning", or "info"
            category: Issue category
            description: Issue description
            recommendation: Recommended fix
        """
        self.issues.append(
            DiagnosticIssue(
                severity=severity,
                category=category,
                description=description,
                recommendation=recommendation,
            )
        )

    def check_zombie_processes(self) -> None:
        """Check for zombie or orphaned Claude processes."""
        logger.info("[Check] Scanning for Claude processes...")

        claude_procs = []
        for proc in psutil.process_iter(["pid", "name", "status", "cmdline"]):
            try:
                name = proc.info["name"]
                cmdline = proc.info["cmdline"]

                if (name and "claude" in name.lower()) or (
                    cmdline and any("claude" in arg.lower() for arg in cmdline)
                ):
                    claude_procs.append(proc)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        if not claude_procs:
            logger.info("  ✅ No Claude processes found")
            return

        for proc in claude_procs:
            try:
                status = proc.status()
                cpu = proc.cpu_percent(interval=0.1)
                mem = proc.memory_info().rss / 1024 / 1024

                logger.info(
                    f"  Found: PID={proc.pid} STATUS={status} CPU={cpu:.1f}% MEM={mem:.1f}MB"
                )

                # Check for zombie
                if status == psutil.STATUS_ZOMBIE:
                    self.add_issue(
                        severity="critical",
                        category="Zombie Process",
                        description=f"Zombie Claude process detected (PID={proc.pid})",
                        recommendation=f"Kill zombie process: kill -9 {proc.pid}",
                    )

                # Check for high CPU/memory
                if cpu > 50 and mem > 300:
                    self.add_issue(
                        severity="warning",
                        category="High Resource Usage",
                        description=f"Claude process using {cpu:.1f}% CPU and {mem:.1f}MB memory (PID={proc.pid})",
                        recommendation=(
                            f"1. Check if process is stuck in a loop\n"
                            f"2. Monitor with: uv run python -m scripts.monitor_sdk_subprocess --duration 60\n"
                            f"3. If stuck, kill: kill {proc.pid}"
                        ),
                    )

            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

    def check_configuration(self) -> None:
        """Check SDK configuration for common issues."""
        logger.info("[Check] Validating SDK configuration...")

        # Check for ANTHROPIC_API_KEY
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            self.add_issue(
                severity="critical",
                category="Configuration",
                description="ANTHROPIC_API_KEY environment variable not set",
                recommendation="Set ANTHROPIC_API_KEY in .env file or export it",
            )
        else:
            logger.info("  ✅ ANTHROPIC_API_KEY is set")

        # Check for claude binary
        claude_bin = shutil.which("claude")
        if not claude_bin:
            self.add_issue(
                severity="critical",
                category="Installation",
                description="Claude binary not found in PATH",
                recommendation="Install Claude SDK: npm install -g @anthropic-ai/sdk",
            )
        else:
            logger.info(f"  ✅ Claude binary found: {claude_bin}")

        # Check PilotSpaceAgent configuration
        agent_file = Path("backend/src/pilot_space/ai/agents/pilotspace_agent.py")
        if agent_file.exists():
            content = agent_file.read_text()

            # Check for Ollama override
            if '"ANTHROPIC_BASE_URL": "http://localhost:11434"' in content:
                self.add_issue(
                    severity="warning",
                    category="Configuration",
                    description="Using Ollama local endpoint (http://localhost:11434)",
                    recommendation=(
                        "If not using Ollama, remove ANTHROPIC_BASE_URL override in pilotspace_agent.py:420-422.\n"
                        "This may cause SDK to retry with incorrect endpoints."
                    ),
                )

            # Check for non-standard model
            if '"kimi-k2.5:cloud"' in content:
                self.add_issue(
                    severity="warning",
                    category="Configuration",
                    description='Using non-standard model "kimi-k2.5:cloud"',
                    recommendation=(
                        'Change to standard Anthropic model: "claude-sonnet-4-20250514"\n'
                        "Non-standard models may cause compatibility issues."
                    ),
                )

    def check_workspace_spaces(self) -> None:
        """Check for orphaned workspace spaces."""
        logger.info("[Check] Scanning workspace spaces...")

        spaces_dir = Path("/tmp/pilot-space")
        if not spaces_dir.exists():
            logger.info("  ℹ️  No /tmp/pilot-space directory found")
            return

        workspace_dirs = list(spaces_dir.glob("workspace-*"))
        if not workspace_dirs:
            logger.info("  ✅ No workspace directories found")
            return

        total_size = sum(
            sum(f.stat().st_size for f in d.rglob("*") if f.is_file()) for d in workspace_dirs
        )
        total_size_mb = total_size / 1024 / 1024

        logger.info(f"  Found {len(workspace_dirs)} workspace(s), {total_size_mb:.1f}MB total")

        if total_size_mb > 100:
            self.add_issue(
                severity="warning",
                category="Disk Usage",
                description=f"Workspace spaces using {total_size_mb:.1f}MB disk space",
                recommendation=(
                    "Clean up old workspaces:\n"
                    f"  rm -rf {spaces_dir}/*\n"
                    "Or implement cleanup cron job."
                ),
            )

    async def check_redis_client_pool(self) -> None:
        """Check Redis for cached SDK clients."""
        logger.info("[Check] Checking Redis client pool...")

        try:
            from pilot_space.infrastructure.cache.redis import RedisClient

            redis = RedisClient(url=os.getenv("REDIS_URL"))
            await redis.connect()

            # Check for client session keys
            keys = await redis.redis.keys("client:*")
            if keys:
                logger.info(f"  Found {len(keys)} cached client session(s)")

                if len(keys) > 10:
                    self.add_issue(
                        severity="warning",
                        category="Client Pool",
                        description=f"{len(keys)} cached client sessions in Redis",
                        recommendation=(
                            "Client pool may not be evicting idle clients properly.\n"
                            "Check ConversationWorker._cleanup_idle_clients() logic."
                        ),
                    )
            else:
                logger.info("  ✅ No cached client sessions")

            await redis.disconnect()

        except Exception as e:
            logger.warning(f"  ⚠️  Could not connect to Redis: {e}")
            self.add_issue(
                severity="info",
                category="Redis",
                description="Could not check Redis client pool",
                recommendation="Verify REDIS_URL is set and Redis is running",
            )

    def print_report(self) -> None:
        """Print diagnostic report."""
        print("\n" + "=" * 80)
        print("CLAUDE SDK DIAGNOSTIC REPORT")
        print("=" * 80)

        if not self.issues:
            print("\n✅ No issues detected! System appears healthy.\n")
            print("=" * 80)
            return

        # Group by severity
        critical = [i for i in self.issues if i.severity == "critical"]
        warnings = [i for i in self.issues if i.severity == "warning"]
        info = [i for i in self.issues if i.severity == "info"]

        print(f"\nIssues found: {len(self.issues)}")
        print(f"  🔴 Critical: {len(critical)}")
        print(f"  🟡 Warnings: {len(warnings)}")
        print(f"  ℹ️  Info: {len(info)}")

        # Print critical issues first
        if critical:
            print("\n" + "=" * 80)
            print("🔴 CRITICAL ISSUES")
            print("=" * 80)
            for i, issue in enumerate(critical, 1):
                print(f"\n{i}. [{issue.category}] {issue.description}")
                print(f"   Recommendation: {issue.recommendation}")

        # Print warnings
        if warnings:
            print("\n" + "=" * 80)
            print("🟡 WARNINGS")
            print("=" * 80)
            for i, issue in enumerate(warnings, 1):
                print(f"\n{i}. [{issue.category}] {issue.description}")
                print(f"   Recommendation: {issue.recommendation}")

        # Print info
        if info:
            print("\n" + "=" * 80)
            print("ℹ️  INFORMATION")
            print("=" * 80)
            for i, issue in enumerate(info, 1):
                print(f"\n{i}. [{issue.category}] {issue.description}")
                print(f"   Recommendation: {issue.recommendation}")

        print("\n" + "=" * 80)
        print("NEXT STEPS")
        print("=" * 80)
        print("\n1. Address critical issues immediately")
        print("2. Monitor SDK subprocess: uv run python -m scripts.monitor_sdk_subprocess")
        print("3. Profile performance: uv run python -m scripts.profile_sdk_performance")
        print("4. Check logs for errors: tail -f backend/logs/app.log")
        print("\n" + "=" * 80 + "\n")


async def main() -> None:
    """Run diagnostics."""
    print("\n" + "=" * 80)
    print("CLAUDE SDK DIAGNOSTICS")
    print("=" * 80)
    print("\nScanning for common issues...\n")

    diagnostics = SDKDiagnostics()

    # Run checks
    diagnostics.check_zombie_processes()
    diagnostics.check_configuration()
    diagnostics.check_workspace_spaces()
    await diagnostics.check_redis_client_pool()

    # Print report
    diagnostics.print_report()


if __name__ == "__main__":
    asyncio.run(main())
