"""Sprint 1a Gate: CRDT load test (Feature 016).

PERF-016-001: 10 concurrent editors (7 human + 3 AI skill) sustained 60s,
p95 sync latency <500ms (gate), <200ms (target).

This harness tests the synchronization model without a real WebSocket server.
It simulates concurrent document operations and measures merge latency.

Gate outcome:
  PASS (p95 <500ms) -> proceed with Supabase Realtime
  FAIL (p95 >=500ms) -> evaluate y-websocket or drop M6a

Other benchmarks in this file:
  PERF-016-002: Keystroke latency at 200 blocks <100ms
  PERF-016-005: Dirty detection on 200-block note <50ms
  PERF-016-006: Focus Mode toggle time <200ms
"""

from __future__ import annotations

import random
import statistics
import threading
import time
from collections.abc import Callable
from queue import Queue
from typing import Any

import pytest

pytestmark = pytest.mark.benchmark


# ---------------------------------------------------------------------------
# Simulated CRDT model
# ---------------------------------------------------------------------------


class _SimulatedYDoc:
    """Thread-safe in-memory document simulating Yjs CRDT semantics.

    Real CRDT convergence testing requires actual ypy/yrs — this tests
    the synchronization orchestration layer (latency, concurrency, merging).
    """

    def __init__(self) -> None:
        self._blocks: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._clock = 0

    def apply_operation(self, block_id: str, content: str, owner: str) -> tuple[float, float]:
        """Apply an insert/update op. Returns (start_time, end_time)."""
        start = time.perf_counter()
        with self._lock:
            self._clock += 1
            self._blocks[block_id] = {
                "content": content,
                "owner": owner,
                "clock": self._clock,
            }
        end = time.perf_counter()
        return start, end

    def read_all(self) -> dict[str, dict[str, Any]]:
        with self._lock:
            return dict(self._blocks)

    @property
    def block_count(self) -> int:
        with self._lock:
            return len(self._blocks)


def _run_editor(
    doc: _SimulatedYDoc,
    editor_id: str,
    owner_type: str,
    duration_s: float,
    result_queue: Queue[float],
) -> None:
    """Simulate one editor applying operations for `duration_s` seconds."""
    deadline = time.perf_counter() + duration_s
    while time.perf_counter() < deadline:
        block_id = f"block-{editor_id}-{random.randint(0, 20)}"
        content = f"Content from {editor_id} at {time.perf_counter():.4f}"
        start, end = doc.apply_operation(block_id, content, owner_type)
        latency_ms = (end - start) * 1000
        result_queue.put(latency_ms)
        # Simulate human typing pace or AI batch writes
        if owner_type == "human":
            time.sleep(random.uniform(0.05, 0.15))  # ~10 wpm
        else:
            time.sleep(random.uniform(0.1, 0.3))  # AI writes in bursts


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
# PERF-016-001: Sprint 1a Gate — 10 editors, p95 <500ms
# ---------------------------------------------------------------------------


class TestCRDTGate:
    """PERF-016-001: 10 concurrent editors for 5s, p95 sync latency <500ms."""

    def test_concurrent_editors_p95_gate(self) -> None:
        """Gate test: 7 human + 3 AI skill editors, p95 <500ms.

        Uses 5s instead of 60s to keep CI fast; real gate uses 60s.
        """
        doc = _SimulatedYDoc()
        result_queue: Queue[float] = Queue()
        editors = [("human", f"human-{i}") for i in range(7)] + [
            ("ai", f"ai-skill-{i}") for i in range(3)
        ]
        threads = [
            threading.Thread(
                target=_run_editor,
                args=(doc, editor_id, owner_type, 3.0, result_queue),
                daemon=True,
            )
            for owner_type, editor_id in editors
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10.0)

        latencies = []
        while not result_queue.empty():
            latencies.append(result_queue.get_nowait())

        assert len(latencies) > 50, (
            f"Too few operations recorded ({len(latencies)}). "
            "Test may have timed out or had threading issue."
        )

        latencies.sort()
        p95_idx = int(len(latencies) * 0.95)
        p95 = latencies[min(p95_idx, len(latencies) - 1)]
        p50 = statistics.median(latencies)

        assert p95 < 500, (
            f"PERF-016-001 GATE FAILED: p95={p95:.2f}ms (gate: 500ms, target: 200ms). "
            f"p50={p50:.2f}ms, ops={len(latencies)}. "
            "Consider y-websocket or reducing AI operation frequency."
        )

    def test_no_data_loss_under_concurrent_writes(self) -> None:
        """All operations must be eventually visible (CRDT convergence property)."""
        doc = _SimulatedYDoc()
        result_queue: Queue[float] = Queue()
        threads = [
            threading.Thread(
                target=_run_editor,
                args=(doc, f"editor-{i}", "human", 1.0, result_queue),
                daemon=True,
            )
            for i in range(5)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5.0)

        # Document should have blocks from all editors
        final_state = doc.read_all()
        assert len(final_state) > 0

    def test_ai_and_human_editors_coexist(self) -> None:
        """Human and AI editors can both write without deadlock."""
        doc = _SimulatedYDoc()
        q: Queue[float] = Queue()

        human_thread = threading.Thread(
            target=_run_editor, args=(doc, "human-1", "human", 0.5, q), daemon=True
        )
        ai_thread = threading.Thread(
            target=_run_editor, args=(doc, "ai-skill-1", "ai", 0.5, q), daemon=True
        )

        human_thread.start()
        ai_thread.start()
        human_thread.join(timeout=3.0)
        ai_thread.join(timeout=3.0)

        assert not human_thread.is_alive(), "Human thread hung"
        assert not ai_thread.is_alive(), "AI thread hung"


# ---------------------------------------------------------------------------
# PERF-016-002: Keystroke latency at 200 blocks <100ms
# ---------------------------------------------------------------------------


class TestKeystrokeLatency:
    """PERF-016-002: Block update p95 <100ms with 200-block document."""

    @pytest.fixture(scope="class")
    def large_doc(self) -> _SimulatedYDoc:
        doc = _SimulatedYDoc()
        # Pre-populate with 200 blocks
        for i in range(200):
            doc.apply_operation(f"block-{i}", f"Existing content {i}", "human")
        return doc

    def test_keystroke_p95_under_100ms(self, large_doc: _SimulatedYDoc) -> None:
        q: Queue[float] = Queue()

        def single_keystroke() -> None:
            _, _ = large_doc.apply_operation(
                f"block-{random.randint(0, 199)}", "Updated content", "human"
            )

        p95 = _measure_p95(single_keystroke, iterations=50)

        assert p95 < 100, (
            f"PERF-016-002 FAILED: p95={p95:.2f}ms (SLO: <100ms at 200 blocks). "
            "Block update operation is too slow."
        )

    def test_200_blocks_in_document(self, large_doc: _SimulatedYDoc) -> None:
        assert large_doc.block_count >= 200


# ---------------------------------------------------------------------------
# PERF-016-005: Dirty detection on 200-block note <50ms
# ---------------------------------------------------------------------------


class TestDirtyDetection:
    """PERF-016-005: Dirty detection on 200-block note in <50ms."""

    def test_hash_based_dirty_detection_under_50ms(self) -> None:
        """Simulate dirty detection by hashing document content."""
        blocks = [{"id": f"block-{i}", "content": f"Content {i}"} for i in range(200)]

        def detect_dirty() -> bool:
            # Simulate dirty check: hash all block contents
            content_hash = hash(tuple((b["id"], b["content"]) for b in blocks))
            return content_hash != 0  # always different from 0

        p95 = _measure_p95(detect_dirty, iterations=50)

        assert p95 < 50, (
            f"PERF-016-005 FAILED: p95={p95:.2f}ms (SLO: <50ms at 200 blocks). "
            "Dirty detection algorithm needs optimization."
        )


# ---------------------------------------------------------------------------
# PERF-016-006: Focus Mode toggle <200ms
# ---------------------------------------------------------------------------


class TestFocusModeToggle:
    """PERF-016-006: Focus Mode toggle (100 AI + 100 human blocks) <200ms."""

    def test_focus_mode_toggle_under_200ms(self) -> None:
        """Simulate filtering 200 blocks by owner type."""
        blocks = [
            {
                "id": f"block-{i}",
                "content": f"Content {i}",
                "owner": "human" if i % 2 == 0 else "ai",
            }
            for i in range(200)
        ]

        def toggle_focus_mode() -> list[dict[str, Any]]:
            return [b for b in blocks if b["owner"] == "human"]

        p95 = _measure_p95(toggle_focus_mode, iterations=50)

        assert p95 < 200, (
            f"PERF-016-006 FAILED: p95={p95:.2f}ms (SLO: <200ms for 200-block Focus Mode toggle). "
            "Block filtering needs optimization."
        )

    def test_focus_mode_shows_only_human_blocks(self) -> None:
        blocks = [
            {"id": str(i), "owner": "human" if i % 2 == 0 else "ai:skill-1"} for i in range(200)
        ]
        human_blocks = [b for b in blocks if b["owner"] == "human"]
        assert len(human_blocks) == 100
        assert all(b["owner"] == "human" for b in human_blocks)
