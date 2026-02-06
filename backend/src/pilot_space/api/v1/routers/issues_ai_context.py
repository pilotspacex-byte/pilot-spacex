"""Issues AI Context API endpoints.

T210: Create AI Context endpoints for issues.

Endpoints:
- GET /issues/{id}/ai-context - Get or generate context
- POST /issues/{id}/ai-context/regenerate - Force regenerate
- POST /issues/{id}/ai-context/chat - Refine context via chat
- GET /issues/{id}/ai-context/export - Export context
- POST /issues/{id}/ai-context/tasks/{task_id}/complete - Mark task done
- DELETE /issues/{id}/ai-context/conversation - Clear conversation

Note: Streaming endpoints are in issues_ai_context_streaming.py
"""

from __future__ import annotations

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from pilot_space.api.v1.schemas.ai_context import (
    AIContextResponse,
    ChatMessageResponse,
    ConversationHistoryResponse,
    ExportContextResponse,
    GenerateContextResponse,
    RefineContextRequest,
    RefineContextResponse,
)
from pilot_space.dependencies import (
    get_ai_context_service,
    get_current_user,
    get_current_workspace_id,
    get_db_session_dep,
    get_refine_ai_context_service,
    get_user_api_keys,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/issues/{issue_id}/ai-context", tags=["ai-context"])


# Rate limiting tracking (simplified - use Redis in production)
_generation_counts: dict[str, list[float]] = {}


def _check_rate_limit(user_id: str, limit: int = 5, window_hours: int = 1) -> bool:
    """Check if user is within rate limit.

    Args:
        user_id: User UUID string.
        limit: Max requests per window.
        window_hours: Time window in hours.

    Returns:
        True if within limit, False if exceeded.
    """
    import time

    now = time.time()
    window_seconds = window_hours * 3600

    if user_id not in _generation_counts:
        _generation_counts[user_id] = []

    # Clean old entries
    _generation_counts[user_id] = [
        ts for ts in _generation_counts[user_id] if now - ts < window_seconds
    ]

    if len(_generation_counts[user_id]) >= limit:
        return False

    _generation_counts[user_id].append(now)
    return True


# =============================================================================
# AI Context Endpoints
# =============================================================================


@router.get(
    "",
    response_model=AIContextResponse,
    summary="Get AI context for an issue",
)
async def get_ai_context(
    issue_id: UUID,
    workspace_id: Annotated[UUID, Depends(get_current_workspace_id)],
    user_id: Annotated[UUID, Depends(get_current_user)],
    api_keys: Annotated[dict[str, str], Depends(get_user_api_keys)],
    session: Annotated[..., Depends(get_db_session_dep)],
    service: Annotated[..., Depends(get_ai_context_service)],
    generate_if_missing: bool = Query(default=True),
) -> AIContextResponse:
    """Get AI context for an issue, optionally generating if missing.

    If context exists and is fresh (< 1 hour old), returns cached version.
    If generate_if_missing is True, generates new context if not found.

    Args:
        issue_id: Issue UUID.
        workspace_id: Current workspace.
        user_id: Current user.
        api_keys: User's API keys.
        session: Database session.
        service: Generated AI context service.
        generate_if_missing: Generate if no context exists.

    Returns:
        AI context response.

    Raises:
        HTTPException: If context not found and generation disabled or failed.
    """
    from pilot_space.application.services.ai_context import GenerateAIContextPayload
    from pilot_space.infrastructure.database.repositories import AIContextRepository

    context_repo = AIContextRepository(session)

    # Try to get existing context
    context = await context_repo.get_by_issue_id(issue_id)

    if context and not context.is_stale:
        return AIContextResponse.from_model(context)

    if not generate_if_missing:
        if not context:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"AI context not found for issue: {issue_id}",
            )
        # Return stale context
        return AIContextResponse.from_model(context)

    # Check rate limit
    if not _check_rate_limit(str(user_id)):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Maximum 5 context generations per hour.",
        )

    import uuid as uuid_module

    payload = GenerateAIContextPayload(
        workspace_id=workspace_id,
        issue_id=issue_id,
        user_id=user_id,
        force_regenerate=False,
        correlation_id=str(uuid_module.uuid4()),
        api_keys=api_keys,
    )

    try:
        await service.execute(payload)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.exception("Failed to generate AI context")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate AI context: {e}",
        ) from e

    # Fetch and return the generated context
    context = await context_repo.get_by_issue_id(issue_id)
    if not context:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve generated context",
        )

    return AIContextResponse.from_model(context)


@router.post(
    "/regenerate",
    response_model=GenerateContextResponse,
    summary="Force regenerate AI context",
)
async def regenerate_ai_context(
    issue_id: UUID,
    workspace_id: Annotated[UUID, Depends(get_current_workspace_id)],
    user_id: Annotated[UUID, Depends(get_current_user)],
    api_keys: Annotated[dict[str, str], Depends(get_user_api_keys)],
    session: Annotated[..., Depends(get_db_session_dep)],
    service: Annotated[..., Depends(get_ai_context_service)],
) -> GenerateContextResponse:
    """Force regenerate AI context, bypassing cache.

    Rate limited to 5 generations per hour per user.

    Args:
        issue_id: Issue UUID.
        workspace_id: Current workspace.
        user_id: Current user.
        api_keys: User's API keys.
        session: Database session.
        service: Generated AI context service.

    Returns:
        Generation result.
    """
    from pilot_space.application.services.ai_context import GenerateAIContextPayload

    # Check rate limit
    if not _check_rate_limit(str(user_id)):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Maximum 5 context generations per hour.",
        )

    import uuid as uuid_module

    payload = GenerateAIContextPayload(
        workspace_id=workspace_id,
        issue_id=issue_id,
        user_id=user_id,
        force_regenerate=True,
        correlation_id=str(uuid_module.uuid4()),
        api_keys=api_keys,
    )

    try:
        result = await service.execute(payload)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.exception("Failed to regenerate AI context")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to regenerate AI context: {e}",
        ) from e

    return GenerateContextResponse(
        context_id=str(result.context_id),
        issue_id=str(result.issue_id),
        summary=result.summary,
        complexity=result.complexity,
        task_count=result.task_count,
        related_issue_count=result.related_issue_count,
        claude_code_prompt=result.claude_code_prompt,
        from_cache=result.from_cache,
        generated_at=result.generated_at,
        version=result.version,
    )


@router.post(
    "/chat",
    response_model=RefineContextResponse,
    summary="Refine AI context via chat",
)
async def refine_ai_context(
    issue_id: UUID,
    request: RefineContextRequest,
    workspace_id: Annotated[UUID, Depends(get_current_workspace_id)],
    user_id: Annotated[UUID, Depends(get_current_user)],
    api_keys: Annotated[dict[str, str], Depends(get_user_api_keys)],
    session: Annotated[..., Depends(get_db_session_dep)],
    service: Annotated[..., Depends(get_refine_ai_context_service)],
) -> RefineContextResponse:
    """Refine AI context with a chat message.

    Supports multi-turn conversation for context refinement.

    Args:
        issue_id: Issue UUID.
        request: Refinement request with query.
        workspace_id: Current workspace.
        user_id: Current user.
        api_keys: User's API keys.
        session: Database session.
        service: Refine AI context service.

    Returns:
        Refinement result.
    """
    import uuid as uuid_module

    from pilot_space.application.services.ai_context import RefineAIContextPayload

    payload = RefineAIContextPayload(
        workspace_id=workspace_id,
        issue_id=issue_id,
        user_id=user_id,
        query=request.query,
        correlation_id=str(uuid_module.uuid4()),
        api_keys=api_keys,
    )

    try:
        result = await service.execute(payload)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.exception("Failed to refine AI context")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to refine AI context: {e}",
        ) from e

    return RefineContextResponse(
        context_id=str(result.context_id),
        issue_id=str(result.issue_id),
        response=result.response,
        conversation_count=result.conversation_count,
        last_refined_at=result.last_refined_at,
    )


@router.get(
    "/export",
    response_model=ExportContextResponse,
    summary="Export AI context",
)
async def export_ai_context(
    issue_id: UUID,
    workspace_id: Annotated[UUID, Depends(get_current_workspace_id)],
    user_id: Annotated[UUID, Depends(get_current_user)],
    session: Annotated[..., Depends(get_db_session_dep)],
    format: str = Query(default="markdown", pattern="^(markdown|json)$"),
    include_conversation: bool = Query(default=False),
) -> ExportContextResponse:
    """Export AI context as markdown or JSON.

    Args:
        issue_id: Issue UUID.
        workspace_id: Current workspace.
        user_id: Current user.
        session: Database session.
        format: Export format (markdown or json).
        include_conversation: Include conversation history.

    Returns:
        Exported content.
    """
    from pilot_space.application.services.ai_context import (
        ExportAIContextPayload,
        ExportAIContextService,
        ExportFormat,
    )
    from pilot_space.infrastructure.database.repositories import (
        AIContextRepository,
        IssueRepository,
    )

    context_repo = AIContextRepository(session)
    issue_repo = IssueRepository(session)

    service = ExportAIContextService(
        session=session,
        ai_context_repository=context_repo,
        issue_repository=issue_repo,
    )

    export_format = ExportFormat.MARKDOWN if format == "markdown" else ExportFormat.JSON

    payload = ExportAIContextPayload(
        workspace_id=workspace_id,
        issue_id=issue_id,
        user_id=user_id,
        format=export_format,
        include_conversation=include_conversation,
    )

    try:
        result = await service.execute(payload)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e

    return ExportContextResponse(
        content=result.content,
        format=result.format.value,
        filename=result.filename,
        content_type=result.content_type,
    )


@router.get(
    "/conversation",
    response_model=ConversationHistoryResponse,
    summary="Get conversation history",
)
async def get_conversation_history(
    issue_id: UUID,
    session: Annotated[..., Depends(get_db_session_dep)],
) -> ConversationHistoryResponse:
    """Get conversation history for AI context.

    Args:
        issue_id: Issue UUID.
        session: Database session.

    Returns:
        Conversation history.
    """
    from pilot_space.infrastructure.database.repositories import AIContextRepository

    context_repo = AIContextRepository(session)
    context = await context_repo.get_by_issue_id(issue_id)

    if not context:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"AI context not found for issue: {issue_id}",
        )

    messages = [
        ChatMessageResponse(
            role=msg.get("role", "user"),
            content=msg.get("content", ""),
            timestamp=msg.get("timestamp"),
        )
        for msg in (context.conversation_history or [])
    ]

    return ConversationHistoryResponse(
        messages=messages,
        total_count=len(messages),
    )


@router.delete(
    "/conversation",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Clear conversation history",
)
async def clear_conversation_history(
    issue_id: UUID,
    session: Annotated[..., Depends(get_db_session_dep)],
) -> None:
    """Clear conversation history for AI context.

    Args:
        issue_id: Issue UUID.
        session: Database session.
    """
    from pilot_space.infrastructure.database.repositories import AIContextRepository

    context_repo = AIContextRepository(session)
    result = await context_repo.clear_conversation_history(issue_id)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"AI context not found for issue: {issue_id}",
        )

    await session.commit()


@router.post(
    "/tasks/{task_id}/complete",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Mark a task as completed",
)
async def mark_task_completed(
    issue_id: UUID,
    task_id: str,
    session: Annotated[..., Depends(get_db_session_dep)],
) -> None:
    """Mark an implementation task as completed.

    Args:
        issue_id: Issue UUID.
        task_id: Task ID within the checklist.
        session: Database session.
    """
    from pilot_space.infrastructure.database.repositories import AIContextRepository

    context_repo = AIContextRepository(session)
    result = await context_repo.mark_task_completed(issue_id, task_id)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task '{task_id}' not found in AI context for issue: {issue_id}",
        )

    await session.commit()


__all__ = ["router"]
