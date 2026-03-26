"""AI issue extraction endpoints.

Extract structured issues from note content.

T058-T059: Issue extraction and approval.
"""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from pilot_space.api.middleware.request_context import CorrelationId, WorkspaceId
from pilot_space.api.utils.sse import SSEResponse, SSEStreamBuilder
from pilot_space.api.v1.dependencies import CreateExtractedIssuesServiceDep
from pilot_space.application.services.ai_extraction import (
    CreateExtractedIssuesPayload,
    ExtractedIssueInput,
)
from pilot_space.dependencies import (
    CurrentUserId,
    DbSession,
)
from pilot_space.dependencies.auth import require_workspace_member
from pilot_space.infrastructure.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["AI Extraction"])


class ExtractIssuesRequest(BaseModel):
    """Request for issue extraction."""

    note_title: str = Field(
        max_length=255,
        description="Note title",
    )
    note_content: dict[str, Any] = Field(description="TipTap JSON content")
    project_id: str | None = Field(
        default=None,
        description="Project ID for context",
    )
    project_context: str | None = Field(
        default=None,
        max_length=2000,
        description="Project description for context",
    )
    selected_text: str | None = Field(
        default=None,
        max_length=5000,
        description="User-selected text to focus on",
    )
    available_labels: list[str] | None = Field(
        default=None,
        max_length=50,
        description="Labels available in the project",
    )
    max_issues: int = Field(
        default=10,
        ge=1,
        le=20,
        description="Maximum number of issues to extract",
    )


class ExtractedIssueResponse(BaseModel):
    """Single extracted issue."""

    title: str = Field(description="Issue title")
    description: str = Field(description="Issue description")
    priority: int = Field(description="Suggested priority (0-4)")
    labels: list[str] = Field(description="Suggested labels")
    confidence_score: float = Field(description="Confidence score (0-1)")
    confidence_tag: str = Field(description="Confidence category")
    source_block_ids: list[str] = Field(default_factory=list, description="Source blocks")
    rationale: str = Field(default="", description="Extraction rationale")


class ExtractIssuesResponse(BaseModel):
    """Response for issue extraction."""

    issues: list[ExtractedIssueResponse] = Field(description="Extracted issues")
    recommended_count: int = Field(description="High confidence issues")
    total_count: int = Field(description="Total issues")
    processing_time_ms: float = Field(description="Processing time")


class ExtractedIssueInputSchema(BaseModel):
    """Single issue to create from extraction."""

    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    priority: int = Field(default=4, ge=0, le=4)
    source_block_id: str | None = None


class CreateExtractedIssuesRequestSchema(BaseModel):
    """Request to create extracted issues (auto-approve, DD-003 non-destructive)."""

    issues: list[ExtractedIssueInputSchema] = Field(default_factory=list)
    project_id: str | None = Field(default=None, description="Project UUID to assign issues to")
    note_id: str | None = Field(
        default=None, description="Source note ID (for no-note extraction route)"
    )


class CreatedIssueData(BaseModel):
    """Single created issue in the response."""

    id: str
    identifier: str
    title: str


class CreateExtractedIssuesResponse(BaseModel):
    """Response for creating extracted issues."""

    created_issues: list[CreatedIssueData]
    created_count: int
    source_note_id: str | None
    message: str


@router.post(
    "/notes/{note_id}/extract-issues",
    summary="Extract issues from note with SSE streaming",
    description="Extract structured issues from note content with confidence tags (DD-048).",
    response_model=None,
)
async def extract_issues_stream(
    workspace_id: WorkspaceId,
    correlation_id: CorrelationId,
    note_id: str,
    extract_request: ExtractIssuesRequest,
    current_user_id: CurrentUserId,
    request: Request,
    session: DbSession,
    _member: Annotated[UUID, Depends(require_workspace_member)],
) -> SSEResponse:
    """Extract issues from note content with confidence tags.

    Returns SSE stream with progress, issue, complete, and error events.
    """
    _ = correlation_id  # Used for tracing

    async def generate_events():
        from pilot_space.application.services.extraction import (
            ExtractIssuesPayload,
            IssueExtractionService,
        )

        builder = SSEStreamBuilder()

        yield builder.event(
            "progress", {"stage": "analyzing", "message": "Analyzing note content..."}
        )

        try:
            service = IssueExtractionService(session=session)
            payload = ExtractIssuesPayload(
                workspace_id=workspace_id,
                note_id=note_id,
                note_title=extract_request.note_title,
                note_content=extract_request.note_content,
                project_id=extract_request.project_id,
                project_context=extract_request.project_context,
                selected_text=extract_request.selected_text,
                available_labels=extract_request.available_labels,
                max_issues=extract_request.max_issues,
            )

            yield builder.event(
                "progress", {"stage": "extracting", "message": "Extracting issues..."}
            )

            result = await service.extract(payload)

            for idx, issue in enumerate(result.issues):
                yield builder.event(
                    "issue",
                    {
                        "index": idx,
                        "title": issue.title,
                        "description": issue.description,
                        "priority": issue.priority,
                        "labels": issue.labels,
                        "confidenceScore": issue.confidence_score,
                        "confidenceTag": issue.confidence_tag,
                        "sourceBlockIds": issue.source_block_ids,
                        "rationale": issue.rationale,
                    },
                )

            yield builder.event(
                "complete",
                {
                    "totalCount": result.total_count,
                    "recommendedCount": result.recommended_count,
                    "processingTimeMs": result.processing_time_ms,
                    "model": result.model,
                },
            )

        except Exception:
            logger.exception("Issue extraction failed", extra={"note_id": note_id})
            yield builder.event(
                "error",
                {"code": "EXTRACTION_FAILED", "message": "Extraction failed. Please try again."},
            )

    return SSEResponse(generate_events())


@router.post(
    "/notes/{note_id}/extract-issues/approve",
    summary="Create extracted issues from note",
    description="Auto-approve and create extracted issues directly (DD-003 non-destructive).",
    response_model=CreateExtractedIssuesResponse,
)
async def approve_extracted_issues(
    workspace_id: WorkspaceId,
    note_id: str,
    body: CreateExtractedIssuesRequestSchema,
    current_user_id: CurrentUserId,
    session: DbSession,
    service: CreateExtractedIssuesServiceDep,
    _member: Annotated[UUID, Depends(require_workspace_member)],
) -> CreateExtractedIssuesResponse:
    """Create extracted issues from a note (auto-approve)."""
    payload = CreateExtractedIssuesPayload(
        workspace_id=workspace_id,
        note_id=note_id,
        issues=[
            ExtractedIssueInput(
                title=i.title,
                description=i.description,
                priority=i.priority,
                source_block_id=i.source_block_id,
            )
            for i in body.issues
        ],
        project_id=body.project_id,
        user_id=current_user_id,
    )
    result = await service.execute(payload)
    return CreateExtractedIssuesResponse(
        created_issues=[
            CreatedIssueData(id=ci.id, identifier=ci.identifier, title=ci.title)
            for ci in result.created_issues
        ],
        created_count=result.created_count,
        source_note_id=result.source_note_id,
        message=result.message,
    )


@router.post(
    "/extract-issues/approve",
    summary="Create extracted issues without note context",
    description="Create issues from chat extraction when no note is in context (DD-003 non-destructive).",
    response_model=CreateExtractedIssuesResponse,
)
async def approve_extracted_issues_no_note(
    workspace_id: WorkspaceId,
    body: CreateExtractedIssuesRequestSchema,
    current_user_id: CurrentUserId,
    session: DbSession,
    service: CreateExtractedIssuesServiceDep,
    _member: Annotated[UUID, Depends(require_workspace_member)],
) -> CreateExtractedIssuesResponse:
    """Create extracted issues without note context (auto-approve)."""
    payload = CreateExtractedIssuesPayload(
        workspace_id=workspace_id,
        note_id=body.note_id,
        issues=[
            ExtractedIssueInput(
                title=i.title,
                description=i.description,
                priority=i.priority,
                source_block_id=i.source_block_id,
            )
            for i in body.issues
        ],
        project_id=body.project_id,
        user_id=current_user_id,
    )
    result = await service.execute(payload)
    return CreateExtractedIssuesResponse(
        created_issues=[
            CreatedIssueData(id=ci.id, identifier=ci.identifier, title=ci.title)
            for ci in result.created_issues
        ],
        created_count=result.created_count,
        source_note_id=result.source_note_id,
        message=result.message,
    )


__all__ = ["router"]
