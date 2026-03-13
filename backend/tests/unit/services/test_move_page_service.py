"""Unit tests for MovePageService.

Tests cover all depth enforcement, cascade, and error-path scenarios.
The NoteRepository is fully mocked — no SQLite table setup needed.
get_descendants is mocked because SQLite cannot run recursive CTEs.
"""

from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from pilot_space.application.services.note.move_page_service import (
    MovePagePayload,
    MovePageResult,
    MovePageService,
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
    parent: MagicMock | None = None,
    siblings: list[MagicMock] | None = None,
    descendants: list[dict[str, Any]] | None = None,
) -> MagicMock:
    """Build a MagicMock NoteRepository with pre-configured async methods."""
    repo = MagicMock()

    async def _get_by_id(id_: uuid.UUID) -> MagicMock | None:
        if note is not None and id_ == note.id:
            return note
        if parent is not None and id_ == parent.id:
            return parent
        return None

    repo.get_by_id = AsyncMock(side_effect=_get_by_id)
    repo.get_siblings = AsyncMock(return_value=siblings or [])
    repo.get_descendants = AsyncMock(return_value=descendants or [])
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
async def test_move_page_to_new_parent() -> None:
    """Moving a depth-0 note under a depth-0 parent yields depth=1."""
    workspace_id = uuid.uuid4()
    project_id = uuid.uuid4()

    parent = _make_note(workspace_id=workspace_id, project_id=project_id, depth=0)
    note = _make_note(workspace_id=workspace_id, project_id=project_id, depth=0)

    repo = _make_repo(note=note, parent=parent)
    session = _make_session()
    service = MovePageService(session=session, note_repository=repo)

    result = await service.execute(
        MovePagePayload(
            note_id=note.id,
            new_parent_id=parent.id,
            workspace_id=workspace_id,
            actor_id=uuid.uuid4(),
        )
    )

    assert isinstance(result, MovePageResult)
    assert result.depth_delta == 1
    assert note.depth == 1
    assert note.parent_id == parent.id


@pytest.mark.asyncio
async def test_move_page_to_root() -> None:
    """Moving a depth-1 note to root (new_parent_id=None) yields depth=0."""
    workspace_id = uuid.uuid4()
    project_id = uuid.uuid4()
    parent_id = uuid.uuid4()

    note = _make_note(
        workspace_id=workspace_id,
        project_id=project_id,
        parent_id=parent_id,
        depth=1,
    )

    repo = _make_repo(note=note)
    session = _make_session()
    service = MovePageService(session=session, note_repository=repo)

    result = await service.execute(
        MovePagePayload(
            note_id=note.id,
            new_parent_id=None,
            workspace_id=workspace_id,
            actor_id=uuid.uuid4(),
        )
    )

    assert result.depth_delta == -1
    assert note.depth == 0
    assert note.parent_id is None


@pytest.mark.asyncio
async def test_move_cascades_depth_to_descendants() -> None:
    """Moving a note with descendants cascades the depth delta."""
    workspace_id = uuid.uuid4()
    project_id = uuid.uuid4()
    child_id = uuid.uuid4()

    parent = _make_note(workspace_id=workspace_id, project_id=project_id, depth=0)
    note = _make_note(workspace_id=workspace_id, project_id=project_id, depth=0)

    fake_desc: dict[str, Any] = {
        "id": child_id,
        "parent_id": note.id,
        "depth": 1,
        "position": 1000,
    }

    repo = _make_repo(note=note, parent=parent, descendants=[fake_desc])
    session = _make_session()
    service = MovePageService(session=session, note_repository=repo)

    result = await service.execute(
        MovePagePayload(
            note_id=note.id,
            new_parent_id=parent.id,
            workspace_id=workspace_id,
            actor_id=uuid.uuid4(),
        )
    )

    assert result.depth_delta == 1
    assert note.depth == 1
    # Verify the bulk UPDATE was executed with the depth delta
    assert session.execute.call_count >= 1


@pytest.mark.asyncio
async def test_move_exceeds_depth_limit() -> None:
    """Moving a note that would push a descendant beyond depth 2 raises ValueError."""
    workspace_id = uuid.uuid4()
    project_id = uuid.uuid4()

    # parent at depth=1; moving note under it -> note depth=2
    # note has a child at offset 1 from itself (depth=1 when note is depth=0)
    # so child would become depth=3 after move
    parent = _make_note(workspace_id=workspace_id, project_id=project_id, depth=1)
    note = _make_note(workspace_id=workspace_id, project_id=project_id, depth=0)

    fake_desc: dict[str, Any] = {
        "id": str(uuid.uuid4()),
        "parent_id": str(note.id),
        "depth": 1,  # offset from note=0 is 1; new_depth=2+1=3 > MAX_DEPTH
        "position": 1000,
    }

    repo = _make_repo(note=note, parent=parent, descendants=[fake_desc])
    session = _make_session()
    service = MovePageService(session=session, note_repository=repo)

    with pytest.raises(ValueError, match="descendant beyond the 3-level depth limit"):
        await service.execute(
            MovePagePayload(
                note_id=note.id,
                new_parent_id=parent.id,
                workspace_id=workspace_id,
                actor_id=uuid.uuid4(),
            )
        )


@pytest.mark.asyncio
async def test_move_cross_project_rejected() -> None:
    """Moving a page to a parent in a different project raises ValueError."""
    workspace_id = uuid.uuid4()
    project_id = uuid.uuid4()
    other_project_id = uuid.uuid4()

    note = _make_note(workspace_id=workspace_id, project_id=project_id, depth=0)
    parent = _make_note(workspace_id=workspace_id, project_id=other_project_id, depth=0)

    repo = _make_repo(note=note, parent=parent)
    session = _make_session()
    service = MovePageService(session=session, note_repository=repo)

    with pytest.raises(ValueError, match="different project"):
        await service.execute(
            MovePagePayload(
                note_id=note.id,
                new_parent_id=parent.id,
                workspace_id=workspace_id,
                actor_id=uuid.uuid4(),
            )
        )


@pytest.mark.asyncio
async def test_move_personal_page_rejected() -> None:
    """Moving a personal page (project_id=None) raises ValueError."""
    workspace_id = uuid.uuid4()

    note = _make_note(workspace_id=workspace_id, project_id=None, depth=0)

    repo = _make_repo(note=note)
    session = _make_session()
    service = MovePageService(session=session, note_repository=repo)

    with pytest.raises(ValueError, match="Personal page re-parenting not yet supported"):
        await service.execute(
            MovePagePayload(
                note_id=note.id,
                new_parent_id=uuid.uuid4(),
                workspace_id=workspace_id,
                actor_id=uuid.uuid4(),
            )
        )


@pytest.mark.asyncio
async def test_move_note_not_found() -> None:
    """Moving a non-existent note raises ValueError."""
    workspace_id = uuid.uuid4()

    repo = _make_repo()  # get_by_id always returns None
    session = _make_session()
    service = MovePageService(session=session, note_repository=repo)

    with pytest.raises(ValueError, match="Note not found"):
        await service.execute(
            MovePagePayload(
                note_id=uuid.uuid4(),
                new_parent_id=None,
                workspace_id=workspace_id,
                actor_id=uuid.uuid4(),
            )
        )


@pytest.mark.asyncio
async def test_move_target_parent_not_found() -> None:
    """Moving to a non-existent parent raises ValueError."""
    workspace_id = uuid.uuid4()
    project_id = uuid.uuid4()

    note = _make_note(workspace_id=workspace_id, project_id=project_id, depth=0)
    # parent is not registered in repo — returns None
    repo = _make_repo(note=note)
    session = _make_session()
    service = MovePageService(session=session, note_repository=repo)

    with pytest.raises(ValueError, match="Target parent not found"):
        await service.execute(
            MovePagePayload(
                note_id=note.id,
                new_parent_id=uuid.uuid4(),
                workspace_id=workspace_id,
                actor_id=uuid.uuid4(),
            )
        )


@pytest.mark.asyncio
async def test_move_note_to_deep_parent_exceeds_depth() -> None:
    """Moving any note under a depth-2 parent (new_depth=3) is rejected."""
    workspace_id = uuid.uuid4()
    project_id = uuid.uuid4()

    # parent is at depth 2; placing any note under it would give depth 3
    parent = _make_note(workspace_id=workspace_id, project_id=project_id, depth=2)
    note = _make_note(workspace_id=workspace_id, project_id=project_id, depth=0)

    repo = _make_repo(note=note, parent=parent)
    session = _make_session()
    service = MovePageService(session=session, note_repository=repo)

    with pytest.raises(ValueError, match="3-level depth limit"):
        await service.execute(
            MovePagePayload(
                note_id=note.id,
                new_parent_id=parent.id,
                workspace_id=workspace_id,
                actor_id=uuid.uuid4(),
            )
        )


# ---------------------------------------------------------------------------
# Issue 1: Self-parenting and ancestor-descendant cycle guard tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_move_page_to_itself_raises_value_error() -> None:
    """Moving a page to itself (new_parent_id == note.id) raises ValueError."""
    workspace_id = uuid.uuid4()
    project_id = uuid.uuid4()

    note = _make_note(workspace_id=workspace_id, project_id=project_id, depth=0)

    repo = _make_repo(note=note)
    session = _make_session()
    service = MovePageService(session=session, note_repository=repo)

    with pytest.raises(ValueError, match="Cannot move a page to itself"):
        await service.execute(
            MovePagePayload(
                note_id=note.id,
                new_parent_id=note.id,  # same as note.id
                workspace_id=workspace_id,
                actor_id=uuid.uuid4(),
            )
        )


@pytest.mark.asyncio
async def test_move_page_to_descendant_raises_cycle_error() -> None:
    """Moving a page to one of its own descendants raises ValueError containing 'cycle'."""
    workspace_id = uuid.uuid4()
    project_id = uuid.uuid4()

    note = _make_note(workspace_id=workspace_id, project_id=project_id, depth=0)
    child_id = uuid.uuid4()

    # Simulate child as a descendant of note
    fake_desc: dict[str, Any] = {
        "id": child_id,
        "parent_id": note.id,
        "depth": 1,
        "position": 1000,
    }

    # child acts as parent target
    child_parent = _make_note(
        workspace_id=workspace_id,
        project_id=project_id,
        depth=1,
        note_id=child_id,
    )

    repo = _make_repo(note=note, parent=child_parent, descendants=[fake_desc])
    session = _make_session()
    service = MovePageService(session=session, note_repository=repo)

    with pytest.raises(ValueError, match="cycle"):
        await service.execute(
            MovePagePayload(
                note_id=note.id,
                new_parent_id=child_id,  # child is a descendant of note
                workspace_id=workspace_id,
                actor_id=uuid.uuid4(),
            )
        )


# ---------------------------------------------------------------------------
# Issue 4: FOR UPDATE locking — verify get_siblings called with for_update=True
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_compute_tail_position_uses_for_update_locking() -> None:
    """_compute_tail_position passes for_update=True to get_siblings."""
    workspace_id = uuid.uuid4()
    project_id = uuid.uuid4()

    parent = _make_note(workspace_id=workspace_id, project_id=project_id, depth=0)
    note = _make_note(workspace_id=workspace_id, project_id=project_id, depth=0)

    repo = _make_repo(note=note, parent=parent)
    session = _make_session()
    service = MovePageService(session=session, note_repository=repo)

    await service.execute(
        MovePagePayload(
            note_id=note.id,
            new_parent_id=parent.id,
            workspace_id=workspace_id,
            actor_id=uuid.uuid4(),
        )
    )

    # Verify get_siblings was called with for_update=True
    repo.get_siblings.assert_called_once()
    call_kwargs = repo.get_siblings.call_args
    assert call_kwargs.kwargs.get("for_update") is True or (
        len(call_kwargs.args) > 4 and call_kwargs.args[4] is True
    )
