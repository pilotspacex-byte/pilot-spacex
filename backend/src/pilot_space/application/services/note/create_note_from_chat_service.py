"""Service for creating a note from a homepage chat session.

Fetches AI chat messages from the session, structures them as
TipTap content blocks, and creates a Note linked to the source
session via source_chat_session_id.

References:
- specs/012-homepage-note/spec.md Chat-to-Note Endpoint
- US-19: Homepage Hub feature
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any
from uuid import UUID

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class CreateNoteFromChatPayload:
    """Payload for creating a note from a chat session.

    Attributes:
        workspace_id: Workspace scope.
        user_id: User creating the note.
        chat_session_id: Source AI session ID.
        title: Note title.
        project_id: Optional project to associate.
    """

    workspace_id: UUID
    user_id: UUID
    chat_session_id: UUID
    title: str
    project_id: UUID | None = None


@dataclass
class CreateNoteFromChatResult:
    """Result from creating a note from chat.

    Attributes:
        note_id: ID of the created note.
        title: Final note title.
        source_chat_session_id: Linked session ID.
    """

    note_id: UUID
    title: str
    source_chat_session_id: UUID


class CreateNoteFromChatService:
    """Service for converting a homepage chat session into a note.

    Retrieves the AISession and its messages, builds TipTap
    JSON content from the conversation, calculates word count,
    and creates the Note with source_chat_session_id populated.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize CreateNoteFromChatService.

        Args:
            session: The async database session.
        """
        self._session = session

    async def execute(self, payload: CreateNoteFromChatPayload) -> CreateNoteFromChatResult:
        """Execute note creation from chat.

        Args:
            payload: The creation payload.

        Returns:
            CreateNoteFromChatResult with created note metadata.

        Raises:
            ValueError: If title is empty or session not found.
        """
        from pilot_space.infrastructure.database.models.ai_message import MessageRole
        from pilot_space.infrastructure.database.models.ai_session import AISession
        from pilot_space.infrastructure.database.models.note import Note
        from pilot_space.infrastructure.database.repositories.note_repository import (
            NoteRepository,
        )

        if not payload.title or not payload.title.strip():
            msg = "Note title is required"
            raise ValueError(msg)

        # Fetch the AI session
        ai_session = await self._session.get(AISession, payload.chat_session_id)
        if ai_session is None:
            msg = f"Chat session {payload.chat_session_id} not found"
            raise ValueError(msg)

        # Verify workspace ownership
        if ai_session.workspace_id != payload.workspace_id:
            msg = "Chat session does not belong to this workspace"
            raise ValueError(msg)

        # Build TipTap content from messages
        messages = sorted(ai_session.messages, key=lambda m: m.created_at)
        content = self._build_tiptap_content(messages, MessageRole)

        # Calculate word count
        word_count = self._calculate_word_count(content)
        reading_time_mins = max(1, word_count // 200) if word_count > 0 else 0

        # Create the note
        note = Note(
            workspace_id=payload.workspace_id,
            owner_id=payload.user_id,
            title=payload.title.strip(),
            content=content,
            word_count=word_count,
            reading_time_mins=reading_time_mins,
            project_id=payload.project_id,
            source_chat_session_id=payload.chat_session_id,
        )

        note_repo = NoteRepository(self._session)
        created_note = await note_repo.create(note)

        logger.info(
            "Note created from chat session",
            extra={
                "note_id": str(created_note.id),
                "session_id": str(payload.chat_session_id),
                "word_count": word_count,
            },
        )

        return CreateNoteFromChatResult(
            note_id=created_note.id,
            title=created_note.title,
            source_chat_session_id=payload.chat_session_id,
        )

    @staticmethod
    def _build_tiptap_content(messages: list[Any], role_enum: type) -> dict[str, Any]:
        """Convert chat messages into TipTap document structure.

        User messages become blockquotes, assistant messages become
        regular paragraphs. System messages are skipped.

        Args:
            messages: Sorted list of AIMessage objects.
            role_enum: MessageRole enum for comparison.

        Returns:
            TipTap JSON document dict.
        """
        blocks: list[dict[str, Any]] = []

        for msg in messages:
            if msg.role == role_enum.SYSTEM:
                continue

            text_node: dict[str, Any] = {
                "type": "text",
                "text": msg.content,
            }

            if msg.role == role_enum.USER:
                # User messages as blockquotes
                blocks.append(
                    {
                        "type": "blockquote",
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [text_node],
                            }
                        ],
                    }
                )
            else:
                # Assistant messages as paragraphs
                blocks.append(
                    {
                        "type": "paragraph",
                        "content": [text_node],
                    }
                )

        if not blocks:
            blocks = [{"type": "paragraph", "content": []}]

        return {"type": "doc", "content": blocks}

    @staticmethod
    def _calculate_word_count(content: dict[str, Any]) -> int:
        """Calculate word count from TipTap JSON content.

        Args:
            content: TipTap JSON document.

        Returns:
            Word count.
        """
        text = CreateNoteFromChatService._extract_text(content)
        if not text:
            return 0
        return len([w for w in re.split(r"\s+", text) if w])

    @staticmethod
    def _extract_text(node: dict[str, Any]) -> str:
        """Recursively extract text from TipTap JSON.

        Args:
            node: TipTap JSON node.

        Returns:
            Concatenated text content.
        """
        parts: list[str] = []
        if node.get("type") == "text" and "text" in node:
            parts.append(str(node["text"]))
        children: list[dict[str, Any]] | None = node.get("content")  # type: ignore[assignment]
        if children is not None:
            parts.extend(CreateNoteFromChatService._extract_text(child) for child in children)
        return " ".join(parts)


__all__ = [
    "CreateNoteFromChatPayload",
    "CreateNoteFromChatResult",
    "CreateNoteFromChatService",
]
