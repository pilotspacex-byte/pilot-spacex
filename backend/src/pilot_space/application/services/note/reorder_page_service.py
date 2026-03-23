"""ReorderPageService for sibling position management.

Implements TREE-03: users can reorder a page among its siblings using
gap-based position arithmetic with automatic re-sequencing on gap exhaustion.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

from pilot_space.domain.exceptions import NotFoundError, ValidationError
from pilot_space.infrastructure.logging import get_logger

logger = get_logger(__name__)

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from pilot_space.infrastructure.database.models.note import Note
    from pilot_space.infrastructure.database.repositories.note_repository import (
        NoteRepository,
    )

_GAP = 1000  # Standard position gap between siblings


@dataclass(frozen=True, slots=True)
class ReorderPagePayload:
    """Payload for reordering a page among its siblings.

    Attributes:
        note_id: The note to reorder.
        insert_after_id: Sibling note ID to insert after. None prepends.
        workspace_id: The workspace context.
        actor_id: The user performing the reorder.
    """

    note_id: UUID
    insert_after_id: UUID | None
    workspace_id: UUID
    actor_id: UUID


@dataclass(frozen=True, slots=True)
class ReorderPageResult:
    """Result from a page reorder operation.

    Attributes:
        note: The updated note.
    """

    note: Note


class ReorderPageService:
    """Service for reordering a page among its siblings.

    Uses gap-based midpoint arithmetic. When the midpoint collides with a
    neighbor (gap exhaustion), all siblings are re-sequenced with gap 1000.
    """

    def __init__(self, session: AsyncSession, note_repository: NoteRepository) -> None:
        """Initialize ReorderPageService.

        Args:
            session: The async database session.
            note_repository: Repository for note tree operations.
        """
        self._session = session
        self._note_repo = note_repository

    async def execute(self, payload: ReorderPagePayload) -> ReorderPageResult:
        """Execute the page reorder operation.

        Args:
            payload: Reorder parameters including note ID and insert anchor.

        Returns:
            ReorderPageResult with the updated note.

        Raises:
            ValueError: If note not found or personal page attempted.
        """
        # Fetch and validate note
        note = await self._note_repo.get_by_id(payload.note_id)
        if note is None or note.workspace_id != payload.workspace_id:
            msg = "Note not found"
            raise NotFoundError(msg)

        # Guard: personal pages not yet supported
        if note.project_id is None:
            msg = "Personal page reordering not yet supported"
            raise ValidationError(msg)

        # Fetch siblings (ordered by position ASC, note itself excluded)
        siblings = await self._note_repo.get_siblings(
            note.parent_id,
            payload.workspace_id,
            note.project_id,
            note.id,
        )

        # Compute new position; -1 is the gap-exhaustion sentinel
        new_position = self._compute_insert_position(siblings, payload.insert_after_id)

        if new_position == -1:
            # Gap exhausted — re-sequence all siblings and place note correctly
            await self._resequence_siblings(siblings, note, payload.insert_after_id)
        else:
            note.position = new_position

        await self._session.flush()
        await self._session.refresh(note)

        logger.info(
            "ReorderPageService: reordered note %s to position=%d",
            note.id,
            note.position,
        )

        return ReorderPageResult(note=note)

    def _compute_insert_position(
        self,
        siblings: Sequence[Note],
        insert_after_id: UUID | None,
    ) -> int:
        """Compute the new position for the note.

        Returns the computed position, or -1 as a sentinel when the midpoint
        would collide with an existing sibling (gap exhaustion).

        Args:
            siblings: Ordered list of sibling notes (note excluded, position ASC).
            insert_after_id: Sibling ID to insert after, or None to prepend.

        Returns:
            New position integer, or -1 if re-sequencing is required.
        """
        if not siblings:
            return _GAP

        if insert_after_id is None:
            # Prepend: half of first sibling's position, minimum 1
            return max(1, siblings[0].position // 2)

        positions = [s.position for s in siblings]
        ids = [s.id for s in siblings]

        try:
            idx = ids.index(insert_after_id)
        except ValueError:
            # Anchor not found among siblings — append
            return siblings[-1].position + _GAP

        if idx == len(siblings) - 1:
            # Append after last sibling
            return siblings[-1].position + _GAP

        # Midpoint between idx and idx+1
        mid = (positions[idx] + positions[idx + 1]) // 2
        if mid == positions[idx] or mid == positions[idx + 1]:
            # Gap exhausted — signal for re-sequence
            return -1
        return mid

    async def _resequence_siblings(
        self,
        siblings: Sequence[Note],
        note: Note,
        insert_after_id: UUID | None,
    ) -> None:
        """Re-sequence all siblings with gap 1000, placing note at the correct slot.

        Builds an ordered list of all nodes (siblings + note), determines the
        insertion position, then assigns contiguous 1000-gapped positions.

        Args:
            siblings: Ordered sibling list (note excluded, position ASC).
            note: The note being reordered.
            insert_after_id: Anchor sibling ID (None = prepend).
        """
        # Build the new ordered list
        ordered: list[Note] = []

        if insert_after_id is None:
            # Note goes first
            ordered.append(note)
            ordered.extend(siblings)
        else:
            inserted = False
            for sib in siblings:
                ordered.append(sib)
                if sib.id == insert_after_id:
                    ordered.append(note)
                    inserted = True
            if not inserted:
                # Anchor not found — append
                ordered.append(note)

        # Assign gap-1000 positions
        for i, n in enumerate(ordered):
            n.position = (i + 1) * _GAP
