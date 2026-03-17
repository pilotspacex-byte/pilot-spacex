"""Unit tests for GetCycleService.get_velocity_chart."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from pilot_space.application.services.cycle.get_cycle_service import (
    GetCycleService,
)
from pilot_space.infrastructure.database.repositories.cycle_repository import (
    CycleMetrics,
)

pytestmark = pytest.mark.asyncio

_PROJECT_ID = uuid4()
_WORKSPACE_ID = uuid4()


def _make_cycle(name: str, sequence: int) -> MagicMock:
    cycle = MagicMock()
    cycle.id = uuid4()
    cycle.name = name
    cycle.sequence = sequence
    return cycle


def _make_metrics(
    cycle_id: object, completed_points: int, total_points: int, velocity: float
) -> CycleMetrics:
    return CycleMetrics(
        cycle_id=cycle_id,  # type: ignore[arg-type]
        total_issues=10,
        completed_issues=5,
        in_progress_issues=3,
        not_started_issues=2,
        total_points=total_points,
        completed_points=completed_points,
        completion_percentage=50.0,
        velocity=velocity,
    )


class TestGetVelocityChart:
    async def test_returns_empty_when_no_completed_cycles(self) -> None:
        repo = AsyncMock()
        repo.get_completed_cycles_with_metrics = AsyncMock(return_value=[])

        service = GetCycleService(cycle_repository=repo)
        result = await service.get_velocity_chart(_PROJECT_ID, _WORKSPACE_ID)

        assert result.project_id == _PROJECT_ID
        assert result.data_points == []
        assert result.average_velocity == 0.0

    async def test_returns_data_points_in_chronological_order(self) -> None:
        """Repository returns newest first; service should reverse to chronological."""
        cycle_old = _make_cycle("Sprint 1", 1)
        cycle_new = _make_cycle("Sprint 2", 2)

        metrics_old = _make_metrics(
            cycle_old.id, completed_points=10, total_points=15, velocity=2.0
        )
        metrics_new = _make_metrics(
            cycle_new.id, completed_points=20, total_points=25, velocity=4.0
        )

        # Repo returns newest first (desc sequence)
        repo = AsyncMock()
        repo.get_completed_cycles_with_metrics = AsyncMock(
            return_value=[(cycle_new, metrics_new), (cycle_old, metrics_old)]
        )

        service = GetCycleService(cycle_repository=repo)
        result = await service.get_velocity_chart(_PROJECT_ID, _WORKSPACE_ID, limit=10)

        assert len(result.data_points) == 2
        # Should be chronological: Sprint 1 first
        assert result.data_points[0].cycle_name == "Sprint 1"
        assert result.data_points[0].completed_points == 10
        assert result.data_points[0].velocity == 2.0
        assert result.data_points[1].cycle_name == "Sprint 2"
        assert result.data_points[1].completed_points == 20
        assert result.data_points[1].velocity == 4.0

    async def test_calculates_average_velocity(self) -> None:
        cycle1 = _make_cycle("Sprint 1", 1)
        cycle2 = _make_cycle("Sprint 2", 2)

        metrics1 = _make_metrics(cycle1.id, completed_points=10, total_points=15, velocity=2.0)
        metrics2 = _make_metrics(cycle2.id, completed_points=20, total_points=25, velocity=6.0)

        repo = AsyncMock()
        repo.get_completed_cycles_with_metrics = AsyncMock(
            return_value=[(cycle2, metrics2), (cycle1, metrics1)]
        )

        service = GetCycleService(cycle_repository=repo)
        result = await service.get_velocity_chart(_PROJECT_ID, _WORKSPACE_ID)

        assert result.average_velocity == pytest.approx(4.0)

    async def test_passes_limit_to_repository(self) -> None:
        repo = AsyncMock()
        repo.get_completed_cycles_with_metrics = AsyncMock(return_value=[])

        service = GetCycleService(cycle_repository=repo)
        await service.get_velocity_chart(_PROJECT_ID, _WORKSPACE_ID, limit=5)

        repo.get_completed_cycles_with_metrics.assert_called_once_with(
            _PROJECT_ID, _WORKSPACE_ID, limit=5
        )

    async def test_passes_workspace_id_to_repository(self) -> None:
        """workspace_id must be forwarded to the repository for tenant isolation."""
        other_workspace = uuid4()
        repo = AsyncMock()
        repo.get_completed_cycles_with_metrics = AsyncMock(return_value=[])

        service = GetCycleService(cycle_repository=repo)
        await service.get_velocity_chart(_PROJECT_ID, other_workspace, limit=10)

        repo.get_completed_cycles_with_metrics.assert_called_once_with(
            _PROJECT_ID, other_workspace, limit=10
        )

    async def test_workspace_scoping_isolates_separate_workspaces(self) -> None:
        """Calls with different workspace_ids must pass distinct values to the repository."""
        workspace_a = uuid4()
        workspace_b = uuid4()

        repo = AsyncMock()
        repo.get_completed_cycles_with_metrics = AsyncMock(return_value=[])

        service = GetCycleService(cycle_repository=repo)

        await service.get_velocity_chart(_PROJECT_ID, workspace_a)
        await service.get_velocity_chart(_PROJECT_ID, workspace_b)

        calls = repo.get_completed_cycles_with_metrics.call_args_list
        assert calls[0].args[1] == workspace_a
        assert calls[1].args[1] == workspace_b
        assert calls[0].args[1] != calls[1].args[1]
