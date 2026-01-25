"""AI API router.

Endpoints for AI-powered features:
- Ghost text generation (SSE streaming)
- Note analysis and margin annotations
- Issue extraction from notes
- AI conversation

T096: AI router implementation.
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Path, Query, Request, status
from pydantic import BaseModel, Field

from pilot_space.ai.agents.base import Provider
from pilot_space.ai.agents.conversation_agent import (
    ConversationInput,
    ConversationMessage,
    MessageRole,
)
from pilot_space.ai.agents.ghost_text_agent import GhostTextInput
from pilot_space.ai.agents.issue_extractor_agent import IssueExtractionInput
from pilot_space.ai.exceptions import AIConfigurationError, AIError, RateLimitError
from pilot_space.ai.orchestrator import WorkspaceAIConfig, get_orchestrator
from pilot_space.api.utils.sse import SSEResponse, SSEStreamBuilder
from pilot_space.api.v1.schemas.annotation import (
    AnalyzeNoteRequest,
    AnalyzeNoteResponse,
)
from pilot_space.api.v1.schemas.note import extract_text_from_tiptap
from pilot_space.dependencies import CurrentUserIdOrDemo, DbSession

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


# Issue Extraction Endpoint


@router.post(
    "/extract-issues",
    response_model=ExtractIssuesResponse,
    summary="Extract issues from note",
    description="Extract structured issues from note content.",
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


__all__ = ["router"]
