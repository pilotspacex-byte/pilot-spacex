"""GetOnboardingService for querying onboarding state.

Implements CQRS-lite query pattern for onboarding state retrieval.
Auto-syncs step completions by detecting actual workspace state.

T012: Create OnboardingService (CQRS-lite).
Source: FR-001, FR-002
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from pilot_space.application.services.onboarding.types import OnboardingStepsResult

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from pilot_space.infrastructure.database.models.onboarding import WorkspaceOnboarding
    from pilot_space.infrastructure.database.repositories.onboarding_repository import (
        OnboardingRepository,
    )

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class GetOnboardingResult:
    """Result from querying onboarding state.

    Attributes:
        id: Onboarding record ID.
        workspace_id: Workspace ID.
        steps: Step completion status.
        guided_note_id: ID of guided note if created.
        dismissed_at: When checklist was dismissed.
        completed_at: When all steps were completed.
        completion_percentage: 0-100 percentage.
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
    created_at: datetime
    updated_at: datetime


class GetOnboardingService:
    """Service for querying onboarding state.

    Handles onboarding state retrieval with auto-creation
    for new workspaces.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize GetOnboardingService.

        Args:
            session: The async database session.
        """
        self._session = session

    async def execute(
        self,
        workspace_id: UUID,
    ) -> GetOnboardingResult:
        """Execute onboarding state query.

        Auto-creates onboarding record if not exists.
        Auto-syncs step completions by checking actual workspace state.

        Args:
            workspace_id: The workspace UUID.

        Returns:
            GetOnboardingResult with current state.
        """
        from pilot_space.infrastructure.database.repositories.onboarding_repository import (
            OnboardingRepository,
        )

        repo = OnboardingRepository(self._session)

        # Get or create onboarding record
        onboarding = await repo.upsert_for_workspace(workspace_id)

        # Auto-sync: detect completed steps from actual workspace state
        await self._auto_sync_steps(repo, onboarding, workspace_id)

        steps = onboarding.steps
        return GetOnboardingResult(
            id=onboarding.id,
            workspace_id=onboarding.workspace_id,
            steps=OnboardingStepsResult(
                ai_providers=steps.get("ai_providers", False),
                invite_members=steps.get("invite_members", False),
                first_note=steps.get("first_note", False),
            ),
            guided_note_id=onboarding.guided_note_id,
            dismissed_at=onboarding.dismissed_at,
            completed_at=onboarding.completed_at,
            completion_percentage=onboarding.completion_percentage,
            created_at=onboarding.created_at,
            updated_at=onboarding.updated_at,
        )

    async def _auto_sync_steps(
        self,
        repo: OnboardingRepository,
        onboarding: WorkspaceOnboarding,
        workspace_id: UUID,
    ) -> None:
        """Auto-detect and persist step completions from workspace state.

        Checks actual workspace data (API keys, member count) and marks
        steps complete if the corresponding action was already performed
        outside the onboarding flow.

        Args:
            repo: OnboardingRepository instance.
            onboarding: Current WorkspaceOnboarding record.
            workspace_id: The workspace UUID.
        """
        from pilot_space.infrastructure.database.models.workspace_api_key import (
            WorkspaceAPIKey,
        )
        from pilot_space.infrastructure.database.models.workspace_member import (
            WorkspaceMember,
        )

        from sqlalchemy import func, select

        steps = onboarding.steps
        synced = False

        # Auto-detect ai_providers: check if any API key exists
        # Keys may be in workspace_api_keys (SecureKeyStorage) or ai_configurations
        if not steps.get("ai_providers", False):
            from pilot_space.infrastructure.database.models.ai_configuration import (
                AIConfiguration,
            )

            key_count = await self._session.scalar(
                select(func.count()).select_from(WorkspaceAPIKey).where(
                    WorkspaceAPIKey.workspace_id == workspace_id,
                )
            )
            if not key_count:
                key_count = await self._session.scalar(
                    select(func.count()).select_from(AIConfiguration).where(
                        AIConfiguration.workspace_id == workspace_id,
                        AIConfiguration.is_active == True,  # noqa: E712
                    )
                )
            if key_count and key_count > 0:
                await repo.update_step(workspace_id, "ai_providers", completed=True)
                synced = True

        # Auto-detect invite_members: check if workspace has >1 member
        if not steps.get("invite_members", False):
            member_count = await self._session.scalar(
                select(func.count()).select_from(WorkspaceMember).where(
                    WorkspaceMember.workspace_id == workspace_id,
                    WorkspaceMember.is_deleted == False,  # noqa: E712
                )
            )
            if member_count and member_count > 1:
                await repo.update_step(workspace_id, "invite_members", completed=True)
                synced = True

        if synced:
            # Refresh to get updated state after step updates
            await self._session.refresh(onboarding)
            logger.info(
                "Auto-synced onboarding steps",
                extra={"workspace_id": str(workspace_id)},
            )


__all__ = ["GetOnboardingResult", "GetOnboardingService"]
