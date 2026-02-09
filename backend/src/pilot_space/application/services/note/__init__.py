"""Note application services (CQRS-lite).

Command services:
- CreateNoteService: Create new notes
- CreateNoteFromChatService: Create note from AI chat session
- UpdateNoteService: Update existing notes

Query services:
- GetNoteService: Retrieve notes with relations
"""

from pilot_space.application.services.note.create_note_from_chat_service import (
    CreateNoteFromChatPayload,
    CreateNoteFromChatResult,
    CreateNoteFromChatService,
)
from pilot_space.application.services.note.create_note_service import (
    CreateNotePayload,
    CreateNoteResult,
    CreateNoteService,
)
from pilot_space.application.services.note.get_note_service import (
    GetNoteOptions,
    GetNoteService,
)
from pilot_space.application.services.note.update_note_service import (
    UpdateNotePayload,
    UpdateNoteResult,
    UpdateNoteService,
)

__all__ = [
    "CreateNoteFromChatPayload",
    "CreateNoteFromChatResult",
    "CreateNoteFromChatService",
    "CreateNotePayload",
    "CreateNoteResult",
    "CreateNoteService",
    "GetNoteOptions",
    "GetNoteService",
    "UpdateNotePayload",
    "UpdateNoteResult",
    "UpdateNoteService",
]
