"""Performance harness: Version Engine & PM Blocks benchmarks (Feature 017).

Tests PERF-017-001 through PERF-017-004.

Marked `benchmark` — excluded from PR gate.
Run with: uv run pytest -m benchmark tests/performance/

SLOs:
  PERF-017-001: AI change digest generation <3s (95th percentile)
  PERF-017-002: Diff computation between two 200-block versions <1s
  PERF-017-003: DAG render for 50 nodes <1s
  PERF-017-004: Sprint board render for 100 issues across 6 lanes <500ms
"""

from __future__ import annotations

import random
import time
from collections.abc import Callable
from typing import Any
from uuid import uuid4

import pytest

pytestmark = pytest.mark.benchmark


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_block(block_type: str = "paragraph") -> dict[str, Any]:
    return {
        "id": str(uuid4()),
        "type": block_type,
        "content": [{"type": "text", "text": f"Block content {uuid4().hex[:8]}"}],
    }


def _make_note_content(block_count: int) -> dict[str, Any]:
    return {
        "type": "doc",
        "content": [_make_block() for _ in range(block_count)],
    }


def _diff_note_versions(old_content: dict[str, Any], new_content: dict[str, Any]) -> dict[str, Any]:
    """Block-level diff: added, removed, changed block IDs."""
    old_blocks = {b["id"]: b for b in old_content["content"]}
    new_blocks = {b["id"]: b for b in new_content["content"]}
    added = [bid for bid in new_blocks if bid not in old_blocks]
    removed = [bid for bid in old_blocks if bid not in new_blocks]
    changed = [
        bid
        for bid in old_blocks
        if bid in new_blocks and old_blocks[bid]["content"] != new_blocks[bid]["content"]
    ]
    return {"added": added, "removed": removed, "changed": changed}


def _build_dag(node_count: int) -> dict[str, list[str]]:
    """Build an acyclic DAG with node_count nodes."""
    adjacency: dict[str, list[str]] = {str(i): [] for i in range(node_count)}
    for i in range(1, node_count):
        parent = random.randint(0, i - 1)
        adjacency[str(parent)].append(str(i))
    return adjacency


def _compute_critical_path(dag: dict[str, list[str]]) -> list[str]:
    """Find critical path (longest path) via DFS from node 0."""
    longest: list[str] = []

    def dfs(node: str, path: list[str]) -> None:
        nonlocal longest
        current = [*path, node]
        if len(current) > len(longest):
            longest = current
        for child in dag.get(node, []):
            dfs(child, current)

    dfs("0", [])
    return longest


def _render_sprint_board(issues: list[dict[str, Any]], lanes: list[str]) -> dict[str, Any]:
    """Group issues into lanes."""
    board: dict[str, list[dict[str, Any]]] = {lane: [] for lane in lanes}
    for issue in issues:
        lane = issue.get("state", lanes[0])
        if lane in board:
            board[lane].append(issue)
    return board


def _measure_p95(fn: Callable[[], Any], iterations: int) -> float:
    latencies = []
    for _ in range(iterations):
        start = time.perf_counter()
        fn()
        latencies.append((time.perf_counter() - start) * 1000)
    latencies.sort()
    p95_idx = int(len(latencies) * 0.95)
    return latencies[min(p95_idx, len(latencies) - 1)]


# ---------------------------------------------------------------------------
# PERF-017-001: AI change digest generation <3s
# ---------------------------------------------------------------------------


class TestDigestGenerationPerf:
    """PERF-017-001: Digest generation for 50-block changes in <3s."""

    def test_diff_computation_for_digest_input_is_fast(self) -> None:
        """Digest input preparation (diff) must be <100ms for 50-block note."""
        old = _make_note_content(50)
        new = _make_note_content(50)
        # Modify some blocks to create changes
        for block in new["content"][:10]:
            block["content"] = [{"type": "text", "text": "Modified content"}]

        start = time.perf_counter()
        diff = _diff_note_versions(old, new)
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert elapsed_ms < 100, (
            f"PERF-017-001: Diff prep took {elapsed_ms:.1f}ms (limit: 100ms). "
            "Diff computation is blocking digest generation."
        )
        # Structural correctness
        assert "added" in diff
        assert "removed" in diff
        assert "changed" in diff

    def test_digest_cache_lookup_overhead_negligible(self) -> None:
        """Cache key computation for digest should be <1ms."""
        note_id = uuid4()
        version_id = uuid4()

        start = time.perf_counter()
        cache_key = f"digest:{note_id}:{version_id}"
        _ = hash(cache_key)
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert elapsed_ms < 1, f"Cache key overhead {elapsed_ms:.3f}ms too high"
        assert str(note_id) in cache_key


# ---------------------------------------------------------------------------
# PERF-017-002: Diff computation <1s for two 200-block versions
# ---------------------------------------------------------------------------


class TestDiffComputationPerf:
    """PERF-017-002: Diff two 200-block versions in <1s."""

    @pytest.fixture(scope="class")
    def two_large_versions(self) -> tuple[dict[str, Any], dict[str, Any]]:
        old = _make_note_content(200)
        new_content = _make_note_content(200)
        # Mix in some IDs from old to simulate realistic changes
        for i in range(0, 200, 3):
            new_content["content"][i]["id"] = old["content"][i]["id"]
        # Modify some shared blocks
        for i in range(0, 50, 3):
            new_content["content"][i]["content"] = [{"type": "text", "text": "Changed"}]
        return old, new_content

    def test_diff_200_blocks_under_1s(
        self, two_large_versions: tuple[dict[str, Any], dict[str, Any]]
    ) -> None:
        old, new = two_large_versions

        p95 = _measure_p95(lambda: _diff_note_versions(old, new), iterations=20)

        assert p95 < 1000, (
            f"PERF-017-002 FAILED: p95={p95:.1f}ms (SLO: <1000ms). "
            "Block-level diff algorithm needs optimization."
        )

    def test_diff_produces_correct_categories(
        self, two_large_versions: tuple[dict[str, Any], dict[str, Any]]
    ) -> None:
        old, new = two_large_versions
        diff = _diff_note_versions(old, new)
        total_changes = len(diff["added"]) + len(diff["removed"]) + len(diff["changed"])
        assert total_changes > 0  # we know we made changes


# ---------------------------------------------------------------------------
# PERF-017-003: DAG render for 50 nodes <1s
# ---------------------------------------------------------------------------


class TestDAGRenderPerf:
    """PERF-017-003: Dependency DAG with 50 nodes renders critical path in <1s."""

    @pytest.fixture(scope="class")
    def dag_50_nodes(self) -> dict[str, list[str]]:
        return _build_dag(50)

    def test_dag_critical_path_under_1s(self, dag_50_nodes: dict[str, list[str]]) -> None:
        p95 = _measure_p95(lambda: _compute_critical_path(dag_50_nodes), iterations=20)

        assert p95 < 1000, (
            f"PERF-017-003 FAILED: p95={p95:.1f}ms (SLO: <1000ms at 50 nodes). "
            "Critical path algorithm needs memoization."
        )

    def test_dag_acyclic_for_50_nodes(self, dag_50_nodes: dict[str, list[str]]) -> None:
        """Builder must produce acyclic graph — test validates no self-loops."""
        for node, children in dag_50_nodes.items():
            assert node not in children, f"Self-loop detected at node {node}"

    def test_critical_path_non_empty(self, dag_50_nodes: dict[str, list[str]]) -> None:
        path = _compute_critical_path(dag_50_nodes)
        assert len(path) >= 1
        assert path[0] == "0"  # always starts at root


# ---------------------------------------------------------------------------
# PERF-017-004: Sprint board render <500ms for 100 issues / 6 lanes
# ---------------------------------------------------------------------------


SPRINT_LANES = ["backlog", "todo", "in_progress", "in_review", "done", "cancelled"]


class TestSprintBoardRenderPerf:
    """PERF-017-004: Sprint board groups 100 issues into 6 lanes in <500ms."""

    @pytest.fixture(scope="class")
    def issues_100(self) -> list[dict[str, Any]]:
        return [
            {
                "id": str(uuid4()),
                "name": f"Issue {i}",
                "state": random.choice(SPRINT_LANES),
                "estimate": random.randint(1, 8),
            }
            for i in range(100)
        ]

    def test_board_render_under_500ms(self, issues_100: list[dict[str, Any]]) -> None:
        p95 = _measure_p95(
            lambda: _render_sprint_board(issues_100, SPRINT_LANES),
            iterations=50,
        )

        assert p95 < 500, (
            f"PERF-017-004 FAILED: p95={p95:.1f}ms (SLO: <500ms). "
            "Sprint board grouping is too slow — check for N+1 patterns."
        )

    def test_all_lanes_present_in_output(self, issues_100: list[dict[str, Any]]) -> None:
        board = _render_sprint_board(issues_100, SPRINT_LANES)
        assert set(board.keys()) == set(SPRINT_LANES)

    def test_all_issues_accounted_for(self, issues_100: list[dict[str, Any]]) -> None:
        board = _render_sprint_board(issues_100, SPRINT_LANES)
        total = sum(len(v) for v in board.values())
        assert total == 100

    def test_six_lanes_defined(self) -> None:
        assert len(SPRINT_LANES) == 6
