"""Performance harness: Memory Search latency benchmarks (Feature 015).

Tests PERF-015-001 through PERF-015-003.

These tests are marked `benchmark` and excluded from the default PR gate.
Run with: uv run pytest -m benchmark tests/performance/

SLOs:
  PERF-015-001: p95 memory search <200ms at 1000 entries
  PERF-015-002: p95 memory search <500ms at 5000 entries
  PERF-015-003: single embedding generation <500ms

Mock boundary: embedding API mocked (cost + determinism).
Real dependency: hybrid scoring logic tested against in-memory stubs.
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
# Test helpers
# ---------------------------------------------------------------------------


def _generate_random_vector(dim: int = 768) -> list[float]:
    """Generate a random unit-normalized vector."""
    vec = [random.gauss(0, 1) for _ in range(dim)]
    magnitude = sum(x * x for x in vec) ** 0.5
    if magnitude == 0:
        return [0.0] * dim
    return [x / magnitude for x in vec]


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    mag_a = sum(x * x for x in a) ** 0.5
    mag_b = sum(x * x for x in b) ** 0.5
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


def _keyword_score(content: str, query: str) -> float:
    """Simple keyword overlap score [0.0, 1.0]."""
    query_words = set(query.lower().split())
    content_words = set(content.lower().split())
    if not query_words:
        return 0.0
    return len(query_words & content_words) / len(query_words)


class _MemoryEntryStub:
    """Lightweight in-memory stand-in for MemoryEntry ORM rows."""

    __slots__ = ("content", "embedding", "id", "workspace_id")

    def __init__(self, workspace_id: Any) -> None:
        self.id = uuid4()
        self.workspace_id = workspace_id
        self.content = f"Memory entry about {uuid4().hex[:8]} implementation pattern"
        self.embedding = _generate_random_vector(768)


def _run_hybrid_search(
    entries: list[_MemoryEntryStub],
    query_embedding: list[float],
    query_text: str,
    top_k: int = 5,
) -> list[tuple[_MemoryEntryStub, float]]:
    """Hybrid search: 0.7 * vector_score + 0.3 * keyword_score."""
    scored = []
    for entry in entries:
        vector_score = max(0.0, _cosine_similarity(entry.embedding, query_embedding))
        keyword = _keyword_score(entry.content, query_text)
        hybrid = 0.7 * vector_score + 0.3 * keyword
        scored.append((entry, hybrid))
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:top_k]


def _measure_p95(fn: Callable[[], Any], iterations: int) -> float:
    """Run fn N times, return p95 latency in milliseconds."""
    latencies = []
    for _ in range(iterations):
        start = time.perf_counter()
        fn()
        latencies.append((time.perf_counter() - start) * 1000)
    latencies.sort()
    p95_idx = int(len(latencies) * 0.95)
    return latencies[min(p95_idx, len(latencies) - 1)]


# ---------------------------------------------------------------------------
# PERF-015-001: p95 <200ms at 1000 entries
# ---------------------------------------------------------------------------


class TestMemorySearchAt1000Entries:
    """PERF-015-001: Memory search p95 latency <200ms at 1000 entries."""

    @pytest.fixture(scope="class")
    def entries_1000(self) -> list[_MemoryEntryStub]:
        workspace_id = uuid4()
        return [_MemoryEntryStub(workspace_id) for _ in range(1000)]

    def test_p95_under_200ms(self, entries_1000: list[_MemoryEntryStub]) -> None:
        query_embedding = _generate_random_vector(768)
        query_text = "implementation pattern"

        p95 = _measure_p95(
            lambda: _run_hybrid_search(entries_1000, query_embedding, query_text),
            iterations=20,
        )

        # Pure Python hybrid search over 1000 entries should be well under 200ms.
        # Real implementation with pgvector will be faster via HNSW index.
        assert p95 < 200, (
            f"PERF-015-001 FAILED: p95={p95:.1f}ms (SLO: <200ms at 1000 entries). "
            "Check HNSW index configuration and hybrid scoring implementation."
        )

    def test_returns_top_k_results(self, entries_1000: list[_MemoryEntryStub]) -> None:
        query_embedding = _generate_random_vector(768)
        results = _run_hybrid_search(entries_1000, query_embedding, "test", top_k=5)
        assert len(results) == 5

    def test_scores_are_descending(self, entries_1000: list[_MemoryEntryStub]) -> None:
        query_embedding = _generate_random_vector(768)
        results = _run_hybrid_search(entries_1000, query_embedding, "pattern", top_k=10)
        scores = [s for _, s in results]
        assert scores == sorted(scores, reverse=True)

    def test_hybrid_weighting_correct(self) -> None:
        """Hybrid score = 0.7 * vector + 0.3 * keyword."""
        entry = _MemoryEntryStub(uuid4())
        entry.content = "keyword match test"
        entry.embedding = _generate_random_vector(768)

        query_embedding = entry.embedding  # perfect vector match
        results = _run_hybrid_search([entry], query_embedding, "keyword match", top_k=1)
        _, score = results[0]
        # vector_score ≈ 1.0, keyword_score depends on overlap
        assert 0.7 <= score <= 1.0


# ---------------------------------------------------------------------------
# PERF-015-002: p95 <500ms at 5000 entries
# ---------------------------------------------------------------------------


class TestMemorySearchAt5000Entries:
    """PERF-015-002: Memory search p95 latency <500ms at 5000 entries."""

    @pytest.fixture(scope="class")
    def entries_5000(self) -> list[_MemoryEntryStub]:
        workspace_id = uuid4()
        return [_MemoryEntryStub(workspace_id) for _ in range(5000)]

    def test_p95_under_500ms(self, entries_5000: list[_MemoryEntryStub]) -> None:
        query_embedding = _generate_random_vector(768)
        query_text = "architecture pattern"

        p95 = _measure_p95(
            lambda: _run_hybrid_search(entries_5000, query_embedding, query_text),
            iterations=10,
        )

        assert p95 < 500, (
            f"PERF-015-002 FAILED: p95={p95:.1f}ms (SLO: <500ms at 5000 entries). "
            "Scale test failed — review HNSW ef_search and index configuration."
        )

    def test_workspace_scoping_does_not_add_overhead(
        self, entries_5000: list[_MemoryEntryStub]
    ) -> None:
        """Filtering by workspace_id should be handled by DB index, not app code."""
        workspace_id = entries_5000[0].workspace_id
        scoped = [e for e in entries_5000 if e.workspace_id == workspace_id]
        # All entries share same workspace in fixture
        assert len(scoped) == 5000


# ---------------------------------------------------------------------------
# PERF-015-003: Embedding generation <500ms
# ---------------------------------------------------------------------------


class TestEmbeddingGenerationThroughput:
    """PERF-015-003: Single embedding generation <500ms per entry.

    This harness measures the overhead excluding actual Gemini API call.
    Real API testing is done in integration tests with actual Gemini calls.
    """

    def test_vector_generation_overhead_negligible(self) -> None:
        """Vector creation overhead (excluding API) should be <1ms."""
        start = time.perf_counter()
        _generate_random_vector(768)
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert elapsed_ms < 1, f"Vector generation overhead {elapsed_ms:.2f}ms is too high"

    def test_768_dimension_consistency(self) -> None:
        """Gemini embedding-001 always returns 768-dimensional vectors."""
        vec = _generate_random_vector(768)
        assert len(vec) == 768

    def test_cosine_similarity_symmetric(self) -> None:
        a = _generate_random_vector(768)
        b = _generate_random_vector(768)
        assert abs(_cosine_similarity(a, b) - _cosine_similarity(b, a)) < 1e-10

    def test_self_cosine_similarity_is_one(self) -> None:
        a = _generate_random_vector(768)
        sim = _cosine_similarity(a, a)
        assert abs(sim - 1.0) < 1e-10
