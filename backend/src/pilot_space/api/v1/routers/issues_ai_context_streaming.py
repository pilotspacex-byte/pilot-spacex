"""AI Context Streaming API endpoints.

T210: SSE streaming endpoints for AI context operations.

Endpoints:
- POST /issues/{id}/ai-context/chat/stream - SSE refinement streaming
- POST /issues/{id}/ai-context/stream - SSE generation with section events
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from pilot_space.api.v1.schemas.ai_context import RefineContextRequest
from pilot_space.api.v1.streaming import format_sse_event
from pilot_space.dependencies import (
    get_ai_context_service,
    get_current_user_id,
    get_current_workspace_id,
    get_redis_client,
    get_refine_ai_context_service,
    get_session,
)
from pilot_space.infrastructure.cache.redis import RedisClient
from pilot_space.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from pilot_space.infrastructure.database.models.ai_context import AIContext

logger = get_logger(__name__)

router = APIRouter(prefix="/issues/{issue_id}/ai-context", tags=["ai-context"])


async def _check_rate_limit(
    redis: RedisClient,
    user_id: str,
    limit: int = 5,
    window_seconds: int = 3600,
) -> bool:
    """Check if user is within rate limit using Redis INCR + TTL.

    Args:
        redis: Redis client instance.
        user_id: User UUID string.
        limit: Max requests per window.
        window_seconds: Time window in seconds.

    Returns:
        True if within limit, False if exceeded.
        Defaults to allowing the request if Redis is unavailable.
    """
    key = f"ai_context_ratelimit:{user_id}"
    current = await redis.incr(key)
    if current is None:
        # Redis unavailable — allow the request (fail-open)
        logger.warning("Redis unavailable for rate limiting, allowing request for user %s", user_id)
        return True
    if current == 1:
        await redis.expire(key, window_seconds)
    return current <= limit


# =============================================================================
# DB → SSE Mappers
# =============================================================================

# State name to state group mapping for SSE payloads
_STATE_GROUP_MAP: dict[str, str] = {
    "Backlog": "unstarted",
    "Todo": "unstarted",
    "In Progress": "started",
    "In Review": "started",
    "Done": "completed",
    "Cancelled": "cancelled",
}


def _map_context_summary(
    context: AIContext,
    result_summary: str,
) -> dict[str, Any]:
    """Map AIContext model to context_summary SSE payload.

    Args:
        context: Full AIContext model from DB.
        result_summary: Summary text from service result.

    Returns:
        Dict matching ContextSummary frontend interface.
    """
    issue = context.issue
    return {
        "issueIdentifier": issue.identifier if issue else "",
        "title": issue.name if issue else "",
        "summaryText": result_summary,
        "stats": {
            "relatedCount": len(context.related_issues),
            "docsCount": len(context.related_notes) + len(context.related_pages),
            "filesCount": len(context.code_references),
            "tasksCount": len(context.tasks_checklist),
        },
    }


def _map_related_issues(context: AIContext) -> list[dict[str, Any]]:
    """Map AIContext.related_issues to ContextRelatedIssue[] SSE payload.

    Args:
        context: Full AIContext model from DB.

    Returns:
        List of dicts matching ContextRelatedIssue frontend interface.
    """
    items: list[dict[str, Any]] = []
    for issue_data in context.related_issues:
        state_name = issue_data.get("state", "")
        items.append(
            {
                "relationType": issue_data.get("relation_type", "relates"),
                "issueId": issue_data.get("id", ""),
                "identifier": issue_data.get("identifier", ""),
                "title": issue_data.get("title", ""),
                "summary": issue_data.get("excerpt", ""),
                "status": state_name,
                "stateGroup": _STATE_GROUP_MAP.get(state_name, "unstarted"),
            }
        )
    return items


def _map_related_docs(context: AIContext) -> list[dict[str, Any]]:
    """Map AIContext.related_notes + related_pages to ContextRelatedDoc[] SSE payload.

    Args:
        context: Full AIContext model from DB.

    Returns:
        List of dicts matching ContextRelatedDoc frontend interface.
    """
    items: list[dict[str, Any]] = []
    for note_data in context.related_notes:
        items.append(
            {
                "docType": "note",
                "title": note_data.get("title", ""),
                "summary": note_data.get("excerpt", ""),
            }
        )
    for page_data in context.related_pages:
        items.append(
            {
                "docType": "spec",
                "title": page_data.get("title", ""),
                "summary": page_data.get("excerpt", ""),
            }
        )
    return items


def _map_tasks(context: AIContext) -> list[dict[str, Any]]:
    """Map AIContext.tasks_checklist to ContextTask[] SSE payload.

    Args:
        context: Full AIContext model from DB.

    Returns:
        List of dicts matching ContextTask frontend interface.
    """
    items: list[dict[str, Any]] = []
    for idx, task in enumerate(context.tasks_checklist):
        # Map string dependencies to int indices where possible
        raw_deps = task.get("dependencies", [])
        int_deps: list[int] = []
        for dep in raw_deps:
            if isinstance(dep, int):
                int_deps.append(dep)
            elif isinstance(dep, str) and dep.isdigit():
                int_deps.append(int(dep))

        items.append(
            {
                "id": task.get("id", task.get("order", idx)),
                "title": task.get("description", ""),
                "estimate": _effort_to_estimate(task.get("estimated_effort", "M")),
                "dependencies": int_deps,
                "completed": task.get("completed", False),
            }
        )
    return items


def _effort_to_estimate(effort: str) -> str:
    """Convert effort size (S/M/L/XL) to human-readable estimate.

    Args:
        effort: Effort code from task data.

    Returns:
        Human-readable estimate string.
    """
    mapping = {"S": "~1h", "M": "~2-3h", "L": "~4-6h", "XL": "~8h+"}
    return mapping.get(effort, "~2-3h")


def _map_prompts(context: AIContext) -> list[dict[str, Any]]:
    """Map AIContext.claude_code_prompt + tasks to ContextPrompt[] SSE payload.

    Creates per-task metadata entries plus a single full-prompt entry.
    Falls back to single prompt if no tasks.

    Args:
        context: Full AIContext model from DB.

    Returns:
        List of dicts matching ContextPrompt frontend interface.
    """
    prompt_text = context.claude_code_prompt or ""
    tasks = context.tasks_checklist or []

    if not prompt_text:
        return []

    # If tasks exist, create per-task metadata entries + one full prompt
    if tasks:
        items: list[dict[str, Any]] = []
        for idx, task in enumerate(tasks):
            task_desc = task.get("description", "Unnamed task")
            items.append(
                {
                    "taskId": idx,
                    "title": f"Task {idx + 1}: {task_desc}",
                    "content": (
                        f"## {task_desc}\n\n"
                        f"Estimated effort: {_effort_to_estimate(task.get('estimated_effort', 'M'))}\n\n"
                        f"Dependencies: {', '.join(str(d) for d in task.get('dependencies', [])) or 'None'}"
                    ),
                }
            )
        # Append full implementation prompt as last entry
        items.append(
            {
                "taskId": len(tasks),
                "title": "Full Implementation Guide",
                "content": prompt_text,
            }
        )
        return items

    # Fallback: single prompt covering the whole issue
    return [
        {
            "taskId": 0,
            "title": "Implementation Guide",
            "content": prompt_text,
        }
    ]


@router.post(
    "/chat/stream",
    response_class=StreamingResponse,
    summary="Stream refinement response via SSE",
)
async def stream_ai_context_refinement(
    issue_id: UUID,
    request: RefineContextRequest,
    workspace_id: Annotated[UUID, Depends(get_current_workspace_id)],
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    session: Annotated[..., Depends(get_session)],
    service: Annotated[..., Depends(get_refine_ai_context_service)],
):
    """Stream AI context refinement response via SSE.

    Args:
        issue_id: Issue UUID.
        request: Refinement request with query.
        workspace_id: Current workspace.
        user_id: Current user.
        session: Database session.
        service: Refine AI context service.

    Returns:
        Streaming SSE response.
    """
    import uuid as uuid_module

    from pilot_space.application.services.ai_context import RefineAIContextPayload

    payload = RefineAIContextPayload(
        workspace_id=workspace_id,
        issue_id=issue_id,
        user_id=user_id,
        query=request.query,
        correlation_id=str(uuid_module.uuid4()),
    )

    async def event_generator():
        """Generate SSE events."""
        try:
            async for chunk in service.stream(payload):
                yield format_sse_event("text_delta", {"delta": chunk})
            yield format_sse_event("done", {})
        except Exception:
            logger.exception("Error streaming refinement")
            yield format_sse_event(
                "error",
                {"message": "Refinement failed. Please try again.", "type": "refinement_error"},
            )

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@router.post(
    "/stream",
    response_class=StreamingResponse,
    summary="Stream AI context generation with phase updates",
)
async def stream_ai_context_generation(
    issue_id: UUID,
    workspace_id: Annotated[UUID, Depends(get_current_workspace_id)],
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    session: Annotated[..., Depends(get_session)],
    service: Annotated[..., Depends(get_ai_context_service)],
    redis: Annotated[RedisClient, Depends(get_redis_client)],
):
    """Stream AI context generation with section-based SSE events.

    SSE Events (in order):
    - 'phase': Progress indicators during generation
    - 'context_summary': Issue overview with stats
    - 'related_issues': Related issues with relation types
    - 'related_docs': Related documents (notes, ADRs, specs)
    - 'ai_tasks': Implementation tasks with dependencies
    - 'ai_prompts': Ready-to-use Claude Code prompts
    - 'context_error': Per-section errors (other sections still stream)
    - 'context_complete': All sections finished
    - 'error': Fatal generation error

    Args:
        issue_id: Issue UUID.
        workspace_id: Current workspace.
        user_id: Current user.
        session: Database session.
        service: AI context service.

    Returns:
        Streaming SSE response with section events.
    """
    from pilot_space.application.services.ai_context import GenerateAIContextPayload
    from pilot_space.infrastructure.database.repositories import AIContextRepository

    # Define phases for progress tracking
    phases = [
        "Analyzing issue",
        "Finding related docs",
        "Searching codebase",
        "Finding similar issues",
        "Generating implementation guide",
    ]

    async def phase_generator():
        """Generate SSE events with phase progress and section data."""
        try:
            # Emit initial pending status for all phases
            for phase_name in phases:
                yield format_sse_event("phase", {"name": phase_name, "status": "pending"})

            # Check rate limit
            if not await _check_rate_limit(redis, str(user_id)):
                yield format_sse_event(
                    "error",
                    {
                        "message": "Rate limit exceeded. Maximum 5 context generations per hour.",
                        "type": "rate_limit_error",
                    },
                )
                return

            import uuid as uuid_module

            payload = GenerateAIContextPayload(
                workspace_id=workspace_id,
                issue_id=issue_id,
                user_id=user_id,
                force_regenerate=False,
                correlation_id=str(uuid_module.uuid4()),
            )

            # Emit phase progress sequentially (complete previous before starting next)
            for i, phase_name in enumerate(phases):
                if i > 0:
                    yield format_sse_event(
                        "phase",
                        {"name": phases[i - 1], "status": "complete"},
                    )
                yield format_sse_event("phase", {"name": phase_name, "status": "in_progress"})

            # Execute the service (blocks until complete)
            result = await service.execute(payload)

            # Mark final phase complete
            yield format_sse_event(
                "phase",
                {"name": phases[-1], "status": "complete"},
            )

            # Fetch full AIContext model for structured section data
            context_repo = AIContextRepository(session)
            context = await context_repo.get_by_issue_id(issue_id)

            if not context:
                # Fallback: emit legacy complete event if context not found
                yield format_sse_event(
                    "complete",
                    {
                        "claudeCodePrompt": result.claude_code_prompt or "",
                        "relatedDocs": [],
                        "relatedCode": [],
                        "similarIssues": [],
                    },
                )
                yield format_sse_event("context_complete", {})
                return

            # Emit structured section events with per-section error isolation
            # Section 1: context_summary
            try:
                summary_payload = _map_context_summary(
                    context,
                    result.summary,
                )
                yield format_sse_event("context_summary", summary_payload)
            except Exception as e:
                logger.warning("Failed to map context_summary: %s", e, exc_info=True)
                yield format_sse_event(
                    "context_error",
                    {
                        "section": "summary",
                        "message": "Failed to generate summary. Please try again.",
                    },
                )

            # Section 2: related_issues
            try:
                related_issues = _map_related_issues(context)
                yield format_sse_event("related_issues", {"items": related_issues})
            except Exception as e:
                logger.warning("Failed to map related_issues: %s", e, exc_info=True)
                yield format_sse_event(
                    "context_error",
                    {
                        "section": "related_issues",
                        "message": "Failed to load related issues. Please try again.",
                    },
                )

            # Section 3: related_docs
            try:
                related_docs = _map_related_docs(context)
                yield format_sse_event("related_docs", {"items": related_docs})
            except Exception as e:
                logger.warning("Failed to map related_docs: %s", e, exc_info=True)
                yield format_sse_event(
                    "context_error",
                    {
                        "section": "related_docs",
                        "message": "Failed to load related documents. Please try again.",
                    },
                )

            # Section 4: ai_tasks
            try:
                tasks = _map_tasks(context)
                yield format_sse_event("ai_tasks", {"items": tasks})
            except Exception as e:
                logger.warning("Failed to map ai_tasks: %s", e, exc_info=True)
                yield format_sse_event(
                    "context_error",
                    {"section": "tasks", "message": "Failed to generate tasks. Please try again."},
                )

            # Section 5: ai_prompts
            try:
                prompts = _map_prompts(context)
                yield format_sse_event("ai_prompts", {"items": prompts})
            except Exception as e:
                logger.warning("Failed to map ai_prompts: %s", e, exc_info=True)
                yield format_sse_event(
                    "context_error",
                    {
                        "section": "prompts",
                        "message": "Failed to generate prompts. Please try again.",
                    },
                )

            # Final: signal all sections complete
            yield format_sse_event("context_complete", {})

        except ValueError:
            logger.warning("Validation error in AI context generation")
            yield format_sse_event(
                "error",
                {
                    "message": "Invalid request parameters. Please check your input.",
                    "type": "validation_error",
                },
            )
        except Exception:
            logger.exception("Error streaming AI context generation")
            yield format_sse_event(
                "error",
                {
                    "message": "Failed to generate AI context. Please try again.",
                    "type": "generation_error",
                },
            )

    return StreamingResponse(
        phase_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


__all__ = ["router"]
