"""CreateAnnotationService for creating AI-generated annotations.

Implements CQRS-lite command pattern for annotation creation.
Used by AI agents to add suggestions to notes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from pilot_space.domain.exceptions import NotFoundError, ValidationError
from pilot_space.infrastructure.database.models.note_annotation import (
    AnnotationStatus,
    AnnotationType,
)

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from pilot_space.infrastructure.database.models.note_annotation import (
        NoteAnnotation,
    )
    from pilot_space.infrastructure.database.repositories.note_annotation_repository import (
        NoteAnnotationRepository,
    )
    from pilot_space.infrastructure.database.repositories.note_repository import (
        NoteRepository,
    )


@dataclass(frozen=True, slots=True)
class CreateAnnotationPayload:
    """Payload for creating an AI annotation.

    Attributes:
        workspace_id: The workspace ID.
        note_id: The note ID to annotate.
        block_id: The TipTap block ID this annotation refers to.
        annotation_type: Type of annotation (suggestion/warning/issue_candidate/info).
        content: The annotation text content.
        confidence: AI confidence score (0.0 to 1.0).
        ai_metadata: Optional AI context (model, reasoning, etc.).
    """

    workspace_id: UUID
    note_id: UUID
    block_id: str
    annotation_type: AnnotationType
    content: str
    confidence: float = 0.5
    ai_metadata: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class CreateAnnotationResult:
    """Result from annotation creation.

    Attributes:
        annotation: The created annotation.
        is_high_confidence: Whether confidence >= 0.8.
    """

    annotation: NoteAnnotation
    is_high_confidence: bool


class CreateAnnotationService:
    """Service for creating AI annotations.

    Handles annotation creation with validation and metadata.
    Used by AI agents during note analysis.
    """

    def __init__(
        self,
        session: AsyncSession,
        note_repository: NoteRepository,
        annotation_repository: NoteAnnotationRepository,
    ) -> None:
        """Initialize CreateAnnotationService.

        Args:
            session: The async database session.
            note_repository: Repository for note queries.
            annotation_repository: Repository for annotation persistence.
        """
        self._session = session
        self._note_repo = note_repository
        self._annotation_repo = annotation_repository

    async def execute(self, payload: CreateAnnotationPayload) -> CreateAnnotationResult:
        """Execute annotation creation.

        Args:
            payload: The creation payload.

        Returns:
            CreateAnnotationResult with created annotation.

        Raises:
            ValidationError: If content, block_id, or confidence invalid.
            NotFoundError: If note not found.
        """
        from pilot_space.infrastructure.database.models.note_annotation import (
            NoteAnnotation,
        )

        # Validate content
        if not payload.content or not payload.content.strip():
            msg = "Annotation content is required"
            raise ValidationError(msg)

        # Validate block_id
        if not payload.block_id or not payload.block_id.strip():
            msg = "Block ID is required"
            raise ValidationError(msg)

        # Validate confidence range
        if not 0.0 <= payload.confidence <= 1.0:
            msg = "Confidence must be between 0.0 and 1.0"
            raise ValidationError(msg)

        # Verify note exists
        note = await self._note_repo.get_by_id(payload.note_id)
        if not note:
            msg = f"Note with ID {payload.note_id} not found"
            raise NotFoundError(msg)

        # Verify note belongs to workspace
        if note.workspace_id != payload.workspace_id:
            msg = "Note does not belong to the specified workspace"
            raise ValidationError(msg)

        # Build AI metadata with defaults
        ai_metadata = payload.ai_metadata or {}
        if "created_by" not in ai_metadata:
            ai_metadata["created_by"] = "ai_agent"

        # Create annotation
        annotation = NoteAnnotation(
            workspace_id=payload.workspace_id,
            note_id=payload.note_id,
            block_id=payload.block_id.strip(),
            type=payload.annotation_type,
            content=payload.content.strip(),
            confidence=payload.confidence,
            status=AnnotationStatus.PENDING,
            ai_metadata=ai_metadata,
        )

        created_annotation = await self._annotation_repo.create(annotation)

        return CreateAnnotationResult(
            annotation=created_annotation,
            is_high_confidence=payload.confidence >= 0.8,
        )

    async def create_batch(
        self,
        payloads: list[CreateAnnotationPayload],
    ) -> list[CreateAnnotationResult]:
        """Create multiple annotations in a batch.

        Args:
            payloads: List of creation payloads.

        Returns:
            List of CreateAnnotationResult for each annotation.

        Raises:
            ValidationError: If content, block_id, or confidence invalid.
            NotFoundError: If note not found.
        """
        results: list[CreateAnnotationResult] = []
        for payload in payloads:
            result = await self.execute(payload)
            results.append(result)
        return results
