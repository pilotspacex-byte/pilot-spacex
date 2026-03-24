"""IntentService: lifecycle management for WorkIntents.

T-011: confirmAll with cap=10, C-8 dedup gate
T-005: Confirm, reject, edit single intent operations

Feature 015: AI Workforce Platform (M2)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any
from uuid import UUID

from pilot_space.domain.exceptions import ForbiddenError, NotFoundError, ValidationError
from pilot_space.domain.work_intent import DedupStatus, IntentStatus, WorkIntent
from pilot_space.infrastructure.database.models.work_intent import (
    WorkIntent as WorkIntentModel,
)
from pilot_space.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from pilot_space.infrastructure.database.repositories.intent_repository import (
        WorkIntentRepository,
    )

logger = get_logger(__name__)

# ConfirmAll limits per T-011
_CONFIRM_ALL_MIN_CONFIDENCE = 0.7
_CONFIRM_ALL_MAX_COUNT = 10


@dataclass(frozen=True, slots=True)
class ConfirmIntentPayload:
    """Payload for confirming a single intent."""

    intent_id: UUID
    workspace_id: UUID


@dataclass(frozen=True, slots=True)
class RejectIntentPayload:
    """Payload for rejecting a single intent."""

    intent_id: UUID
    workspace_id: UUID


@dataclass(frozen=True, slots=True)
class EditIntentPayload:
    """Payload for editing a detected intent (before confirmation)."""

    intent_id: UUID
    workspace_id: UUID
    new_what: str | None = None
    new_why: str | None = None
    new_constraints: list[Any] | None = None
    new_acceptance: list[Any] | None = None


@dataclass(frozen=True, slots=True)
class ConfirmAllPayload:
    """Payload for batch confirmation of top-N detected intents."""

    workspace_id: UUID
    min_confidence: float = _CONFIRM_ALL_MIN_CONFIDENCE
    max_count: int = _CONFIRM_ALL_MAX_COUNT


@dataclass
class ConfirmAllResult:
    """Result from confirmAll operation.

    Attributes:
        confirmed: Intents that were confirmed.
        remaining_count: Number of detected intents still pending.
        deduplicating_count: Intents excluded because dedup_status=pending.
    """

    confirmed: list[WorkIntentModel]
    remaining_count: int
    deduplicating_count: int


def _model_to_domain(model: WorkIntentModel) -> WorkIntent:
    """Convert ORM model to domain entity."""
    return WorkIntent(
        id=model.id,
        workspace_id=model.workspace_id,
        what=model.what,
        why=model.why,
        constraints=model.constraints,
        acceptance=model.acceptance,
        confidence=model.confidence,
        status=IntentStatus(model.status.value),
        dedup_status=DedupStatus(model.dedup_status.value),
        source_block_id=model.source_block_id,
        owner=model.owner,
        parent_intent_id=model.parent_intent_id,
        dedup_hash=model.dedup_hash,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


class IntentService:
    """Manages WorkIntent lifecycle: confirm, reject, edit, confirmAll.

    Implements T-011 confirmAll with C-8 dedup gate:
    - Only confirms intents where dedup_status='complete'
    - Caps at max_count (default 10) per call
    - Returns deduplicating_count for UI feedback
    """

    def __init__(
        self,
        session: AsyncSession,
        intent_repository: WorkIntentRepository,
    ) -> None:
        self._session = session
        self._intent_repo = intent_repository

    async def confirm(self, payload: ConfirmIntentPayload) -> WorkIntentModel:
        """Confirm a single detected intent.

        Args:
            payload: Intent ID and workspace validation.

        Returns:
            Updated WorkIntent ORM model.

        Raises:
            ValueError: If intent not found, workspace mismatch, or invalid transition.
        """
        intent = await self._intent_repo.get_by_id(payload.intent_id)
        if intent is None:
            msg = f"Intent {payload.intent_id} not found"
            raise NotFoundError(msg)
        if intent.workspace_id != payload.workspace_id:
            msg = "Intent does not belong to workspace"
            raise ForbiddenError(msg)

        # Apply domain transition
        domain = _model_to_domain(intent)
        domain.confirm()  # Raises ValueError for invalid transitions

        intent.status = domain.status  # type: ignore[assignment]

        updated = await self._intent_repo.update(intent)
        await self._session.flush()

        logger.info(
            "Intent confirmed",
            extra={"intent_id": str(payload.intent_id)},
        )
        return updated

    async def reject(self, payload: RejectIntentPayload) -> WorkIntentModel:
        """Reject an intent from any non-terminal state.

        Args:
            payload: Intent ID and workspace validation.

        Returns:
            Updated WorkIntent ORM model.

        Raises:
            ValueError: If intent not found, workspace mismatch, or terminal.
        """
        intent = await self._intent_repo.get_by_id(payload.intent_id)
        if intent is None:
            msg = f"Intent {payload.intent_id} not found"
            raise NotFoundError(msg)
        if intent.workspace_id != payload.workspace_id:
            msg = "Intent does not belong to workspace"
            raise ForbiddenError(msg)

        domain = _model_to_domain(intent)
        domain.reject()

        intent.status = domain.status  # type: ignore[assignment]
        updated = await self._intent_repo.update(intent)
        await self._session.flush()

        logger.info(
            "Intent rejected",
            extra={"intent_id": str(payload.intent_id)},
        )
        return updated

    async def edit(self, payload: EditIntentPayload) -> WorkIntentModel:
        """Edit an intent that is still in DETECTED status.

        Updates what/why fields and recomputes dedup hash.

        Args:
            payload: Edit parameters.

        Returns:
            Updated WorkIntent ORM model.

        Raises:
            ValueError: If intent not found, workspace mismatch, or not mutable.
        """
        intent = await self._intent_repo.get_by_id(payload.intent_id)
        if intent is None:
            msg = f"Intent {payload.intent_id} not found"
            raise NotFoundError(msg)
        if intent.workspace_id != payload.workspace_id:
            msg = "Intent does not belong to workspace"
            raise ForbiddenError(msg)

        domain = _model_to_domain(intent)

        if payload.new_what is not None:
            domain.update_what(payload.new_what)
            intent.what = domain.what
            intent.dedup_hash = domain.dedup_hash
            # Reset dedup_status so J-1 re-processes
            from pilot_space.infrastructure.database.models.work_intent import (
                DedupStatus as DBDedupStatus,
            )

            intent.dedup_status = DBDedupStatus.PENDING  # type: ignore[assignment]

        if payload.new_why is not None:
            domain.update_why(payload.new_why)
            intent.why = domain.why

        if payload.new_constraints is not None:
            if not domain.is_mutable:
                msg = f"Cannot update constraints after status is {domain.status.value!r}"
                raise ValidationError(msg)
            intent.constraints = payload.new_constraints

        if payload.new_acceptance is not None:
            if not domain.is_mutable:
                msg = f"Cannot update acceptance after status is {domain.status.value!r}"
                raise ValidationError(msg)
            intent.acceptance = payload.new_acceptance

        updated = await self._intent_repo.update(intent)
        await self._session.flush()

        logger.info(
            "Intent edited",
            extra={"intent_id": str(payload.intent_id)},
        )
        return updated

    async def confirm_all(self, payload: ConfirmAllPayload) -> ConfirmAllResult:
        """Confirm top-N detected intents by confidence.

        C-8: Only confirms intents where dedup_status='complete'.
        Intents with dedup_status='pending' are excluded and reported
        as deduplicating_count.

        Args:
            payload: Workspace + confidence threshold + max count.

        Returns:
            ConfirmAllResult with confirmed list, remaining count, deduplicating count.
        """
        min_confidence = max(0.0, min(1.0, payload.min_confidence))
        max_count = max(1, min(payload.max_count, _CONFIRM_ALL_MAX_COUNT))

        # Fetch all detected intents for workspace
        all_detected = await self._intent_repo.list_by_workspace_and_status(
            payload.workspace_id,
            IntentStatus.DETECTED,
        )

        # Filter by confidence
        above_threshold = [i for i in all_detected if i.confidence >= min_confidence]

        # C-8: Split by dedup_status
        from pilot_space.infrastructure.database.models.work_intent import (
            DedupStatus as DBDedupStatus,
        )

        dedup_complete = [i for i in above_threshold if i.dedup_status == DBDedupStatus.COMPLETE]
        dedup_pending = [i for i in above_threshold if i.dedup_status == DBDedupStatus.PENDING]

        # Sort complete by confidence desc, take top N
        dedup_complete.sort(key=lambda x: (-x.confidence, x.created_at))
        to_confirm = dedup_complete[:max_count]

        confirmed: list[WorkIntentModel] = []
        for intent in to_confirm:
            domain = _model_to_domain(intent)
            try:
                domain.confirm()
                intent.status = domain.status  # type: ignore[assignment]
                updated = await self._intent_repo.update(intent)
                confirmed.append(updated)
            except ValueError:
                logger.warning(
                    "Could not confirm intent during confirmAll",
                    extra={"intent_id": str(intent.id)},
                )

        await self._session.flush()

        # Remaining = all detected minus what we just confirmed
        remaining_count = len(all_detected) - len(confirmed)
        deduplicating_count = len(dedup_pending)

        logger.info(
            "ConfirmAll complete",
            extra={
                "workspace_id": str(payload.workspace_id),
                "confirmed": len(confirmed),
                "remaining": remaining_count,
                "deduplicating": deduplicating_count,
            },
        )

        return ConfirmAllResult(
            confirmed=confirmed,
            remaining_count=remaining_count,
            deduplicating_count=deduplicating_count,
        )

    async def get_intent(self, intent_id: UUID, workspace_id: UUID) -> WorkIntentModel:
        """Fetch a single intent by ID, scoped to workspace.

        Args:
            intent_id: Intent UUID.
            workspace_id: Workspace UUID for RLS validation.

        Returns:
            WorkIntent ORM model.

        Raises:
            ValueError: If not found or workspace mismatch.
        """
        intent = await self._intent_repo.get_by_id(intent_id)
        if intent is None:
            msg = f"Intent {intent_id} not found"
            raise NotFoundError(msg)
        if intent.workspace_id != workspace_id:
            msg = "Intent does not belong to workspace"
            raise ForbiddenError(msg)
        return intent

    async def list_by_status(
        self,
        workspace_id: UUID,
        status: IntentStatus,
    ) -> list[WorkIntentModel]:
        """List intents for a workspace filtered by status.

        Args:
            workspace_id: Workspace UUID.
            status: Status filter.

        Returns:
            List of WorkIntent ORM models.
        """
        results = await self._intent_repo.list_by_workspace_and_status(
            workspace_id,
            status,
        )
        return list(results)
