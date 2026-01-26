"""AI issue extraction endpoints.

Extract structured issues from note content.

T058-T059: Issue extraction and approval.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field

from pilot_space.ai.agents.sdk_base import AgentContext
from pilot_space.api.utils.sse import SSEResponse, SSEStreamBuilder
from pilot_space.api.v1.schemas.note import extract_text_from_tiptap
from pilot_space.dependencies import (
    CurrentUserIdOrDemo,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["AI Extraction"])


class ExtractIssuesRequest(BaseModel):
    """Request for issue extraction."""

    note_id: str = Field(description="Note ID")
    note_title: str = Field(
        max_length=255,
        description="Note title",
    )
    note_content: dict[str, Any] = Field(description="TipTap JSON content")
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
        description="Labels available in the project",
    )


class ExtractedIssueResponse(BaseModel):
    """Single extracted issue."""

    title: str = Field(description="Issue title")
    description: str = Field(description="Issue description")
    priority: str = Field(description="Suggested priority")
    labels: list[str] = Field(description="Suggested labels")
    confidence: float = Field(description="Confidence score")
    confidence_tag: str = Field(description="Confidence category")
    source_text: str = Field(default="", description="Source text")


class ExtractIssuesResponse(BaseModel):
    """Response for issue extraction."""

    issues: list[ExtractedIssueResponse] = Field(description="Extracted issues")
    recommended_count: int = Field(description="High confidence issues")
    total_count: int = Field(description="Total issues")
    processing_time_ms: float = Field(description="Processing time")


class ApproveExtractedIssuesRequest(BaseModel):
    """Request to approve extracted issues."""

    approval_id: str = Field(description="Approval request ID")
    selected_issues: list[int] = Field(description="Indices of issues to create (from extraction)")


def get_workspace_id(request: Request) -> uuid.UUID:
    """Get workspace ID from request headers.

    Supports both UUID and slug-based demo workspace IDs.
    """
    workspace_id_str = request.headers.get("X-Workspace-ID") or request.headers.get(
        "X-Workspace-Id"
    )
    if not workspace_id_str:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Workspace-ID header required",
        )

    # Check for demo workspace slugs
    demo_workspace_uuid = uuid.UUID("00000000-0000-0000-0000-000000000002")
    demo_workspace_slugs = {"pilot-space-demo", "demo", "test"}

    if workspace_id_str.lower() in demo_workspace_slugs:
        return demo_workspace_uuid

    # Try to parse as UUID
    try:
        return uuid.UUID(workspace_id_str)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid workspace ID format: {workspace_id_str}",
        ) from e


def get_correlation_id(request: Request) -> str:
    """Get or generate correlation ID for request."""
    correlation_id = request.headers.get("X-Correlation-ID")
    if not correlation_id:
        correlation_id = str(uuid.uuid4())
    return correlation_id


@router.post(
    "/notes/{note_id}/extract-issues",
    summary="Extract issues from note with SSE streaming",
    description="Extract structured issues from note content with confidence tags (DD-048). Returns SSE stream.",
    response_model=None,
)
async def extract_issues_stream(
    note_id: str,
    request: Request,
    extract_request: ExtractIssuesRequest,
    current_user_id: CurrentUserIdOrDemo,
) -> SSEResponse:
    """Extract issues from note content with confidence tags.

    Returns SSE stream with:
    - progress: Extraction progress updates
    - issue: Each extracted issue as found
    - complete: Final summary with all issues
    - error: If extraction fails

    Issues will require approval before creation (DD-003).

    Args:
        note_id: Note ID to extract from.
        request: FastAPI request.
        extract_request: Extraction request.
        current_user_id: Current user ID.

    Returns:
        SSE stream of extraction events.
    """
    _correlation_id = get_correlation_id(request)
    workspace_id = get_workspace_id(request)

    async def generate_events():
        builder = SSEStreamBuilder()
        try:
            # Emit start event
            yield builder.event(
                "progress",
                {"status": "analyzing", "message": "Reading note content..."},
            )

            # TODO: Fetch note from database
            # For now, use request data
            _note_content = extract_text_from_tiptap(extract_request.note_content)

            yield builder.event(
                "progress", {"status": "extracting", "message": "Extracting issues..."}
            )

            # Build input for SDK agent
            from uuid import UUID

            from pilot_space.ai.agents.issue_extractor_sdk_agent import (
                IssueExtractorInput,
            )

            _input_data = IssueExtractorInput(
                note_id=UUID(note_id),
                project_id=UUID(extract_request.note_id)
                if extract_request.note_id
                else UUID("00000000-0000-0000-0000-000000000000"),
                max_issues=10,
                min_confidence=0.5,
            )

            _context = AgentContext(workspace_id=workspace_id, user_id=UUID(str(current_user_id)))

            # TODO: Get agent from DI container
            # For now, create directly (will need ToolRegistry, etc.)
            # agent = IssueExtractorAgent(...)
            # result = await agent.execute(input_data, context)

            # Emit placeholder result
            yield builder.event(
                "issue",
                {
                    "index": 0,
                    "title": "Sample Issue",
                    "description": "This is a placeholder",
                    "labels": ["todo"],
                    "priority": 2,
                    "confidence_tag": "default",
                    "confidence_score": 0.7,
                    "rationale": "Placeholder for SDK integration",
                },
            )

            # Emit completion
            yield builder.event(
                "complete",
                {
                    "status": "complete",
                    "total_issues": 1,
                    "summary": "Extracted 1 issue from note",
                    "requires_approval": True,
                    "cost_usd": 0.0,
                },
            )

        except Exception as e:
            logger.exception("Failed to extract issues")
            yield builder.error(str(e), type(e).__name__)

    return SSEResponse(generate_events())


@router.post(
    "/notes/{note_id}/extract-issues/approve",
    summary="Approve and create extracted issues",
    description="Approve selected extracted issues and create them in the project (DD-003).",
)
async def approve_extracted_issues(
    note_id: str,
    request: Request,
    body: ApproveExtractedIssuesRequest,
    current_user_id: CurrentUserIdOrDemo,
) -> dict[str, Any]:
    """Approve and create selected extracted issues.

    Args:
        note_id: Source note ID
        request: FastAPI request
        body: Approval request with selected issue indices
        current_user_id: Current user ID

    Returns:
        Created issue IDs
    """
    _workspace_id = get_workspace_id(request)

    # TODO: Integrate with ApprovalService
    # approval_service = get_approval_service()
    # approval = await approval_service.get_request(body.approval_id)

    # TODO: Verify approval belongs to user's workspace
    # if not approval or approval.workspace_id != workspace_id:
    #     raise HTTPException(404, "Approval request not found")

    # TODO: Check approval status
    # if approval.status != "pending":
    #     raise HTTPException(400, f"Approval already {approval.status}")

    # TODO: Resolve approval
    # await approval_service.resolve(
    #     approval_id=body.approval_id,
    #     resolved_by=current_user_id,
    #     approved=True,
    #     note=f"Creating {len(body.selected_issues)} issues",
    # )

    # TODO: Create selected issues via IssueService
    # created_ids = []
    # for idx in body.selected_issues:
    #     if idx < len(approval.payload["issues"]):
    #         issue_data = approval.payload["issues"][idx]
    #         issue = await issue_service.create(
    #             project_id=current_user.current_project_id,
    #             title=issue_data["title"],
    #             description=issue_data["description"],
    #             labels=issue_data.get("labels", []),
    #             priority=issue_data.get("priority", 2),
    #             created_by=current_user_id,
    #             source_note_id=note_id,
    #         )
    #         created_ids.append(str(issue.id))

    # Placeholder response
    return {
        "created_issues": [],
        "message": "Approval endpoint placeholder - requires ApprovalService integration",
    }


__all__ = ["router"]
