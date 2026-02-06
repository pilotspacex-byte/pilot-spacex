"""CreateGuidedNoteService for creating guided first note.

Implements CQRS-lite command pattern for guided note creation.

T012: Create OnboardingService (CQRS-lite).
T040: Guided note template content.
Source: FR-011, US4
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any
from uuid import UUID

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


# T040: Guided note template content
# Topic: "Planning authentication for our app" (per spec decision)
GUIDED_NOTE_TITLE = "Planning authentication for our app"

GUIDED_NOTE_CONTENT: dict[str, Any] = {
    "type": "doc",
    "content": [
        {
            "type": "heading",
            "attrs": {"level": 1},
            "content": [{"type": "text", "text": "Planning authentication for our app"}],
        },
        {
            "type": "paragraph",
            "content": [
                {
                    "type": "text",
                    "text": "We need to implement user authentication for our application. "
                    "This note captures our initial thinking about the approach.",
                }
            ],
        },
        {
            "type": "heading",
            "attrs": {"level": 2},
            "content": [{"type": "text", "text": "Requirements"}],
        },
        {
            "type": "bulletList",
            "content": [
                {
                    "type": "listItem",
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [
                                {
                                    "type": "text",
                                    "text": "Implement secure login with email and password",
                                }
                            ],
                        }
                    ],
                },
                {
                    "type": "listItem",
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [
                                {"type": "text", "text": "Add OAuth support for Google and GitHub"}
                            ],
                        }
                    ],
                },
                {
                    "type": "listItem",
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [
                                {
                                    "type": "text",
                                    "text": "Fix the session timeout handling - users are being logged out too quickly",
                                }
                            ],
                        }
                    ],
                },
            ],
        },
        {
            "type": "heading",
            "attrs": {"level": 2},
            "content": [{"type": "text", "text": "Technical Approach"}],
        },
        {
            "type": "paragraph",
            "content": [
                {
                    "type": "text",
                    "text": "We're considering using JWT tokens for stateless authentication. "
                    "The tokens would be stored in httpOnly cookies for security.",
                }
            ],
        },
        {
            "type": "paragraph",
            "content": [
                {
                    "type": "text",
                    "text": "For the OAuth flow, we need to add redirect handlers and token exchange logic. "
                    "This involves setting up app credentials with each provider.",
                }
            ],
        },
        {
            "type": "heading",
            "attrs": {"level": 2},
            "content": [{"type": "text", "text": "Next Steps"}],
        },
        {
            "type": "orderedList",
            "content": [
                {
                    "type": "listItem",
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [
                                {
                                    "type": "text",
                                    "text": "Create the authentication service module",
                                }
                            ],
                        }
                    ],
                },
                {
                    "type": "listItem",
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [
                                {"type": "text", "text": "Implement password hashing with bcrypt"}
                            ],
                        }
                    ],
                },
                {
                    "type": "listItem",
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [
                                {
                                    "type": "text",
                                    "text": "Add rate limiting to prevent brute force attacks",
                                }
                            ],
                        }
                    ],
                },
            ],
        },
        {
            "type": "paragraph",
            "content": [
                {
                    "type": "text",
                    "marks": [{"type": "italic"}],
                    "text": "Try pausing after typing to see AI suggestions, "
                    "or select text to see AI options in the margin.",
                }
            ],
        },
    ],
}


@dataclass(frozen=True, slots=True)
class CreateGuidedNotePayload:
    """Payload for creating guided first note.

    Attributes:
        workspace_id: The workspace ID.
        owner_id: The user ID creating the note.
    """

    workspace_id: UUID
    owner_id: UUID


@dataclass(frozen=True, slots=True)
class CreateGuidedNoteResult:
    """Result from guided note creation.

    Attributes:
        note_id: ID of the created note.
        title: Note title.
        already_exists: True if guided note already existed.
    """

    note_id: UUID
    title: str
    already_exists: bool = False


class CreateGuidedNoteService:
    """Service for creating guided first note.

    Creates a note with pre-populated content about authentication planning.
    Sets is_guided_template=True for tooltip triggering.
    Returns 409 CONFLICT if guided note already exists.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize CreateGuidedNoteService.

        Args:
            session: The async database session.
        """
        self._session = session

    async def execute(
        self,
        payload: CreateGuidedNotePayload,
    ) -> CreateGuidedNoteResult:
        """Execute guided note creation.

        Args:
            payload: The creation payload.

        Returns:
            CreateGuidedNoteResult with note info.

        Raises:
            ValueError: If guided note already exists (409 CONFLICT).
        """
        from pilot_space.infrastructure.database.models.note import Note
        from pilot_space.infrastructure.database.repositories.note_repository import (
            NoteRepository,
        )
        from pilot_space.infrastructure.database.repositories.onboarding_repository import (
            OnboardingRepository,
        )

        onboarding_repo = OnboardingRepository(self._session)
        note_repo = NoteRepository(self._session)

        # Get or create onboarding record
        onboarding = await onboarding_repo.upsert_for_workspace(payload.workspace_id)

        # Check if guided note already exists
        if onboarding.guided_note_id:
            # Return existing note info
            existing_note = await note_repo.get_by_id(onboarding.guided_note_id)
            if existing_note:
                return CreateGuidedNoteResult(
                    note_id=existing_note.id,
                    title=existing_note.title,
                    already_exists=True,
                )

        # Create the guided note
        note = Note(
            workspace_id=payload.workspace_id,
            owner_id=payload.owner_id,
            title=GUIDED_NOTE_TITLE,
            content=GUIDED_NOTE_CONTENT,
            is_guided_template=True,
            is_pinned=True,  # Pin for visibility
            word_count=self._calculate_word_count(GUIDED_NOTE_CONTENT),
            reading_time_mins=1,
        )

        created_note = await note_repo.create(note)

        # Update onboarding with guided note reference
        await onboarding_repo.set_guided_note_id(
            workspace_id=payload.workspace_id,
            note_id=created_note.id,
        )

        # Mark first_note step as complete
        await onboarding_repo.update_step(
            workspace_id=payload.workspace_id,
            step_name="first_note",
            completed=True,
        )

        return CreateGuidedNoteResult(
            note_id=created_note.id,
            title=created_note.title,
            already_exists=False,
        )

    def _calculate_word_count(self, content: dict[str, Any]) -> int:
        """Calculate word count from TipTap content.

        Args:
            content: TipTap JSON document.

        Returns:
            Approximate word count.
        """
        text = self._extract_text(content)
        if not text:
            return 0
        return len(text.split())

    def _extract_text(self, node: dict[str, Any]) -> str:
        """Recursively extract text from TipTap node.

        Args:
            node: TipTap JSON node.

        Returns:
            Extracted text.
        """
        parts: list[str] = []

        if node.get("type") == "text" and "text" in node:
            parts.append(str(node["text"]))

        for child in node.get("content", []):
            parts.append(self._extract_text(child))

        return " ".join(parts)


__all__ = ["CreateGuidedNotePayload", "CreateGuidedNoteResult", "CreateGuidedNoteService"]
