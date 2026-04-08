"""Update Cycle service.

Handles cycle updates with status transitions and validation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from pilot_space.domain.exceptions import ConflictError, NotFoundError, ValidationError
from pilot_space.infrastructure.database.models import Cycle, CycleStatus
from pilot_space.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from pilot_space.infrastructure.database.repositories import CycleRepository
    from pilot_space.infrastructure.database.repositories.audit_log_repository import (
        AuditLogRepository,
    )
    from pilot_space.infrastructure.queue.supabase_queue import SupabaseQueueClient

logger = get_logger(__name__)

# Sentinel for unchanged fields
UNCHANGED: Any = object()


@dataclass
class UpdateCyclePayload:
    """Payload for updating a cycle.

    Use UNCHANGED for fields that should not be modified.

    Attributes:
        cycle_id: Cycle UUID to update.
        actor_id: User performing the update.
        name: New name.
        description: New description.
        start_date: New start date.
        end_date: New end date.
        status: New status.
        owned_by_id: New owner.
    """

    cycle_id: UUID
    actor_id: UUID
    name: Any = UNCHANGED
    description: Any = UNCHANGED
    start_date: Any = UNCHANGED
    end_date: Any = UNCHANGED
    status: Any = UNCHANGED
    owned_by_id: Any = UNCHANGED


@dataclass
class UpdateCycleResult:
    """Result from cycle update."""

    cycle: Cycle
    updated_fields: list[str]


class UpdateCycleService:
    """Service for updating cycles.

    Handles:
    - Field updates with validation
    - Status transitions
    - Automatic deactivation of other cycles on activation
    """

    def __init__(
        self,
        session: AsyncSession,
        cycle_repository: CycleRepository,
        queue: SupabaseQueueClient | None = None,
        audit_log_repository: AuditLogRepository | None = None,
    ) -> None:
        """Initialize service.

        Args:
            session: Async database session.
            cycle_repository: Cycle repository.
            queue: Optional queue client for KG population.
            audit_log_repository: Optional audit log repository for compliance writes.
        """
        self._session = session
        self._cycle_repo = cycle_repository
        self._queue = queue
        self._audit_repo = audit_log_repository

    async def execute(self, payload: UpdateCyclePayload) -> UpdateCycleResult:
        """Update a cycle.

        Args:
            payload: Update parameters.

        Returns:
            UpdateCycleResult with updated cycle.

        Raises:
            ValueError: If cycle not found or validation fails.
        """
        cycle = await self._cycle_repo.get_by_id_with_relations(payload.cycle_id)
        if not cycle:
            raise NotFoundError(f"Cycle not found: {payload.cycle_id}")

        updated_fields: list[str] = []

        # Update name
        if payload.name is not UNCHANGED:
            if payload.name and payload.name.strip():
                if len(payload.name) > 255:
                    raise ValidationError("Cycle name must be 255 characters or less")
                cycle.name = payload.name.strip()
                updated_fields.append("name")
            else:
                raise ValidationError("Cycle name cannot be empty")

        # Update description
        if payload.description is not UNCHANGED:
            cycle.description = payload.description
            updated_fields.append("description")

        # Update dates
        if payload.start_date is not UNCHANGED:
            cycle.start_date = payload.start_date
            updated_fields.append("start_date")

        if payload.end_date is not UNCHANGED:
            cycle.end_date = payload.end_date
            updated_fields.append("end_date")

        # Validate dates after update
        start = payload.start_date if payload.start_date is not UNCHANGED else cycle.start_date
        end = payload.end_date if payload.end_date is not UNCHANGED else cycle.end_date
        if start and end and end < start:
            raise ValidationError("End date must be after start date")

        # Update owner
        if payload.owned_by_id is not UNCHANGED:
            cycle.owned_by_id = payload.owned_by_id
            updated_fields.append("owned_by_id")

        # Update status with transition logic
        if payload.status is not UNCHANGED:
            old_status = cycle.status
            new_status = payload.status

            # Validate status transition
            self._validate_status_transition(old_status, new_status)

            # If activating, deactivate other cycles
            if new_status == CycleStatus.ACTIVE and old_status != CycleStatus.ACTIVE:
                await self._cycle_repo.deactivate_project_cycles(
                    cycle.project_id,
                    exclude_cycle_id=cycle.id,
                )

            cycle.status = new_status
            updated_fields.append("status")

        await self._cycle_repo.update(cycle)

        # Reload with relationships
        cycle = await self._cycle_repo.get_by_id_with_relations(cycle.id)

        logger.info(
            "Cycle updated",
            extra={
                "cycle_id": str(payload.cycle_id),
                "updated_fields": updated_fields,
            },
        )

        # Enqueue KG populate on content-relevant changes (non-fatal)
        kg_relevant_fields = {"name", "description", "status", "start_date", "end_date"}
        if (
            self._queue is not None
            and cycle is not None
            and kg_relevant_fields & set(updated_fields)
        ):
            try:
                from pilot_space.infrastructure.queue.models import QueueName

                await self._queue.enqueue(
                    QueueName.AI_NORMAL,
                    {
                        "task_type": "kg_populate",
                        "entity_type": "cycle",
                        "entity_id": str(cycle.id),
                        "workspace_id": str(cycle.workspace_id),
                        "actor_user_id": str(payload.actor_id),
                        "project_id": str(cycle.project_id),
                    },
                )
            except Exception as exc:
                logger.warning("UpdateCycleService: failed to enqueue kg_populate: %s", exc)

        # Write audit log entry (non-fatal)
        if self._audit_repo is not None and cycle is not None and updated_fields:
            try:
                from pilot_space.infrastructure.database.models.audit_log import ActorType

                await self._audit_repo.create(
                    workspace_id=cycle.workspace_id,
                    actor_id=payload.actor_id,
                    actor_type=ActorType.USER,
                    action="cycle.update",
                    resource_type="cycle",
                    resource_id=cycle.id,
                    payload={"changed_fields": updated_fields},
                    ip_address=None,
                )
            except Exception as exc:
                logger.warning("UpdateCycleService: failed to write audit log: %s", exc)

        return UpdateCycleResult(
            cycle=cycle,  # type: ignore[arg-type]
            updated_fields=updated_fields,
        )

    def _validate_status_transition(
        self,
        current: CycleStatus,
        target: CycleStatus,
    ) -> None:
        """Validate status transition is allowed.

        Valid transitions:
        - DRAFT -> PLANNED, ACTIVE, CANCELLED
        - PLANNED -> ACTIVE, CANCELLED
        - ACTIVE -> COMPLETED, CANCELLED
        - COMPLETED -> (none, final state)
        - CANCELLED -> (none, final state)

        Args:
            current: Current status.
            target: Target status.

        Raises:
            ValueError: If transition is not allowed.
        """
        if current == target:
            return  # No change

        valid_transitions: dict[CycleStatus, set[CycleStatus]] = {
            CycleStatus.DRAFT: {
                CycleStatus.PLANNED,
                CycleStatus.ACTIVE,
                CycleStatus.CANCELLED,
            },
            CycleStatus.PLANNED: {CycleStatus.ACTIVE, CycleStatus.CANCELLED},
            CycleStatus.ACTIVE: {CycleStatus.COMPLETED, CycleStatus.CANCELLED},
            CycleStatus.COMPLETED: set(),
            CycleStatus.CANCELLED: set(),
        }

        if target not in valid_transitions.get(current, set()):
            raise ConflictError(f"Invalid status transition: {current.value} -> {target.value}")


__all__ = ["UNCHANGED", "UpdateCyclePayload", "UpdateCycleResult", "UpdateCycleService"]
