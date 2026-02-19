"""Factory for WorkIntent domain entity.

Provides make_work_intent() with sensible defaults for test use.
Follows simple factory function pattern (no factory_boy dependency)
since WorkIntent is a pure domain dataclass, not an ORM model.

Usage:
    intent = make_work_intent()
    confirmed = make_work_intent(status=IntentStatus.CONFIRMED, what="Ship feature")
    child = make_work_intent(parent_intent_id=parent.id)
"""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from pilot_space.domain.work_intent import DedupStatus, IntentStatus, WorkIntent


def make_work_intent(
    *,
    workspace_id: UUID | None = None,
    what: str = "Implement user authentication",
    confidence: float = 0.85,
    id: UUID | None = None,
    why: str | None = "Users need secure access to the platform",
    constraints: list[Any] | dict[str, Any] | None = None,
    acceptance: list[Any] | dict[str, Any] | None = None,
    status: IntentStatus = IntentStatus.DETECTED,
    owner: str | None = None,
    parent_intent_id: UUID | None = None,
    source_block_id: UUID | None = None,
    dedup_status: DedupStatus = DedupStatus.PENDING,
) -> WorkIntent:
    """Create a WorkIntent with valid defaults.

    All parameters are keyword-only to prevent positional argument errors.

    Args:
        workspace_id: Workspace UUID (generated if not provided).
        what: Intent description text.
        confidence: Detection confidence score (0.0-1.0).
        id: Entity UUID (None for unsaved state, generated if needed).
        why: Intent motivation text.
        constraints: Optional JSONB constraints.
        acceptance: Optional JSONB acceptance criteria.
        status: Lifecycle status (default: DETECTED).
        owner: User ID or 'system' string.
        parent_intent_id: Parent intent for decomposition.
        source_block_id: TipTap block UUID that triggered detection.
        dedup_status: Dedup resolution state.

    Returns:
        WorkIntent instance with computed dedup_hash.
    """
    return WorkIntent(
        workspace_id=workspace_id or uuid4(),
        what=what,
        confidence=confidence,
        id=id,
        why=why,
        constraints=constraints,
        acceptance=acceptance,
        status=status,
        owner=owner,
        parent_intent_id=parent_intent_id,
        source_block_id=source_block_id,
        dedup_status=dedup_status,
    )


def make_confirmed_work_intent(**kwargs: Any) -> WorkIntent:
    """Create a WorkIntent in CONFIRMED status.

    Builds a DETECTED intent, then calls confirm() to apply the
    proper status transition. Use this when tests need post-confirm state.

    Args:
        **kwargs: Forwarded to make_work_intent() (status is ignored).

    Returns:
        WorkIntent in CONFIRMED status.
    """
    kwargs.pop("status", None)
    intent = make_work_intent(status=IntentStatus.DETECTED, **kwargs)
    intent.confirm()
    return intent


def make_executing_work_intent(**kwargs: Any) -> WorkIntent:
    """Create a WorkIntent in EXECUTING status.

    Args:
        **kwargs: Forwarded to make_work_intent() (status is ignored).

    Returns:
        WorkIntent in EXECUTING status.
    """
    kwargs.pop("status", None)
    intent = make_work_intent(status=IntentStatus.DETECTED, **kwargs)
    intent.confirm()
    intent.start_executing()
    return intent


__all__ = [
    "make_confirmed_work_intent",
    "make_executing_work_intent",
    "make_work_intent",
]
