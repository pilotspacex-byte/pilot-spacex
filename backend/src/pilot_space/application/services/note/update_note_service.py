"""UpdateNoteService for updating existing notes.

Implements CQRS-lite command pattern for note updates.
Supports partial updates with optimistic locking.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, cast

from pilot_space.domain.exceptions import ConflictError, NotFoundError, ValidationError
from pilot_space.infrastructure.logging import get_logger

logger = get_logger(__name__)

# Sentinel that distinguishes "field omitted" from "field explicitly set to None".
# Used for icon_emoji to allow clearing (explicit None) vs no-op (UNSET).
UNSET: object = object()

if TYPE_CHECKING:
    from datetime import datetime
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from pilot_space.infrastructure.database.models.note import Note
    from pilot_space.infrastructure.database.repositories.audit_log_repository import (
        AuditLogRepository,
    )
    from pilot_space.infrastructure.database.repositories.note_repository import (
        NoteRepository,
    )
    from pilot_space.infrastructure.queue.supabase_queue import SupabaseQueueClient


class OptimisticLockError(ConflictError):
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
    actor_id: UUID | None = None
    title: str | None = None
    content: dict[str, Any] | None = None
    summary: str | None = None
    is_pinned: bool | None = None
    project_id: UUID | None = None
    clear_project_id: bool = False
    expected_updated_at: datetime | None = None
    # UNSET = field omitted (no-op); None = explicit clear; str = set value
    icon_emoji: str | None | object = field(default_factory=lambda: UNSET)


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

    def __init__(
        self,
        session: AsyncSession,
        note_repository: NoteRepository,
        queue: SupabaseQueueClient | None = None,
        audit_log_repository: AuditLogRepository | None = None,
    ) -> None:
        """Initialize UpdateNoteService.

        Args:
            session: The async database session.
            note_repository: Repository for note operations.
            queue: Optional queue client for KG populate jobs.
            audit_log_repository: Optional audit log repository for compliance writes.
        """
        self._session = session
        self._note_repo = note_repository
        self._queue = queue
        self._audit_repo = audit_log_repository

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
        # Fetch existing note
        note = await self._note_repo.get_by_id(payload.note_id)
        if not note:
            msg = f"Note with ID {payload.note_id} not found"
            raise NotFoundError(msg)

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
                raise ValidationError(msg)
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

        if payload.clear_project_id:
            note.project_id = None
            fields_updated.append("project_id")
        elif payload.project_id is not None:
            note.project_id = payload.project_id
            fields_updated.append("project_id")

        if payload.icon_emoji is not UNSET:
            # None or empty/whitespace string means "remove the emoji" — store as None
            if payload.icon_emoji is None or (
                isinstance(payload.icon_emoji, str) and not payload.icon_emoji.strip()
            ):
                note.icon_emoji = None
            else:
                note.icon_emoji = cast("str", payload.icon_emoji)
            fields_updated.append("icon_emoji")

        # Save changes
        if fields_updated:
            updated_note = await self._note_repo.update(note)
        else:
            updated_note = note

        # Write audit log entry (non-fatal)
        if self._audit_repo is not None and fields_updated:
            try:
                from pilot_space.infrastructure.database.models.audit_log import ActorType

                await self._audit_repo.create(
                    workspace_id=updated_note.workspace_id,
                    actor_id=payload.actor_id,
                    actor_type=ActorType.USER,
                    action="note.update",
                    resource_type="note",
                    resource_id=updated_note.id,
                    payload={"changed_fields": fields_updated},
                    ip_address=None,
                )
            except Exception as exc:
                logger.warning("UpdateNoteService: failed to write audit log: %s", exc)

        # Enqueue KG populate job if content changed and note belongs to a project (non-fatal)
        if (
            self._queue is not None
            and "content" in fields_updated
            and updated_note.project_id is not None
        ):
            try:
                from pilot_space.infrastructure.queue.models import QueueName

                await self._queue.enqueue(
                    QueueName.AI_NORMAL,
                    {
                        "task_type": "kg_populate",
                        "entity_type": "note",
                        "entity_id": str(updated_note.id),
                        "workspace_id": str(updated_note.workspace_id),
                        "project_id": str(updated_note.project_id),
                    },
                )
            except Exception as exc:
                logger.warning("UpdateNoteService: failed to enqueue kg_populate: %s", exc)

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
