"""Normalize user-facing state name strings to canonical display names.

Extracted from workspace_issues.py where state name normalization was
inline in the router.
"""

from __future__ import annotations

_STATE_NAME_MAP: dict[str, str] = {
    "backlog": "Backlog",
    "todo": "Todo",
    "in_progress": "In Progress",
    "in-progress": "In Progress",
    "in_review": "In Review",
    "in-review": "In Review",
    "done": "Done",
    "cancelled": "Cancelled",
    "canceled": "Cancelled",
}


def normalize_state_name(value: str) -> str:
    """Normalize a state name string to its canonical display form.

    Args:
        value: State name string (e.g. ``"in_progress"``, ``"Done"``).

    Returns:
        Canonical display name if recognised, otherwise the original value.
    """
    return _STATE_NAME_MAP.get(value.lower(), value)
