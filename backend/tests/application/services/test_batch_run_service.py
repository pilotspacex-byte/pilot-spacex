"""Unit tests for BatchRunService and kahn_topological_sort.

Tests focus on the pure topological sort algorithm (no DB needed) and
service-level behaviour using mocked repositories.

Phase 76 Plan 01 — sprint batch implementation foundation.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from pilot_space.application.services.batch_run_service import (
    BatchRunService,
    CreateBatchRunPayload,
    kahn_topological_sort,
)
from pilot_space.domain.exceptions import (
    BatchRunCycleDetectedError,
    BatchRunError,
)
from pilot_space.infrastructure.database.models.batch_run_issue import BatchRunIssueStatus


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_uuid(n: int) -> UUID:
    """Return a deterministic UUID for test readability."""
    return UUID(f"00000000-0000-0000-0000-{n:012d}")


A = make_uuid(1)
B = make_uuid(2)
C = make_uuid(3)
D = make_uuid(4)
E = make_uuid(5)


# ---------------------------------------------------------------------------
# Pure unit tests: kahn_topological_sort
# ---------------------------------------------------------------------------


class TestKahnTopologicalSort:
    """Tests for the pure kahn_topological_sort function.

    No DB or async required — these exercise the algorithm only.
    """

    def test_kahn_sort_linear_chain(self) -> None:
        """A → B → C gives {A:0, B:1, C:2} with no cycle."""
        order, cycles = kahn_topological_sort(
            [A, B, C],
            [(A, B), (B, C)],
        )
        assert cycles == []
        assert order[A] == 0
        assert order[B] == 1
        assert order[C] == 2

    def test_kahn_sort_parallel_tracks(self) -> None:
        """A → C, B → C gives {A:0, B:0, C:1}."""
        order, cycles = kahn_topological_sort(
            [A, B, C],
            [(A, C), (B, C)],
        )
        assert cycles == []
        assert order[A] == 0
        assert order[B] == 0
        assert order[C] == 1

    def test_kahn_sort_no_deps(self) -> None:
        """With no edges, all issues get wave 0."""
        order, cycles = kahn_topological_sort([A, B, C], [])
        assert cycles == []
        assert order[A] == 0
        assert order[B] == 0
        assert order[C] == 0

    def test_kahn_sort_cycle_detection_simple(self) -> None:
        """A → B → A is a cycle; cycle_issues is non-empty."""
        order, cycles = kahn_topological_sort(
            [A, B],
            [(A, B), (B, A)],
        )
        assert len(cycles) == 2
        assert set(cycles) == {A, B}
        # execution_order_map is empty on cycle detection
        assert order == {}

    def test_kahn_sort_cycle_detection_three_node_cycle(self) -> None:
        """A → B → C → A is a cycle."""
        order, cycles = kahn_topological_sort(
            [A, B, C],
            [(A, B), (B, C), (C, A)],
        )
        assert set(cycles) == {A, B, C}
        assert order == {}

    def test_kahn_sort_mixed_deps_and_independent(self) -> None:
        """D is independent; A → B → C are chained; D gets wave 0."""
        order, cycles = kahn_topological_sort(
            [A, B, C, D],
            [(A, B), (A, C)],
        )
        assert cycles == []
        assert order[A] == 0
        assert order[D] == 0
        assert order[B] == 1
        assert order[C] == 1

    def test_kahn_sort_diamond_dependency(self) -> None:
        """Diamond: A → B, A → C, B → D, C → D."""
        order, cycles = kahn_topological_sort(
            [A, B, C, D],
            [(A, B), (A, C), (B, D), (C, D)],
        )
        assert cycles == []
        assert order[A] == 0
        assert order[B] == 1
        assert order[C] == 1
        assert order[D] == 2

    def test_kahn_sort_single_node_no_deps(self) -> None:
        """A single issue with no links gets wave 0."""
        order, cycles = kahn_topological_sort([A], [])
        assert cycles == []
        assert order[A] == 0

    def test_kahn_sort_ignores_out_of_scope_edges(self) -> None:
        """Edges where either endpoint is not in issue_ids are ignored."""
        unknown = uuid4()
        order, cycles = kahn_topological_sort(
            [A, B],
            [(A, B), (unknown, A), (B, unknown)],
        )
        assert cycles == []
        assert order[A] == 0
        assert order[B] == 1

    def test_kahn_sort_partial_cycle_isolated_node(self) -> None:
        """A → B → A cycle; C is independent and NOT in cycle_issues."""
        order, cycles = kahn_topological_sort(
            [A, B, C],
            [(A, B), (B, A)],
        )
        # C has no deps so it should complete
        assert C not in cycles
        assert set(cycles) == {A, B}


# ---------------------------------------------------------------------------
# Service-level tests (mocked repository + session)
# ---------------------------------------------------------------------------


class TestBatchRunServiceCancelCascade:
    """Tests for cancel_batch_run cascade behaviour."""

    @pytest.mark.asyncio
    async def test_cancel_batch_run_calls_cancel_pending(self) -> None:
        """cancel_batch_run calls cancel_pending_issues on the repository."""
        session = AsyncMock()
        service = BatchRunService(session)

        # Build a minimal fake BatchRun
        fake_run = MagicMock()
        fake_run.id = uuid4()

        # Patch the repository used inside the service
        with patch.object(service, "_repo") as mock_repo:
            mock_repo.get_by_id_with_items = AsyncMock(return_value=fake_run)
            mock_repo.cancel_pending_issues = AsyncMock(return_value=3)
            mock_repo.update_batch_run_status = AsyncMock()

            await service.cancel_batch_run(fake_run.id)

            mock_repo.cancel_pending_issues.assert_awaited_once_with(fake_run.id)
            mock_repo.update_batch_run_status.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_cancel_batch_run_raises_not_found(self) -> None:
        """cancel_batch_run raises BatchRunNotFoundError when run is missing."""
        from pilot_space.domain.exceptions import BatchRunNotFoundError

        session = AsyncMock()
        service = BatchRunService(session)

        with patch.object(service, "_repo") as mock_repo:
            mock_repo.get_by_id_with_items = AsyncMock(return_value=None)

            with pytest.raises(BatchRunNotFoundError):
                await service.cancel_batch_run(uuid4())

    @pytest.mark.asyncio
    async def test_cancel_issue_delegates_to_repo(self) -> None:
        """cancel_issue calls update_issue_status with CANCELLED status."""
        session = AsyncMock()
        service = BatchRunService(session)
        issue_id = uuid4()

        with patch.object(service, "_repo") as mock_repo:
            mock_repo.update_issue_status = AsyncMock(return_value=None)

            await service.cancel_issue(issue_id)

            mock_repo.update_issue_status.assert_awaited_once_with(
                issue_id,
                BatchRunIssueStatus.CANCELLED,
            )


class TestCreateBatchRunValidation:
    """Tests for create_batch_run domain validation errors."""

    @pytest.mark.asyncio
    async def test_create_batch_run_raises_on_empty_cycle(self) -> None:
        """create_batch_run raises BatchRunError when cycle has no issues."""
        session = AsyncMock()
        service = BatchRunService(session)

        # Patch _load_cycle_issues to return empty list
        service._load_cycle_issues = AsyncMock(return_value=[])  # type: ignore[method-assign]
        service._load_blocks_links = AsyncMock(return_value=[])  # type: ignore[method-assign]

        payload = CreateBatchRunPayload(
            workspace_id=uuid4(),
            cycle_id=uuid4(),
            triggered_by_id=uuid4(),
        )
        with pytest.raises(BatchRunError):
            await service.create_batch_run(payload)

    @pytest.mark.asyncio
    async def test_create_batch_run_raises_on_cycle_detected(self) -> None:
        """create_batch_run raises BatchRunCycleDetectedError on cyclic deps."""
        session = AsyncMock()
        service = BatchRunService(session)

        # Two fake issues
        issue_a = MagicMock()
        issue_a.id = A
        issue_b = MagicMock()
        issue_b.id = B

        service._load_cycle_issues = AsyncMock(return_value=[issue_a, issue_b])  # type: ignore[method-assign]
        # Circular: A blocks B, B blocks A
        service._load_blocks_links = AsyncMock(return_value=[(A, B), (B, A)])  # type: ignore[method-assign]

        payload = CreateBatchRunPayload(
            workspace_id=uuid4(),
            cycle_id=uuid4(),
            triggered_by_id=uuid4(),
        )
        with pytest.raises(BatchRunCycleDetectedError):
            await service.create_batch_run(payload)
