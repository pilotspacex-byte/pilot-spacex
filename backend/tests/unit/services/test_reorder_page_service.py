"""Unit tests for ReorderPageService.

Tests cover sibling position computation with gap arithmetic, prepend/append/insert-between,
gap exhaustion re-sequence, and error paths. NoteRepository is fully mocked.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from pilot_space.application.services.note.reorder_page_service import (
    ReorderPagePayload,
    ReorderPageResult,
    ReorderPageService,
)
from pilot_space.infrastructure.database.models.note import Note

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_note(
    *,
    workspace_id: uuid.UUID,
    project_id: uuid.UUID | None = None,
    parent_id: uuid.UUID | None = None,
    depth: int = 0,
    position: int = 1000,
    note_id: uuid.UUID | None = None,
) -> MagicMock:
    """Create a MagicMock that behaves like a Note instance.

    Using MagicMock avoids SQLAlchemy ORM instrumentation issues and
    the need to spin up related tables in the test SQLite schema.
    """
    note = MagicMock(spec=Note)
    note.id = note_id or uuid.uuid4()
    note.workspace_id = workspace_id
    note.project_id = project_id
    note.parent_id = parent_id
    note.depth = depth
    note.position = position
    note.title = "Test Note"
    note.is_deleted = False
    return note


def _make_repo(
    *,
    note: MagicMock | None = None,
    siblings: list[MagicMock] | None = None,
) -> MagicMock:
    """Build a MagicMock NoteRepository with pre-configured async methods."""
    repo = MagicMock()

    async def _get_by_id(id_: uuid.UUID) -> MagicMock | None:
        if note is not None and id_ == note.id:
            return note
        # Return a sibling if the ID matches
        for sib in siblings or []:
            if sib.id == id_:
                return sib
        return None

    repo.get_by_id = AsyncMock(side_effect=_get_by_id)
    repo.get_siblings = AsyncMock(return_value=siblings or [])
    return repo


def _make_session() -> MagicMock:
    """Build a MagicMock AsyncSession."""
    session = MagicMock(spec=AsyncSession)
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.execute = AsyncMock()
    return session


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reorder_insert_between() -> None:
    """Inserting between two siblings produces midpoint position."""
    workspace_id = uuid.uuid4()
    project_id = uuid.uuid4()
    parent_id = uuid.uuid4()

    # Three existing siblings at 1000, 2000, 3000
    sib1 = _make_note(
        workspace_id=workspace_id, project_id=project_id, parent_id=parent_id, position=1000
    )
    sib2 = _make_note(
        workspace_id=workspace_id, project_id=project_id, parent_id=parent_id, position=2000
    )
    sib3 = _make_note(
        workspace_id=workspace_id, project_id=project_id, parent_id=parent_id, position=3000
    )

    # The note to be reordered — currently at some other position
    note = _make_note(
        workspace_id=workspace_id, project_id=project_id, parent_id=parent_id, position=4000
    )

    repo = _make_repo(note=note, siblings=[sib1, sib2, sib3])
    session = _make_session()
    service = ReorderPageService(session=session, note_repository=repo)

    # Insert after sib1 (between sib1=1000 and sib2=2000) -> midpoint=1500
    result = await service.execute(
        ReorderPagePayload(
            note_id=note.id,
            insert_after_id=sib1.id,
            workspace_id=workspace_id,
            actor_id=uuid.uuid4(),
        )
    )

    assert isinstance(result, ReorderPageResult)
    assert note.position == 1500


@pytest.mark.asyncio
async def test_reorder_prepend() -> None:
    """Inserting with insert_after_id=None places the note before the first sibling."""
    workspace_id = uuid.uuid4()
    project_id = uuid.uuid4()
    parent_id = uuid.uuid4()

    sib1 = _make_note(
        workspace_id=workspace_id, project_id=project_id, parent_id=parent_id, position=1000
    )
    sib2 = _make_note(
        workspace_id=workspace_id, project_id=project_id, parent_id=parent_id, position=2000
    )

    note = _make_note(
        workspace_id=workspace_id, project_id=project_id, parent_id=parent_id, position=3000
    )

    repo = _make_repo(note=note, siblings=[sib1, sib2])
    session = _make_session()
    service = ReorderPageService(session=session, note_repository=repo)

    result = await service.execute(
        ReorderPagePayload(
            note_id=note.id,
            insert_after_id=None,
            workspace_id=workspace_id,
            actor_id=uuid.uuid4(),
        )
    )

    assert isinstance(result, ReorderPageResult)
    # Prepend: position should be half of 1000 = 500
    assert note.position == 500
    assert note.position < sib1.position


@pytest.mark.asyncio
async def test_reorder_append() -> None:
    """Inserting after the last sibling appends with gap 1000."""
    workspace_id = uuid.uuid4()
    project_id = uuid.uuid4()
    parent_id = uuid.uuid4()

    sib1 = _make_note(
        workspace_id=workspace_id, project_id=project_id, parent_id=parent_id, position=1000
    )
    sib2 = _make_note(
        workspace_id=workspace_id, project_id=project_id, parent_id=parent_id, position=2000
    )

    note = _make_note(
        workspace_id=workspace_id, project_id=project_id, parent_id=parent_id, position=500
    )

    repo = _make_repo(note=note, siblings=[sib1, sib2])
    session = _make_session()
    service = ReorderPageService(session=session, note_repository=repo)

    # Insert after last sibling (sib2) -> 2000 + 1000 = 3000
    result = await service.execute(
        ReorderPagePayload(
            note_id=note.id,
            insert_after_id=sib2.id,
            workspace_id=workspace_id,
            actor_id=uuid.uuid4(),
        )
    )

    assert isinstance(result, ReorderPageResult)
    assert note.position == 3000


@pytest.mark.asyncio
async def test_reorder_gap_exhaustion() -> None:
    """When midpoint equals a neighbor, all siblings are re-sequenced with gap 1000."""
    workspace_id = uuid.uuid4()
    project_id = uuid.uuid4()
    parent_id = uuid.uuid4()

    # Positions 1000 and 1001 — midpoint = 1000 (collision), triggers re-sequence
    sib1 = _make_note(
        workspace_id=workspace_id, project_id=project_id, parent_id=parent_id, position=1000
    )
    sib2 = _make_note(
        workspace_id=workspace_id, project_id=project_id, parent_id=parent_id, position=1001
    )

    note = _make_note(
        workspace_id=workspace_id, project_id=project_id, parent_id=parent_id, position=5000
    )

    repo = _make_repo(note=note, siblings=[sib1, sib2])
    session = _make_session()
    service = ReorderPageService(session=session, note_repository=repo)

    # Insert after sib1 (between 1000 and 1001 — gap exhausted)
    result = await service.execute(
        ReorderPagePayload(
            note_id=note.id,
            insert_after_id=sib1.id,
            workspace_id=workspace_id,
            actor_id=uuid.uuid4(),
        )
    )

    assert isinstance(result, ReorderPageResult)
    # After re-sequence: all siblings and note get positions 1000, 2000, 3000
    # note must be between sib1 and sib2, so order is sib1(1000), note(2000), sib2(3000)
    positions = sorted([sib1.position, note.position, sib2.position])
    assert positions == [1000, 2000, 3000]
    # Note is between sib1 and sib2
    assert sib1.position < note.position < sib2.position


@pytest.mark.asyncio
async def test_reorder_no_siblings() -> None:
    """A note with no siblings gets position 1000."""
    workspace_id = uuid.uuid4()
    project_id = uuid.uuid4()

    note = _make_note(workspace_id=workspace_id, project_id=project_id, position=500)

    repo = _make_repo(note=note, siblings=[])
    session = _make_session()
    service = ReorderPageService(session=session, note_repository=repo)

    result = await service.execute(
        ReorderPagePayload(
            note_id=note.id,
            insert_after_id=None,
            workspace_id=workspace_id,
            actor_id=uuid.uuid4(),
        )
    )

    assert isinstance(result, ReorderPageResult)
    assert note.position == 1000


@pytest.mark.asyncio
async def test_reorder_not_found() -> None:
    """Reordering a non-existent note raises ValueError."""
    workspace_id = uuid.uuid4()

    repo = _make_repo()  # get_by_id always returns None
    session = _make_session()
    service = ReorderPageService(session=session, note_repository=repo)

    with pytest.raises(ValueError, match="Note not found"):
        await service.execute(
            ReorderPagePayload(
                note_id=uuid.uuid4(),
                insert_after_id=None,
                workspace_id=workspace_id,
                actor_id=uuid.uuid4(),
            )
        )


@pytest.mark.asyncio
async def test_reorder_personal_page() -> None:
    """Reordering a personal page (project_id=None) raises ValueError."""
    workspace_id = uuid.uuid4()

    # Personal page: project_id is None
    note = _make_note(workspace_id=workspace_id, project_id=None)

    repo = _make_repo(note=note)
    session = _make_session()
    service = ReorderPageService(session=session, note_repository=repo)

    with pytest.raises(ValueError, match="Personal page reordering not yet supported"):
        await service.execute(
            ReorderPagePayload(
                note_id=note.id,
                insert_after_id=None,
                workspace_id=workspace_id,
                actor_id=uuid.uuid4(),
            )
        )
