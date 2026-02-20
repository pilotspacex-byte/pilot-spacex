"""AI issue extraction endpoints.

Extract structured issues from note content.

T058-T059: Issue extraction and approval.
"""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from pilot_space.ai.infrastructure.approval import ApprovalService
from pilot_space.api.middleware.request_context import CorrelationId, WorkspaceId
from pilot_space.api.utils.sse import SSEResponse, SSEStreamBuilder
from pilot_space.dependencies import (
    CurrentUserId,
    DbSession,
    get_approval_service_dep,
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


class ApproveExtractedIssuesRequest(BaseModel):
    """Request to approve extracted issues."""

    approval_id: str = Field(description="Approval request ID")
    selected_issues: list[int] = Field(description="Indices of issues to create")


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
    approval_service: Annotated[ApprovalService, Depends(get_approval_service_dep)],
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


@router.post(
    "/notes/{note_id}/extract-issues/approve",
    summary="Approve and create extracted issues",
    description="Approve selected issues and create them in the project (DD-003).",
)
async def approve_extracted_issues(
    workspace_id: WorkspaceId,
    note_id: str,
    body: ApproveExtractedIssuesRequest,
    current_user_id: CurrentUserId,
    approval_service: Annotated[ApprovalService, Depends(get_approval_service_dep)],
    session: DbSession,
    _member: Annotated[UUID, Depends(require_workspace_member)],
) -> dict[str, Any]:
    """Approve and create selected extracted issues.

    Args:
        workspace_id: Workspace UUID from request context.
        note_id: Source note ID
        body: Approval request with selected issue indices
        current_user_id: Current user ID
        approval_service: Approval service
        session: Database session

    Returns:
        Created issue IDs

    Raises:
        HTTPException: 404 if approval not found, 400 if already resolved
    """
    from pilot_space.application.services.issue import CreateIssuePayload, CreateIssueService
    from pilot_space.infrastructure.database.models.issue import IssuePriority
    from pilot_space.infrastructure.database.repositories import (
        ActivityRepository,
        IssueRepository,
        LabelRepository,
    )

    # Get approval request
    approval = await approval_service.get_request(UUID(body.approval_id))
    if not approval:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Approval request not found",
        )

    # Verify workspace match
    if approval.workspace_id != workspace_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Approval request not found",
        )

    # Check approval status
    if approval.status.value != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Approval already {approval.status.value}",
        )

    # Get issues from payload
    issues_payload = approval.payload.get("issues", [])
    if not issues_payload:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No issues in approval payload",
        )

    # Create issue service
    issue_service = CreateIssueService(
        session=session,
        issue_repository=IssueRepository(session),
        activity_repository=ActivityRepository(session),
        label_repository=LabelRepository(session),
    )

    # Map priority int to IssuePriority enum
    priority_map = {
        0: IssuePriority.URGENT,
        1: IssuePriority.HIGH,
        2: IssuePriority.MEDIUM,
        3: IssuePriority.LOW,
        4: IssuePriority.NONE,
    }

    # Create selected issues
    created_ids = []
    project_id = UUID(approval.context.get("project_id", "00000000-0000-0000-0000-000000000000"))

    for idx in body.selected_issues:
        if idx < 0 or idx >= len(issues_payload):
            continue

        issue_data = issues_payload[idx]

        # Map priority
        priority_int = issue_data.get("priority", 4)
        priority = priority_map.get(priority_int, IssuePriority.NONE)

        # Create issue via service
        payload = CreateIssuePayload(
            workspace_id=workspace_id,
            project_id=project_id,
            reporter_id=UUID(str(current_user_id)),
            name=issue_data.get("title", "Untitled Issue"),
            description=issue_data.get("description"),
            priority=priority,
        )

        try:
            result = await issue_service.execute(payload)
            if result.issue:
                created_ids.append(str(result.issue.id))
        except ValueError as e:
            logger.warning(
                "Failed to create issue",
                extra={"index": idx, "error": str(e)},
            )
            continue

    # Resolve approval
    await approval_service.resolve(
        request_id=UUID(body.approval_id),
        approved=True,
        resolved_by=UUID(str(current_user_id)),
        resolution_note=f"Created {len(created_ids)} of {len(body.selected_issues)} selected issues",
    )

    await session.commit()

    return {
        "created_issues": created_ids,
        "created_count": len(created_ids),
        "source_note_id": note_id,
        "message": f"Successfully created {len(created_ids)} issues",
    }


__all__ = ["router"]
