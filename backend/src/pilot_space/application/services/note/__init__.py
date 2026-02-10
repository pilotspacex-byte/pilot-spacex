"""Note application services (CQRS-lite).

Command services:
- CreateNoteService: Create new notes
- CreateNoteFromChatService: Create note from AI chat session
- UpdateNoteService: Update existing notes
- DeleteNoteService: Soft delete notes
- PinNoteService: Pin/unpin notes
- UpdateAnnotationService: Update annotation status

Query services:
- GetNoteService: Retrieve notes with relations
- ListNotesService: List notes with filtering
- ListAnnotationsService: List note annotations
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
from pilot_space.application.services.note.delete_note_service import (
    DeleteNotePayload,
    DeleteNoteResult,
    DeleteNoteService,
)
from pilot_space.application.services.note.get_note_service import (
    GetNoteOptions,
    GetNoteService,
)
from pilot_space.application.services.note.list_annotations_service import (
    ListAnnotationsPayload,
    ListAnnotationsResult,
    ListAnnotationsService,
)
from pilot_space.application.services.note.list_notes_service import (
    ListNotesPayload,
    ListNotesResult,
    ListNotesService,
)
from pilot_space.application.services.note.pin_note_service import (
    PinNotePayload,
    PinNoteResult,
    PinNoteService,
)
from pilot_space.application.services.note.update_annotation_service import (
    UpdateAnnotationPayload,
    UpdateAnnotationResult,
    UpdateAnnotationService,
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
    "DeleteNotePayload",
    "DeleteNoteResult",
    "DeleteNoteService",
    "GetNoteOptions",
    "GetNoteService",
    "ListAnnotationsPayload",
    "ListAnnotationsResult",
    "ListAnnotationsService",
    "ListNotesPayload",
    "ListNotesResult",
    "ListNotesService",
    "PinNotePayload",
    "PinNoteResult",
    "PinNoteService",
    "UpdateAnnotationPayload",
    "UpdateAnnotationResult",
    "UpdateAnnotationService",
    "UpdateNotePayload",
    "UpdateNoteResult",
    "UpdateNoteService",
]
