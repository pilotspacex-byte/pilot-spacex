"""Onboarding services for Pilot Space (CQRS-lite).

Provides services for workspace onboarding state management:
- GetOnboardingService: Query onboarding state
- UpdateOnboardingService: Update step completion and dismiss
- CreateGuidedNoteService: Create guided first note

T012: Create OnboardingService (CQRS-lite).
Source: FR-001, FR-002, FR-003, FR-011
"""

from pilot_space.application.services.onboarding.create_guided_note_service import (
    CreateGuidedNotePayload,
    CreateGuidedNoteResult,
    CreateGuidedNoteService,
)
from pilot_space.application.services.onboarding.get_onboarding_service import (
    GetOnboardingResult,
    GetOnboardingService,
)
from pilot_space.application.services.onboarding.types import OnboardingStepsResult
from pilot_space.application.services.onboarding.update_onboarding_service import (
    UpdateOnboardingPayload,
    UpdateOnboardingResult,
    UpdateOnboardingService,
)

__all__ = [
    "CreateGuidedNotePayload",
    "CreateGuidedNoteResult",
    "CreateGuidedNoteService",
    "GetOnboardingResult",
    "GetOnboardingService",
    "OnboardingStepsResult",
    "UpdateOnboardingPayload",
    "UpdateOnboardingResult",
    "UpdateOnboardingService",
]
