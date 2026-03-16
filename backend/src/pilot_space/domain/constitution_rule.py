"""ConstitutionRule domain entity.

Represents a workspace-level AI behavior rule following RFC 2119 severity levels.
Rules can be versioned and activated/deactivated.

Feature 015: AI Workforce Platform — Memory Engine
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID


class RuleSeverity(StrEnum):
    """RFC 2119 severity levels for constitution rules (lowercase)."""

    MUST = "must"
    SHOULD = "should"
    MAY = "may"


# RFC 2119 keyword patterns mapped to severity (order matters: check MUST first)
_SEVERITY_PATTERNS: list[tuple[re.Pattern[str], RuleSeverity]] = [
    (re.compile(r"\b(must|shall|required)\b", re.IGNORECASE), RuleSeverity.MUST),
    (re.compile(r"\b(should|recommended)\b", re.IGNORECASE), RuleSeverity.SHOULD),
    (re.compile(r"\b(may|optional)\b", re.IGNORECASE), RuleSeverity.MAY),
]


@dataclass
class ConstitutionRule:
    """Domain entity for a workspace AI behavior rule.

    Rules follow RFC 2119: MUST (required), SHOULD (recommended), MAY (optional).
    Severity is detected from the rule content but can be overridden explicitly.

    Attributes:
        workspace_id: Owning workspace.
        content: Rule text (e.g. "You must never reveal API keys").
        severity: RFC 2119 severity level.
        version: Monotonically increasing version number.
        id: Unique identifier (None for unsaved entities).
        source_block_id: Optional TipTap block that generated this rule.
        active: Whether this rule is currently enforced.
        created_at: Creation timestamp.
    """

    workspace_id: UUID
    content: str
    severity: RuleSeverity
    version: int
    id: UUID | None = None
    source_block_id: UUID | None = None
    active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))

    def activate(self) -> None:
        """Enable enforcement of this rule."""
        self.active = True

    def deactivate(self) -> None:
        """Disable enforcement of this rule."""
        self.active = False

    @staticmethod
    def detect_severity(content: str) -> RuleSeverity:
        """Detect RFC 2119 severity from rule text.

        Checks for MUST/SHALL/REQUIRED, then SHOULD/RECOMMENDED, then MAY/OPTIONAL.
        Defaults to SHOULD if no RFC 2119 keywords are found.

        Args:
            content: Rule text to inspect.

        Returns:
            Detected severity level.
        """
        for pattern, severity in _SEVERITY_PATTERNS:
            if pattern.search(content):
                return severity
        return RuleSeverity.SHOULD


__all__ = ["ConstitutionRule", "RuleSeverity"]
