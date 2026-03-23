"""Unit tests for UpdateNoteService.

Tests cover emoji clear semantics (Issue 5), icon_emoji serialization,
and the UNSET sentinel pattern to distinguish explicit null from omitted field.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from pilot_space.application.services.note.update_note_service import (
    UNSET,
    UpdateNotePayload,
    UpdateNoteService,
)
from pilot_space.domain.exceptions import NotFoundError
from pilot_space.infrastructure.database.models.note import Note

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_note(
    *,
    note_id: uuid.UUID | None = None,
    workspace_id: uuid.UUID | None = None,
    title: str = "Test Note",
    content: dict[str, Any] | None = None,
    icon_emoji: str | None = None,
    word_count: int = 0,
    reading_time_mins: int = 0,
    updated_at: datetime | None = None,
    project_id: uuid.UUID | None = None,
) -> MagicMock:
    """Create a MagicMock that behaves like a Note instance."""
    note = MagicMock(spec=Note)
    note.id = note_id or uuid.uuid4()
    note.workspace_id = workspace_id or uuid.uuid4()
    note.title = title
    note.content = content or {}
    note.icon_emoji = icon_emoji
    note.word_count = word_count
    note.reading_time_mins = reading_time_mins
    note.updated_at = updated_at or datetime(2024, 1, 1, tzinfo=UTC)
    note.project_id = project_id
    note.is_pinned = False
    note.summary = None
    note.owner_id = uuid.uuid4()
    return note


def _make_repo(note: MagicMock | None = None) -> MagicMock:
    """Build a MagicMock NoteRepository."""
    repo = MagicMock()
    repo.get_by_id = AsyncMock(return_value=note)
    repo.update = AsyncMock(side_effect=lambda n: n)
    return repo


def _make_session() -> MagicMock:
    """Build a MagicMock AsyncSession."""
    session = MagicMock(spec=AsyncSession)
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    return session


# ---------------------------------------------------------------------------
# Issue 5: UNSET sentinel for icon_emoji clear vs omit
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_icon_emoji_omitted_is_no_op() -> None:
    """When icon_emoji is not provided (UNSET), existing emoji is preserved."""
    note = _make_note(icon_emoji="🚀")

    repo = _make_repo(note=note)
    session = _make_session()
    service = UpdateNoteService(session=session, note_repository=repo)

    # icon_emoji defaults to UNSET — verify the sentinel is not None
    assert UNSET is not None
    payload = UpdateNotePayload(
        note_id=note.id,
        title="Updated Title",
    )
    result = await service.execute(payload)

    assert result.note.icon_emoji == "🚀"
    assert "icon_emoji" not in result.fields_updated


@pytest.mark.asyncio
async def test_icon_emoji_explicit_none_clears_field() -> None:
    """When icon_emoji=None is explicitly passed, emoji is cleared (set to None)."""
    note = _make_note(icon_emoji="🚀")

    repo = _make_repo(note=note)
    session = _make_session()
    service = UpdateNoteService(session=session, note_repository=repo)

    payload = UpdateNotePayload(
        note_id=note.id,
        icon_emoji=None,  # explicitly cleared
    )
    result = await service.execute(payload)

    assert result.note.icon_emoji is None
    assert "icon_emoji" in result.fields_updated


@pytest.mark.asyncio
async def test_icon_emoji_empty_string_clears_field() -> None:
    """When icon_emoji is an empty string, emoji is cleared (stored as None)."""
    note = _make_note(icon_emoji="🚀")

    repo = _make_repo(note=note)
    session = _make_session()
    service = UpdateNoteService(session=session, note_repository=repo)

    payload = UpdateNotePayload(
        note_id=note.id,
        icon_emoji="",  # empty string means remove
    )
    result = await service.execute(payload)

    assert result.note.icon_emoji is None
    assert "icon_emoji" in result.fields_updated


@pytest.mark.asyncio
async def test_icon_emoji_set_to_new_value() -> None:
    """When icon_emoji is set to a non-empty string, it updates the field."""
    note = _make_note(icon_emoji=None)

    repo = _make_repo(note=note)
    session = _make_session()
    service = UpdateNoteService(session=session, note_repository=repo)

    payload = UpdateNotePayload(
        note_id=note.id,
        icon_emoji="📝",
    )
    result = await service.execute(payload)

    assert result.note.icon_emoji == "📝"
    assert "icon_emoji" in result.fields_updated


@pytest.mark.asyncio
async def test_icon_emoji_whitespace_only_clears_field() -> None:
    """When icon_emoji is whitespace-only, it is treated as clear."""
    note = _make_note(icon_emoji="🚀")

    repo = _make_repo(note=note)
    session = _make_session()
    service = UpdateNoteService(session=session, note_repository=repo)

    payload = UpdateNotePayload(
        note_id=note.id,
        icon_emoji="   ",  # whitespace only
    )
    result = await service.execute(payload)

    assert result.note.icon_emoji is None
    assert "icon_emoji" in result.fields_updated


@pytest.mark.asyncio
async def test_note_not_found_raises_value_error() -> None:
    """When note does not exist, execute raises NotFoundError."""
    repo = _make_repo(note=None)
    session = _make_session()
    service = UpdateNoteService(session=session, note_repository=repo)

    payload = UpdateNotePayload(note_id=uuid.uuid4(), title="New Title")

    with pytest.raises(NotFoundError, match="not found"):
        await service.execute(payload)


@pytest.mark.asyncio
async def test_title_update_trims_whitespace() -> None:
    """Title update strips surrounding whitespace."""
    note = _make_note(title="Old Title")

    repo = _make_repo(note=note)
    session = _make_session()
    service = UpdateNoteService(session=session, note_repository=repo)

    payload = UpdateNotePayload(
        note_id=note.id,
        title="  New Title  ",
    )
    result = await service.execute(payload)

    assert result.note.title == "New Title"
    assert "title" in result.fields_updated


@pytest.mark.asyncio
async def test_no_fields_updated_returns_existing_note() -> None:
    """When payload has no changes, repo.update is not called."""
    note = _make_note()

    repo = _make_repo(note=note)
    session = _make_session()
    service = UpdateNoteService(session=session, note_repository=repo)

    payload = UpdateNotePayload(note_id=note.id)  # all fields UNSET or None
    result = await service.execute(payload)

    assert result.fields_updated == []
    repo.update.assert_not_called()
