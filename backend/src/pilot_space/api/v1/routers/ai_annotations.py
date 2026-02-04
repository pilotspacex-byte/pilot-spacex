"""AI margin annotations endpoints.

Generate AI annotations for note blocks.

T069: Margin annotations.
"""

from __future__ import annotations

import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Path, status
from pydantic import BaseModel, Field

from pilot_space.ai.agents.agent_base import AgentContext
from pilot_space.ai.agents.margin_annotation_agent_sdk import (
    MarginAnnotationInput,
)
from pilot_space.ai.exceptions import AIConfigurationError, RateLimitError
from pilot_space.api.middleware.request_context import CorrelationId, WorkspaceId
from pilot_space.api.utils.sse import SSEResponse, SSEStreamBuilder
from pilot_space.api.v1.schemas.annotation import (
    AnalyzeNoteRequest,
    AnalyzeNoteResponse,
)
from pilot_space.dependencies import (
    CurrentUserIdOrDemo,
    DbSession,
    get_sdk_orchestrator,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["AI Annotations"])


class AnnotateBlocksRequest(BaseModel):
    """Request for block annotation."""

    block_ids: list[str] = Field(..., min_length=1, max_length=20)
    context_blocks: int = Field(default=3, ge=1, le=10)


class AnnotationResponse(BaseModel):
    """Single annotation in response."""

    block_id: str
    type: str
    title: str
    content: str
    confidence: float
    action_label: str | None = None


@router.post(
    "/analyze-note",
    response_model=AnalyzeNoteResponse,
    summary="Analyze note for annotations",
    description="Generate AI margin annotations for a note.",
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
)
async def analyze_note(
    workspace_id: WorkspaceId,
    correlation_id: CorrelationId,
    analyze_request: AnalyzeNoteRequest,
    current_user_id: CurrentUserIdOrDemo,
    session: DbSession,
) -> AnalyzeNoteResponse:
    """Analyze note and generate margin annotations.

    Rate limit: 5 requests/minute per user.

    Args:
        workspace_id: Workspace UUID from request context.
        correlation_id: Correlation ID from request context.
        analyze_request: Analysis request.
        current_user_id: Current user ID.
        session: Database session.

    Returns:
        Generated annotations.
    """
    # Suppress unused variable warnings
    _ = workspace_id, correlation_id

    # TODO: Fetch note from database
    # For now, return placeholder
    from fastapi import HTTPException

    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Note analysis requires database integration",
    )


@router.post(
    "/notes/{note_id}/annotations",
    summary="Generate margin annotations",
    description="Generate AI annotations for note blocks. Returns SSE stream.",
    response_model=None,
)
async def generate_annotations(
    workspace_id: WorkspaceId,
    correlation_id: CorrelationId,
    note_id: Annotated[uuid.UUID, Path(description="Note ID")],
    body: AnnotateBlocksRequest,
    current_user_id: CurrentUserIdOrDemo,
    orchestrator: Annotated[..., Depends(get_sdk_orchestrator)],
    session: DbSession,
) -> SSEResponse:
    """Generate margin annotations for note blocks.

    Returns SSE stream with:
    - progress: Status updates
    - annotation: Each annotation as generated
    - complete: Summary with total count
    - error: Error details if failed

    Rate limit: 10 requests/minute per user.

    Args:
        workspace_id: Workspace UUID from request context.
        correlation_id: Correlation ID from request context.
        note_id: UUID of the note to annotate
        body: Annotation request with block IDs
        current_user_id: Current user ID

    Returns:
        SSE stream of annotations
    """

    async def generate_events():
        builder = SSEStreamBuilder()
        try:
            yield builder.event("progress", {"status": "analyzing"})

            # Build input
            input_data = MarginAnnotationInput(
                note_id=note_id,
                block_ids=body.block_ids,
                context_blocks=body.context_blocks,
            )

            # Build context
            context = AgentContext(
                workspace_id=workspace_id,
                user_id=current_user_id,
                metadata={"correlation_id": correlation_id},
            )

            # Execute agent
            result = await orchestrator.execute(
                "margin_annotation",
                input_data,
                context,
            )

            if not result.success or not result.output:
                yield builder.error(
                    result.error or "Annotation generation failed",
                    "execution_error",
                )
                return

            # Stream annotations
            for annotation in result.output.annotations:
                yield builder.event(
                    "annotation",
                    {
                        "block_id": annotation.block_id,
                        "type": annotation.type.value,
                        "title": annotation.title,
                        "content": annotation.content,
                        "confidence": annotation.confidence,
                        "action_label": annotation.action_label,
                    },
                )

            # Persist annotations to database
            saved_ids: list[str] = []
            try:
                from pilot_space.application.services.annotation.create_annotation_service import (
                    CreateAnnotationPayload,
                    CreateAnnotationService,
                )
                from pilot_space.infrastructure.database.models.note_annotation import (
                    AnnotationType as DBAnnotationType,
                )

                annotation_service = CreateAnnotationService(session)

                # Map AI annotation types directly to database types
                # (DB enum now supports all AI agent types)
                for annotation in result.output.annotations:
                    # Use the annotation type directly
                    try:
                        db_type = DBAnnotationType(annotation.type.value)
                    except ValueError:
                        # Fallback for unknown types
                        db_type = DBAnnotationType.SUGGESTION

                    payload = CreateAnnotationPayload(
                        workspace_id=workspace_id,
                        note_id=note_id,
                        block_id=annotation.block_id,
                        annotation_type=db_type,
                        content=annotation.content,
                        confidence=annotation.confidence,
                        ai_metadata={
                            "title": annotation.title,
                            "action_label": annotation.action_label,
                            "action_payload": annotation.action_payload,
                            "correlation_id": correlation_id,
                        },
                    )

                    create_result = await annotation_service.execute(payload)
                    saved_ids.append(str(create_result.annotation.id))

                await session.commit()
                logger.info(
                    "Persisted annotations to database",
                    extra={
                        "note_id": str(note_id),
                        "annotation_count": len(saved_ids),
                        "correlation_id": correlation_id,
                    },
                )

            except Exception as persist_error:
                # Log error but don't fail the stream - frontend already has annotations
                logger.error(
                    "Failed to persist annotations to database",
                    extra={
                        "note_id": str(note_id),
                        "error": str(persist_error),
                        "correlation_id": correlation_id,
                    },
                    exc_info=True,
                )
                await session.rollback()
                # Continue with completion event even if persistence failed

            # Send completion
            yield builder.done(
                {
                    "total_annotations": len(result.output.annotations),
                    "processed_blocks": result.output.processed_blocks,
                    "saved_annotation_ids": saved_ids,
                }
            )

        except RateLimitError as e:
            yield builder.error(str(e), "rate_limit")
        except AIConfigurationError as e:
            yield builder.error(str(e), "config_error")
        except Exception as e:
            logger.exception(
                "Unexpected error in margin annotation",
                extra={"note_id": str(note_id), "correlation_id": correlation_id},
            )
            yield builder.error(f"Unexpected error: {e}", "internal_error")

    return SSEResponse(generate_events())


__all__ = ["router"]
