"""UpdateNoteService for updating existing notes.

Implements CQRS-lite command pattern for note updates.
Supports partial updates with optimistic locking.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from datetime import datetime
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from pilot_space.infrastructure.database.models.note import Note


class OptimisticLockError(Exception):
    """Raised when optimistic lock check fails."""


@dataclass(slots=True)
class UpdateNotePayload:
    """Payload for updating an existing note.

    All fields except note_id are optional for partial updates.
    Provide expected_updated_at for optimistic locking.

    Attributes:
        note_id: The note ID to update.
        title: New title (if updating).
        content: New TipTap JSON content (if updating).
        summary: New summary (if updating).
        is_pinned: New pinned status (if updating).
        project_id: New project association (if updating).
        expected_updated_at: For optimistic locking - update only if this matches.
    """

    note_id: UUID
    title: str | None = None
    content: dict[str, Any] | None = None
    summary: str | None = None
    is_pinned: bool | None = None
    project_id: UUID | None = None
    expected_updated_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class UpdateNoteResult:
    """Result from note update.

    Attributes:
        note: The updated note.
        word_count: Updated word count.
        reading_time_mins: Updated reading time.
        fields_updated: List of fields that were updated.
    """

    note: Note
    word_count: int
    reading_time_mins: int
    fields_updated: list[str]


class UpdateNoteService:
    """Service for updating notes.

    Handles partial note updates with optimistic locking,
    recalculates word count and reading time when content changes.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize UpdateNoteService.

        Args:
            session: The async database session.
        """
        self._session = session

    async def execute(self, payload: UpdateNotePayload) -> UpdateNoteResult:
        """Execute note update.

        Args:
            payload: The update payload.

        Returns:
            UpdateNoteResult with updated note and metadata.

        Raises:
            ValueError: If note not found or validation fails.
            OptimisticLockError: If expected_updated_at doesn't match.
        """
        from pilot_space.infrastructure.database.repositories.note_repository import (
            NoteRepository,
        )

        note_repo = NoteRepository(self._session)

        # Fetch existing note
        note = await note_repo.get_by_id(payload.note_id)
        if not note:
            msg = f"Note with ID {payload.note_id} not found"
            raise ValueError(msg)

        # Optimistic lock check
        if (
            payload.expected_updated_at is not None
            and note.updated_at != payload.expected_updated_at
        ):
            msg = (
                f"Note was modified by another user. "
                f"Expected updated_at: {payload.expected_updated_at}, "
                f"Actual: {note.updated_at}"
            )
            raise OptimisticLockError(msg)

        # Track updated fields
        fields_updated: list[str] = []

        # Apply updates
        if payload.title is not None:
            if not payload.title.strip():
                msg = "Note title cannot be empty"
                raise ValueError(msg)
            note.title = payload.title.strip()
            fields_updated.append("title")

        if payload.content is not None:
            note.content = payload.content
            note.word_count = self._calculate_word_count(payload.content)
            note.reading_time_mins = self._calculate_reading_time(note.word_count)
            fields_updated.extend(["content", "word_count", "reading_time_mins"])

        if payload.summary is not None:
            note.summary = payload.summary
            fields_updated.append("summary")

        if payload.is_pinned is not None:
            note.is_pinned = payload.is_pinned
            fields_updated.append("is_pinned")

        if payload.project_id is not None:
            note.project_id = payload.project_id
            fields_updated.append("project_id")

        # Save changes
        if fields_updated:
            updated_note = await note_repo.update(note)
        else:
            updated_note = note

        return UpdateNoteResult(
            note=updated_note,
            word_count=updated_note.word_count,
            reading_time_mins=updated_note.reading_time_mins,
            fields_updated=fields_updated,
        )

    def _calculate_word_count(self, content: dict[str, Any]) -> int:
        """Calculate word count from TipTap JSON content.

        Args:
            content: TipTap JSON document.

        Returns:
            Word count.
        """
        text = self._extract_text_from_content(content)
        if not text:
            return 0
        words = [w for w in re.split(r"\s+", text) if w]
        return len(words)

    def _extract_text_from_content(self, content: dict[str, Any]) -> str:
        """Recursively extract text from TipTap JSON content.

        Args:
            content: TipTap JSON node.

        Returns:
            Extracted text.
        """
        text_parts: list[str] = []

        if content.get("type") == "text" and "text" in content:
            text_parts.append(str(content["text"]))

        child_content: list[dict[str, Any]] | None = content.get("content")  # type: ignore[assignment]
        if child_content is not None:
            text_parts.extend(self._extract_text_from_content(child) for child in child_content)

        return " ".join(text_parts)

    def _calculate_reading_time(self, word_count: int) -> int:
        """Calculate reading time based on word count.

        Args:
            word_count: Number of words.

        Returns:
            Reading time in minutes (minimum 1 if content exists).
        """
        if word_count <= 0:
            return 0
        return max(1, word_count // 200)
