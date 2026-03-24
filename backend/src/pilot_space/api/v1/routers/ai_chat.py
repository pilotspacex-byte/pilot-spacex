"""Unified AI chat endpoint for conversational agents.

Provides endpoints for AI chat interactions with streaming responses via SSE.

Flow:
    POST /chat → PilotSpaceAgent.stream() → SSE StreamingResponse

Reference: docs/architect/pilotspace-agent-architecture.md
Design Decisions: DD-066 (SSE streaming), DD-003 (Approval flow)
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import orjson
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from pilot_space.ai.sdk.question_adapter import Question, get_question_adapter
from pilot_space.ai.session.session_manager import AIMessage
from pilot_space.api.v1.routers._chat_schemas import (
    AbortRequest,
    AbortResponse,
    ChatRequest,
    SkillListItem,
    SkillListResponse,
)
from pilot_space.api.v1.routers.ai_chat_model_routing import resolve_model_override
from pilot_space.dependencies import (
    CurrentUserId,
    DbSession,
    PilotSpaceAgentDep,
    SessionHandlerDep,
    SkillRegistryDep,
)
from pilot_space.domain.exceptions import ForbiddenError
from pilot_space.infrastructure.database.rls import set_rls_context
from pilot_space.infrastructure.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["ai-chat"])


async def _recover_question_from_session(
    chat_request: ChatRequest,
    session_handler: Any,
    question_id: UUID,
    question_id_str: str,
    answer_text: str,
) -> ChatRequest | None:
    """Recover question data from persisted session when in-memory registry is empty.

    When a question expires from QuestionAdapter (server restart, 1h cleanup),
    the question_data persisted on the assistant message can be used as fallback.

    Returns:
        Updated ChatRequest with formatted Q&A, or None if recovery failed.
    """
    if not chat_request.session_id or session_handler is None:
        return None

    try:
        sid = UUID(chat_request.session_id)
        mgr = session_handler.session_manager
        ai_session = await mgr.get_session(sid)

        for i in range(len(ai_session.messages) - 1, -1, -1):
            msg = ai_session.messages[i]
            if msg.role != "assistant":
                continue
            qd = msg.question_data
            if qd is None or qd.get("questionId") != question_id_str:
                continue

            # Rebuild Question models from persisted data
            questions_raw = qd.get("questions", [])
            recovered_questions = [Question.model_validate(q) for q in questions_raw]

            # Parse structured JSON answers
            answers_dict: dict[str, str] = {}
            try:
                parsed = orjson.loads(answer_text)
                if isinstance(parsed, dict):
                    answers_dict = {str(k): str(v) for k, v in parsed.items()}
            except (orjson.JSONDecodeError, TypeError):
                answers_dict = {"q0": answer_text}

            # Format Q&A pairs
            qa_lines: list[str] = []
            for qi, q in enumerate(recovered_questions):
                answer_key = f"q{qi}"
                answer_val = answers_dict.get(answer_key, "")
                qa_lines.append(f"Q: {q.question}\nA: {answer_val}")

            formatted_qa = "\n\n".join(qa_lines)
            if len(formatted_qa) > 8000:
                formatted_qa = formatted_qa[:8000] + "\n[Answer truncated]"

            # Update the message with answers
            old = ai_session.messages[i]
            ai_session.messages[i] = AIMessage(
                role=old.role,
                content=old.content,
                timestamp=old.timestamp,
                tokens=old.tokens,
                cost_usd=old.cost_usd,
                question_data={
                    "questionId": question_id_str,
                    "questions": [q.model_dump() for q in recovered_questions],
                    "answers": answers_dict,
                },
            )
            await mgr.persist_session(ai_session)

            return ChatRequest(
                message=f"[User answered AI question {question_id_str}]\n\n{formatted_qa}",
                session_id=chat_request.session_id,
                fork_session_id=chat_request.fork_session_id,
                context=chat_request.context,
                model_override=chat_request.model_override,
            )

    except Exception:
        logger.exception(
            "Failed to recover question_data for expired questionId=%s",
            question_id,
        )

    return None


@router.post("/chat", response_model=None)
async def chat(
    chat_request: ChatRequest,
    fastapi_request: Request,
    user_id: CurrentUserId,
    session: DbSession,
    session_handler: SessionHandlerDep,
    agent: PilotSpaceAgentDep,
) -> StreamingResponse:
    """Unified AI chat endpoint with streaming responses.

    Supports:
    - Multi-turn conversations via session_id
    - Context-aware responses (note, issue, workspace)
    - Direct SSE streaming

    Returns:
        StreamingResponse with SSE events.
    """
    from pilot_space.api.v1.middleware import extract_ai_context

    # Extract context fields with None-safe defaults
    ctx = chat_request.context
    ctx_workspace_id = ctx.workspace_id if ctx else None
    ctx_note_id = ctx.note_id if ctx else None
    ctx_issue_id = ctx.issue_id if ctx else None
    ctx_selected_text = ctx.selected_text if ctx else None
    ctx_selected_block_ids = ctx.selected_block_ids if ctx else []

    # Fallback: resolve workspace_id from middleware (X-Workspace-ID header)
    if ctx_workspace_id is None:
        middleware_ws = getattr(fastapi_request.state, "workspace_id", None)
        if middleware_ws:
            ctx_workspace_id = (
                UUID(middleware_ws) if isinstance(middleware_ws, str) else middleware_ws
            )

    logger.info(
        "Chat request: message='%s', workspace_id=%s, note_id=%s",
        chat_request.message[:50],
        ctx_workspace_id,
        ctx_note_id,
    )

    # Check for [ANSWER:{questionId}] prefix — stateless two-turn model
    # The answer arrives as a new chat turn. We format a contextual message
    # with the Q&A pairs and fall through to normal agent stream processing.
    answer_match = re.match(r"^\[ANSWER:([a-fA-F0-9-]+)\]\s*(.*)", chat_request.message, re.DOTALL)
    if answer_match:
        question_id_str = answer_match.group(1)
        answer_text = answer_match.group(2).strip()

        try:
            question_id = UUID(question_id_str)
            adapter = get_question_adapter()

            # Mark question as resolved in registry (cleanup)
            resolved = await adapter.mark_resolved(
                question_id=question_id,
                user_id=user_id,
            )

            # Build human-readable Q&A context for the agent
            if resolved is not None:
                qa_lines: list[str] = []
                # Parse structured JSON answers
                answers_dict: dict[str, str] = {}
                try:
                    parsed = orjson.loads(answer_text)
                    if isinstance(parsed, dict):
                        answers_dict = {str(k): str(v) for k, v in parsed.items()}
                except (orjson.JSONDecodeError, TypeError):
                    answers_dict = {"q0": answer_text}

                for i, q in enumerate(resolved.questions):
                    answer_key = f"q{i}"
                    answer_val = answers_dict.get(answer_key, "")
                    qa_lines.append(f"Q: {q.question}\nA: {answer_val}")

                formatted_qa = "\n\n".join(qa_lines)
                # Truncate to prevent excessive token consumption
                if len(formatted_qa) > 8000:
                    formatted_qa = formatted_qa[:8000] + "\n[Answer truncated]"
                # Replace the raw message with formatted Q&A context
                chat_request = ChatRequest(
                    message=f"[User answered AI question {question_id_str}]\n\n{formatted_qa}",
                    session_id=chat_request.session_id,
                    fork_session_id=chat_request.fork_session_id,
                    context=chat_request.context,
                    model_override=chat_request.model_override,
                )

                # Persist question_data on last assistant message for session resume
                if chat_request.session_id and session_handler is not None:
                    try:
                        sid = UUID(chat_request.session_id)
                        mgr = session_handler.session_manager
                        ai_session = await mgr.get_session(sid)
                        for i in range(len(ai_session.messages) - 1, -1, -1):
                            if ai_session.messages[i].role == "assistant":
                                old = ai_session.messages[i]
                                ai_session.messages[i] = AIMessage(
                                    role=old.role,
                                    content=old.content,
                                    timestamp=old.timestamp,
                                    tokens=old.tokens,
                                    cost_usd=old.cost_usd,
                                    question_data={
                                        "questionId": str(question_id),
                                        "questions": [q.model_dump() for q in resolved.questions],
                                        "answers": answers_dict,
                                    },
                                )
                                await mgr.persist_session(ai_session)
                                break
                    except Exception:
                        logger.exception(
                            "Failed to persist question_data for questionId=%s",
                            question_id,
                        )

                logger.info(
                    "Formatted answer for questionId=%s as new chat turn",
                    question_id,
                )
            else:
                # Fallback: question expired from in-memory registry (server restart,
                # cleanup, etc.) but question_data was persisted on the assistant message.
                recovered = await _recover_question_from_session(
                    chat_request, session_handler, question_id, question_id_str, answer_text
                )
                if recovered is not None:
                    chat_request = recovered
                    logger.info(
                        "Recovered expired question from session: questionId=%s",
                        question_id,
                    )
                else:
                    logger.warning(
                        "Question %s not found in registry or session, processing as normal message",
                        question_id,
                    )
            # Fall through to normal chat processing (agent receives answer as new turn)
        except ValueError:
            logger.warning(
                "Invalid UUID in [ANSWER:] prefix: %s",
                question_id_str,
            )
            # Fall through to normal chat processing

    # Set RLS context BEFORE any DB queries (note/issue loading, session lookup)
    # This ensures extract_ai_context and session operations respect RLS policies
    await set_rls_context(session, user_id)

    # Fetch and inject attachment content blocks
    from pilot_space.api.v1.routers._chat_attachments import resolve_attachments

    ctx_attachment_ids = ctx.attachment_ids if ctx else []
    attachments, attachment_content_blocks = await resolve_attachments(
        ctx_attachment_ids if ctx_workspace_id is not None else [],
        user_id,
        session,
        storage_client=fastapi_request.app.state.container.storage_client(),
    )

    # Extract full AI context (loads Note/Issue objects if IDs provided)
    if ctx_workspace_id is not None:
        ai_context = await extract_ai_context(
            request=fastapi_request,
            session=session,
            note_id=ctx_note_id,
            issue_id=ctx_issue_id,
            workspace_id=ctx_workspace_id,
            selected_text=ctx_selected_text,
        )
    else:
        # No workspace context — allow contextless chat (no RLS scoping)
        ai_context: dict[str, object] = {}
        if ctx_selected_text:
            ai_context["selected_text"] = ctx_selected_text

    # Forward selected block IDs for tool calls
    if ctx_selected_block_ids:
        ai_context["selected_block_ids"] = ctx_selected_block_ids

    # Get, fork, or create conversation session
    # Priority: fork > explicit session_id > context lookup > create new
    conv_session = None
    is_existing_session = False
    context_id = ctx_note_id or ctx_issue_id
    if session_handler is not None:
        if chat_request.fork_session_id and ctx_workspace_id is not None:
            # Fork from existing session (what-if exploration)
            fork_source = UUID(chat_request.fork_session_id)
            conv_session = await session_handler.fork_session(
                source_session_id=fork_source,
                workspace_id=ctx_workspace_id,
                user_id=user_id,
            )
        elif chat_request.session_id:
            session_id_uuid = UUID(chat_request.session_id)
            conv_session = await session_handler.get_session(
                session_id_uuid,
                workspace_id=ctx_workspace_id,
                user_id=user_id,
            )
            if conv_session:
                is_existing_session = True
            else:
                logger.warning(
                    "Session %s not found in Redis, trying context lookup",
                    chat_request.session_id,
                )

        # NOTE: Context-based session lookup removed in multi-context session architecture.
        # Each "New Chat" creates a distinct session. Users can manually resume sessions
        # using the \resume command or session picker.

        # Create new session (requires workspace_id)
        if conv_session is None and ctx_workspace_id is not None:
            # Build initial context_history entry if context is provided
            initial_context_history: list[dict[str, Any]] = []
            if ctx_note_id or ctx_issue_id:
                initial_context_history.append(
                    {
                        "turn": 0,
                        "note_id": str(ctx_note_id) if ctx_note_id else None,
                        "issue_id": str(ctx_issue_id) if ctx_issue_id else None,
                        "selected_text": ctx_selected_text,
                        "selected_block_ids": ctx_selected_block_ids,
                        "timestamp": datetime.now(UTC).isoformat(),
                    }
                )

            logger.info(
                "Creating new session with initial context_history: %s", initial_context_history
            )
            conv_session = await session_handler.create_session(
                workspace_id=ctx_workspace_id,
                user_id=user_id,
                agent_name="conversation",
                context_id=context_id,  # Still set for initial context reference
                metadata={"context_history": initial_context_history},
            )
            logger.info(
                "New session created: %s", conv_session.session_id if conv_session else None
            )

    logger.info(
        "Session resolved: id=%s, existing=%s, context_id=%s, requested=%s",
        conv_session.session_id if conv_session else None,
        is_existing_session,
        context_id,
        chat_request.session_id,
    )

    # Resolve user-selected model override (AIPR-04)
    resolved_model = (
        await resolve_model_override(chat_request.model_override, ctx_workspace_id, session)
        if chat_request.model_override and ctx_workspace_id is not None
        else None
    )
    agent_input = {
        "message": chat_request.message,
        "context": ai_context,
        "session_id": str(conv_session.session_id) if conv_session else None,
        "resume_session_id": (
            str(conv_session.session_id) if is_existing_session and conv_session else None
        ),
        "user_id": str(user_id),
        "workspace_id": str(ctx_workspace_id) if ctx_workspace_id else None,
        "resolved_model": resolved_model,
        "attachment_content_blocks": attachment_content_blocks,
        "attachment_metadata": [
            {
                "attachment_id": str(a.id),
                "filename": a.filename,
                "mime_type": a.mime_type,
                "source": a.source,
                "size_bytes": a.size_bytes,
            }
            for a in attachments
        ],
    }

    async def stream_response():
        """Generate SSE stream from agent responses.

        Checks for client disconnect after each yielded chunk.
        When disconnect is detected, the generator exits which triggers
        the agent's finally block to interrupt the Claude SDK process.
        After streaming completes, persists the session to PostgreSQL.
        """
        import asyncio

        # Session recovery: re-emit pending questions/approvals for resumed sessions
        if is_existing_session and get_question_adapter().get_pending_count() > 0:
            pending_events = await get_question_adapter().get_pending_sse_events()
            for event_str in pending_events:
                yield event_str

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
                # Set RLS context on fresh session for ai_sessions table access
                await set_rls_context(fresh_db, user_id)

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


@router.post("/chat/abort", response_model=AbortResponse)
async def abort_chat(
    abort_request: AbortRequest,
    user_id: CurrentUserId,
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
            raise ForbiddenError("Access denied to this session")

    interrupted = await agent.interrupt_session(abort_request.session_id)
    return AbortResponse(
        status="interrupted" if interrupted else "not_found",
        session_id=abort_request.session_id,
    )


# ============================================================================
# Skills & Agents listing endpoints
# ============================================================================


@router.get("/skills", response_model=SkillListResponse)
async def list_skills(
    skill_registry: SkillRegistryDep,
    _current_user: CurrentUserId,
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
    Yields SSE-formatted strings from PilotSpaceAgent.
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
        resolved_model=input_data.get("resolved_model"),
    )

    ws_id = input_data.get("workspace_id")
    agent_context = AgentContext(
        workspace_id=UUID(ws_id) if ws_id else UUID("00000000-0000-0000-0000-000000000000"),
        user_id=UUID(input_data["user_id"]),
    )

    async for sse_chunk in agent.stream(chat_input, agent_context):
        yield sse_chunk
