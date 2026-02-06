"""UpdateOnboardingService for updating onboarding state.

Implements CQRS-lite command pattern for onboarding updates.

T012: Create OnboardingService (CQRS-lite).
Source: FR-002, FR-003, FR-013
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Literal
from uuid import UUID

from pilot_space.application.services.onboarding.types import OnboardingStepsResult

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


StepName = Literal["ai_providers", "invite_members", "first_note", "role_setup"]


@dataclass(frozen=True, slots=True)
class UpdateOnboardingPayload:
    """Payload for updating onboarding state.

    Attributes:
        workspace_id: The workspace ID.
        step: Optional step to update.
        completed: Step completion status (required if step provided).
        dismissed: Whether to dismiss the checklist.
    """

    workspace_id: UUID
    step: StepName | None = None
    completed: bool | None = None
    dismissed: bool | None = None


@dataclass(frozen=True, slots=True)
class UpdateOnboardingResult:
    """Result from updating onboarding state.

    Attributes:
        id: Onboarding record ID.
        workspace_id: Workspace ID.
        steps: Step completion status.
        guided_note_id: ID of guided note if created.
        dismissed_at: When checklist was dismissed.
        completed_at: When all steps were completed.
        completion_percentage: 0-100 percentage.
        just_completed: True if update triggered completion (for celebration).
        created_at: Record creation timestamp.
        updated_at: Record update timestamp.
    """

    id: UUID
    workspace_id: UUID
    steps: OnboardingStepsResult
    guided_note_id: UUID | None
    dismissed_at: datetime | None
    completed_at: datetime | None
    completion_percentage: int
    just_completed: bool
    created_at: datetime
    updated_at: datetime


class UpdateOnboardingService:
    """Service for updating onboarding state.

    Handles step completion and dismiss operations.
    Tracks when all steps complete for celebration trigger.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize UpdateOnboardingService.

        Args:
            session: The async database session.
        """
        self._session = session

    async def execute(
        self,
        payload: UpdateOnboardingPayload,
    ) -> UpdateOnboardingResult:
        """Execute onboarding state update.

        Args:
            payload: The update payload.

        Returns:
            UpdateOnboardingResult with updated state.

        Raises:
            ValueError: If validation fails.
        """
        from pilot_space.infrastructure.database.repositories.onboarding_repository import (
            OnboardingRepository,
        )

        repo = OnboardingRepository(self._session)

        # Get or create onboarding record
        onboarding = await repo.upsert_for_workspace(payload.workspace_id)

        was_complete = onboarding.is_complete
        just_completed = False

        # Update step if provided
        if payload.step is not None:
            if payload.completed is None:
                msg = "completed is required when step is provided"
                raise ValueError(msg)

            onboarding = await repo.update_step(
                workspace_id=payload.workspace_id,
                step_name=payload.step,
                completed=payload.completed,
            )

            # Check if this update completed all steps (FR-013)
            if not was_complete and onboarding and onboarding.is_complete:
                just_completed = True

        # Update dismissed state if provided
        if payload.dismissed is not None:
            onboarding = await repo.set_dismissed(
                workspace_id=payload.workspace_id,
                dismissed=payload.dismissed,
            )

        if not onboarding:
            msg = "Onboarding record not found"
            raise ValueError(msg)

        steps = onboarding.steps
        return UpdateOnboardingResult(
            id=onboarding.id,
            workspace_id=onboarding.workspace_id,
            steps=OnboardingStepsResult(
                ai_providers=steps.get("ai_providers", False),
                invite_members=steps.get("invite_members", False),
                first_note=steps.get("first_note", False),
                role_setup=steps.get("role_setup", False),
            ),
            guided_note_id=onboarding.guided_note_id,
            dismissed_at=onboarding.dismissed_at,
            completed_at=onboarding.completed_at,
            completion_percentage=onboarding.completion_percentage,
            just_completed=just_completed,
            created_at=onboarding.created_at,
            updated_at=onboarding.updated_at,
        )


__all__ = [
    "UpdateOnboardingPayload",
    "UpdateOnboardingResult",
    "UpdateOnboardingService",
]
