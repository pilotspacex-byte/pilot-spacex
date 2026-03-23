"""Unit tests for CreateNoteService tree-related behavior.

Covers parent_id support: depth computation, position calculation,
depth limit enforcement, and personal-page nesting rejection.

MagicMock strategy is used (same as test_move_page_service.py):
- Avoids SQLAlchemy ORM instrumentation issues
- Does not require spinning up related tables in SQLite
"""

from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from pilot_space.application.services.note.create_note_service import (
    CreateNotePayload,
    CreateNoteService,
)
from pilot_space.domain.exceptions import NotFoundError, ValidationError
from pilot_space.infrastructure.database.models.note import Note

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_note_mock(
    *,
    depth: int = 0,
    position: int = 1000,
    project_id: uuid.UUID | None = None,
    parent_id: uuid.UUID | None = None,
    note_id: uuid.UUID | None = None,
) -> MagicMock:
    """Create a MagicMock behaving like a Note ORM instance."""
    note = MagicMock(spec=Note)
    note.id = note_id or uuid.uuid4()
    note.depth = depth
    note.position = position
    note.project_id = project_id
    note.parent_id = parent_id
    note.title = "Test Note"
    note.is_deleted = False
    return note


def _make_repo(
    *,
    parent: MagicMock | None = None,
    existing_children: list[MagicMock] | None = None,
) -> MagicMock:
    """Build MagicMock NoteRepository with pre-configured async methods."""
    repo = MagicMock()

    async def _get_by_id(id_: uuid.UUID) -> MagicMock | None:
        if parent is not None and id_ == parent.id:
            return parent
        return None

    repo.get_by_id = AsyncMock(side_effect=_get_by_id)
    repo.get_children = AsyncMock(return_value=existing_children or [])

    # create returns whatever note is passed to it
    async def _create(note: Any) -> Any:
        return note

    repo.create = AsyncMock(side_effect=_create)
    return repo


def _make_session() -> MagicMock:
    """Build MagicMock AsyncSession."""
    session = MagicMock(spec=AsyncSession)
    session.add = MagicMock()
    session.flush = AsyncMock()
    return session


def _make_service(repo: MagicMock) -> CreateNoteService:
    """Build CreateNoteService with mocked dependencies."""
    template_repo = MagicMock()
    template_repo.get_by_id = AsyncMock(return_value=None)
    return CreateNoteService(
        session=_make_session(),
        note_repository=repo,
        template_repository=template_repo,
        queue=None,
        audit_log_repository=None,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestCreateNoteNoParent:
    """Test 1: Creating note with parent_id=None behaves as before."""

    @pytest.mark.asyncio
    async def test_no_parent_creates_root_note(self) -> None:
        """Note with no parent_id gets depth=0 and position=0."""
        workspace_id = uuid.uuid4()
        owner_id = uuid.uuid4()
        project_id = uuid.uuid4()

        repo = _make_repo()
        service = _make_service(repo)

        payload = CreateNotePayload(
            workspace_id=workspace_id,
            owner_id=owner_id,
            title="Root Note",
            project_id=project_id,
            parent_id=None,
        )

        result = await service.execute(payload)

        assert result.note.depth == 0
        assert result.note.position == 0
        assert result.note.parent_id is None
        # get_by_id should NOT be called when parent_id is None
        repo.get_by_id.assert_not_called()


class TestCreateNoteWithValidParent:
    """Test 2: Creating note with valid parent_id computes correct depth and position."""

    @pytest.mark.asyncio
    async def test_child_gets_parent_depth_plus_one(self) -> None:
        """Child note depth = parent.depth + 1."""
        workspace_id = uuid.uuid4()
        project_id = uuid.uuid4()
        parent_id = uuid.uuid4()

        parent = _make_note_mock(depth=0, position=1000, project_id=project_id, note_id=parent_id)
        # No existing siblings — first child
        repo = _make_repo(parent=parent, existing_children=[])
        service = _make_service(repo)

        payload = CreateNotePayload(
            workspace_id=workspace_id,
            owner_id=uuid.uuid4(),
            title="Child Note",
            project_id=project_id,
            parent_id=parent_id,
        )

        result = await service.execute(payload)

        assert result.note.depth == 1
        assert result.note.parent_id == parent_id

    @pytest.mark.asyncio
    async def test_first_child_gets_position_1000(self) -> None:
        """First child (no siblings) gets position=1000."""
        workspace_id = uuid.uuid4()
        project_id = uuid.uuid4()
        parent_id = uuid.uuid4()

        parent = _make_note_mock(depth=0, project_id=project_id, note_id=parent_id)
        repo = _make_repo(parent=parent, existing_children=[])
        service = _make_service(repo)

        payload = CreateNotePayload(
            workspace_id=workspace_id,
            owner_id=uuid.uuid4(),
            title="First Child",
            project_id=project_id,
            parent_id=parent_id,
        )

        result = await service.execute(payload)

        assert result.note.position == 1000

    @pytest.mark.asyncio
    async def test_child_with_siblings_gets_max_plus_1000(self) -> None:
        """Child with existing siblings gets position = max_sibling_position + 1000."""
        workspace_id = uuid.uuid4()
        project_id = uuid.uuid4()
        parent_id = uuid.uuid4()

        parent = _make_note_mock(depth=0, project_id=project_id, note_id=parent_id)
        child1 = _make_note_mock(position=1000)
        child2 = _make_note_mock(position=2000)
        repo = _make_repo(parent=parent, existing_children=[child1, child2])
        service = _make_service(repo)

        payload = CreateNotePayload(
            workspace_id=workspace_id,
            owner_id=uuid.uuid4(),
            title="Third Child",
            project_id=project_id,
            parent_id=parent_id,
        )

        result = await service.execute(payload)

        # max sibling position = 2000, so new child gets 2000 + 1000 = 3000
        assert result.note.position == 3000

    @pytest.mark.asyncio
    async def test_grandchild_gets_depth_two(self) -> None:
        """Grandchild (parent.depth=1) gets depth=2."""
        workspace_id = uuid.uuid4()
        project_id = uuid.uuid4()
        parent_id = uuid.uuid4()

        parent = _make_note_mock(depth=1, project_id=project_id, note_id=parent_id)
        repo = _make_repo(parent=parent, existing_children=[])
        service = _make_service(repo)

        payload = CreateNotePayload(
            workspace_id=workspace_id,
            owner_id=uuid.uuid4(),
            title="Grandchild Note",
            project_id=project_id,
            parent_id=parent_id,
        )

        result = await service.execute(payload)

        assert result.note.depth == 2


class TestCreateNoteDepthLimitExceeded:
    """Test 3: Creating note with parent at depth=2 raises ValueError."""

    @pytest.mark.asyncio
    async def test_depth_limit_exceeded_raises_value_error(self) -> None:
        """Cannot create child of a depth-2 note (would exceed 3-level limit)."""
        workspace_id = uuid.uuid4()
        project_id = uuid.uuid4()
        parent_id = uuid.uuid4()

        # Parent is at depth=2 — creating child would be depth=3 (exceeds max)
        parent = _make_note_mock(depth=2, project_id=project_id, note_id=parent_id)
        repo = _make_repo(parent=parent, existing_children=[])
        service = _make_service(repo)

        payload = CreateNotePayload(
            workspace_id=workspace_id,
            owner_id=uuid.uuid4(),
            title="Too Deep Note",
            project_id=project_id,
            parent_id=parent_id,
        )

        with pytest.raises(ValidationError, match="depth"):
            await service.execute(payload)

    @pytest.mark.asyncio
    async def test_parent_not_found_raises_value_error(self) -> None:
        """Non-existent parent_id raises ValueError."""
        workspace_id = uuid.uuid4()
        project_id = uuid.uuid4()
        nonexistent_parent_id = uuid.uuid4()

        repo = _make_repo(parent=None)
        service = _make_service(repo)

        payload = CreateNotePayload(
            workspace_id=workspace_id,
            owner_id=uuid.uuid4(),
            title="Orphan Note",
            project_id=project_id,
            parent_id=nonexistent_parent_id,
        )

        with pytest.raises(NotFoundError, match=r"(?i)parent"):
            await service.execute(payload)


class TestCreateNotePersonalPageNesting:
    """Test 4: Creating note with parent_id but no project_id raises ValueError."""

    @pytest.mark.asyncio
    async def test_personal_page_nesting_rejected(self) -> None:
        """Personal pages (no project_id) cannot have a parent_id."""
        workspace_id = uuid.uuid4()
        parent_id = uuid.uuid4()

        parent = _make_note_mock(depth=0, project_id=None, note_id=parent_id)
        repo = _make_repo(parent=parent, existing_children=[])
        service = _make_service(repo)

        payload = CreateNotePayload(
            workspace_id=workspace_id,
            owner_id=uuid.uuid4(),
            title="Nested Personal Note",
            project_id=None,  # No project — personal page
            parent_id=parent_id,
        )

        with pytest.raises(ValidationError, match="personal"):
            await service.execute(payload)
