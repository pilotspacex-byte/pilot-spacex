"""WorkIntent domain entity.

Represents a user intent detected from note content or explicit input.
Tracks lifecycle from detection through execution to acceptance/rejection.

Feature 015: AI Workforce Platform
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pilot_space.domain.exceptions import ValidationError


class IntentStatus(StrEnum):
    """Work intent lifecycle status."""

    DETECTED = "detected"
    CONFIRMED = "confirmed"
    EXECUTING = "executing"
    REVIEW = "review"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class DedupStatus(StrEnum):
    """Dedup resolution status."""

    PENDING = "pending"
    COMPLETE = "complete"


# Valid status transitions: source -> set of allowed targets
_ALLOWED_TRANSITIONS: dict[IntentStatus, frozenset[IntentStatus]] = {
    IntentStatus.DETECTED: frozenset({IntentStatus.CONFIRMED, IntentStatus.REJECTED}),
    IntentStatus.CONFIRMED: frozenset({IntentStatus.EXECUTING, IntentStatus.REJECTED}),
    IntentStatus.EXECUTING: frozenset({IntentStatus.REVIEW, IntentStatus.REJECTED}),
    IntentStatus.REVIEW: frozenset({IntentStatus.ACCEPTED, IntentStatus.REJECTED}),
    IntentStatus.ACCEPTED: frozenset(),
    IntentStatus.REJECTED: frozenset(),
}


@dataclass
class WorkIntent:
    """Domain entity representing a user work intent.

    Lifecycle: detected -> confirmed -> executing -> review -> accepted
    Terminal states: accepted, rejected
    Rejected is reachable from any non-terminal state.

    Attributes:
        workspace_id: Workspace this intent belongs to.
        what: Intent description (immutable after confirmed).
        confidence: Detection confidence score (0.0-1.0).
        id: Unique identifier (None for unsaved entities).
        why: Intent motivation (immutable after confirmed).
        constraints: Optional JSONB constraints.
        acceptance: Optional JSONB acceptance criteria.
        status: Current lifecycle status.
        owner: User ID or 'system' that owns this intent.
        parent_intent_id: Parent intent for decomposed sub-intents.
        source_block_id: TipTap block that triggered detection.
        dedup_hash: SHA-256 of normalized `what` for dedup.
        dedup_status: Dedup resolution state.
        created_at: Creation timestamp.
        updated_at: Last update timestamp.
    """

    workspace_id: UUID
    what: str
    confidence: float
    id: UUID | None = None
    why: str | None = None
    constraints: list[Any] | dict[str, Any] | None = None
    acceptance: list[Any] | dict[str, Any] | None = None
    status: IntentStatus = IntentStatus.DETECTED
    owner: str | None = None
    parent_intent_id: UUID | None = None
    source_block_id: UUID | None = None
    dedup_hash: str | None = None
    dedup_status: DedupStatus = DedupStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))

    def __post_init__(self) -> None:
        """Validate initial state."""
        self._validate_confidence(self.confidence)
        if self.dedup_hash is None:
            self.dedup_hash = self.compute_dedup_hash(self.what)

    def transition_to(self, new_status: IntentStatus) -> None:
        """Transition intent to a new status.

        Args:
            new_status: Target status.

        Raises:
            ValueError: If transition is not allowed from current status.
        """
        allowed = _ALLOWED_TRANSITIONS.get(self.status, frozenset())
        if new_status not in allowed:
            msg = (
                f"Cannot transition from {self.status.value!r} to {new_status.value!r}. "
                f"Allowed: {[s.value for s in allowed]}"
            )
            raise ValidationError(msg)
        self.status = new_status
        self.updated_at = datetime.now(tz=UTC)

    def confirm(self) -> None:
        """Confirm the intent, locking `what` and `why` fields."""
        self.transition_to(IntentStatus.CONFIRMED)

    def start_executing(self) -> None:
        """Mark intent as executing."""
        self.transition_to(IntentStatus.EXECUTING)

    def mark_review(self) -> None:
        """Move intent to review state."""
        self.transition_to(IntentStatus.REVIEW)

    def accept(self) -> None:
        """Accept the completed intent."""
        self.transition_to(IntentStatus.ACCEPTED)

    def reject(self) -> None:
        """Reject the intent from any non-terminal state."""
        self.transition_to(IntentStatus.REJECTED)

    def update_what(self, new_what: str) -> None:
        """Update intent description if not yet confirmed.

        Args:
            new_what: New intent description.

        Raises:
            ValueError: If intent is already confirmed or beyond.
        """
        if self.status not in (IntentStatus.DETECTED,):
            msg = f"Cannot update 'what' after status is {self.status.value!r}"
            raise ValidationError(msg)
        self.what = new_what
        self.dedup_hash = self.compute_dedup_hash(new_what)
        self.updated_at = datetime.now(tz=UTC)

    def update_why(self, new_why: str | None) -> None:
        """Update intent motivation if not yet confirmed.

        Args:
            new_why: New motivation text.

        Raises:
            ValueError: If intent is already confirmed or beyond.
        """
        if self.status not in (IntentStatus.DETECTED,):
            msg = f"Cannot update 'why' after status is {self.status.value!r}"
            raise ValidationError(msg)
        self.why = new_why
        self.updated_at = datetime.now(tz=UTC)

    def set_confidence(self, confidence: float) -> None:
        """Update confidence score.

        Args:
            confidence: New confidence score (0.0-1.0).

        Raises:
            ValueError: If confidence is out of range.
        """
        self._validate_confidence(confidence)
        self.confidence = confidence
        self.updated_at = datetime.now(tz=UTC)

    def mark_dedup_complete(self) -> None:
        """Mark dedup check as complete."""
        self.dedup_status = DedupStatus.COMPLETE
        self.updated_at = datetime.now(tz=UTC)

    @property
    def is_terminal(self) -> bool:
        """Check if intent is in a terminal state."""
        return self.status in (IntentStatus.ACCEPTED, IntentStatus.REJECTED)

    @property
    def is_mutable(self) -> bool:
        """Check if core fields can still be modified."""
        return self.status == IntentStatus.DETECTED

    @staticmethod
    def compute_dedup_hash(what: str) -> str:
        """Compute SHA-256 dedup hash from normalized intent text.

        Normalizes by lowercasing and stripping whitespace before hashing.

        Args:
            what: Intent description text.

        Returns:
            64-character hex SHA-256 digest.
        """
        normalized = " ".join(what.lower().split())
        return hashlib.sha256(normalized.encode()).hexdigest()

    @staticmethod
    def _validate_confidence(confidence: float) -> None:
        """Validate confidence is within [0.0, 1.0].

        Args:
            confidence: Confidence score to validate.

        Raises:
            ValueError: If confidence is outside valid range.
        """
        if not (0.0 <= confidence <= 1.0):
            msg = f"Confidence must be between 0.0 and 1.0, got {confidence}"
            raise ValidationError(msg)


__all__ = ["DedupStatus", "IntentStatus", "WorkIntent"]
