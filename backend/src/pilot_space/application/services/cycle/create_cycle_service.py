"""Create Cycle service.

T158: Create CreateCycleService with payload validation.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING

from pilot_space.infrastructure.database.models import Cycle, CycleStatus

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from pilot_space.infrastructure.database.repositories import CycleRepository

logger = logging.getLogger(__name__)


@dataclass
class CreateCyclePayload:
    """Payload for creating a new cycle.

    Attributes:
        workspace_id: Workspace UUID.
        project_id: Project UUID.
        name: Cycle name (e.g., "Sprint 1").
        description: Optional cycle description.
        start_date: Cycle start date.
        end_date: Cycle end date.
        owned_by_id: User who manages this cycle.
        status: Initial status (default: DRAFT).
    """

    workspace_id: UUID
    project_id: UUID
    name: str
    description: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    owned_by_id: UUID | None = None
    status: CycleStatus = CycleStatus.DRAFT


@dataclass
class CreateCycleResult:
    """Result from cycle creation."""

    cycle: Cycle
    created: bool = True


class CreateCycleService:
    """Service for creating cycles.

    Handles:
    - Cycle creation with sequence generation
    - Date validation (end_date must be after start_date)
    - Automatic deactivation of other cycles when activating
    """

    def __init__(
        self,
        session: AsyncSession,
        cycle_repository: CycleRepository,
    ) -> None:
        """Initialize service.

        Args:
            session: Async database session.
            cycle_repository: Cycle repository.
        """
        self._session = session
        self._cycle_repo = cycle_repository

    async def execute(self, payload: CreateCyclePayload) -> CreateCycleResult:
        """Create a new cycle.

        Args:
            payload: Cycle creation parameters.

        Returns:
            CreateCycleResult with created cycle.

        Raises:
            ValueError: If validation fails.
        """
        logger.info(
            "Creating cycle",
            extra={
                "workspace_id": str(payload.workspace_id),
                "project_id": str(payload.project_id),
                "name": payload.name,
            },
        )

        # Validate name
        if not payload.name or not payload.name.strip():
            raise ValueError("Cycle name is required")
        if len(payload.name) > 255:
            raise ValueError("Cycle name must be 255 characters or less")

        # Validate dates
        if payload.start_date and payload.end_date:
            if payload.end_date < payload.start_date:
                raise ValueError("End date must be after start date")

        # Get next sequence for ordering
        sequence = await self._cycle_repo.get_next_sequence(payload.project_id)

        # If activating this cycle, deactivate others
        if payload.status == CycleStatus.ACTIVE:
            await self._cycle_repo.deactivate_project_cycles(payload.project_id)

        # Create cycle
        cycle = Cycle(
            workspace_id=payload.workspace_id,
            project_id=payload.project_id,
            name=payload.name.strip(),
            description=payload.description,
            start_date=payload.start_date,
            end_date=payload.end_date,
            status=payload.status,
            sequence=sequence,
            owned_by_id=payload.owned_by_id,
        )

        # Save cycle
        cycle = await self._cycle_repo.create(cycle)

        # Reload with relationships
        cycle = await self._cycle_repo.get_by_id_with_relations(cycle.id)

        logger.info(
            "Cycle created",
            extra={
                "cycle_id": str(cycle.id) if cycle else None,
                "name": cycle.name if cycle else None,
            },
        )

        return CreateCycleResult(
            cycle=cycle,  # type: ignore[arg-type]
            created=True,
        )


__all__ = ["CreateCyclePayload", "CreateCycleResult", "CreateCycleService"]
