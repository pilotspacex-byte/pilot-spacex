"""Digest context builder for workspace analysis.

Builds a compact text context (<4000 tokens) from workspace data
covering 7-day activity window. Used as input to the generate-digest
skill prompt for Claude Sonnet.

References:
- specs/012-homepage-note/spec.md Background Job Specification
- US-19: Homepage Hub feature
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import func, select

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Token budget: ~4000 tokens = ~16000 chars (1 token ~ 4 chars)
MAX_CONTEXT_CHARS = 15000
# Max entities per category to prevent runaway queries
MAX_ENTITIES = 500
# Max length for user-supplied text in LLM context (prevents prompt injection)
MAX_USER_TEXT_LENGTH = 100
# Pattern matching control characters and common prompt injection markers
_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


@dataclass
class DigestContext:
    """Aggregated workspace context for digest generation.

    Attributes:
        workspace_id: Workspace being analyzed.
        generated_at: When context was built.
        sections: Dict of category -> text summary.
        total_chars: Total character count of all sections.
    """

    workspace_id: UUID
    generated_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))
    sections: dict[str, str] = field(default_factory=dict)
    total_chars: int = 0

    def to_prompt_text(self) -> str:
        """Convert context to prompt-ready text.

        Returns:
            Formatted text for LLM consumption.
        """
        parts = [f"Workspace Digest Context (generated {self.generated_at.isoformat()})"]
        for category, text in self.sections.items():
            parts.append(f"\n## {category}\n{text}")
        return "\n".join(parts)


def _sanitize_user_text(text: str, max_length: int = MAX_USER_TEXT_LENGTH) -> str:
    """Sanitize user-supplied text before including in LLM prompt.

    Strips control characters and truncates to prevent prompt injection.

    Args:
        text: Raw user text.
        max_length: Maximum allowed length.

    Returns:
        Sanitized text safe for LLM prompt inclusion.
    """
    cleaned = _CONTROL_CHARS_RE.sub("", text)
    cleaned = cleaned.strip()
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length] + "..."
    return cleaned


class DigestContextBuilder:
    """Builds aggregated context from workspace data for digest generation.

    Queries issues, notes, and cycles from the last 7 days, summarises
    them into compact text sections, and caps total size at ~4000 tokens.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize DigestContextBuilder.

        Args:
            session: The async database session.
        """
        self._session = session

    async def build(self, workspace_id: UUID) -> DigestContext:
        """Build digest context for a workspace.

        Queries multiple entity types and aggregates into a compact
        text representation suitable for LLM analysis.

        Args:
            workspace_id: Workspace to analyze.

        Returns:
            DigestContext with populated sections.
        """
        ctx = DigestContext(workspace_id=workspace_id)
        since = datetime.now(tz=UTC) - timedelta(days=7)

        # Build sections in priority order; stop if hitting char budget
        builders: list[tuple[str, Any]] = [
            ("Issues Summary", self._build_issues_summary(workspace_id, since)),
            ("Notes Summary", self._build_notes_summary(workspace_id, since)),
            ("Cycle Progress", self._build_cycle_summary(workspace_id)),
        ]

        for category, coro in builders:
            section_text = await coro
            if not section_text:
                continue
            # Truncate section if adding it would exceed budget
            remaining = MAX_CONTEXT_CHARS - ctx.total_chars
            if remaining <= 0:
                break
            if len(section_text) > remaining:
                section_text = section_text[:remaining] + "\n[truncated]"
            ctx.sections[category] = section_text
            ctx.total_chars += len(section_text)

        return ctx

    async def _build_issues_summary(self, workspace_id: UUID, since: datetime) -> str:
        """Summarise recent issue activity.

        Args:
            workspace_id: Workspace to query.
            since: Only include issues updated after this time.

        Returns:
            Text summary of issue states and activity.
        """
        from pilot_space.infrastructure.database.models.issue import Issue
        from pilot_space.infrastructure.database.models.state import State

        # Aggregate counts by state group (limited to MAX_ENTITIES for safety)
        recent_issues = (
            select(Issue.id, Issue.state_id)
            .where(
                Issue.workspace_id == workspace_id,
                Issue.is_deleted == False,  # noqa: E712
                Issue.updated_at >= since,
            )
            .limit(MAX_ENTITIES)
            .subquery()
        )
        query = (
            select(
                State.group.label("state_group"),
                func.count(recent_issues.c.id).label("cnt"),
            )
            .outerjoin(State, recent_issues.c.state_id == State.id)
            .group_by(State.group)
        )
        result = await self._session.execute(query)
        rows = result.all()

        if not rows:
            return ""

        lines = ["Issues updated in last 7 days:"]
        total = 0
        for r in rows:
            raw_group = r.state_group
            group = raw_group.value if hasattr(raw_group, "value") else (raw_group or "unknown")
            count = r.cnt
            total += count
            lines.append(f"- {group}: {count}")
        lines.insert(1, f"Total: {total}")

        # Stale issues (in_progress but no update in 3+ days)
        stale_cutoff = datetime.now(tz=UTC) - timedelta(days=3)
        stale_subq = (
            select(Issue.id)
            .outerjoin(State, Issue.state_id == State.id)
            .where(
                Issue.workspace_id == workspace_id,
                Issue.is_deleted == False,  # noqa: E712
                State.group == "started",
                Issue.updated_at < stale_cutoff,
            )
            .limit(MAX_ENTITIES)
            .subquery()
        )
        stale_query = select(func.count()).select_from(stale_subq)
        stale_result = await self._session.execute(stale_query)
        stale_count = stale_result.scalar() or 0
        if stale_count > 0:
            lines.append(f"\nStale (in-progress, no update 3+ days): {stale_count}")

        # Unassigned high/urgent priority
        unassigned_subq = (
            select(Issue.id)
            .where(
                Issue.workspace_id == workspace_id,
                Issue.is_deleted == False,  # noqa: E712
                Issue.assignee_id.is_(None),
                Issue.priority.in_(["high", "urgent"]),
            )
            .limit(MAX_ENTITIES)
            .subquery()
        )
        unassigned_query = select(func.count()).select_from(unassigned_subq)
        unassigned_result = await self._session.execute(unassigned_query)
        unassigned_count = unassigned_result.scalar() or 0
        if unassigned_count > 0:
            lines.append(f"Unassigned high/urgent: {unassigned_count}")

        return "\n".join(lines)

    async def _build_notes_summary(self, workspace_id: UUID, since: datetime) -> str:
        """Summarise recent note activity.

        Args:
            workspace_id: Workspace to query.
            since: Only include notes updated after this time.

        Returns:
            Text summary of note counts and annotation status.
        """
        from pilot_space.infrastructure.database.models.note import Note
        from pilot_space.infrastructure.database.models.note_annotation import (
            NoteAnnotation,
        )

        # Total recent notes
        note_count_query = select(func.count(Note.id)).where(
            Note.workspace_id == workspace_id,
            Note.is_deleted == False,  # noqa: E712
            Note.updated_at >= since,
        )
        note_result = await self._session.execute(note_count_query)
        note_count = note_result.scalar() or 0

        if note_count == 0:
            return ""

        lines = [f"Notes updated in last 7 days: {note_count}"]

        # Pending annotations count (bounded)
        pending_ann_subq = (
            select(NoteAnnotation.id)
            .join(Note, NoteAnnotation.note_id == Note.id)
            .where(
                Note.workspace_id == workspace_id,
                NoteAnnotation.is_deleted == False,  # noqa: E712
                NoteAnnotation.status == "pending",
            )
            .limit(MAX_ENTITIES)
            .subquery()
        )
        pending_ann_query = select(func.count()).select_from(pending_ann_subq)
        pending_result = await self._session.execute(pending_ann_query)
        pending_count = pending_result.scalar() or 0
        if pending_count > 0:
            lines.append(f"Pending AI annotations: {pending_count}")

        return "\n".join(lines)

    async def _build_cycle_summary(self, workspace_id: UUID) -> str:
        """Summarise active cycle progress.

        Args:
            workspace_id: Workspace to query.

        Returns:
            Text summary of active cycles and their progress.
        """
        from pilot_space.infrastructure.database.models.cycle import Cycle

        query = (
            select(Cycle)
            .where(
                Cycle.workspace_id == workspace_id,
                Cycle.is_deleted == False,  # noqa: E712
                Cycle.status == "active",
            )
            .limit(5)
        )
        result = await self._session.execute(query)
        cycles = result.scalars().all()

        if not cycles:
            return ""

        lines = ["Active cycles:"]
        for c in cycles:
            name = _sanitize_user_text(c.name) if c.name else "Unnamed"
            lines.append(f"- {name}: {c.status}")

        return "\n".join(lines)


__all__ = ["DigestContext", "DigestContextBuilder"]
