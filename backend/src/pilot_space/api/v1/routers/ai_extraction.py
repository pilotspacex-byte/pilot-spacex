"""AI issue extraction endpoints.

Extract structured issues from note content.

T058-T059: Issue extraction and approval.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from pilot_space.api.middleware.request_context import CorrelationId, WorkspaceId
from pilot_space.api.utils.sse import SSEResponse, SSEStreamBuilder
from pilot_space.dependencies import (
    CurrentUserId,
    DbSession,
)
from pilot_space.dependencies.auth import require_workspace_member
from pilot_space.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

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


class ExtractedIssueInput(BaseModel):
    """Single issue to create from extraction."""

    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    priority: int = Field(default=4, ge=0, le=4)
    source_block_id: str | None = None


class CreateExtractedIssuesRequest(BaseModel):
    """Request to create extracted issues (auto-approve, DD-003 non-destructive)."""

    issues: list[ExtractedIssueInput] = Field(default_factory=list)
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

    Returns SSE stream with:
    - progress: Extraction progress updates
    - issue: Each extracted issue as found
    - complete: Final summary with approval_id
    - error: If extraction fails

    Issues require approval before creation (DD-003).

    Args:
        workspace_id: Workspace UUID from request context.
        correlation_id: Correlation ID for tracing.
        note_id: Note ID to extract from.
        extract_request: Extraction request.
        current_user_id: Current user ID.
        request: FastAPI request.
        approval_service: Approval service for human-in-the-loop.
        session: Database session.

    Returns:
        SSE stream of extraction events.
    """
    _ = correlation_id  # Used for tracing

    async def generate_events():
        from pilot_space.application.services.extraction import (
            ExtractIssuesPayload,
            IssueExtractionService,
        )

        builder = SSEStreamBuilder()

        # Progress: starting
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

            # Stream each extracted issue
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

            # Complete event with summary
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


async def _create_extracted_issues(
    workspace_id: UUID,
    note_id: str | None,
    body: CreateExtractedIssuesRequest,
    current_user_id: UUID,
    session: AsyncSession,
) -> CreateExtractedIssuesResponse:
    """Shared logic for creating extracted issues.

    Returns enriched response with identifier and title per created issue.

    Raises:
        HTTPException: 400 for validation errors (RFC 7807 via error handler).
    """
    from sqlalchemy import select as sa_select

    from pilot_space.application.services.issue import CreateIssuePayload, CreateIssueService
    from pilot_space.infrastructure.database.models.issue import IssuePriority
    from pilot_space.infrastructure.database.models.note_issue_link import (
        NoteIssueLink,
        NoteLinkType,
    )
    from pilot_space.infrastructure.database.models.project import Project
    from pilot_space.infrastructure.database.repositories import (
        ActivityRepository,
        IssueRepository,
        LabelRepository,
        NoteIssueLinkRepository,
    )

    if not body.issues:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No issues to create",
        )

    if not body.project_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="project_id is required to create issues",
        )

    try:
        project_id = UUID(body.project_id)
    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid project_id format",
        ) from None

    # Pre-fetch project identifier for constructing issue identifiers
    project_row = await session.execute(
        sa_select(Project.identifier).where(Project.id == project_id)
    )
    project_identifier = project_row.scalar_one_or_none()
    if not project_identifier:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Project not found for id {project_id}",
        )

    note_uuid: UUID | None = None
    if note_id:
        try:
            note_uuid = UUID(note_id)
        except (ValueError, AttributeError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid note_id format",
            ) from None

    issue_service = CreateIssueService(
        session=session,
        issue_repository=IssueRepository(session),
        activity_repository=ActivityRepository(session),
        label_repository=LabelRepository(session),
    )
    link_repo = NoteIssueLinkRepository(session) if note_uuid else None

    priority_map = {
        0: IssuePriority.URGENT,
        1: IssuePriority.HIGH,
        2: IssuePriority.MEDIUM,
        3: IssuePriority.LOW,
        4: IssuePriority.NONE,
    }

    created_issues_data: list[CreatedIssueData] = []
    for issue_data in body.issues:
        payload = CreateIssuePayload(
            workspace_id=workspace_id,
            project_id=project_id,
            reporter_id=current_user_id,
            name=issue_data.title,
            description=issue_data.description,
            priority=priority_map.get(issue_data.priority, IssuePriority.NONE),
        )
        try:
            result = await issue_service.execute(payload)
            if result.issue:
                issue_id = result.issue.id
                identifier = f"{project_identifier}-{result.issue.sequence_id}"
                created_issues_data.append(
                    CreatedIssueData(
                        id=str(issue_id),
                        identifier=identifier,
                        title=result.issue.name,
                    )
                )

                # Create NoteIssueLink when note_id is provided
                if note_uuid and link_repo:
                    try:
                        existing = await link_repo.find_existing(
                            note_id=note_uuid,
                            issue_id=issue_id,
                            link_type=NoteLinkType.EXTRACTED,
                            workspace_id=workspace_id,
                        )
                        if not existing:
                            link = NoteIssueLink(
                                note_id=note_uuid,
                                issue_id=issue_id,
                                link_type=NoteLinkType.EXTRACTED,
                                block_id=issue_data.source_block_id,
                                workspace_id=workspace_id,
                            )
                            await link_repo.create(link)
                    except Exception:
                        logger.warning(
                            "Failed to create NoteIssueLink, issue was still created",
                            extra={
                                "note_id": str(note_uuid),
                                "issue_id": str(issue_id),
                            },
                        )
        except Exception:
            logger.warning(
                "Failed to create issue",
                extra={"title": issue_data.title},
                exc_info=True,
            )
            continue

    await session.commit()

    return CreateExtractedIssuesResponse(
        created_issues=created_issues_data,
        created_count=len(created_issues_data),
        source_note_id=note_id,
        message=f"Successfully created {len(created_issues_data)} issues",
    )


@router.post(
    "/notes/{note_id}/extract-issues/approve",
    summary="Create extracted issues from note",
    description="Auto-approve and create extracted issues directly (DD-003 non-destructive).",
    response_model=CreateExtractedIssuesResponse,
)
async def approve_extracted_issues(
    workspace_id: WorkspaceId,
    note_id: str,
    body: CreateExtractedIssuesRequest,
    current_user_id: CurrentUserId,
    session: DbSession,
    _member: Annotated[UUID, Depends(require_workspace_member)],
) -> CreateExtractedIssuesResponse:
    """Create extracted issues from a note (auto-approve)."""
    return await _create_extracted_issues(
        workspace_id=workspace_id,
        note_id=note_id,
        body=body,
        current_user_id=current_user_id,
        session=session,
    )


@router.post(
    "/extract-issues/approve",
    summary="Create extracted issues without note context",
    description="Create issues from chat extraction when no note is in context (DD-003 non-destructive).",
    response_model=CreateExtractedIssuesResponse,
)
async def approve_extracted_issues_no_note(
    workspace_id: WorkspaceId,
    body: CreateExtractedIssuesRequest,
    current_user_id: CurrentUserId,
    session: DbSession,
    _member: Annotated[UUID, Depends(require_workspace_member)],
) -> CreateExtractedIssuesResponse:
    """Create extracted issues without note context (auto-approve)."""
    return await _create_extracted_issues(
        workspace_id=workspace_id,
        note_id=body.note_id,
        body=body,
        current_user_id=current_user_id,
        session=session,
    )


__all__ = ["router"]
