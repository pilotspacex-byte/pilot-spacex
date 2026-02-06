"""Shared types for onboarding services.

Extracted to avoid circular imports between service modules.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class OnboardingStepsResult:
    """Step completion status (shared across Get/Update services).

    Attributes:
        ai_providers: Whether AI provider is configured.
        invite_members: Whether team members were invited.
        first_note: Whether guided note was created.
    """

    ai_providers: bool
    invite_members: bool
    first_note: bool


__all__ = ["OnboardingStepsResult"]
