"""OnboardingRepository for workspace onboarding state.

Extends BaseRepository with onboarding-specific queries.

T011: Create OnboardingRepository.
Source: FR-001, FR-002, FR-003, US1
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm.attributes import flag_modified

from pilot_space.infrastructure.database.models.onboarding import WorkspaceOnboarding
from pilot_space.infrastructure.database.repositories.base import BaseRepository

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class OnboardingRepository(BaseRepository[WorkspaceOnboarding]):
    """Repository for WorkspaceOnboarding entities.

    Provides specialized queries for onboarding state management.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize OnboardingRepository.

        Args:
            session: The async database session.
        """
        super().__init__(session, WorkspaceOnboarding)

    async def get_by_workspace_id(
        self,
        workspace_id: UUID,
    ) -> WorkspaceOnboarding | None:
        """Get onboarding state by workspace ID.

        Args:
            workspace_id: The workspace UUID.

        Returns:
            WorkspaceOnboarding if found, None otherwise.
        """
        query = select(WorkspaceOnboarding).where(
            WorkspaceOnboarding.workspace_id == workspace_id,
            WorkspaceOnboarding.is_deleted == False,  # noqa: E712
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def upsert_for_workspace(
        self,
        workspace_id: UUID,
    ) -> WorkspaceOnboarding:
        """Create or get onboarding state for workspace.

        Uses INSERT ... ON CONFLICT DO NOTHING pattern.
        Returns existing record if already exists.

        Args:
            workspace_id: The workspace UUID.

        Returns:
            WorkspaceOnboarding (existing or newly created).
        """
        # Try to get existing
        existing = await self.get_by_workspace_id(workspace_id)
        if existing:
            return existing

        # Create new
        onboarding = WorkspaceOnboarding(
            workspace_id=workspace_id,
            steps={"ai_providers": False, "invite_members": False, "first_note": False},
        )
        return await self.create(onboarding)

    async def update_step(
        self,
        workspace_id: UUID,
        step_name: str,
        completed: bool,
    ) -> WorkspaceOnboarding | None:
        """Update a single onboarding step.

        Args:
            workspace_id: The workspace UUID.
            step_name: One of 'ai_providers', 'invite_members', 'first_note'.
            completed: Whether the step is completed.

        Returns:
            Updated WorkspaceOnboarding, or None if not found.

        Raises:
            ValueError: If step_name is invalid.
        """
        if step_name not in ("ai_providers", "invite_members", "first_note"):
            msg = f"Invalid step name: {step_name}"
            raise ValueError(msg)

        onboarding = await self.get_by_workspace_id(workspace_id)
        if not onboarding:
            return None

        # Update the specific step in JSONB
        # Replace dict to ensure SQLAlchemy detects the change, then flag_modified as belt-and-suspenders
        onboarding.steps = {**onboarding.steps, step_name: completed}
        flag_modified(onboarding, "steps")
        onboarding.updated_at = datetime.now(tz=UTC)

        # Check if all steps complete
        if onboarding.is_complete and onboarding.completed_at is None:
            onboarding.completed_at = datetime.now(tz=UTC)
        elif not onboarding.is_complete:
            onboarding.completed_at = None

        await self.session.flush()
        await self.session.refresh(onboarding)
        return onboarding

    async def set_dismissed(
        self,
        workspace_id: UUID,
        dismissed: bool = True,
    ) -> WorkspaceOnboarding | None:
        """Set dismissed state for onboarding.

        Args:
            workspace_id: The workspace UUID.
            dismissed: Whether to dismiss (True) or reopen (False).

        Returns:
            Updated WorkspaceOnboarding, or None if not found.
        """
        onboarding = await self.get_by_workspace_id(workspace_id)
        if not onboarding:
            return None

        if dismissed:
            onboarding.dismissed_at = datetime.now(tz=UTC)
        else:
            onboarding.dismissed_at = None

        onboarding.updated_at = datetime.now(tz=UTC)

        await self.session.flush()
        await self.session.refresh(onboarding)
        return onboarding

    async def set_guided_note_id(
        self,
        workspace_id: UUID,
        note_id: UUID,
    ) -> WorkspaceOnboarding | None:
        """Set the guided note ID for workspace onboarding.

        Args:
            workspace_id: The workspace UUID.
            note_id: The guided note UUID.

        Returns:
            Updated WorkspaceOnboarding, or None if not found.
        """
        onboarding = await self.get_by_workspace_id(workspace_id)
        if not onboarding:
            return None

        onboarding.guided_note_id = note_id
        onboarding.updated_at = datetime.now(tz=UTC)

        await self.session.flush()
        await self.session.refresh(onboarding)
        return onboarding

    async def get_incomplete_onboardings(
        self,
        limit: int = 100,
    ) -> list[WorkspaceOnboarding]:
        """Get all incomplete onboarding records.

        Useful for analytics and reminders.

        Args:
            limit: Maximum number of records to return.

        Returns:
            List of incomplete WorkspaceOnboarding records.
        """
        query = (
            select(WorkspaceOnboarding)
            .where(
                WorkspaceOnboarding.completed_at.is_(None),
                WorkspaceOnboarding.is_deleted == False,  # noqa: E712
            )
            .order_by(WorkspaceOnboarding.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())


__all__ = ["OnboardingRepository"]
