"""Unit tests for workspace_note_links router.

Tests REST API endpoints for note-to-note link CRUD operations.
Uses mock repositories to isolate router logic.
"""

from __future__ import annotations

from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from pydantic import ValidationError

from pilot_space.api.v1.routers.workspace_note_links import (
    BacklinkResponse,
    CreateNoteLinkRequest,
    NoteLinkResponse,
    _link_to_backlink_response,
    _link_to_response,
    _parse_uuid_or_400,
)
from pilot_space.infrastructure.database.models.note_note_link import (
    NoteNoteLink,
    NoteNoteLinkType,
)


class TestParseUuidOr400:
    """Tests for _parse_uuid_or_400 helper."""

    def test_valid_uuid(self) -> None:
        uid = uuid4()
        result = _parse_uuid_or_400(str(uid), "workspace")
        assert result == uid

    def test_invalid_uuid_raises_400(self) -> None:
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            _parse_uuid_or_400("not-a-uuid", "workspace")
        assert exc_info.value.status_code == 400


class TestLinkToResponse:
    """Tests for response conversion helpers."""

    def test_link_to_response(self) -> None:
        link = MagicMock(spec=NoteNoteLink)
        link.id = uuid4()
        link.source_note_id = uuid4()
        link.target_note_id = uuid4()
        link.link_type = NoteNoteLinkType.INLINE
        link.block_id = "block-1"
        link.workspace_id = uuid4()
        link.target_note = MagicMock()
        link.target_note.title = "My Target Note"

        response = _link_to_response(link)

        assert isinstance(response, NoteLinkResponse)
        assert response.id == link.id
        assert response.source_note_id == link.source_note_id
        assert response.target_note_id == link.target_note_id
        assert response.link_type == "inline"
        assert response.block_id == "block-1"
        assert response.target_note_title == "My Target Note"

    def test_link_to_response_no_target_note(self) -> None:
        link = MagicMock(spec=NoteNoteLink)
        link.id = uuid4()
        link.source_note_id = uuid4()
        link.target_note_id = uuid4()
        link.link_type = NoteNoteLinkType.EMBED
        link.block_id = None
        link.workspace_id = uuid4()
        link.target_note = None

        response = _link_to_response(link)

        assert response.target_note_title is None

    def test_link_to_backlink_response(self) -> None:
        link = MagicMock(spec=NoteNoteLink)
        link.id = uuid4()
        link.source_note_id = uuid4()
        link.target_note_id = uuid4()
        link.link_type = NoteNoteLinkType.INLINE
        link.block_id = None
        link.workspace_id = uuid4()
        link.source_note = MagicMock()
        link.source_note.title = "Source Note Title"

        response = _link_to_backlink_response(link)

        assert isinstance(response, BacklinkResponse)
        assert response.source_note_title == "Source Note Title"


class TestCreateNoteLinkRequest:
    """Tests for request schema validation."""

    def test_default_values(self) -> None:
        req = CreateNoteLinkRequest(target_note_id=uuid4())
        assert req.link_type == "inline"
        assert req.block_id is None

    def test_custom_values(self) -> None:
        target_id = uuid4()
        req = CreateNoteLinkRequest(
            target_note_id=target_id,
            link_type="embed",
            block_id="block-abc",
        )
        assert req.target_note_id == target_id
        assert req.link_type == "embed"
        assert req.block_id == "block-abc"

    def test_invalid_link_type_raises_validation_error(self) -> None:
        """Invalid link_type must raise 422 at schema level, not silently default."""
        with pytest.raises(ValidationError) as exc_info:
            CreateNoteLinkRequest(
                target_note_id=uuid4(),
                link_type="malicious_value",  # type: ignore[arg-type]
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("link_type",) for e in errors)

    def test_uppercase_link_type_raises_validation_error(self) -> None:
        """Pydantic Literal is case-sensitive — INLINE is not a valid value."""
        with pytest.raises(ValidationError):
            CreateNoteLinkRequest(
                target_note_id=uuid4(),
                link_type="INLINE",  # type: ignore[arg-type]
            )
