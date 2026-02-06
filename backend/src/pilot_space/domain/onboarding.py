"""WorkspaceOnboarding domain entity.

Tracks onboarding progress for a workspace.
Supports 3 steps: ai_providers, invite_members, first_note.

T007: Create WorkspaceOnboarding domain entity.
Source: FR-001, FR-002, FR-003, FR-013, US1
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID


@dataclass
class OnboardingSteps:
    """Onboarding step completion status.

    Attributes:
        ai_providers: Whether AI provider has been configured.
        invite_members: Whether team members have been invited.
        first_note: Whether guided first note has been created.
    """

    ai_providers: bool = False
    invite_members: bool = False
    first_note: bool = False

    @property
    def completion_count(self) -> int:
        """Get count of completed steps.

        Returns:
            Number of completed steps (0-3).
        """
        return sum([self.ai_providers, self.invite_members, self.first_note])

    @property
    def completion_percentage(self) -> int:
        """Get completion percentage.

        Returns:
            Percentage (0-100) of completed steps.
        """
        return (self.completion_count * 100) // 3

    @property
    def is_complete(self) -> bool:
        """Check if all steps are complete.

        Returns:
            True if all 3 steps are completed.
        """
        return self.ai_providers and self.invite_members and self.first_note

    def to_dict(self) -> dict[str, bool]:
        """Convert to dictionary for JSONB storage.

        Returns:
            Dictionary with step names as keys.
        """
        return {
            "ai_providers": self.ai_providers,
            "invite_members": self.invite_members,
            "first_note": self.first_note,
        }

    @classmethod
    def from_dict(cls, data: dict[str, bool] | None) -> OnboardingSteps:
        """Create from dictionary.

        Args:
            data: Dictionary with step names as keys.

        Returns:
            OnboardingSteps instance.
        """
        if not data:
            return cls()
        return cls(
            ai_providers=data.get("ai_providers", False),
            invite_members=data.get("invite_members", False),
            first_note=data.get("first_note", False),
        )


@dataclass
class WorkspaceOnboarding:
    """Domain entity for workspace onboarding state.

    Tracks the 3-step onboarding progress for a workspace.
    Only visible to workspace owners and admins.

    Attributes:
        id: Unique identifier.
        workspace_id: Workspace this belongs to.
        steps: Step completion status.
        guided_note_id: ID of the created guided note (if any).
        dismissed_at: When the checklist was dismissed.
        completed_at: When all steps were completed.
        created_at: When the record was created.
        updated_at: When the record was last updated.
    """

    workspace_id: UUID
    id: UUID | None = None
    steps: OnboardingSteps = field(default_factory=OnboardingSteps)
    guided_note_id: UUID | None = None
    dismissed_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))

    @property
    def is_dismissed(self) -> bool:
        """Check if onboarding was dismissed.

        Returns:
            True if dismissed_at is set.
        """
        return self.dismissed_at is not None

    @property
    def is_complete(self) -> bool:
        """Check if onboarding is complete.

        Returns:
            True if all steps are complete or completed_at is set.
        """
        return self.completed_at is not None or self.steps.is_complete

    @property
    def completion_percentage(self) -> int:
        """Get completion percentage.

        Returns:
            Percentage (0-100) of completed steps.
        """
        return self.steps.completion_percentage

    def complete_step(self, step_name: str) -> bool:
        """Mark a step as completed.

        Args:
            step_name: One of 'ai_providers', 'invite_members', 'first_note'.

        Returns:
            True if all steps are now complete (triggers celebration).

        Raises:
            ValueError: If step_name is invalid.
        """
        if step_name not in ("ai_providers", "invite_members", "first_note"):
            msg = f"Invalid step name: {step_name}"
            raise ValueError(msg)

        setattr(self.steps, step_name, True)
        self.updated_at = datetime.now(tz=UTC)

        # Check if all steps are complete
        if self.steps.is_complete and self.completed_at is None:
            self.completed_at = datetime.now(tz=UTC)
            return True  # Triggers celebration

        return False

    def uncomplete_step(self, step_name: str) -> None:
        """Mark a step as not completed.

        Args:
            step_name: One of 'ai_providers', 'invite_members', 'first_note'.

        Raises:
            ValueError: If step_name is invalid.
        """
        if step_name not in ("ai_providers", "invite_members", "first_note"):
            msg = f"Invalid step name: {step_name}"
            raise ValueError(msg)

        setattr(self.steps, step_name, False)
        self.updated_at = datetime.now(tz=UTC)

        # Clear completed_at if any step is undone
        if self.completed_at is not None:
            self.completed_at = None

    def dismiss(self) -> None:
        """Dismiss the onboarding checklist.

        Sets dismissed_at to current time.
        FR-003: User can dismiss to collapse to sidebar reminder.
        """
        self.dismissed_at = datetime.now(tz=UTC)
        self.updated_at = datetime.now(tz=UTC)

    def reopen(self) -> None:
        """Reopen the dismissed onboarding checklist.

        Clears dismissed_at to show checklist again.
        """
        self.dismissed_at = None
        self.updated_at = datetime.now(tz=UTC)

    def set_guided_note(self, note_id: UUID) -> None:
        """Set the guided note ID.

        Args:
            note_id: ID of the created guided note.
        """
        self.guided_note_id = note_id
        self.updated_at = datetime.now(tz=UTC)


__all__ = ["OnboardingSteps", "WorkspaceOnboarding"]
