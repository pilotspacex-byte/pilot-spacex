"""Tests for icon_emoji field in Note schemas.

Verifies NoteUpdate accepts and validates icon_emoji,
NoteResponse includes icon_emoji, and related constraints.
"""

from __future__ import annotations

from typing import ClassVar

import pytest
from pydantic import ValidationError

from pilot_space.api.v1.schemas.note import NoteResponse, NoteUpdate, PageTreeResponse


class TestNoteUpdateIconEmoji:
    """Tests for icon_emoji field on NoteUpdate schema."""

    def test_accepts_valid_emoji(self) -> None:
        schema = NoteUpdate(icon_emoji="📝")
        assert schema.icon_emoji == "📝"

    def test_accepts_none(self) -> None:
        schema = NoteUpdate(icon_emoji=None)
        assert schema.icon_emoji is None

    def test_defaults_to_none_when_not_provided(self) -> None:
        schema = NoteUpdate()
        assert schema.icon_emoji is None

    def test_accepts_empty_string(self) -> None:
        # Empty string is valid input (means "remove emoji") — service layer converts to None
        schema = NoteUpdate(icon_emoji="")
        assert schema.icon_emoji == ""

    def test_rejects_emoji_exceeding_10_chars(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            NoteUpdate(icon_emoji="a" * 11)
        errors = exc_info.value.errors()
        assert any("icon_emoji" in str(e) for e in errors)

    def test_accepts_emoji_exactly_10_chars(self) -> None:
        schema = NoteUpdate(icon_emoji="a" * 10)
        assert schema.icon_emoji == "a" * 10

    def test_accepts_multi_char_emoji(self) -> None:
        # Some emojis are multi-byte unicode — string length matters, not bytes
        schema = NoteUpdate(icon_emoji="🚀")
        assert schema.icon_emoji == "🚀"


class TestNoteResponseIconEmoji:
    """Tests for icon_emoji field on NoteResponse schema."""

    _base_fields: ClassVar[dict[str, object]] = {
        "id": "00000000-0000-0000-0000-000000000001",
        "workspace_id": "00000000-0000-0000-0000-000000000002",
        "title": "Test Note",
        "is_pinned": False,
        "word_count": 100,
        "last_edited_by_id": None,
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
    }

    def test_includes_icon_emoji_when_set(self) -> None:
        schema = NoteResponse(**self._base_fields, icon_emoji="📝")
        assert schema.icon_emoji == "📝"

    def test_icon_emoji_defaults_to_none_when_not_provided(self) -> None:
        schema = NoteResponse(**self._base_fields)
        assert schema.icon_emoji is None

    def test_icon_emoji_is_none_when_explicitly_none(self) -> None:
        schema = NoteResponse(**self._base_fields, icon_emoji=None)
        assert schema.icon_emoji is None


class TestPageTreeResponseIconEmoji:
    """Tests that PageTreeResponse inherits icon_emoji from NoteResponse."""

    _base_fields: ClassVar[dict[str, object]] = {
        "id": "00000000-0000-0000-0000-000000000001",
        "workspace_id": "00000000-0000-0000-0000-000000000002",
        "title": "Tree Node",
        "is_pinned": False,
        "word_count": 0,
        "last_edited_by_id": None,
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
        "parent_id": None,
        "depth": 0,
        "position": 1000,
    }

    def test_page_tree_response_inherits_icon_emoji(self) -> None:
        schema = PageTreeResponse(**self._base_fields, icon_emoji="🌳")
        assert schema.icon_emoji == "🌳"

    def test_page_tree_response_icon_emoji_defaults_to_none(self) -> None:
        schema = PageTreeResponse(**self._base_fields)
        assert schema.icon_emoji is None
