"""Unified AI chat endpoint for conversational agents.

Provides endpoints for AI chat interactions with streaming responses via SSE.
Supports both queue-based async mode and direct blocking SSE mode.

Queue mode (AI_QUEUE_MODE=true):
    POST /chat → enqueue job → return {job_id, session_id, stream_url}
    GET /chat/stream/{job_id} → Redis pub/sub SSE stream

Direct mode (AI_QUEUE_MODE=false):
    POST /chat → PilotSpaceAgent.stream() → SSE StreamingResponse

Reference: docs/architect/pilotspace-agent-architecture.md
Design Decisions: DD-058 (SSE streaming), DD-003 (Approval flow)
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID, uuid4

import orjson
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import Field

from pilot_space.api.v1.schemas.base import BaseSchema
from pilot_space.dependencies import (
    CurrentUserIdOrDemo,
    DbSession,
    PilotSpaceAgentDep,
    QueueClientDep,
    RedisDep,
    SessionHandlerDep,
    SkillRegistryDep,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["ai-chat"])


class ChatContext(BaseSchema):
    """Context for AI chat request."""

    workspace_id: UUID = Field(..., description="Workspace ID for context")
    note_id: UUID | None = Field(None, description="Note ID if chatting within note")
    issue_id: UUID | None = Field(None, description="Issue ID if chatting about issue")
    project_id: UUID | None = Field(None, description="Project ID if chatting about project")
    selected_text: str | None = Field(
        None, max_length=10000, description="Selected text from editor"
    )
    selected_block_ids: list[str] = Field(
        default_factory=list,
        description="Block IDs selected in editor",
    )


class ChatRequest(BaseSchema):
    """Request for AI chat interaction."""

    message: str = Field(..., min_length=1, max_length=10000, description="User message")
    session_id: str | None = Field(None, description="Session ID to resume conversation")
    fork_session_id: str | None = Field(
        None,
        description="Session ID to fork from (creates a branch for what-if exploration)",
    )
    context: ChatContext = Field(..., description="Context for AI response")


class ChatQueueResponse(BaseSchema):
    """Response when queue mode is enabled."""

    job_id: str = Field(..., description="Queue job identifier")
    session_id: str = Field(..., description="Conversation session ID")
    stream_url: str = Field(..., description="URL to connect for SSE stream")


@router.post("/chat", response_model=None)
async def chat(
    chat_request: ChatRequest,
    fastapi_request: Request,
    user_id: CurrentUserIdOrDemo,
    session: DbSession,
    session_handler: SessionHandlerDep,
    agent: PilotSpaceAgentDep,
    queue_client: QueueClientDep,
    redis_client: RedisDep,
) -> StreamingResponse | ChatQueueResponse:
    """Unified AI chat endpoint with streaming responses.

    Supports:
    - Multi-turn conversations via session_id
    - Context-aware responses (note, issue, workspace)
    - Queue-based async mode (AI_QUEUE_MODE=true)
    - Direct SSE streaming mode (AI_QUEUE_MODE=false)

    Returns:
        StreamingResponse (direct mode) or ChatQueueResponse (queue mode).
    """
    from pilot_space.api.v1.middleware import extract_ai_context

    logger.info(
        "Chat request: message='%s', workspace_id=%s",
        chat_request.message[:50],
        chat_request.context.workspace_id,
    )

    # Extract full AI context (loads Note/Issue objects if IDs provided)
    ai_context = await extract_ai_context(
        request=fastapi_request,
        session=session,
        note_id=chat_request.context.note_id,
        issue_id=chat_request.context.issue_id,
        workspace_id=chat_request.context.workspace_id,
        selected_text=chat_request.context.selected_text,
    )

    # Forward selected block IDs for tool calls
    if chat_request.context.selected_block_ids:
        ai_context["selected_block_ids"] = chat_request.context.selected_block_ids

    # Get, fork, or create conversation session
    # Priority: fork > explicit session_id > context lookup > create new
    conv_session = None
    is_existing_session = False
    context_id = chat_request.context.note_id or chat_request.context.issue_id
    if session_handler is not None:
        if chat_request.fork_session_id:
            # Fork from existing session (what-if exploration)
            fork_source = UUID(chat_request.fork_session_id)
            conv_session = await session_handler.fork_session(
                source_session_id=fork_source,
                workspace_id=chat_request.context.workspace_id,
                user_id=user_id,
            )
        elif chat_request.session_id:
            session_id_uuid = UUID(chat_request.session_id)
            conv_session = await session_handler.get_session(
                session_id_uuid,
                workspace_id=chat_request.context.workspace_id,
                user_id=user_id,
            )
            if conv_session:
                is_existing_session = True
            else:
                logger.warning(
                    "Session %s not found in Redis, trying context lookup",
                    chat_request.session_id,
                )

        # Fallback: if explicit session_id failed or not provided, try context
        if conv_session is None and context_id:
            conv_session = await session_handler.get_session_by_context(
                user_id=user_id,
                workspace_id=chat_request.context.workspace_id,
                agent_name="conversation",
                context_id=context_id,
            )
            if conv_session:
                is_existing_session = True

        # Last resort: create new session
        if conv_session is None:
            conv_session = await session_handler.create_session(
                workspace_id=chat_request.context.workspace_id,
                user_id=user_id,
                agent_name="conversation",
                context_id=context_id,
            )

    logger.info(
        "Session resolved: id=%s, existing=%s, context_id=%s, requested=%s",
        conv_session.session_id if conv_session else None,
        is_existing_session,
        context_id,
        chat_request.session_id,
    )

    # Queue mode: enqueue and return job reference
    from pilot_space.config import get_settings
    from pilot_space.infrastructure.queue.models import QueueName

    settings = get_settings()
    if settings.ai_queue_mode and queue_client is not None:
        job_id = str(uuid4())
        await queue_client.enqueue(
            QueueName.AI_CHAT,
            {
                "job_id": job_id,
                "message": chat_request.message,
                "session_id": str(conv_session.session_id) if conv_session else None,
                "workspace_id": str(chat_request.context.workspace_id),
                "user_id": str(user_id),
                "context": ai_context,
            },
        )

        # Store job ownership in Redis for stream_job auth validation
        await redis_client.setex(
            f"stream:owner:{job_id}",
            600,  # 10 min TTL (matches stream session)
            str(user_id),
        )

        return ChatQueueResponse(
            job_id=job_id,
            session_id=str(conv_session.session_id) if conv_session else "",
            stream_url=f"/api/v1/ai/chat/stream/{job_id}",
        )

    # Direct mode: blocking SSE stream
    # session_id: tracking ID for all conversations (new or resumed)
    # resume_session_id: only set when resuming an existing session (triggers
    # --resume in Claude SDK CLI to restore conversation history)
    agent_input = {
        "message": chat_request.message,
        "context": ai_context,
        "session_id": str(conv_session.session_id) if conv_session else None,
        "resume_session_id": (
            str(conv_session.session_id) if is_existing_session and conv_session else None
        ),
        "user_id": str(user_id),
        "workspace_id": str(chat_request.context.workspace_id),
    }

    async def stream_response():
        """Generate SSE stream from agent responses.

        Checks for client disconnect after each yielded chunk.
        When disconnect is detected, the generator exits which triggers
        the agent's finally block to interrupt the Claude SDK process.
        After streaming completes, persists the session to PostgreSQL.
        """
        import asyncio

        try:
            async with asyncio.timeout(600):
                async for sse_chunk in _execute_agent_stream(
                    agent, input_data=agent_input, context=ai_context
                ):
                    yield sse_chunk

                    # Detect client disconnect after each chunk
                    if await fastapi_request.is_disconnected():
                        logger.info("Client disconnected during chat stream, stopping")
                        break
        except TimeoutError:
            logger.warning("Direct SSE stream timeout")
            error_data = {
                "errorCode": "stream_timeout",
                "message": "Stream exceeded maximum duration",
                "retryable": False,
            }
            yield f"event: error\ndata: {orjson.dumps(error_data).decode()}\n\n"
        except Exception as e:
            logger.exception("Chat endpoint error: %s", e)
            error_data = {
                "errorCode": "api_error",
                "message": "An internal error occurred",
                "retryable": False,
            }
            yield f"event: error\ndata: {orjson.dumps(error_data).decode()}\n\n"

    async def _persist_session_background() -> None:
        """Persist session to PostgreSQL after stream completes.

        Runs as a BackgroundTask so the db session is fresh and the
        StreamingResponse generator has fully completed.
        """
        if not conv_session or not session_handler:
            return
        try:
            from pilot_space.infrastructure.database.engine import get_db_session

            async with get_db_session() as fresh_db:
                from pilot_space.ai.sdk.session_store import SessionStore

                store = SessionStore(
                    session_handler.session_manager,
                    fresh_db,
                )
                await store.save_to_db(conv_session.session_id)
                logger.info(
                    "Persisted session %s to database (background)",
                    conv_session.session_id,
                )
        except Exception:
            logger.exception(
                "Failed to persist session %s after stream",
                conv_session.session_id,
            )

    from starlette.background import BackgroundTask

    return StreamingResponse(
        stream_response(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
        background=BackgroundTask(_persist_session_background),
    )


class AbortRequest(BaseSchema):
    """Request to abort an active chat session."""

    session_id: str = Field(..., description="Session ID to abort")


class AbortResponse(BaseSchema):
    """Response from abort request."""

    status: str = Field(..., description="'interrupted' or 'not_found'")
    session_id: str = Field(..., description="Session ID that was targeted")


@router.post("/chat/abort", response_model=AbortResponse)
async def abort_chat(
    abort_request: AbortRequest,
    user_id: CurrentUserIdOrDemo,
    agent: PilotSpaceAgentDep,
    session_handler: SessionHandlerDep,
) -> AbortResponse:
    """Abort an active chat session.

    Sends interrupt signal to the Claude SDK subprocess, stopping
    the current turn gracefully. Called by frontend before closing
    SSE connection to ensure clean shutdown.

    Args:
        abort_request: Contains session_id to abort.
        user_id: Authenticated user ID (validates ownership).
        agent: PilotSpaceAgent instance.
        session_handler: Session handler for ownership verification.

    Returns:
        AbortResponse with status.

    Raises:
        HTTPException 403: If session does not belong to the user.
    """
    # Verify session ownership before allowing abort
    if session_handler is not None:
        session = await session_handler.get_session(UUID(abort_request.session_id))
        if session and session.user_id != user_id:
            raise HTTPException(status_code=403, detail="Access denied to this session")

    interrupted = await agent.interrupt_session(abort_request.session_id)
    return AbortResponse(
        status="interrupted" if interrupted else "not_found",
        session_id=abort_request.session_id,
    )


class AnswerRequest(BaseSchema):
    """Request to submit an answer to an agent question."""

    session_id: str = Field(..., description="Active chat session ID")
    question_id: str = Field(..., description="Question ID (tool call ID) to answer")
    answer: str = Field(..., min_length=1, max_length=5000, description="User's answer")


class AnswerResponse(BaseSchema):
    """Response from answer submission."""

    status: str = Field(..., description="'submitted' or 'error'")
    question_id: str = Field(..., description="Question ID that was answered")


@router.post("/chat/answer", response_model=AnswerResponse)
async def answer_question(
    answer_request: AnswerRequest,
    agent: PilotSpaceAgentDep,
    _current_user: CurrentUserIdOrDemo,
) -> AnswerResponse:
    """Submit a user answer to an agent's AskUserQuestion.

    The agent pauses execution when it calls AskUserQuestion.
    This endpoint delivers the user's response so the agent can continue.

    Args:
        answer_request: Contains session_id, question_id, and answer.
        agent: PilotSpaceAgent instance.

    Returns:
        AnswerResponse with submission status.
    """
    try:
        await agent.submit_tool_result(
            session_id=answer_request.session_id,
            tool_call_id=answer_request.question_id,
            result=answer_request.answer,
        )
        return AnswerResponse(
            status="submitted",
            question_id=answer_request.question_id,
        )
    except Exception as e:
        logger.exception("Failed to submit answer: %s", e)
        return AnswerResponse(
            status="error",
            question_id=answer_request.question_id,
        )


@router.get("/chat/stream/{job_id}")
async def stream_job(
    job_id: str,
    user_id: CurrentUserIdOrDemo,
    redis_client: RedisDep,
) -> StreamingResponse:
    """SSE stream endpoint for queue-mode chat jobs.

    Clients connect here after receiving a job_id from POST /chat.
    Delivers stored events (catch-up) then live events via Redis pub/sub.
    Validates that the authenticated user owns the job before streaming.

    Args:
        job_id: Queue job identifier.
        user_id: Authenticated user ID (validates ownership).
        redis_client: Redis client for pub/sub.

    Returns:
        StreamingResponse with SSE events.

    Raises:
        HTTPException 403: If job does not belong to the user.
    """
    # Validate job ownership via Redis metadata
    owner_raw = await redis_client.get_raw(f"stream:owner:{job_id}")
    if owner_raw is not None:
        owner_str = owner_raw.decode() if isinstance(owner_raw, bytes) else str(owner_raw)
        if owner_str != str(user_id):
            raise HTTPException(status_code=403, detail="Access denied to this stream")

    async def event_stream():
        import asyncio

        try:
            async with asyncio.timeout(600):
                # 1. Catch up on stored events (for reconnection or late connect)
                stored = await redis_client.lrange(f"stream:events:{job_id}", 0, -1)
                for event_bytes in stored:
                    yield event_bytes.decode()

                # 2. Subscribe to live events
                pubsub = await redis_client.subscribe(f"chat:stream:{job_id}")
                try:
                    async for msg in pubsub.listen():
                        if msg["type"] == "message":
                            data = msg["data"]
                            event_str = data.decode() if isinstance(data, bytes) else data
                            yield event_str
                            if '"stream_end"' in event_str or '"error"' in event_str:
                                break
                finally:
                    await pubsub.unsubscribe(f"chat:stream:{job_id}")
                    await pubsub.aclose()
        except TimeoutError:
            logger.warning("SSE stream timeout for job %s", job_id)
            error_data = {
                "errorCode": "stream_timeout",
                "message": "Stream exceeded maximum duration",
                "retryable": False,
            }
            yield f"event: error\ndata: {orjson.dumps(error_data).decode()}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ============================================================================
# Skills & Agents listing endpoints
# ============================================================================


class SkillListItem(BaseSchema):
    """Skill metadata for frontend display."""

    name: str = Field(..., description="Skill identifier (e.g., 'extract-issues')")
    description: str = Field(..., description="Brief description of skill purpose")
    when_to_use: str = Field(default="", description="Usage guidance")


class SkillListResponse(BaseSchema):
    """List of available skills."""

    skills: list[SkillListItem] = Field(default_factory=list, description="Available skills")
    total: int = Field(..., ge=0, description="Total skill count")


@router.get("/skills", response_model=SkillListResponse)
async def list_skills(
    skill_registry: SkillRegistryDep,
    _current_user: CurrentUserIdOrDemo,
) -> SkillListResponse:
    """List available AI skills for autocomplete."""
    if skill_registry is None:
        return SkillListResponse(skills=[], total=0)

    skills = skill_registry.list_skills()

    return SkillListResponse(
        skills=[
            SkillListItem(
                name=s.name,
                description=s.description or "",
                when_to_use=(s.when_to_use[:200] + "...")
                if s.when_to_use and len(s.when_to_use) > 200
                else (s.when_to_use or ""),
            )
            for s in skills
        ],
        total=len(skills),
    )


class AgentListItem(BaseSchema):
    """Agent metadata for frontend display."""

    name: str = Field(..., description="Agent identifier")
    description: str = Field(default="", description="Agent description")


class AgentListResponse(BaseSchema):
    """List of registered agents."""

    agents: list[AgentListItem] = Field(default_factory=list, description="Registered agents")
    total: int = Field(..., ge=0, description="Total agent count")


AGENT_DESCRIPTIONS: dict[str, str] = {
    "ghost_text": "Real-time writing suggestions",
    "margin_annotation": "Document margin suggestions",
    "issue_extractor": "Extract issues from notes",
    "ai_context": "Generate issue context",
    "conversation": "General AI assistant",
    "issue_enhancer": "Enhance issue details",
    "assignee_recommender": "Recommend issue assignees",
    "duplicate_detector": "Find duplicate issues",
    "pr_review": "Review pull requests",
    "commit_linker": "Link commits to issues",
    "doc_generator": "Generate documentation",
    "task_decomposer": "Break down issues into tasks",
    "diagram_generator": "Generate diagrams",
}


# ============================================================================
# Internal helpers
# ============================================================================


async def _execute_agent_stream(
    agent: Any,
    input_data: dict[str, Any],
    context: dict[str, Any],  # kept for API compatibility
):
    """Execute PilotSpaceAgent with streaming output.

    Bridges the FastAPI endpoint to PilotSpaceAgent.stream() method.

    Args:
        agent: PilotSpaceAgent instance.
        input_data: Dict with message, context, session_id, user_id, workspace_id.
        context: AI context dict (included for compatibility).

    Yields:
        SSE-formatted strings from PilotSpaceAgent.
    """
    from pilot_space.ai.agents.agent_base import AgentContext
    from pilot_space.ai.agents.pilotspace_agent import ChatInput

    chat_input = ChatInput(
        message=input_data["message"],
        session_id=UUID(input_data["session_id"]) if input_data.get("session_id") else None,
        resume_session_id=input_data.get("resume_session_id"),
        context=input_data.get("context", {}),
        user_id=UUID(input_data["user_id"]) if input_data.get("user_id") else None,
        workspace_id=UUID(input_data["workspace_id"]) if input_data.get("workspace_id") else None,
    )

    agent_context = AgentContext(
        workspace_id=UUID(input_data["workspace_id"]),
        user_id=UUID(input_data["user_id"]),
    )

    async for sse_chunk in agent.stream(chat_input, agent_context):
        yield sse_chunk
