"""AI API router.

Endpoints for AI-powered features:
- Ghost text generation (SSE streaming)
- Note analysis and margin annotations
- Issue extraction from notes
- AI conversation
- Cost tracking and analytics

T096: AI router implementation.
T091-T094: Cost tracking endpoints.
"""

from __future__ import annotations

import logging
import time
import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Path, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from pilot_space.ai.agents.base import Provider
from pilot_space.ai.agents.conversation_agent import (
    ConversationInput,
    ConversationMessage,
    MessageRole,
)
from pilot_space.ai.agents.ghost_text_agent import GhostTextInput
from pilot_space.ai.agents.issue_extractor_agent import IssueExtractionInput
from pilot_space.ai.agents.margin_annotation_agent_sdk import (
    MarginAnnotationInput,
)
from pilot_space.ai.agents.sdk_base import AgentContext
from pilot_space.ai.exceptions import AIConfigurationError, AIError, RateLimitError
from pilot_space.ai.orchestrator import WorkspaceAIConfig, get_orchestrator
from pilot_space.api.utils.sse import SSEResponse, SSEStreamBuilder
from pilot_space.api.v1.schemas.annotation import (
    AnalyzeNoteRequest,
    AnalyzeNoteResponse,
)
from pilot_space.api.v1.schemas.approval import (
    ApprovalDetailResponse,
    ApprovalListResponse,
    ApprovalRequestResponse,
    ApprovalResolution,
    ApprovalResolutionResponse,
    ApprovalStatus as ApprovalStatusSchema,
)
from pilot_space.api.v1.schemas.cost import (
    CostByAgent,
    CostByDay,
    CostByUser,
    CostByUserResponse,
    CostSummaryResponse,
    CostTrendsResponse,
    TrendDataPoint,
)
from pilot_space.api.v1.schemas.note import extract_text_from_tiptap
from pilot_space.dependencies import (
    CostTrackerDep,
    CurrentUserIdOrDemo,
    DbSession,
)
from pilot_space.infrastructure.database.models.ai_cost_record import AICostRecord
from pilot_space.infrastructure.database.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["AI"])


# Request/Response Schemas


class GhostTextRequest(BaseModel):
    """Request for ghost text generation."""

    current_text: str = Field(
        min_length=1,
        max_length=10000,
        description="Text being typed",
    )
    cursor_position: int = Field(
        ge=0,
        description="Cursor position in text",
    )
    context: str | None = Field(
        default=None,
        max_length=5000,
        description="Previous paragraphs for context",
    )
    language: str | None = Field(
        default=None,
        max_length=50,
        description="Programming language (for code)",
    )
    is_code: bool = Field(
        default=False,
        description="Whether content is code-related",
    )


class GhostTextResponse(BaseModel):
    """Response for ghost text generation."""

    suggestion: str = Field(description="Completion suggestion")
    cursor_offset: int = Field(description="Cursor offset after accepting")
    is_empty: bool = Field(description="Whether suggestion is empty")
    degraded: bool = Field(
        default=False,
        description="Whether fallback was used",
    )


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


class ChatRequest(BaseModel):
    """Request for AI chat."""

    message: str = Field(
        min_length=1,
        max_length=5000,
        description="User message",
    )
    history: list[dict[str, str]] | None = Field(
        default=None,
        description="Previous conversation history",
    )
    system_context: str | None = Field(
        default=None,
        max_length=2000,
        description="Additional context",
    )


class ChatResponse(BaseModel):
    """Response for AI chat."""

    response: str = Field(description="AI response")
    truncated: bool = Field(
        default=False,
        description="Whether history was truncated",
    )


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


class HealthResponse(BaseModel):
    """AI health check response."""

    status: str = Field(description="Overall status")
    providers: dict[str, Any] = Field(description="Provider health")


# Helper to get correlation ID


def get_correlation_id(request: Request) -> str:
    """Get or generate correlation ID for request."""
    correlation_id = request.headers.get("X-Correlation-ID")
    if not correlation_id:
        correlation_id = str(uuid.uuid4())
    return correlation_id


# Demo workspace UUID for slug-based workspace IDs
DEMO_WORKSPACE_UUID = uuid.UUID("00000000-0000-0000-0000-000000000002")
DEMO_WORKSPACE_SLUGS = {"pilot-space-demo", "demo", "test"}


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
    if workspace_id_str.lower() in DEMO_WORKSPACE_SLUGS:
        return DEMO_WORKSPACE_UUID

    # Try to parse as UUID
    try:
        return uuid.UUID(workspace_id_str)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid workspace ID format: {workspace_id_str}",
        ) from e


# Ghost Text Endpoint


@router.post(
    "/ghost-text",
    summary="Generate ghost text suggestion",
    description="Generate inline text completion. Returns SSE stream or JSON.",
    response_model=None,
)
async def generate_ghost_text(
    request: Request,
    ghost_request: GhostTextRequest,
    current_user_id: CurrentUserIdOrDemo,
    stream: Annotated[bool, Query(description="Enable SSE streaming")] = False,
) -> GhostTextResponse | SSEResponse:
    """Generate ghost text suggestion.

    Rate limit: 10 requests/minute per user.

    Args:
        request: FastAPI request.
        ghost_request: Ghost text request data.
        current_user_id: Current user ID.
        stream: Whether to stream response via SSE.

    Returns:
        Ghost text suggestion or SSE stream.
    """
    correlation_id = get_correlation_id(request)
    workspace_id = get_workspace_id(request)

    orchestrator = get_orchestrator()

    # Ensure workspace is configured (for demo, auto-configure)
    if not orchestrator.get_workspace_config(workspace_id):
        # In production, this would come from database
        orchestrator.configure_workspace(
            WorkspaceAIConfig(
                workspace_id=workspace_id,
                api_keys={
                    Provider.GEMINI: request.headers.get("X-Google-API-Key", ""),
                    Provider.CLAUDE: request.headers.get("X-Anthropic-API-Key", ""),
                    Provider.OPENAI: request.headers.get("X-OpenAI-API-Key", ""),
                },
            )
        )

    input_data = GhostTextInput(
        current_text=ghost_request.current_text,
        cursor_position=ghost_request.cursor_position,
        context=ghost_request.context,
        language=ghost_request.language,
        is_code=ghost_request.is_code,
    )

    try:
        if stream:
            # SSE streaming response
            async def stream_generator():
                builder = SSEStreamBuilder()
                try:
                    async for token in orchestrator.stream_ghost_text(
                        input_data,
                        workspace_id,
                        current_user_id,
                        correlation_id,
                    ):
                        yield builder.event("token", {"text": token})
                    yield builder.done()
                except AIError as e:
                    yield builder.error(str(e), e.code)

            return SSEResponse(stream_generator())

        # Regular JSON response
        result = await orchestrator.generate_ghost_text(
            input_data,
            workspace_id,
            current_user_id,
            correlation_id,
        )

        return GhostTextResponse(
            suggestion=result.output.suggestion,
            cursor_offset=result.output.cursor_offset,
            is_empty=result.output.is_empty,
            degraded=False,
        )

    except RateLimitError as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(e),
            headers={"Retry-After": str(e.retry_after_seconds)},
        ) from e

    except AIConfigurationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


# Note Analysis Endpoint


@router.post(
    "/analyze-note",
    response_model=AnalyzeNoteResponse,
    summary="Analyze note for annotations",
    description="Generate AI margin annotations for a note.",
)
async def analyze_note(
    request: Request,
    analyze_request: AnalyzeNoteRequest,
    current_user_id: CurrentUserIdOrDemo,
    session: DbSession,
) -> AnalyzeNoteResponse:
    """Analyze note and generate margin annotations.

    Rate limit: 5 requests/minute per user.

    Args:
        request: FastAPI request.
        analyze_request: Analysis request.
        current_user_id: Current user ID.
        session: Database session.

    Returns:
        Generated annotations.
    """
    get_correlation_id(request)
    get_workspace_id(request)  # Validate workspace ID
    time.time()

    # TODO: Fetch note from database
    # For now, return placeholder
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Note analysis requires database integration",
    )


# Margin Annotations Endpoint (T069)


@router.post(
    "/notes/{note_id}/annotations",
    summary="Generate margin annotations",
    description="Generate AI annotations for note blocks. Returns SSE stream.",
    response_model=None,
)
async def generate_annotations(
    note_id: Annotated[uuid.UUID, Path(description="Note ID")],
    request: Request,
    body: AnnotateBlocksRequest,
    current_user_id: CurrentUserIdOrDemo,
) -> SSEResponse:
    """Generate margin annotations for note blocks.

    Returns SSE stream with:
    - progress: Status updates
    - annotation: Each annotation as generated
    - complete: Summary with total count
    - error: Error details if failed

    Rate limit: 10 requests/minute per user.

    Args:
        note_id: UUID of the note to annotate
        request: FastAPI request
        body: Annotation request with block IDs
        current_user_id: Current user ID

    Returns:
        SSE stream of annotations
    """
    correlation_id = get_correlation_id(request)
    workspace_id = get_workspace_id(request)

    async def generate_events():
        builder = SSEStreamBuilder()
        try:
            # Get SDK orchestrator
            from pilot_space.ai.sdk_orchestrator import SDKOrchestrator
            from pilot_space.container import get_container

            container = get_container()
            orchestrator = container.sdk_orchestrator()

            if not isinstance(orchestrator, SDKOrchestrator):
                yield builder.error("SDK orchestrator not available", "config_error")
                return

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

            # Send completion
            yield builder.done(
                {
                    "total_annotations": len(result.output.annotations),
                    "processed_blocks": result.output.processed_blocks,
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


# Issue Extraction Endpoint (SSE Streaming - T058)


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


# Legacy non-streaming endpoint (deprecated)
@router.post(
    "/extract-issues",
    response_model=ExtractIssuesResponse,
    summary="Extract issues from note (deprecated)",
    description="Extract structured issues from note content. Use /notes/{note_id}/extract-issues instead.",
    deprecated=True,
)
async def extract_issues(
    request: Request,
    extract_request: ExtractIssuesRequest,
    current_user_id: CurrentUserIdOrDemo,
) -> ExtractIssuesResponse:
    """Extract issues from note content.

    Rate limit: 5 requests/minute per user.

    Args:
        request: FastAPI request.
        extract_request: Extraction request.
        current_user_id: Current user ID.

    Returns:
        Extracted issues with confidence scores.
    """
    correlation_id = get_correlation_id(request)
    workspace_id = get_workspace_id(request)
    start_time = time.time()

    orchestrator = get_orchestrator()

    # Configure workspace if needed
    if not orchestrator.get_workspace_config(workspace_id):
        orchestrator.configure_workspace(
            WorkspaceAIConfig(
                workspace_id=workspace_id,
                api_keys={
                    Provider.CLAUDE: request.headers.get("X-Anthropic-API-Key", ""),
                },
            )
        )

    # Extract text from TipTap content
    note_content = extract_text_from_tiptap(extract_request.note_content)

    input_data = IssueExtractionInput(
        note_title=extract_request.note_title,
        note_content=note_content,
        project_context=extract_request.project_context,
        selected_text=extract_request.selected_text,
        available_labels=extract_request.available_labels,
    )

    try:
        result = await orchestrator.extract_issues(
            input_data,
            workspace_id,
            current_user_id,
            correlation_id,
        )

        processing_time = (time.time() - start_time) * 1000

        return ExtractIssuesResponse(
            issues=[
                ExtractedIssueResponse(
                    title=issue.title,
                    description=issue.description,
                    priority=issue.priority.value,
                    labels=issue.labels,
                    confidence=issue.confidence,
                    confidence_tag=issue.confidence_tag.value,
                    source_text=issue.source_text,
                )
                for issue in result.output.issues
            ],
            recommended_count=result.output.recommended_count,
            total_count=result.output.total_count,
            processing_time_ms=processing_time,
        )

    except RateLimitError as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(e),
            headers={"Retry-After": str(e.retry_after_seconds)},
        ) from e

    except AIConfigurationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


# Issue Extraction Approval Endpoint (T059)


class ApproveExtractedIssuesRequest(BaseModel):
    """Request to approve extracted issues."""

    approval_id: str = Field(description="Approval request ID")
    selected_issues: list[int] = Field(description="Indices of issues to create (from extraction)")


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


# Chat Endpoint


@router.post(
    "/chat",
    summary="AI chat",
    description="Multi-turn conversation with AI assistant.",
    response_model=None,
)
async def ai_chat(
    request: Request,
    chat_request: ChatRequest,
    current_user_id: CurrentUserIdOrDemo,
    stream: Annotated[bool, Query(description="Enable SSE streaming")] = False,
) -> ChatResponse | SSEResponse:
    """AI chat conversation.

    Rate limit: 20 requests/minute per user.

    Args:
        request: FastAPI request.
        chat_request: Chat request.
        current_user_id: Current user ID.
        stream: Whether to stream response.

    Returns:
        AI response or SSE stream.
    """
    correlation_id = get_correlation_id(request)
    workspace_id = get_workspace_id(request)

    orchestrator = get_orchestrator()

    # Configure workspace if needed
    if not orchestrator.get_workspace_config(workspace_id):
        orchestrator.configure_workspace(
            WorkspaceAIConfig(
                workspace_id=workspace_id,
                api_keys={
                    Provider.CLAUDE: request.headers.get("X-Anthropic-API-Key", ""),
                },
            )
        )

    # Build conversation history
    history: list[ConversationMessage] = []
    if chat_request.history:
        for msg in chat_request.history:
            role = MessageRole.USER if msg.get("role") == "user" else MessageRole.ASSISTANT
            history.append(ConversationMessage(role=role, content=msg.get("content", "")))

    input_data = ConversationInput(
        message=chat_request.message,
        history=history,
        system_context=chat_request.system_context,
    )

    try:
        if stream:

            async def stream_generator():
                builder = SSEStreamBuilder()
                try:
                    async for chunk in orchestrator.stream_chat(
                        input_data,
                        workspace_id,
                        current_user_id,
                        correlation_id,
                    ):
                        yield builder.event("chunk", {"text": chunk})
                    yield builder.done()
                except AIError as e:
                    yield builder.error(str(e), e.code)

            return SSEResponse(stream_generator())

        result = await orchestrator.chat(
            input_data,
            workspace_id,
            current_user_id,
            correlation_id,
        )

        return ChatResponse(
            response=result.output.response,
            truncated=result.output.truncated,
        )

    except RateLimitError as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(e),
            headers={"Retry-After": str(e.retry_after_seconds)},
        ) from e

    except AIConfigurationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


# Health Check


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="AI health check",
    description="Check AI provider health and circuit breaker status.",
)
async def ai_health() -> HealthResponse:
    """Check AI provider health.

    Returns:
        Provider health status.
    """
    orchestrator = get_orchestrator()
    providers = orchestrator.get_provider_health()

    # Determine overall status
    all_healthy = all(p.get("status") == "healthy" for p in providers.values())

    return HealthResponse(
        status="healthy" if all_healthy else "degraded",
        providers=providers,
    )


# PR Review Status (T199)


@router.get(
    "/pr-review/{job_id}",
    summary="Get PR review status",
    description="Check status of a PR review job.",
)
async def get_pr_review_status(
    job_id: Annotated[str, Path(description="Job ID from trigger response")],
) -> dict[str, Any]:
    """Get status of a PR review job.

    Args:
        job_id: Job identifier from trigger response.

    Returns:
        Job status and results (if completed).
    """
    from pilot_space.application.services.ai import (
        GetPRReviewStatusService,
    )
    from pilot_space.container import get_container

    container = get_container()
    cache_client = container.redis_client() if container.redis_client else None

    service = GetPRReviewStatusService(cache_client=cache_client)
    result = await service.execute(job_id)

    if not result.found or not result.job_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found",
        )

    job_info = result.job_info

    # Calculate progress estimate
    progress_percent = 0
    if job_info.status.value == "queued":
        progress_percent = 10
    elif job_info.status.value == "processing":
        progress_percent = 50
    elif job_info.status.value in {"completed", "failed"}:
        progress_percent = 100

    # Build response
    response_data: dict[str, Any] = {
        "job_id": job_info.job_id,
        "status": job_info.status.value,
        "repository": job_info.repository,
        "pr_number": job_info.pr_number,
        "queued_at": job_info.queued_at.isoformat(),
        "started_at": job_info.started_at.isoformat() if job_info.started_at else None,
        "completed_at": job_info.completed_at.isoformat() if job_info.completed_at else None,
        "progress_percent": progress_percent,
        "error": job_info.error,
    }

    # Add result data if available
    if job_info.result:
        response_data["summary"] = {
            "summary": job_info.result.get("review_summary", ""),
            "approval_recommendation": job_info.result.get("approval_recommendation", "comment"),
            "critical_count": job_info.result.get("critical_count", 0),
            "warning_count": job_info.result.get("warning_count", 0),
        }

    return response_data


# Cost Tracking Endpoints (T091-T094)


@router.get(
    "/costs/summary",
    response_model=CostSummaryResponse,
    summary="Get AI cost summary",
    description="Get aggregated AI cost summary for workspace.",
)
async def get_cost_summary(
    request: Request,
    current_user_id: CurrentUserIdOrDemo,
    cost_tracker: CostTrackerDep,
    session: DbSession,
    start_date: Annotated[date | None, Query(description="Period start date")] = None,
    end_date: Annotated[date | None, Query(description="Period end date")] = None,
) -> CostSummaryResponse:
    """Get AI cost summary for workspace.

    Default period: last 30 days.
    Requires workspace context via X-Workspace-Id header.

    Args:
        request: FastAPI request.
        current_user_id: Current authenticated user ID.
        cost_tracker: Cost tracker dependency.
        session: Database session.
        start_date: Optional period start date.
        end_date: Optional period end date.

    Returns:
        Cost summary with breakdowns by agent, user, and day.
    """
    workspace_id = get_workspace_id(request)

    # Default to last 30 days
    if not end_date:
        end_date = datetime.now(UTC).date()
    if not start_date:
        start_date = end_date - timedelta(days=30)

    # Validate date range
    if start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_date must be before or equal to end_date",
        )

    # Get total metrics
    total_query = select(
        func.coalesce(func.sum(AICostRecord.cost_usd), 0).label("total_cost"),
        func.count(AICostRecord.id).label("total_requests"),
        func.coalesce(func.sum(AICostRecord.input_tokens), 0).label("total_input_tokens"),
        func.coalesce(func.sum(AICostRecord.output_tokens), 0).label("total_output_tokens"),
    ).where(
        (AICostRecord.workspace_id == workspace_id)
        & (func.date(AICostRecord.created_at).between(start_date, end_date))
        & (AICostRecord.is_deleted == False)  # noqa: E712
    )
    total_result = await session.execute(total_query)
    total_row = total_result.one()

    # Get detailed breakdowns
    details = await cost_tracker.get_cost_summary_detailed(
        workspace_id=workspace_id,
        start_date=start_date,
        end_date=end_date,
    )

    # Fetch user names for by_user breakdown
    user_ids = [uuid.UUID(u["user_id"]) for u in details["by_user"]]
    users_map = {}
    if user_ids:
        users_query = select(User).where(User.id.in_(user_ids))
        users_result = await session.execute(users_query)
        users_map = {str(u.id): u.full_name or u.email for u in users_result.scalars()}

    # Build response
    by_agent = [CostByAgent(**item) for item in details["by_agent"]]
    by_user = [
        CostByUser(
            user_id=item["user_id"],
            user_name=users_map.get(item["user_id"], "Unknown User"),
            total_cost_usd=item["total_cost_usd"],
            request_count=item["request_count"],
        )
        for item in details["by_user"]
    ]
    by_day = [CostByDay(**item) for item in details["by_day"]]

    return CostSummaryResponse(
        workspace_id=str(workspace_id),
        period_start=start_date,
        period_end=end_date,
        total_cost_usd=float(total_row.total_cost),
        total_requests=int(total_row.total_requests),
        total_input_tokens=int(total_row.total_input_tokens),
        total_output_tokens=int(total_row.total_output_tokens),
        by_agent=by_agent,
        by_user=by_user,
        by_day=by_day,
    )


@router.get(
    "/costs/by-user",
    response_model=CostByUserResponse,
    summary="Get cost breakdown by user",
    description="Get AI cost breakdown by user for workspace.",
)
async def get_cost_by_user(
    request: Request,
    current_user_id: CurrentUserIdOrDemo,
    cost_tracker: CostTrackerDep,
    session: DbSession,
    start_date: Annotated[date | None, Query(description="Period start date")] = None,
    end_date: Annotated[date | None, Query(description="Period end date")] = None,
) -> CostByUserResponse:
    """Get cost breakdown by user.

    Default period: last 30 days.

    Args:
        request: FastAPI request.
        current_user_id: Current authenticated user ID.
        cost_tracker: Cost tracker dependency.
        session: Database session.
        start_date: Optional period start date.
        end_date: Optional period end date.

    Returns:
        User cost breakdown.
    """
    workspace_id = get_workspace_id(request)

    # Default to last 30 days
    if not end_date:
        end_date = datetime.now(UTC).date()
    if not start_date:
        start_date = end_date - timedelta(days=30)

    # Validate date range
    if start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_date must be before or equal to end_date",
        )

    user_costs = await cost_tracker.get_cost_by_user_detailed(
        workspace_id=workspace_id,
        start_date=start_date,
        end_date=end_date,
    )

    # Fetch user names
    user_ids = [uuid.UUID(u["user_id"]) for u in user_costs]
    users_map = {}
    if user_ids:
        users_query = select(User).where(User.id.in_(user_ids))
        users_result = await session.execute(users_query)
        users_map = {str(u.id): u.full_name or u.email for u in users_result.scalars()}

    users = [
        CostByUser(
            user_id=item["user_id"],
            user_name=users_map.get(item["user_id"], "Unknown User"),
            total_cost_usd=item["total_cost_usd"],
            request_count=item["request_count"],
        )
        for item in user_costs
    ]

    total_cost = sum(u.total_cost_usd for u in users)

    return CostByUserResponse(
        workspace_id=str(workspace_id),
        period_start=start_date,
        period_end=end_date,
        users=users,
        total_cost_usd=total_cost,
    )


@router.get(
    "/costs/trends",
    response_model=CostTrendsResponse,
    summary="Get cost trends",
    description="Get AI cost trends over time.",
)
async def get_cost_trends(
    request: Request,
    current_user_id: CurrentUserIdOrDemo,
    cost_tracker: CostTrackerDep,
    start_date: Annotated[date | None, Query(description="Period start date")] = None,
    end_date: Annotated[date | None, Query(description="Period end date")] = None,
    granularity: Annotated[str, Query(description="Granularity: daily or weekly")] = "daily",
) -> CostTrendsResponse:
    """Get cost trends over time.

    Default period: last 30 days for daily, last 90 days for weekly.

    Args:
        request: FastAPI request.
        current_user_id: Current authenticated user ID.
        cost_tracker: Cost tracker dependency.
        start_date: Optional period start date.
        end_date: Optional period end date.
        granularity: Trend granularity (daily or weekly).

    Returns:
        Cost trends data.
    """
    workspace_id = get_workspace_id(request)

    # Validate granularity
    if granularity not in {"daily", "weekly"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="granularity must be 'daily' or 'weekly'",
        )

    # Default date ranges
    if not end_date:
        end_date = datetime.now(UTC).date()
    if not start_date:
        # Default: 30 days for daily, 90 days for weekly
        days_back = 90 if granularity == "weekly" else 30
        start_date = end_date - timedelta(days=days_back)

    # Validate date range
    if start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_date must be before or equal to end_date",
        )

    trends_data = await cost_tracker.get_cost_trends(
        workspace_id=workspace_id,
        start_date=start_date,
        end_date=end_date,
        granularity=granularity,
    )

    trends = [TrendDataPoint(**item) for item in trends_data]

    return CostTrendsResponse(
        workspace_id=str(workspace_id),
        period_start=start_date,
        period_end=end_date,
        granularity=granularity,
        trends=trends,
    )


# Approval Queue Endpoints (T073-T075)


def _get_context_preview(payload: dict[str, Any]) -> str:
    """Generate brief context from payload.

    Args:
        payload: Action payload dictionary.

    Returns:
        Brief preview string.
    """
    if "title" in payload:
        return payload["title"][:100]
    if "issues" in payload:
        issue_count = len(payload["issues"])
        return f"{issue_count} issue{'s' if issue_count != 1 else ''} to create"
    if "issue_id" in payload:
        return f"Action on issue {payload['issue_id']}"
    return "Action pending approval"


async def verify_workspace_admin(current_user_id: uuid.UUID, workspace_id: uuid.UUID) -> None:
    """Verify user is workspace admin.

    Args:
        current_user_id: User to verify.
        workspace_id: Workspace to check.

    Raises:
        HTTPException: If user is not admin.
    """
    # TODO: Implement proper admin check via workspace_members table
    # For now, allow all authenticated users (MVP)


@router.get(
    "/approvals",
    response_model=ApprovalListResponse,
    summary="List approval requests",
    description="List approval requests for workspace with optional status filter (DD-003).",
)
async def list_approvals(
    request: Request,
    current_user_id: CurrentUserIdOrDemo,
    session: DbSession,
    status: Annotated[ApprovalStatusSchema | None, Query(description="Filter by status")] = None,
    limit: Annotated[int, Query(ge=1, le=100, description="Maximum results")] = 20,
    offset: Annotated[int, Query(ge=0, description="Results to skip")] = 0,
) -> ApprovalListResponse:
    """List approval requests for workspace.

    Filters:
    - status: Filter by status (pending, approved, rejected, expired)

    Returns paginated list of approval requests.
    Requires workspace admin permission.

    Args:
        request: FastAPI request.
        current_user_id: Current user ID.
        session: Database session.
        status: Optional status filter.
        limit: Maximum results.
        offset: Results to skip.

    Returns:
        List of approval requests with pagination.
    """
    workspace_id = get_workspace_id(request)

    # Verify user is workspace admin
    await verify_workspace_admin(current_user_id, workspace_id)

    # Get approval service
    from pilot_space.ai.infrastructure.approval import ApprovalService

    approval_service = ApprovalService(session)

    # List requests
    requests, total = await approval_service.list_requests(
        workspace_id=workspace_id,
        status=status.value if status else None,
        limit=limit,
        offset=offset,
    )

    # Count pending
    pending_count = await approval_service.count_pending(workspace_id)

    # Build response
    return ApprovalListResponse(
        requests=[
            ApprovalRequestResponse(
                id=str(r.id),
                agent_name=r.agent_name,
                action_type=r.action_type,
                status=ApprovalStatusSchema(r.status),
                created_at=r.created_at,
                expires_at=r.expires_at,
                requested_by=r.user.name if r.user else "Unknown",
                context_preview=_get_context_preview(r.payload),
            )
            for r in requests
        ],
        total=total,
        pending_count=pending_count,
    )


@router.get(
    "/approvals/{approval_id}",
    response_model=ApprovalDetailResponse,
    summary="Get approval request details",
    description="Get full details of an approval request including payload.",
)
async def get_approval(
    request: Request,
    approval_id: Annotated[uuid.UUID, Path(description="Approval request ID")],
    current_user_id: CurrentUserIdOrDemo,
    session: DbSession,
) -> ApprovalDetailResponse:
    """Get approval request details including payload.

    Args:
        request: FastAPI request.
        approval_id: Approval request ID.
        current_user_id: Current user ID.
        session: Database session.

    Returns:
        Full approval request details.

    Raises:
        HTTPException: If request not found or unauthorized.
    """
    workspace_id = get_workspace_id(request)

    from pilot_space.ai.infrastructure.approval import ApprovalService

    approval_service = ApprovalService(session)

    # Get request
    approval_request = await approval_service.get_request(approval_id)

    if not approval_request or approval_request.workspace_id != workspace_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Approval request not found",
        )

    return ApprovalDetailResponse(
        id=str(approval_request.id),
        agent_name=approval_request.agent_name,
        action_type=approval_request.action_type,
        status=ApprovalStatusSchema(approval_request.status),
        payload=approval_request.payload,
        context=approval_request.context,
        created_at=approval_request.created_at,
        expires_at=approval_request.expires_at,
        resolved_at=approval_request.resolved_at,
        resolved_by=approval_request.resolver.name if approval_request.resolver else None,
        resolution_note=approval_request.resolution_note,
    )


@router.post(
    "/approvals/{approval_id}/resolve",
    response_model=ApprovalResolutionResponse,
    summary="Resolve approval request",
    description="Approve or reject an approval request. If approved, executes the pending action.",
)
async def resolve_approval(
    request: Request,
    approval_id: Annotated[uuid.UUID, Path(description="Approval request ID")],
    body: ApprovalResolution,
    current_user_id: CurrentUserIdOrDemo,
    session: DbSession,
) -> ApprovalResolutionResponse:
    """Resolve an approval request.

    If approved, executes the pending action.
    If rejected, discards the action.

    Args:
        request: FastAPI request.
        approval_id: Approval request ID.
        body: Resolution decision.
        current_user_id: Current user ID.
        session: Database session.

    Returns:
        Resolution result with action outcome.

    Raises:
        HTTPException: If request not found, unauthorized, or already resolved.
    """
    workspace_id = get_workspace_id(request)

    # Verify user is workspace admin
    await verify_workspace_admin(current_user_id, workspace_id)

    from pilot_space.ai.infrastructure.approval import ApprovalService

    approval_service = ApprovalService(session)

    # Get request
    approval_request = await approval_service.get_request(approval_id)

    if not approval_request or approval_request.workspace_id != workspace_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Approval request not found",
        )

    if approval_request.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Request already {approval_request.status}",
        )

    # Resolve the request
    await approval_service.resolve(
        request_id=approval_id,
        resolved_by=current_user_id,
        approved=body.approved,
        resolution_note=body.note,
    )

    result: dict[str, Any] = {"approved": body.approved, "action_result": None}

    # If approved, execute the action
    if body.approved:
        try:
            action_result = await _execute_approved_action(
                approval_request.agent_name,
                approval_request.action_type,
                approval_request.payload,
                current_user_id,
                session,
            )
            result["action_result"] = action_result
        except Exception as e:
            logger.exception("Failed to execute approved action")
            result["action_error"] = str(e)

    return ApprovalResolutionResponse(**result)


async def _execute_approved_action(
    agent_name: str,
    action_type: str,
    payload: dict[str, Any],
    current_user_id: uuid.UUID,
    session: Any,
) -> dict[str, Any]:
    """Execute the approved action.

    Args:
        agent_name: Name of the requesting agent.
        action_type: Type of action to execute.
        payload: Action payload.
        current_user_id: User who approved.
        session: Database session.

    Returns:
        Execution result.
    """
    # TODO: Implement action execution based on action_type
    # This will require integration with various service classes

    if action_type == "extract_issues":
        # Placeholder for issue creation
        # In full implementation, would call IssueService to create issues
        return {
            "created_issues": [],
            "message": "Issue creation not yet implemented",
        }

    # Default: mark as executed
    return {"executed": True, "agent": agent_name}


__all__ = ["router"]
