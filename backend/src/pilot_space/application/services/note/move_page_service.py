"""MovePageService for re-parenting pages within a project tree.

Implements TREE-02: users can move a page to a different parent with
depth enforcement and descendant cascade (max depth 2).
"""

from __future__ import annotations

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

MAX_DEPTH = 2


@dataclass(frozen=True, slots=True)
class MovePagePayload:
    """Payload for moving a page to a new parent.

    Attributes:
        note_id: The note to move.
        new_parent_id: Target parent note ID. None promotes to tree root.
        workspace_id: The workspace context for authorization.
        actor_id: The user performing the move.
    """

    note_id: UUID
    new_parent_id: UUID | None
    workspace_id: UUID
    actor_id: UUID


@dataclass(frozen=True, slots=True)
class MovePageResult:
    """Result from a page move operation.

    Attributes:
        note: The updated note.
        depth_delta: How much the depth changed (positive = moved deeper).
    """

    note: Note
    depth_delta: int


class MovePageService:
    """Service for moving a page to a new parent within a project tree.

    Enforces:
    - 3-level max depth (0, 1, 2)
    - Same-project constraint
    - Descendant depth cascade
    - Personal page (project_id=None) guard
    """

    def __init__(self, session: AsyncSession, note_repository: NoteRepository) -> None:
        """Initialize MovePageService.

        Args:
            session: The async database session.
            note_repository: Repository for note tree operations.
        """
        self._session = session
        self._note_repo = note_repository

    async def execute(self, payload: MovePagePayload) -> MovePageResult:
        """Execute the page move operation.

        Args:
            payload: Move parameters including note ID and target parent.

        Returns:
            MovePageResult with updated note and depth delta.

        Raises:
            ValueError: If validation fails (not found, cross-project, depth exceeded).
        """
        # Fetch the note
        note = await self._note_repo.get_by_id(payload.note_id)
        if note is None or note.workspace_id != payload.workspace_id:
            msg = "Note not found"
            raise NotFoundError(msg)

        # Guard: cannot move a page to itself
        if payload.new_parent_id == note.id:
            msg = "Cannot move a page to itself"
            raise ValidationError(msg)

        # Guard: personal pages (project_id=None) cannot be re-parented yet
        if note.project_id is None:
            msg = "Personal page re-parenting not yet supported"
            raise ValidationError(msg)

        # Resolve target depth and validate parent
        new_depth: int
        if payload.new_parent_id is not None:
            parent = await self._note_repo.get_by_id(payload.new_parent_id)
            if parent is None or parent.workspace_id != payload.workspace_id:
                msg = "Target parent not found"
                raise NotFoundError(msg)
            if parent.project_id != note.project_id:
                msg = "Cannot move page to a different project"
                raise ValidationError(msg)
            new_depth = parent.depth + 1
        else:
            new_depth = 0

        # Depth limit check for the note itself
        if new_depth > MAX_DEPTH:
            msg = "Move would exceed the 3-level depth limit"
            raise ValidationError(msg)

        # Descendant depth check — mocked in tests since SQLite lacks recursive CTE
        descendants = await self._note_repo.get_descendants(note.id)

        # Guard: cannot move to a descendant (would create a cycle)
        if payload.new_parent_id is not None and descendants:
            descendant_ids = {d["id"] for d in descendants}
            if payload.new_parent_id in descendant_ids:
                msg = "Cannot move a page to one of its descendants (would create cycle)"
                raise ValidationError(msg)

        if descendants:
            max_offset = max(int(d["depth"]) - note.depth for d in descendants)
            if new_depth + max_offset > MAX_DEPTH:
                msg = "Move would push a descendant beyond the 3-level depth limit"
                raise ValidationError(msg)

        depth_delta = new_depth - note.depth

        # Compute tail position under the new parent
        new_position = await self._compute_tail_position(
            parent_id=payload.new_parent_id,
            workspace_id=payload.workspace_id,
            project_id=note.project_id,
        )

        # Update the note
        note.parent_id = payload.new_parent_id  # type: ignore[assignment]
        note.depth = new_depth
        note.position = new_position
        await self._session.flush()

        # Cascade depth delta to all descendants
        if descendants and depth_delta != 0:
            from sqlalchemy import update

            from pilot_space.infrastructure.database.models.note import Note

            desc_ids = [d["id"] for d in descendants]
            await self._session.execute(
                update(Note)
                .where(Note.id.in_(desc_ids), Note.workspace_id == payload.workspace_id)
                .values(depth=Note.depth + depth_delta)
            )

        await self._session.flush()
        await self._session.refresh(note)

        logger.info(
            "MovePageService: moved note %s to parent=%s depth=%d delta=%d",
            note.id,
            payload.new_parent_id,
            new_depth,
            depth_delta,
        )

        return MovePageResult(note=note, depth_delta=depth_delta)

    async def _compute_tail_position(
        self,
        parent_id: UUID | None,
        workspace_id: UUID,
        project_id: UUID | None,
    ) -> int:
        """Compute the tail position (max + 1000) under the given parent.

        Uses a gap of 1000 between siblings to allow future reordering
        without renumbering.

        Args:
            parent_id: Target parent note ID (None for root level).
            workspace_id: Workspace context.
            project_id: Project context.

        Returns:
            Next position value (1000 if no siblings exist).
        """
        siblings = await self._note_repo.get_siblings(
            parent_id=parent_id,
            workspace_id=workspace_id,
            project_id=project_id,
            exclude_note_id=self._null_uuid(),
            for_update=True,
        )
        if not siblings:
            return 1000
        return max(s.position for s in siblings) + 1000

    @staticmethod
    def _null_uuid() -> UUID:
        """Return a sentinel nil UUID used to exclude nothing from sibling query."""
        import uuid

        return uuid.UUID("00000000-0000-0000-0000-000000000000")
