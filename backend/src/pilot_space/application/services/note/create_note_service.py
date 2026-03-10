"""CreateNoteService for creating new notes.

Implements CQRS-lite command pattern for note creation.
Supports template-based creation and automatic metadata calculation.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from pilot_space.infrastructure.logging import get_logger

logger = get_logger(__name__)

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from pilot_space.infrastructure.database.models.note import Note
    from pilot_space.infrastructure.database.repositories.audit_log_repository import (
        AuditLogRepository,
    )
    from pilot_space.infrastructure.database.repositories.note_repository import (
        NoteRepository,
    )
    from pilot_space.infrastructure.database.repositories.template_repository import (
        TemplateRepository,
    )
    from pilot_space.infrastructure.queue.supabase_queue import SupabaseQueueClient


@dataclass(frozen=True, slots=True)
class CreateNotePayload:
    """Payload for creating a new note.

    Attributes:
        workspace_id: The workspace ID.
        owner_id: The user ID of the note creator.
        title: The note title.
        content: Optional TipTap JSON content (defaults to empty doc).
        summary: Optional note summary.
        project_id: Optional project ID to associate the note.
        template_id: Optional template ID to copy content from.
        is_pinned: Whether the note should be pinned.
    """

    workspace_id: UUID
    owner_id: UUID
    title: str
    content: dict[str, Any] | None = None
    summary: str | None = None
    project_id: UUID | None = None
    template_id: UUID | None = None
    is_pinned: bool = False


@dataclass(frozen=True, slots=True)
class CreateNoteResult:
    """Result from note creation.

    Attributes:
        note: The created note.
        word_count: Calculated word count.
        reading_time_mins: Calculated reading time.
        template_applied: Whether a template was applied.
    """

    note: Note
    word_count: int = 0
    reading_time_mins: int = 0
    template_applied: bool = False


class CreateNoteService:
    """Service for creating notes.

    Handles note creation with optional template copying,
    word count calculation, and reading time estimation.
    """

    def __init__(
        self,
        session: AsyncSession,
        note_repository: NoteRepository,
        template_repository: TemplateRepository,
        queue: SupabaseQueueClient | None = None,
        audit_log_repository: AuditLogRepository | None = None,
    ) -> None:
        """Initialize CreateNoteService.

        Args:
            session: The async database session.
            note_repository: Repository for note operations.
            template_repository: Repository for template operations.
            queue: Optional queue client for KG populate jobs.
            audit_log_repository: Optional audit log repository for compliance writes.
        """
        self._session = session
        self._note_repo = note_repository
        self._template_repo = template_repository
        self._queue = queue
        self._audit_repo = audit_log_repository

    async def execute(self, payload: CreateNotePayload) -> CreateNoteResult:
        """Execute note creation.

        Args:
            payload: The creation payload.

        Returns:
            CreateNoteResult with created note and metadata.

        Raises:
            ValueError: If validation fails.
        """
        from pilot_space.infrastructure.database.models.note import Note

        # Validate title
        if not payload.title or not payload.title.strip():
            msg = "Note title is required"
            raise ValueError(msg)

        # Get template content if template_id provided
        content = payload.content or self._get_empty_doc()
        template_applied = False

        if payload.template_id:
            template = await self._template_repo.get_by_id(payload.template_id)
            if template and template.content:
                content = template.content
                template_applied = True

        # Calculate word count and reading time
        word_count = self._calculate_word_count(content)
        reading_time_mins = self._calculate_reading_time(word_count)

        # Create note
        note = Note(
            workspace_id=payload.workspace_id,
            owner_id=payload.owner_id,
            title=payload.title.strip(),
            content=content,
            summary=payload.summary,
            word_count=word_count,
            reading_time_mins=reading_time_mins,
            is_pinned=payload.is_pinned,
            template_id=payload.template_id,
            project_id=payload.project_id,
        )

        created_note = await self._note_repo.create(note)

        # Write audit log entry (non-fatal)
        if self._audit_repo is not None:
            try:
                from pilot_space.infrastructure.database.models.audit_log import ActorType

                await self._audit_repo.create(
                    workspace_id=payload.workspace_id,
                    actor_id=payload.owner_id,
                    actor_type=ActorType.USER,
                    action="note.create",
                    resource_type="note",
                    resource_id=created_note.id,
                    payload={
                        "before": {},
                        "after": {
                            "title": created_note.title,
                            "project_id": (str(payload.project_id) if payload.project_id else None),
                        },
                    },
                    ip_address=None,
                )
            except Exception as exc:
                logger.warning("CreateNoteService: failed to write audit log: %s", exc)

        # Enqueue KG populate job if note belongs to a project (non-fatal)
        if self._queue is not None and payload.project_id is not None:
            try:
                from pilot_space.infrastructure.queue.models import QueueName

                await self._queue.enqueue(
                    QueueName.AI_NORMAL,
                    {
                        "task_type": "kg_populate",
                        "entity_type": "note",
                        "entity_id": str(created_note.id),
                        "workspace_id": str(payload.workspace_id),
                        "project_id": str(payload.project_id),
                    },
                )
            except Exception as exc:
                logger.warning("CreateNoteService: failed to enqueue kg_populate: %s", exc)

        return CreateNoteResult(
            note=created_note,
            word_count=word_count,
            reading_time_mins=reading_time_mins,
            template_applied=template_applied,
        )

    def _get_empty_doc(self) -> dict[str, Any]:
        """Get empty TipTap document structure.

        Returns:
            Empty TipTap document as dict.
        """
        return {
            "type": "doc",
            "content": [
                {
                    "type": "paragraph",
                    "content": [],
                }
            ],
        }

    def _calculate_word_count(self, content: dict[str, Any]) -> int:
        """Calculate word count from TipTap JSON content.

        Extracts text from TipTap document and counts words.

        Args:
            content: TipTap JSON document.

        Returns:
            Word count.
        """
        text = self._extract_text_from_content(content)
        if not text:
            return 0
        # Split by whitespace and filter empty strings
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

        # Get text content if this is a text node
        if content.get("type") == "text" and "text" in content:
            text_parts.append(str(content["text"]))

        # Recursively process child content
        child_content: list[dict[str, Any]] | None = content.get("content")  # type: ignore[assignment]
        if child_content is not None:
            text_parts.extend(self._extract_text_from_content(child) for child in child_content)

        return " ".join(text_parts)

    def _calculate_reading_time(self, word_count: int) -> int:
        """Calculate reading time based on word count.

        Assumes average reading speed of 200 words per minute.

        Args:
            word_count: Number of words.

        Returns:
            Reading time in minutes (minimum 1 if content exists).
        """
        if word_count <= 0:
            return 0
        return max(1, word_count // 200)
