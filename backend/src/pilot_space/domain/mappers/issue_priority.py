"""Map user-facing priority strings to the IssuePriority enum.

Extracted from workspace_issues.py and workspace_notes_ai.py where the
same mapping dict was duplicated in three places.
"""

from __future__ import annotations

from pilot_space.infrastructure.database.models.issue import IssuePriority

_PRIORITY_MAP: dict[str, IssuePriority] = {
    "urgent": IssuePriority.URGENT,
    "high": IssuePriority.HIGH,
    "medium": IssuePriority.MEDIUM,
    "low": IssuePriority.LOW,
    "none": IssuePriority.NONE,
}


def map_priority_string(
    value: str,
    default: IssuePriority = IssuePriority.NONE,
) -> IssuePriority:
    """Convert a case-insensitive priority string to :class:`IssuePriority`.

    Args:
        value: Priority string (e.g. ``"high"``, ``"MEDIUM"``).
        default: Fallback when *value* is not recognised.

    Returns:
        Matching :class:`IssuePriority` member, or *default*.
    """
    return _PRIORITY_MAP.get(value.lower(), default)
