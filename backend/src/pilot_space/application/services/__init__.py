"""Application services for Pilot Space (CQRS-lite).

Organized by domain aggregate:
- workspace/: Workspace command/query services
- project/: Project command/query services
- issue/: Issue command/query services with AI enhancement
- note/: Note command/query services
- annotation/: AI annotation services
- discussion/: Discussion thread services
- cycle/: Cycle command/query services
- ai/: AI-specific services (context generation, approval flow)
- integration/: Integration services (GitHub, Slack)
"""

from pilot_space.application.services.annotation import (
    CreateAnnotationPayload,
    CreateAnnotationResult,
    CreateAnnotationService,
)
from pilot_space.application.services.discussion import (
    CreateDiscussionPayload,
    CreateDiscussionResult,
    CreateDiscussionService,
)
from pilot_space.application.services.note import (
    CreateNotePayload,
    CreateNoteResult,
    CreateNoteService,
    GetNoteOptions,
    GetNoteService,
    UpdateNotePayload,
    UpdateNoteResult,
    UpdateNoteService,
)

__all__ = [
    # Annotation services
    "CreateAnnotationPayload",
    "CreateAnnotationResult",
    "CreateAnnotationService",
    # Discussion services
    "CreateDiscussionPayload",
    "CreateDiscussionResult",
    "CreateDiscussionService",
    # Note services
    "CreateNotePayload",
    "CreateNoteResult",
    "CreateNoteService",
    "GetNoteOptions",
    "GetNoteService",
    "UpdateNotePayload",
    "UpdateNoteResult",
    "UpdateNoteService",
]
