"""AI margin annotations endpoints.

Generate AI annotations for note blocks.

T069: Margin annotations.
Note: margin_annotation_agent_sdk was removed during DD-086 migration.
Annotations now route through PilotSpaceAgent orchestrator.
"""

from __future__ import annotations

import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Path, status
from pydantic import BaseModel, Field

from pilot_space.api.middleware.request_context import CorrelationId, WorkspaceId
from pilot_space.api.utils.sse import SSEResponse, SSEStreamBuilder
from pilot_space.api.v1.schemas.annotation import (
    AnalyzeNoteRequest,
    AnalyzeNoteResponse,
)
from pilot_space.dependencies import (
    CurrentUserId,
    DbSession,
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
    current_user_id: CurrentUserId,
    session: DbSession,
) -> AnalyzeNoteResponse:
    """Analyze note and generate margin annotations.

    Note: This endpoint is pending migration to PilotSpaceAgent (DD-086).
    """
    _ = workspace_id, correlation_id, analyze_request, current_user_id, session

    from fastapi import HTTPException

    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Note analysis is being migrated to PilotSpaceAgent (DD-086)",
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
    current_user_id: CurrentUserId,
    session: DbSession,
) -> SSEResponse:
    """Generate margin annotations for note blocks.

    Returns SSE stream with annotation events.

    Note: margin_annotation_agent_sdk was removed during DD-086 migration.
    This endpoint now returns a migration notice via SSE until PilotSpaceAgent
    integration is completed.
    """
    _ = workspace_id, session

    async def generate_events():
        builder = SSEStreamBuilder()
        yield builder.event("progress", {"status": "analyzing"})

        logger.info(
            "Annotation request received (pending DD-086 migration)",
            extra={
                "note_id": str(note_id),
                "block_count": len(body.block_ids),
                "user_id": str(current_user_id),
                "correlation_id": correlation_id,
            },
        )

        yield builder.error(
            "Margin annotations are being migrated to PilotSpaceAgent (DD-086). "
            "Use the AI chat to request annotations instead.",
            "not_implemented",
        )

    return SSEResponse(generate_events())


__all__ = ["router"]
